#!/usr/bin/env python3
from __future__ import annotations

import argparse, base64, io, json, mimetypes, os, smtplib, ssl
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo
from qct_auto import compute_qct

try:
    from qct_auto import compute_qct
except ImportError:
    from scripts.qct_auto import compute_qct

import requests
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure

ROOT = Path("/opt/daily-report")


def jload(p: str) -> Any:
    with Path(p).open("r", encoding="utf-8") as f:
        return json.load(f)


def parse_env_file(path: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not path or not os.path.exists(path):
        return out
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out

def apply_env_from_file(path: str) -> None:
    """
    Load KEY=VALUE pairs into os.environ (only if key not already set).
    This is critical under sudo/systemd where interactive shell env is missing.
    """
    env = parse_env_file(path)
    for k, v in env.items():
        if not k or v is None:
            continue
        if not os.environ.get(k):
            os.environ[k] = v

def first_existing(paths: List[str]) -> Optional[str]:
    for p in paths or []:
        if not p:
            continue
        ps = p if os.path.isabs(p) else str(ROOT / p)
        if os.path.exists(ps):
            return ps
    return None


def last_friday_close(now: datetime, tz: ZoneInfo) -> datetime:
    local = now.astimezone(tz)
    back = (local.weekday() - 4) % 7
    d = local - timedelta(days=back)
    return d.replace(hour=16, minute=30, second=0, microsecond=0)


def safe_float(x: Any) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None

def resolve_path(p: str) -> str:
    if not p:
        return ""
    return p if os.path.isabs(p) else str(ROOT / p)

def load_qct_scores(path: str) -> Dict[str, Dict[str, float]]:
    """
    Load per-CID Q/C/T and optional precomputed total score from JSON.

    Accepts common shapes:
      1) {"items":[{"cid":"...", "Q":..,"C":..,"T":..,"score":..}, ...]}
      2) {"items": {"CID": {"Q":..,"C":..,"T":..,"score":..}, ...}}
      3) {"CID": {"Q":..,"C":..,"T":..,"score":..}, ...}
    """
    if not path or not os.path.exists(path):
        return {}
    try:
        obj = jload(path)
    except Exception:
        return {}

    items = obj.get("items") if isinstance(obj, dict) else None
    data = items if items is not None else obj

    def num(x: Any) -> Optional[float]:
        try:
            return float(x)
        except Exception:
            return None

    out: Dict[str, Dict[str, float]] = {}

    if isinstance(data, list):
        for it in data:
            if not isinstance(it, dict):
                continue
            cid = str(it.get("cid") or it.get("CID") or it.get("id") or "").strip()
            if not cid:
                continue
            rec: Dict[str, float] = {}
            for k in ("Q", "C", "T", "score"):
                v = num(it.get(k))
                if v is not None:
                    rec[k] = v
            if rec:
                out[cid] = rec

    elif isinstance(data, dict):
        for cid, it in data.items():
            if not cid or not isinstance(it, dict):
                continue
            rec: Dict[str, float] = {}
            for k in ("Q", "C", "T", "score"):
                v = num(it.get(k))
                if v is not None:
                    rec[k] = v
            if rec:
                out[str(cid).strip()] = rec

    return out

def fmt_yield(y: Optional[float]) -> str:
    if y is None:
        return "n/a"
    # Accept either 0.034 or 3.4
    yy = y * 100.0 if y <= 1.5 else y
    return f"{yy:.1f}%"

def get_current_yield(cid: str, reg: Dict[str, Dict[str, Any]], ov: Dict[str, Any]) -> Optional[float]:
    """
    Best-effort yield lookup.
    Priority:
      1) overrides.stocks[cid].yield or .dividend_yield
      2) registry map fields (yield / dividend_yield)
    Returns float (either fraction or percent), or None.
    """
    try:
        stock_ov = (ov.get("stocks", {}) or {}) if isinstance(ov, dict) else {}
        if isinstance(stock_ov.get(cid), dict):
            s = stock_ov[cid]
            y = safe_float(s.get("yield"))
            if y is None:
                y = safe_float(s.get("dividend_yield"))
            if y is not None:
                return y
    except Exception:
        pass

    try:
        it = reg.get(cid, {}) or {}
        y = safe_float(it.get("yield"))
        if y is None:
            y = safe_float(it.get("dividend_yield"))
        return y
    except Exception:
        return None


def load_registry_map(path: str) -> Dict[str, Dict[str, Any]]:
    root = jload(path)
    items = root.get("items") if isinstance(root, dict) else None
    items = items if isinstance(items, list) else (root if isinstance(root, list) else [])

    out: Dict[str, Dict[str, Any]] = {}
    for it in items:
        if not isinstance(it, dict):
            continue
        cid = it.get("cid") or it.get("id") or it.get("symbol") or it.get("ticker")
        if cid is None:
            continue
        out[str(cid).strip()] = it
    return out

def extract_cids_from_source(src_path: str) -> List[str]:
    """
    Extract CIDs from known input schemas.
    Supports:
      - uranium_block.json style: {"generated_at_utc": "...", "rows": [ {..."cid": "..."} ]}
      - {"items": [...]} style
      - list of dicts with cid/symbol/ticker/id
      - generic recursive scan (keys only) for cid/CID/symbol/ticker/id
    """
    try:
        obj = json.loads(Path(src_path).read_text(encoding="utf-8"))
    except Exception:
        return []

    keys = ("cid", "CID", "symbol", "ticker", "id")
    out: List[str] = []
    seen: set[str] = set()

    def add(v: Any) -> None:
        if v is None:
            return
        if isinstance(v, (int, float)):
            v = str(v)
        if isinstance(v, str):
            s = v.strip()
            if s and s not in seen:
                seen.add(s)
                out.append(s)

    def scan(x: Any) -> None:
        if isinstance(x, dict):
            for k in keys:
                if k in x:
                    add(x.get(k))
            for v in x.values():
                scan(v)
        elif isinstance(x, list):
            for v in x:
                scan(v)

    # Prefer common container schemas first (rows/items), but tolerate nested weirdness
    if isinstance(obj, dict):
        for container_key in ("rows", "items"):
            container = obj.get(container_key)
            if isinstance(container, list):
                for r in container:
                    if isinstance(r, dict):
                        # fast-path: grab first matching key if present
                        for k in keys:
                            if k in r and r.get(k) is not None:
                                add(r.get(k))
                                break
                        else:
                            # fallback: nested dicts inside row
                            scan(r)
                if out:
                    return out

    # List-of-dicts schema
    if isinstance(obj, list):
        for r in obj:
            if isinstance(r, dict):
                for k in keys:
                    if k in r and r.get(k) is not None:
                        add(r.get(k))
                        break
                else:
                    scan(r)
        if out:
            return out

    # Last resort: recursive scan on whole object
    scan(obj)
    return out

def _norm_cid(s: Any) -> str:
    return str(s or "").strip()

def build_canonical_map(ov: Dict[str, Any]) -> Dict[str, str]:
    """
    Optional overrides-driven canonicalisation to collapse dual listings.
    In overrides JSON, support either:
      - top-level {"canonical": {"UROY.US": "URC.TO", ...}}
      - or {"dedupe": {"canonical": {...}}}
    Returns mapping src_cid -> canonical_cid.
    """
    if not isinstance(ov, dict):
        return {}

    cand = ov.get("canonical")
    if not isinstance(cand, dict):
        ded = ov.get("dedupe", {})
        cand = ded.get("canonical") if isinstance(ded, dict) else None
    if not isinstance(cand, dict):
        return {}

    out: Dict[str, str] = {}
    for k, v in cand.items():
        ks = _norm_cid(k)
        vs = _norm_cid(v)
        if ks and vs:
            out[ks] = vs
    return out

def canonicalise_cid(cid: str, canon: Dict[str, str]) -> str:
    """
    Follow canonical redirects (with loop protection).
    """
    cur = _norm_cid(cid)
    for _ in range(6):
        nxt = _norm_cid(canon.get(cur))
        if not nxt or nxt == cur:
            break
        cur = nxt
    return cur

def choose_preferred_listing(
    cids: List[str],
    canon_cid: str,
    reg: Dict[str, Dict[str, Any]],
    stock_ov: Dict[str, Any],
    preferred_suffixes: List[str],
) -> str:
    """
    Pick which listing to keep among duplicates that canonicalise to the same issuer.
    Preference order:
      1) If any candidate is explicitly "owned" in overrides, keep that one
      2) Prefer exchanges via preferred_suffixes (e.g. [".TO", ".LSE", ".US"])
      3) If canonical CID appears in the group, keep it
      4) Otherwise keep the first candidate (stable order)
    """
    # 1) owned_by in overrides wins
    def owned(cid: str) -> bool:
        o = stock_ov.get(cid, {}) if isinstance(stock_ov, dict) else {}
        owners = o.get("owned_by", [])
        return isinstance(owners, list) and len(owners) > 0

    owned_cands = [x for x in cids if owned(x)]
    if owned_cands:
        return owned_cands[0]

    # 2) preferred exchange suffixes
    for suf in preferred_suffixes or []:
        for x in cids:
            if x.upper().endswith(suf.upper()):
                return x

    # 3) canonical itself
    for x in cids:
        if _norm_cid(x) == _norm_cid(canon_cid):
            return x

    return cids[0] if cids else canon_cid

def dedupe_rated_cids(
    rated: List[str],
    reg: Dict[str, Dict[str, Any]],
    ov: Dict[str, Any],
    theme_key: str,
) -> List[str]:
    """
    Collapse dual listings using overrides-driven canonical map.
    Keeps original order as much as possible (first occurrence wins within preference rules).
    """
    stock_ov = (ov.get("stocks", {}) or {}) if isinstance(ov, dict) else {}
    canon = build_canonical_map(ov)

    # Theme-specific preferred suffix ordering (overrideable)
    # Defaults: nuclear prefers TSX then LSE then US; alt_power prefers US then LSE then TSX.
    pref: List[str] = []
    if isinstance(ov, dict):
        ded = ov.get("dedupe", {}) or {}
        if isinstance(ded, dict):
            theme_prefs = (ded.get("preferred_suffixes", {}) or {})
            if isinstance(theme_prefs, dict):
                pref = theme_prefs.get(theme_key, []) or []
    if not pref:
        pref = [".TO", ".LSE", ".US"] if theme_key == "nuclear" else [".US", ".LSE", ".TO"]

    # Group by canonical issuer
    groups: Dict[str, List[str]] = {}
    order: List[str] = []
    for cid in rated:
        c = _norm_cid(cid)
        if not c:
            continue
        cc = canonicalise_cid(c, canon)
        if cc not in groups:
            groups[cc] = []
            order.append(cc)
        groups[cc].append(c)

    # Choose one per group
    out: List[str] = []
    for cc in order:
        cids = groups.get(cc, [])
        chosen = choose_preferred_listing(cids, cc, reg, stock_ov, pref)
        if chosen:
            out.append(chosen)
    return out

def cid_to_eodhd_symbol(cid: str) -> str:
    """
    Map internal CID -> EODHD symbol.
    - LSE: internal ".L" -> EODHD ".LSE"
    - Otherwise: return as-is
    """
    c = (cid or "").strip()
    if not c:
        return c

    # If already has a known vendor suffix, keep it.
    if c.endswith((".LSE", ".US", ".TO", ".V", ".SW", ".PA", ".DE", ".AS", ".MI")):
        return c

    # Internal shorthand -> vendor convention
    if c.endswith(".L"):
        return c[:-2] + ".LSE"

    return c

def fetch_eodhd_bars(symbol: str, token: str, start_date: str) -> Tuple[List[dict], str]:
    """
    Returns bars as: [{"close": float, "volume": float}, ...] (oldest->newest) plus basis label.
    """
    import requests

    url = f"https://eodhd.com/api/eod/{symbol}"
    params = {
        "api_token": token,
        "fmt": "json",
        "from": start_date,
        "period": "d",
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json() or []

    bars: List[dict] = []
    basis = "close"
    for row in data:
        # Prefer adjusted_close if present, else close
        ac = row.get("adjusted_close", None)
        c = row.get("close", None)
        px = ac if ac is not None else c
        if ac is not None:
            basis = "adj_close"
        try:
            close = float(px)
        except Exception:
            continue
        try:
            vol = float(row.get("volume") or 0.0)
        except Exception:
            vol = 0.0
        if close > 0:
            bars.append({"close": close, "volume": vol})
    return bars, basis


def fetch_eodhd_series(symbol: str, token: str, start_date: str) -> Tuple[List[float], str]:
    bars, basis = fetch_eodhd_bars(symbol, token, start_date)
    series = [b["close"] for b in bars]
    return series, basis

def get_series(cid: str, asof_local: datetime, days: int, keep: int) -> Tuple[List[float], str]:
    # Token lookup: env first, then local env file for sudo/systemd runs
    token = os.environ.get("EODHD_API_TOKEN") or os.environ.get("EODHD_API_KEY") or ""
    if not token:
        for p in ("/opt/daily-report/.env_market", "/opt/daily-report/.env", "/opt/daily-report/.env_local"):
            if os.path.exists(p):
                try:
                    env = parse_env_file(p)
                    token = env.get("EODHD_API_TOKEN") or env.get("EODHD_API_KEY") or ""
                    if token:
                        break
                except Exception:
                    pass

    if not token:
        return [], "NO_TOKEN"

    start = (asof_local - timedelta(days=days)).date().isoformat()
    sym = cid_to_eodhd_symbol(cid)
    try:
        bars, basis = fetch_eodhd_bars(sym, token, start)
        series = [b["close"] for b in bars]
        s = series[-keep:] if len(series) > keep else series
        return s, (basis if s else "NO_DATA")
    except Exception:
        return [], "NO_DATA"

def _eodhd_token() -> str:
    # Prefer runtime env, but allow a file fallback for ubuntu/systemd runs.
    tok = (os.environ.get("EODHD_API_TOKEN") or os.environ.get("EODHD_API_KEY") or "").strip()
    if tok:
        return tok

    # Optional: /opt/daily-report/.env_eodhd containing EODHD_API_TOKEN=... or EODHD_API_KEY=...
    p = ROOT / ".env_eodhd"
    try:
        if p.exists():
            for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k in ("EODHD_API_TOKEN", "EODHD_API_KEY") and v:
                    return v
    except Exception:
        pass
    return ""


def get_180d_series(cid: str, asof_local: datetime) -> Tuple[List[float], str]:
    return get_series(cid, asof_local, days=210, keep=180)


def get_1y_series(cid: str, asof_local: datetime) -> Tuple[List[float], str]:
    return get_series(cid, asof_local, days=400, keep=252)

def normalise_100(vals: List[float]) -> List[float]:
    if not vals or not vals[0]:
        return vals
    b = vals[0]
    return [100.0 * (v / b) for v in vals]


def spark_data_uri(vals: List[float], width_px: int = 120, height_px: int = 36) -> str:
    if not vals or len(vals) < 2:
        return ""
    up = vals[-1] >= vals[0]
    col = "#16a34a" if up else "#dc2626"
    fig = Figure(figsize=(width_px / 100.0, height_px / 100.0), dpi=100)
    fig.patch.set_alpha(0.0)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    ax.set_facecolor((1, 1, 1, 0))
    ax.plot(range(len(vals)), vals, linewidth=2.2, color=col, solid_capstyle="round")
    ax.margins(x=0.02, y=0.15)
    buf = io.BytesIO()
    FigureCanvas(fig).print_png(buf)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"<img src='data:image/png;base64,{b64}' width='{width_px}' height='{height_px}' style='display:block' alt='spark' />"


def pct_rank(values: List[float], x: float) -> float:
    if not values:
        return 50.0
    vals = sorted(values)
    le = sum(1 for v in vals if v <= x)
    return 100.0 * le / len(vals)


def load_manual_scores(path: str) -> Dict[str, Dict[str, float]]:
    if not path or not os.path.exists(path):
        return {}
    obj = jload(path)
    items = obj.get("items", {}) if isinstance(obj, dict) else {}
    out: Dict[str, Dict[str, float]] = {}
    if isinstance(items, dict):
        for cid, sc in items.items():
            if isinstance(sc, dict):
                out[cid] = {"Q": float(sc.get("Q", 50.0)), "C": float(sc.get("C", 50.0))}
    return out


def load_overrides(path: str) -> Dict[str, Any]:
    if path and os.path.exists(path):
        try:
            return jload(path) or {}
        except Exception:
            return {}
    return {}

@dataclass
class Row:
    cid: str
    name: str
    score: float
    q: float
    c: float
    t: float
    q_share: str
    c_share: str
    t_share: str
    qct_src: str = ""
    spark: str = ""
    close: str = "n/a"
    wow: str = "n/a"
    mom30: str = "n/a"
    mom180: str = "n/a"
    tr1y: str = "n/a"
    basis: str = "NO_DATA"
    signal: str = ""
    action: str = ""
    why: List[str] = None
    owners: List[str] = None
    first_buy: str = "n/a"


def pill(text: str) -> str:
    return (
        "<span style='display:inline-block;padding:3px 8px;border:1px solid #d7d7d7;"
        "border-radius:999px;font-size:12px;line-height:16px;margin:0 6px 6px 0;"
        "white-space:nowrap;color:#222;background:#fff;'>" + text + "</span>"
    )

def stock_card(rank: int, r: Row) -> str:
    owners_html = (" " + pill("Owned " + "/".join(r.owners))) if r.owners else ""
    why_html = ""
    if r.why:
        why_html = "<div style='font-size:12px;color:#444;margin-top:6px'>" + "<br>".join(r.why[:4]) + "</div>"
    meta_html = "<div style='font-size:12px;color:#555;margin-top:6px'>Close: <b>%s</b> &nbsp;|&nbsp; WoW: <b>%s</b></div>" % (
        r.close, r.wow
    )

    pills = [
        pill(f"Score {r.score:.0f}"),
        pill(f"Mom 30D {r.mom30}"),
        pill(f"Mom 180D {r.mom180}"),
        pill(f"TR 1Y {r.tr1y}"),
        pill(f"Signal {r.signal}"),
        pill(f"First buy {r.first_buy}"),
        pill(f"Action {r.action}"),
        pill(f"Basis {r.basis}"),
    ]

    # Only show Q/C/T when populated from a real source (auto or SoT override)
    if getattr(r, "qct_src", ""):
        pills.append(pill(f"Q/C/T {r.q:.0f}/{r.c:.0f}/{r.t:.0f}"))
        pills.append(pill(f"Q/C/T shares {r.q_share}/{r.c_share}/{r.t_share}"))

    return (
        "<table role='presentation' width='100%' cellspacing='0' cellpadding='0' "
        "style='border:1px solid #e6e6e6;border-radius:12px;margin:10px 0;background:#fff'>"
        "<tr><td style='padding:10px 12px;vertical-align:top'>"
        f"<div style='font-size:14px;font-weight:600;color:#111'>#{rank} {r.name} ({r.cid}){owners_html}</div>"
        f"{why_html}{meta_html}"
        "</td><td align='right' style='padding:10px 12px;vertical-align:top'>"
        f"{r.spark}"
        "</td></tr><tr><td colspan='2' style='padding:0 12px 10px 12px'>"
        + "".join(pills)
        + "</td></tr></table>"
    )

def send_via_smtp(env: Dict[str, str], subject: str, html_body: str) -> None:
    host = (env.get("SMTP_HOST") or "").strip()
    port = int((env.get("SMTP_PORT") or "587").strip())
    user = (env.get("SMTP_USER") or "").strip()
    pw = (env.get("SMTP_PASS") or "").strip()
    mail_from = (env.get("EMAIL_FROM") or "").strip()
    mail_to = (env.get("EMAIL_TO") or "").strip()
    if not (host and user and pw and mail_from and mail_to):
        raise SystemExit("Missing SMTP_* or EMAIL_FROM/EMAIL_TO in .env_email")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = mail_from
    msg["To"] = mail_to
    msg.set_content("HTML email required.")
    msg.add_alternative(html_body, subtype="html")

    logo_path = (env.get("LOGO_PATH") or "").strip() or str(ROOT / "assets/logo.png")
    try:
        lp = Path(logo_path)
        if lp.exists():
            data = lp.read_bytes()
            ctype, _ = mimetypes.guess_type(str(lp))
            subtype = (ctype.split("/", 1)[1] if ctype and ctype.startswith("image/") else "png") or "png"
            html_part = msg.get_body(preferencelist=("html",))
            if html_part is not None:
                html_part.add_related(data, maintype="image", subtype=subtype, cid="<logo>", filename=lp.name, disposition="inline")
    except Exception:
        pass

    context = ssl.create_default_context()
    with smtplib.SMTP(host, port) as s:
        s.starttls(context=context)
        s.login(user, pw)
        s.send_message(msg)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="/opt/daily-report/in/weekly_nuclear_altpower_config.json")
    ap.add_argument("--asof", default="", help="Override Friday close date YYYY-MM-DD")
    ap.add_argument("--send", action="store_true")
    args = ap.parse_args()

    cfg = jload(args.config)

    # Ensure data tokens exist when running under sudo/systemd (ubuntu user)
    candidates = [
        str(cfg.get("data_env_file") or ""),
        str(ROOT / ".env_data"),
        str((cfg.get("email") or {}).get("smtp_env_file") or ""),
    ]
    for p in candidates:
        if p and os.path.exists(p):
            apply_env_from_file(p)
            break

    tz = ZoneInfo(cfg["timezone"])
    asof_local = (
        datetime.fromisoformat(args.asof).replace(tzinfo=tz, hour=16, minute=30)
        if args.asof
        else last_friday_close(datetime.now(tz), tz)
    )
    asof_date = asof_local.date().isoformat()

    reg = load_registry_map(cfg["registry_path"])
    ov = load_overrides(cfg.get("overrides_path", ""))

    sleeve = ov.get("sleeve", {}) or {}
    title = str(sleeve.get("title", sleeve.get("label", "")) or "").strip()
    proposition = str(sleeve.get("proposition", "") or "").strip()

    ranking = cfg.get("ranking") or {}
    w = ranking.get("weights") or {"Q": 0.4, "C": 0.4, "T": 0.2}
    core_n = int(ranking.get("core_n", 10))
    next_n = int(ranking.get("next_n", 5))
    min_include = float(ranking.get("min_score_include", 0.0))
    manual = load_manual_scores(str(ranking.get("manual_scores_path") or "").strip())

    gates = (cfg.get("signals", {}).get("gates", {}) or {})
    buy_score_min = float(gates.get("buy_score_min", 70))
    top10_median_min = float(gates.get("buy_theme_top10_median_min", 65))
    breadth_min = int(gates.get("buy_theme_breadth_min", 5))
    buy_weeks = int(cfg.get("signals", {}).get("buy_top3_weeks", 2))

    FONT_STACK = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,'Apple Color Emoji','Segoe UI Emoji','Segoe UI Symbol'"

    html: List[str] = [
        "<!doctype html><html><head>",
        "<meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1.0'>",
        "<meta name='color-scheme' content='light dark'>",
        "<meta name='supported-color-schemes' content='light dark'>",
        "<style>"
        ".logo-pill{display:inline-block;background:#fff;border-radius:12px;padding:8px 12px;line-height:0}"
        ".logo-img{display:block;border:0;outline:none;text-decoration:none;height:auto}"
        "summary{cursor:pointer}"
        "</style>",
        "</head><body>",
        (
            f'<div style="font-family:{FONT_STACK};'
            "font-size:14px;line-height:1.35;color:#111;"
            "-webkit-text-size-adjust:100%;font-variant-numeric:tabular-nums;\">"
        ),
        "<div style='margin:0 0 10px 0;'>"
        "<span class='logo-pill'>"
        "<img class='logo-img' src='cid:logo' alt='Kairos' width='160' />"
        "</span></div>",
        f"<h2 style='margin:0 0 6px 0'>{(title + ' | ') if title else ''}Friday Close: {asof_date}</h2>",
    ]

    if proposition:
        html.append(
            f"<div style='font-size:13px;color:#333;margin:0 0 10px 0'>{proposition}</div>"
        )

    html.append(
        "<div style='font-size:12px;color:#666;margin:0 0 8px 0'>"
        "Sparkline = last 180 trading days (Friday-close series)."
        "</div>"
    )

    actions_buy: List[str] = []
    total_rated = 0

    s1y_cache: Dict[str, List[float]] = {}

    def get_1y_cached(cid: str) -> List[float]:
        if cid in s1y_cache:
            return s1y_cache[cid]
        s, _ = get_series(cid, asof_local, days=400, keep=252)
        s1y_cache[cid] = s
        return s

    def pct_change(series: List[float], idx: int) -> Optional[float]:
        """Percent change from series[idx] to series[-1], or None if invalid."""
        if not series or len(series) < 2:
            return None
        try:
            base = float(series[idx])
            last = float(series[-1])
        except Exception:
            return None
        if base == 0.0:
            return None
        return (last / base) - 1.0

    def render_buy_gate_pills(
        *,
        buy_gate: bool,
        top10_median: float,
        top10_median_min: float,
        breadth: int,
        breadth_min: int,
        buy_score_min: float,
        yield_pill: str = "",
    ) -> str:
        return (
            "<div style='font-size:12px;color:#444;margin:0 0 8px 0'>"
            + (yield_pill + " " if yield_pill else "")
            + pill("BUY gate " + ("ENABLED" if buy_gate else "DISABLED"))
            + pill(f"Top10 median {top10_median:.0f} vs {top10_median_min:.0f}")
            + pill(f"Breadth {breadth} vs {breadth_min}")
            + pill(f"Score min {buy_score_min:.0f}")
            + "</div>"
        )

    for theme_key in ("nuclear", "alt_power"):
        tcfg = cfg["themes"][theme_key]
        label = tcfg.get("label", theme_key)

        html.append(f"<hr><h3 style='margin:14px 0 6px 0'>{label}</h3>")
        candidate_sources: List[str] = []
        wl_sources = tcfg.get("watchlist_sources") or []
        fw_sources = tcfg.get("followed_sources") or []
        fallback_sources = tcfg.get("sources") or tcfg.get("source") or []

        for v in (wl_sources, fw_sources, fallback_sources):
            if isinstance(v, (str, Path)):
                candidate_sources.append(str(v))
            elif isinstance(v, list):
                candidate_sources.extend([str(x) for x in v if x])

        src: Optional[str] = None
        rated_raw: List[str] = []
        for p in candidate_sources:
            ps = p if os.path.isabs(p) else str(ROOT / p)
            if not os.path.exists(ps):
                continue
            cids = extract_cids_from_source(ps)
            if cids:
                src = ps
                rated_raw = cids
                break

        if not src:
            raise SystemExit(
                f"[ERR] no usable sources for theme '{theme_key}'. "
                "All candidate sources were missing or produced zero CIDs."
            )

        rated = dedupe_rated_cids(rated_raw, reg, ov, theme_key)
        dup_removed = max(0, len(rated_raw) - len(rated))
        total_rated += len(rated)

        theme_ov = (ov.get("themes", {}) or {}).get(theme_key, {}) or {}
        subs = theme_ov.get("subthemes", []) or []

        def _proxy_cids(x):
            """Accept either ['CID', ...] or [{'label':..., 'cid':'CID'}, ...]."""
            if not x:
                return []
            out = []
            for it in x:
                if isinstance(it, str):
                    s = it.strip()
                    if s:
                        out.append(s)
                elif isinstance(it, dict):
                    s = str(it.get("cid") or "").strip()
                    if s:
                        out.append(s)
            return out

        # Prefer per-theme proxies, else fall back to top-level (your JSON uses top-level keys).
        proxies = _proxy_cids(
            theme_ov.get("uranium_proxies")
            or ov.get("uranium_proxies")
            or []
        )
        ap_proxies = _proxy_cids(
            theme_ov.get("alt_power_proxies")
            or ov.get("alt_power_proxies")
            or []
        )

        stock_ov = ov.get("stocks", {}) or {}

        series_180: Dict[str, List[float]] = {}
        basis_180: Dict[str, str] = {}
        returns_180: Dict[str, float] = {}

        # Build 180D series + 180D returns first (so T is real)
        for cid in rated:
            s180, basis = get_series(cid, asof_local, days=210, keep=180)
            series_180[cid] = s180
            basis_180[cid] = basis
            r180 = 0.0
            if s180 and len(s180) >= 2 and s180[0]:
                r180 = (float(s180[-1]) / float(s180[0])) - 1.0
            returns_180[cid] = r180

        # Trend rank (T): percentile rank of 180D return within this week's rated universe
        all_r = list(returns_180.values())
        trend = {cid: pct_rank(all_r, returns_180.get(cid, 0.0)) for cid in rated}

        # Optional SoT Q/C/T feed (can override Q/C/T and/or score)
        scores_path = resolve_path(str(tcfg.get("scores_path") or "").strip())
        qct_map = load_qct_scores(scores_path) if scores_path else {}
        if scores_path and not qct_map:
            raise SystemExit(
                f"[ERR] scores_path configured for {theme_key} but produced zero scores: {scores_path}"
            )
        scored: List[Tuple[str, float, float, float, float]] = []
        for cid in rated:
            base_q = float(manual.get(cid, {}).get("Q", 50.0))
            base_c = float(manual.get(cid, {}).get("C", 50.0))
            base_t = float(trend.get(cid, 50.0))

            rec = qct_map.get(cid, {}) if isinstance(qct_map, dict) else {}
            qv = float(rec.get("Q", base_q))
            cv = float(rec.get("C", base_c))
            tv = float(rec.get("T", base_t))

            if "score" in rec:
                score = float(rec["score"])
            else:
                score = (
                    float(w.get("Q", 0.4)) * qv
                    + float(w.get("C", 0.4)) * cv
                    + float(w.get("T", 0.2)) * tv
                )

            scored.append((cid, score, qv, cv, tv))

        scored.sort(key=lambda x: x[1], reverse=True)

        # BUY gate (computed AFTER scored exists)
        top10 = scored[: min(core_n, len(scored))]
        top10_scores = sorted([x[1] for x in top10])
        if top10_scores:
            mid = len(top10_scores) // 2
            top10_median = (
                top10_scores[mid]
                if len(top10_scores) % 2
                else 0.5 * (top10_scores[mid - 1] + top10_scores[mid])
            )
        else:
            top10_median = 0.0

        breadth = sum(1 for _cid, s, *_ in scored if s >= buy_score_min)
        buy_gate = (top10_median >= top10_median_min) and (breadth >= breadth_min)

        # Rated universe line + dedupe note
        rated_line = (
            f"<div style='font-size:12px;color:#444;margin:0 0 6px 0'>"
            f"Rated universe this week: <b>{len(rated)}</b>"
        )
        if dup_removed:
            rated_line += f" <span style='color:#777'>(removed {dup_removed} duplicates)</span>"
        rated_line += "</div>"
        html.append(rated_line)

        if subs:
            html.append(
                "<div style='font-size:12px;color:#444;margin:0 0 8px 0'>"
                "<b>Subthemes:</b><ul style='margin:4px 0 0 18px'>"
            )
            for s in subs[:4]:
                html.append(f"<li><b>{s.get('title','')}</b>: {s.get('text','')}</li>")
            html.append("</ul></div>")

        # Yield pill (stable): use the top-scored CID this week
        top_cid = scored[0][0] if scored else None
        yld = get_current_yield(top_cid, reg, ov) if top_cid else None
        yield_pill = pill(f"Yield {fmt_yield(yld)}") if yld is not None else ""

        html.append(
            render_buy_gate_pills(
                buy_gate=buy_gate,
                top10_median=top10_median,
                top10_median_min=top10_median_min,
                breadth=breadth,
                breadth_min=breadth_min,
                buy_score_min=buy_score_min,
                yield_pill=yield_pill,
            )
        )

        # Benchmarks / proxies
        if theme_key == "alt_power" and ap_proxies:
            series_list: List[List[float]] = []
            used: List[str] = []
            for pcid in ap_proxies[:2]:
                s1y, _basis = get_series(pcid, asof_local, days=400, keep=252)
                if s1y:
                    series_list.append(normalise_100(s1y))
                    used.append(pcid)
            if series_list:
                m = min(len(x) for x in series_list)
                combo = [sum(x[-m + i] for x in series_list) / len(series_list) for i in range(m)]
                html.append("<div style='margin:8px 0 10px 0'>")
                html.append(
                    "<div style='font-size:12px;color:#444'>"
                    f"<b>Alt-Power proxy (1Y, normalised 100):</b> {', '.join(used)}"
                    "</div>"
                )
                html.append(spark_data_uri(combo, 160, 40))
                html.append("</div>")
        if theme_key == "nuclear" and proxies:
            for label2, days, keep in (("180D", 210, 180), ("1Y", 400, 252)):
                series_list2: List[List[float]] = []
                used2: List[str] = []
                for pcid in proxies[:2]:
                    s, _ = get_series(pcid, asof_local, days=days, keep=keep)
                    if s:
                        series_list2.append(normalise_100(s))
                        used2.append(pcid)
                if series_list2:
                    m = min(len(x) for x in series_list2)
                    combo = [
                        sum(x[-m + i] for x in series_list2) / len(series_list2) for i in range(m)
                    ]
                    top_margin = "8px" if label2 == "180D" else "0"
                    bottom_margin = "6px" if label2 == "180D" else "10px"
                    html.append(f"<div style='margin:{top_margin} 0 {bottom_margin} 0'>")
                    html.append(
                        "<div style='font-size:12px;color:#444'>"
                        f"<b>Uranium proxy ({label2}, normalised 100):</b> {', '.join(used2)}"
                        "</div>"
                    )
                    html.append(spark_data_uri(combo, 160, 40))
                    html.append("</div>")

        # --- Auto Q/C/T (computed once per theme sleeve) ---
        from qct_auto import compute_qct

        def _resolve_eodhd_token() -> str:
            tok = (os.environ.get("EODHD_API_TOKEN") or os.environ.get("EODHD_API_KEY") or "").strip()
            if tok:
                return tok
            for p in ("/opt/daily-report/.env_market", "/opt/daily-report/.env", "/opt/daily-report/.env_local"):
                if os.path.exists(p):
                    try:
                        env2 = parse_env_file(p)
                        tok = (env2.get("EODHD_API_TOKEN") or env2.get("EODHD_API_KEY") or "").strip()
                        if tok:
                            return tok
                    except Exception:
                        pass
            return ""

        qct_map: Dict[str, Dict[str, float]] = {}
        tok = _resolve_eodhd_token()
        if tok and scored:
            start = (asof_local - timedelta(days=220)).date().isoformat()
            bars_by_cid: Dict[str, List[dict]] = {}
            for _cid, _sc, _qv, _cv, _tv in scored:
                sym = cid_to_eodhd_symbol(_cid)
                try:
                    bars, _basis = fetch_eodhd_bars(sym, tok, start)
                    bars = bars[-200:] if len(bars) > 200 else bars
                    if bars:
                        bars_by_cid[_cid] = bars
                except Exception:
                    pass
            if bars_by_cid:
                qct_map = compute_qct(bars_by_cid)

        def mk_row(
            rank: int, cid: str, score: float, qv: float, cv: float, tv: float, streak: int
        ) -> Row:
            it = reg.get(cid, {}) or {}
            o = stock_ov.get(cid, {}) if isinstance(stock_ov, dict) else {}
            name = str(o.get("display_name") or it.get("name") or cid).strip()

            qct = qct_map.get(cid) if isinstance(qct_map, dict) else None
            qct_src = ""
            q_share = c_share = t_share = ""

            if qct:
                score = float(qct.get("score", score))
                qv = float(qct.get("q", qv))
                cv = float(qct.get("c", cv))
                tv = float(qct.get("t", tv))
                q_share = f'{float(qct.get("q_share", 0.0)):.0f}%'
                c_share = f'{float(qct.get("c_share", 0.0)):.0f}%'
                t_share = f'{float(qct.get("t_share", 0.0)):.0f}%'
                qct_src = "auto"

            # If auto Q/C/T populated, keep its shares.
            # Otherwise compute shares from the manual qv/cv/tv + weights.
            if not qct_src:
                q_contrib = float(w.get("Q", 0.4)) * qv
                c_contrib = float(w.get("C", 0.4)) * cv
                t_contrib = float(w.get("T", 0.2)) * tv
                tot = (q_contrib + c_contrib + t_contrib) or 1.0
                q_share = f"{(100*q_contrib/tot):.0f}%"
                c_share = f"{(100*c_contrib/tot):.0f}%"
                t_share = f"{(100*t_contrib/tot):.0f}%"

            s180 = series_180.get(cid, [])
            basis = basis_180.get(cid, "NO_DATA")
            spark = spark_data_uri(s180)

            close, wow = "n/a", "n/a"
            if s180 and len(s180) >= 2:
                close = f"{s180[-1]:.2f}"
                if len(s180) >= 6 and s180[-6]:
                    wow = f"{((s180[-1] / s180[-6]) - 1.0):+.1%}"

            p30 = pct_change(s180, -31) if (s180 and len(s180) >= 31) else None
            mom30 = f"{p30:+.0%}" if p30 is not None else "n/a"

            p180 = pct_change(s180, 0) if (s180 and len(s180) >= 2) else None
            mom180 = f"{p180:+.0%}" if p180 is not None else "n/a"

            s1y = get_1y_cached(cid)
            p1y = pct_change(s1y, 0) if (s1y and len(s1y) >= 2) else None
            tr1y = f"{p1y:+.0%}" if p1y is not None else "n/a"

            first_buy = "n/a"
            if rank <= 3 and score < buy_score_min:
                first_buy = "BELOW TARGET"
            elif buy_gate and rank <= 3 and score >= buy_score_min:
                first_buy = "NOW" if streak >= buy_weeks else f"W{max(1, streak)}/{buy_weeks}"

            owners = o.get("owned_by", []) if isinstance(o.get("owned_by", []), list) else []
            why = o.get("why", []) if isinstance(o.get("why", []), list) else []
            if not why:
                why = ["Add blurb in overrides.", "What it is + why it can win (2 lines)."]
            signal = f"TOP3_W{streak}" if rank <= 3 else "OK"
            action = (
                "BUY/ADD"
                if (buy_gate and rank <= 3 and score >= buy_score_min and streak >= buy_weeks)
                else "HOLD"
            )

            return Row(
                cid=cid,
                name=name,
                score=score,
                q=qv,
                c=cv,
                t=tv,
                q_share=q_share,
                c_share=c_share,
                t_share=t_share,
                qct_src=qct_src,
                spark=spark,
                close=close,
                wow=wow,
                mom30=mom30,
                mom180=mom180,
                tr1y=tr1y,
                basis=basis,
                signal=signal,
                action=action,
                why=why,
                owners=owners,
                first_buy=first_buy,
            )

        core = [x for x in scored[:core_n] if x[1] >= min_include]
        nxt = [x for x in scored[core_n : core_n + next_n] if x[1] >= min_include]

        html.append("<h4 style='margin:12px 0 6px 0'>Core 10</h4>")
        streak = 1  # placeholder: wire to history later

        for i, (cid, sc, qv, cv, tv) in enumerate(core, start=1):
            r = mk_row(i, cid, sc, qv, cv, tv, streak if i <= 3 else 0)
            html.append(stock_card(i, r))
            if r.action == "BUY/ADD":
                actions_buy.append(cid)

        html.append("<details style='margin:6px 0 0 0'>")
        html.append(
            "<summary style='font-weight:600;margin:12px 0 6px 0'>Next 5 (click to expand)</summary>"
        )
        for j, (cid, sc, qv, cv, tv) in enumerate(nxt, start=core_n + 1):
            html.append(stock_card(j, mk_row(j, cid, sc, qv, cv, tv, 0)))
        html.append("</details>")

    tot_line = (
        "<div style='font-size:12px;color:#444;margin:0 0 10px 0'>"
        f"Rated universe (total): <b>{total_rated}</b>"
        "</div>"
    )
    for idx, line in enumerate(html):
        if "Sparkline = last 180 trading days" in line:
            html.insert(idx + 1, tot_line)
            break
    else:
        html.insert(0, tot_line)

    html.extend(
        [
            "<hr><h3 style='margin:14px 0 6px 0'>Actions this week</h3>",
            "<ul style='margin:6px 0 0 18px'><li><b>BUY/ADD</b>: %s</li></ul>"
            % (", ".join(actions_buy) if actions_buy else "—"),
            "<hr><div style='font-size:11px;color:#666;margin-top:8px'><b>Pill legend:</b> "
            "Mom 30D=% change vs ~30 trading days ago; "
            "Mom 180D=% change vs ~180 trading days ago; "
            "WoW=vs ~5 trading days ago; "
            "TR 1Y=% change over ~252 trading days; "
            "Basis TR_ADJ uses adjusted_close else PRICE.</div>",
            "</div></body></html>",
        ]
    )

    out_dir = cfg["out_dir"]
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    out_html = Path(out_dir) / "weekly_nuclear_altpower.html"
    out_html.write_text("\n".join(html), encoding="utf-8")
    print("Wrote:", str(out_html))

    subject = f"{cfg['email']['subject_prefix']} | Friday Close: {asof_date}"
    if args.send:
        env = parse_env_file(cfg["email"]["smtp_env_file"])
        send_via_smtp(env, subject, "\n".join(html))
        print("Sent:", subject)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())














