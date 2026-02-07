#!/usr/bin/env python3
from __future__ import annotations

import argparse, base64, io, json, mimetypes, os, smtplib, ssl, sys, subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo
from scripts.lib_scored_block import load_scored_block, scored_tuples_from_rows

try:
    from qct_auto import compute_qct
except ImportError:
    from scripts.qct_auto import compute_qct

import requests
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure


# --- gated uranium regeneration (auto) ---
def _regen_uranium_gated():
    """Regenerate out/data/uranium_block.gated.json from in/uranium_block.json (atomic).
    This prevents stale gated artifacts from contaminating weekly runs.
    """
    import json
    from datetime import datetime, timezone
    from pathlib import Path
    from src.utils.atomic_write import write_json_atomic

    root = Path(__file__).resolve().parents[1]
    src = root / "in/uranium_block.json"
    dst = root / "out/data/uranium_block.gated.json"

    obj = json.loads(src.read_text(encoding="utf-8"))
    rows = obj.get("rows", [])
    if not isinstance(rows, list):
        raise SystemExit("ERROR: in/uranium_block.json expected {rows:[...]}")

    out = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rows": rows,
    }
    write_json_atomic(dst, out, indent=2, ensure_ascii=False)
    print(f"[OK] regen gated uranium -> {dst} rows={len(rows)}")

# --- end gated uranium regeneration (auto) ---

# --- gated alt_power regeneration (auto) ---
def _regen_alt_power_gated():
    """Regenerate out/data/alt_power_block.gated.json from in/alt_power_meta.json (atomic).
    This prevents stale alt-power gated artifacts from contaminating weekly runs.
    """
    from datetime import datetime, timezone
    from pathlib import Path
    import json
    from src.utils.atomic_write import write_json_atomic

    root = Path(__file__).resolve().parents[1]
    src = root / "in/alt_power_meta.json"
    dst = root / "out/data/alt_power_block.gated.json"

    if not src.exists():
        raise SystemExit(f"ERROR: missing {src}")

    rows = json.loads(src.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise SystemExit(f"ERROR: {src} expected JSON list")

    ids = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        if int(r.get("enabled", 0) or 0) != 1:
            continue

        # prefer your canonical market id used everywhere else
        for k in ("eodhd", "symbol", "id", "cid"):
            v = r.get(k)
            if isinstance(v, str) and v.strip():
                ids.append(v.strip().upper())
                break

    # de-dup preserve order
    seen = set()
    ids = [x for x in ids if not (x in seen or seen.add(x))]

    out = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rows": [{"cid": x, "name": x, "nuclear_category": "Alt Power"} for x in ids],
    }

    write_json_atomic(dst, out, indent=2, ensure_ascii=False)
    print(f"[OK] regen gated alt_power -> {dst} rows={len(ids)}")
# --- end gated alt_power regeneration (auto) ---


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
    # Normalize to 100 at a sane baseline.
    # Guard against 0/None/tiny baselines and unit mismatches that cause ridiculous spikes.
    if not vals or len(vals) < 2:
        return vals

    # pick first "sane" positive value as baseline
    b = None
    for v in vals[:10]:
        try:
            fv = float(v)
        except Exception:
            continue
        if fv > 1e-6:
            b = fv
            break
    if b is None:
        return vals

    out = [100.0 * (float(v) / b) for v in vals]

    # clip absurd outliers (keeps charts usable; doesn't hide data in the underlying series)
    # If you see clips often, the data feed is inconsistent and should be fixed upstream.
    cap = 500.0
    return [cap if x > cap else x for x in out]

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

from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Row:
    cid: str
    name: str
    score: float

    # canonical internal fields
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

    def __post_init__(self) -> None:
        # avoid None lists leaking into JSON rendering
        if self.why is None:
            self.why = []
        if self.owners is None:
            self.owners = []

# Debug rows MUST reflect what we actually render (Row objects),
# otherwise you’ll keep staring at fake 50s forever.

def row_to_debug(r: Row) -> Dict[str, Any]:
    return {
        "cid": r.cid,
        "name": r.name,
        "score": float(r.score),
        "Q": float(r.q),
        "C": float(r.c),
        "T": float(r.t),
        "q_share": r.q_share,
        "c_share": r.c_share,
        "t_share": r.t_share,
        "qct_src": (r.qct_src or None),
        "close": r.close,
        "wow": r.wow,
        "mom30": r.mom30,
        "mom180": r.mom180,
        "tr1y": r.tr1y,
        "basis": r.basis,
        "signal": r.signal,
        "action": r.action,
        "owners": r.owners or [],
        "why": r.why or [],
        "first_buy": r.first_buy,
    }


def pill(text: str) -> str:
    return (
        "<span style='display:inline-block;padding:3px 8px;border:1px solid #d7d7d7;"
        "border-radius:999px;font-size:12px;line-height:16px;margin:0 6px 6px 0;"
        "white-space:nowrap;color:#222;background:#fff;'>" + text + "</span>"
    )

def stock_card(rank: int, r: Row) -> str:
    # Stamp the full CID into the HTML (invisible) so tests can grep it reliably.
    cid_tag = f"<!--CID:{r.cid}-->"

    # NOTE: Keep your existing markup, just make sure cid_tag is prefixed.
    return (
        cid_tag
        + "<div style='border:1px solid #ddd;border-radius:10px;padding:10px;margin:10px 0'>"
        + f"<div style='font-size:13px'><b>#{rank} {r.cid}</b> — {r.name}</div>"
        + "<div style='font-size:12px;color:#444;margin-top:6px'>"
        + f"Score {r.score:.1f} &nbsp; "
        + f"Q {r.q:.0f} ({r.q_share}) &nbsp; "
        + f"C {r.c:.0f} ({r.c_share}) &nbsp; "
        + f"T {r.t:.0f} ({r.t_share})"
        + (f" &nbsp; <span style='color:#777'>(QCT:{r.qct_src})</span>" if r.qct_src else "")
        + "</div>"
        + "<div style='margin-top:6px'>" + (r.spark or "") + "</div>"
        + "<div style='font-size:12px;color:#444;margin-top:6px'>"
        + f"Close {r.close or 'n/a'} &nbsp; WoW {r.wow or 'n/a'} &nbsp; Mom30 {r.mom30 or 'n/a'} &nbsp; Mom180 {r.mom180 or 'n/a'} &nbsp; TR1Y {r.tr1y or 'n/a'}"
        + f" &nbsp; <span style='color:#777'>({r.basis})</span>"
        + "</div>"
        + "<div style='font-size:12px;color:#444;margin-top:6px'>"
        + f"<b>Signal:</b> {r.signal} &nbsp; <b>Action:</b> {r.action}"
        + (f" &nbsp; <b>First buy:</b> {r.first_buy}" if r.first_buy else "")
        + "</div>"
        + "</div>"
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
    manual_path = str((cfg.get("manual_scores_path") or ranking.get("manual_scores_path") or "")).strip()
    manual = load_manual_scores(manual_path)
    print(f"[DBG] manual_scores_path={manual_path} exists={os.path.exists(manual_path)} loaded={len(manual)}")

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
        "<meta name='color-scheme' content='light'>",
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

    # We store the final rendered Row objects per theme so debug JSON matches reality.
    themes_out: List[Dict[str, Any]] = []

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

    # ranking config (used by both themes)
    rk = cfg.get("ranking") or {}
    core_n = int(rk.get("core_n") or 10)
    next_n = int(rk.get("next_n") or 5)
    N = core_n + next_n

    for theme_key in ("nuclear", "alt_power"):
        themes = cfg.get("themes") or {}
        if theme_key not in themes:
            continue

        tcfg = themes[theme_key]
        label = tcfg.get("label", theme_key)
        html.append(f"<hr><h3 style='margin:14px 0 6px 0'>{label}</h3>")

        # ranking config
        rk = cfg.get("ranking") or {}
        core_n = int(rk.get("core_n") or 10)
        next_n = int(rk.get("next_n") or 5)
        N = core_n + next_n

        src: Optional[str] = None
        rated_raw: List[str] = []
        rated: List[str] = []
        dup_removed = 0
        sot_by_cid: Dict[str, dict] = {}


        if theme_key == "alt_power":
            sot_path = ROOT / "out/data/alt_power_block.scored.json"
            if not sot_path.exists():
                raise SystemExit(f"[ERR] missing scored SoT for alt_power: {sot_path}")

            # Ensure SoT schema hygiene + theme_score computed (idempotent)
            import subprocess

            cmd = [
                sys.executable, str(ROOT / "scripts/apply_theme_blend.py"),
                "--in", str(sot_path),
                "--config", str(args.config),
                "--theme", "alt_power",
                "--inplace",
            ]
            subprocess.check_call(cmd)

            sot = json.loads(sot_path.read_text(encoding="utf-8", errors="replace"))
            rows = sot.get("rows") or []
            if not isinstance(rows, list) or not rows:
                raise SystemExit(f"[ERR] scored SoT has no rows[]: {sot_path}")

            # Tripwire: Alt-Power SoT must expose Q sub-scores (downstream expects these)
            bad = []
            for rr in rows:
                if not isinstance(rr, dict):
                    continue
                # only enforce for rows that are actually scored/rankable
                if rr.get("theme_score") is None:
                    continue
                if rr.get("q_fin_score") is None or rr.get("q_qual_score") is None:
                    bad.append(str(rr.get("qct_symbol") or rr.get("cid") or rr.get("ticker") or rr.get("name") or "UNKNOWN"))
                    if len(bad) >= 5:
                        break
            if bad:
                raise SystemExit("[ERR] alt_power SoT missing q_fin_score/q_qual_score for: " + ", ".join(bad))

            ranked: List[tuple[str, float]] = []
            for rr in rows:
                if not isinstance(rr, dict):
                    continue
                cid2 = str(rr.get("qct_symbol") or rr.get("cid") or "").strip()
                ts = rr.get("theme_score")
                if not cid2 or ts is None:
                    continue
                try:
                    ranked.append((cid2, float(ts)))
                    sot_by_cid[cid2] = rr
                except Exception:
                    continue

            ranked.sort(key=lambda x: x[1], reverse=True)
            rated_raw = [cid2 for cid2, _ in ranked[:N]]
            if len(rated_raw) != N:
                raise SystemExit(f"[ERR] alt_power: only {len(rated_raw)}/{N} rows with theme_score")

            # Alt-Power universe is exactly SoT top-N (do NOT let dedupe/filtering shrink it)
            rated = rated_raw[:]
            src = str(sot_path)

        else:
            candidate_sources: List[str] = []
            wl_sources = tcfg.get("watchlist_sources") or []
            fw_sources = tcfg.get("followed_sources") or []
            fallback_sources = tcfg.get("sources") or tcfg.get("source") or []
            for v in (wl_sources, fw_sources, fallback_sources):
                if isinstance(v, (str, Path)):
                    candidate_sources.append(str(v))
                elif isinstance(v, list):
                    candidate_sources.extend([str(x) for x in v if x])

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
                raise SystemExit(f"[ERR] no usable sources for theme '{theme_key}'.")

            rated = dedupe_rated_cids(rated_raw, reg, ov, theme_key)
            dup_removed = max(0, len(rated_raw) - len(rated))

        total_rated += len(rated)


        # --- DEBUG/VERIFICATION: stamp chosen CIDs into HTML (hidden) ---
        # This lets presence tests confirm SoT -> rendered selection wiring,
        # even if the visual card renderer doesn't print the CID verbatim.
        if theme_key == "alt_power":
            html.append("<!--ALT_POWER_TOPN_BEGIN-->")
            # (intentionally empty) - we no longer emit a separate CID list here
            html.append("<!--ALT_POWER_TOPN_END-->")

        theme_ov = (ov.get("themes", {}) or {}).get(theme_key, {}) or {}
        subs = theme_ov.get("subthemes", []) or []
        if theme_key == "alt_power":
            subs = []

        def _proxy_cids(x):
            """Accept either ['CID', ...] or [{'label':..., 'cid':'CID'}, ...]."""
            if not x:
                return []
            out: List[str] = []
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

        # Prefer per-theme proxies, else fall back to top-level overrides
        proxies = _proxy_cids(theme_ov.get("uranium_proxies") or ov.get("uranium_proxies") or [])
        ap_proxies = _proxy_cids(theme_ov.get("alt_power_proxies") or ov.get("alt_power_proxies") or [])

        stock_ov = ov.get("stocks", {}) or {}
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

        # --- Build scored list (cid, score, Q, C, T) before first use ---

        # Auto-QCT is canonical. Ignore any configured scores_path (legacy).
        qct_map: Dict[str, Dict[str, float]] = {}

        # Build best-effort per-CID fallback from rated_raw (prefer theme_score, else score)
        meta_score: Dict[str, float] = {}
        try:
            for rr in rated_raw:
                if not isinstance(rr, dict):
                    continue
                rcid = str(rr.get("cid") or rr.get("CID") or rr.get("id") or rr.get("symbol") or rr.get("ticker") or "").strip()
                if not rcid:
                    continue
                ts = safe_float(rr.get("theme_score"))
                if ts is None:
                    ts = safe_float(rr.get("score"))
                if ts is None:
                    continue
                prev = meta_score.get(rcid)
                if prev is None or ts > prev:
                    meta_score[rcid] = ts
        except Exception:
            meta_score = {}

        scored: List[Tuple[str, float, float, float, float]] = []

        for cid in rated:
            fallback = meta_score.get(cid)

            # Baseline score/Q/C/T (auto QCT may overwrite later)
            score = float(fallback if fallback is not None else 50.0)
            qv = float(fallback if fallback is not None else 50.0)
            cv = float(fallback if fallback is not None else 50.0)
            tv = float(fallback if fallback is not None else 50.0)

            # If trend is available, let it drive T baseline (still overwritten by auto when present)
            if "trend" in locals():
                try:
                    tv = float(trend.get(cid, tv))
                except Exception:
                    pass

            # If you still have a qct_map loaded earlier (file-based or auto), apply it here.
            rec = qct_map.get(cid) if isinstance(qct_map, dict) else None
            if isinstance(rec, dict) and rec:
                score = float(rec.get("score", score))
                qv = float(rec.get("q", qv))
                cv = float(rec.get("c", cv))
                tv = float(rec.get("t", tv))

            scored.append((cid, float(score), float(qv), float(cv), float(tv)))

        # --- De-dupe scored by CID (keep best score per CID) ---
        best: Dict[str, Tuple[float, float, float, float]] = {}
        for cid, score, qv, cv, tv in scored:
            prev = best.get(cid)
            if (prev is None) or (score > prev[0]):
                best[cid] = (float(score), float(qv), float(cv), float(tv))

        scored = [(cid, sc, q, c, t) for cid, (sc, q, c, t) in best.items()]
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
            tok0 = (os.environ.get("EODHD_API_TOKEN") or os.environ.get("EODHD_API_KEY") or "").strip()
            if tok0:
                return tok0
            for p in ("/opt/daily-report/.env_market", "/opt/daily-report/.env", "/opt/daily-report/.env_local"):
                if os.path.exists(p):
                    try:
                        env2 = parse_env_file(p)
                        tok0 = (env2.get("EODHD_API_TOKEN") or env2.get("EODHD_API_KEY") or "").strip()
                        if tok0:
                            return tok0
                    except Exception:
                        pass
            return ""

        # --- Auto Q/C/T from EODHD bars (single source of truth for gates/debug/render) ---
        qct_map: Dict[str, Dict[str, float]] = {}
        tok = _resolve_eodhd_token()
        print(f"[DBG] qct_auto tok={'yes' if tok else 'no'} scored={len(scored)}")

        if tok and scored:
            # Pull a longer window so compute_qct has enough usable bars after filtering
            start = (asof_local - timedelta(days=500)).date().isoformat()

            bars_by_cid: Dict[str, List[dict]] = {}
            fetch_ok = 0
            fetch_err = 0

            for cid0, _sc, _qv, _cv, _tv in scored:
                sym = cid_to_eodhd_symbol(cid0)
                try:
                    bars, _basis = fetch_eodhd_bars(sym, tok, start)
                    bars = bars[-200:] if (bars and len(bars) > 200) else (bars or [])
                    if bars:
                        bars_by_cid[cid0] = bars
                        fetch_ok += 1
                except Exception:
                    fetch_err += 1

            print(f"[DBG] qct_auto fetch_ok={fetch_ok} fetch_err={fetch_err} bars_by_cid={len(bars_by_cid)}")

            if bars_by_cid:
                try:
                    qct_map = compute_qct(bars_by_cid) or {}
                except Exception as e:
                    qct_map = {}
                    print(f"[DBG] qct_auto compute_err={e!r}")

            print(f"[DBG] qct_auto qct_map={len(qct_map)}")

            # IMPORTANT: Apply computed Q/C/T back onto scored tuples so gates/debug/output use real values
            if isinstance(qct_map, dict) and qct_map:
                scored2: List[Tuple[str, float, float, float, float]] = []
                for cid, score, qv, cv, tv in scored:
                    rec = qct_map.get(cid)
                    if isinstance(rec, dict) and rec:
                        score = float(rec.get("score", score))
                        qv = float(rec.get("q", qv))
                        cv = float(rec.get("c", cv))
                        tv = float(rec.get("t", tv))
                    scored2.append((cid, score, qv, cv, tv))

                scored = scored2
                scored.sort(key=lambda x: x[1], reverse=True)

                # quick sanity: does qct_map actually contain non-uniform C values?
                try:
                    cs = [
                        float(v.get("c"))
                        for v in qct_map.values()
                        if isinstance(v, dict) and v.get("c") is not None
                    ]
                    if cs:
                        uniq = len({round(x, 2) for x in cs})
                        print(f"[DBG] qct_auto c_min={min(cs):.2f} c_max={max(cs):.2f} c_unique~={uniq}")
                        for k, v in list(qct_map.items())[:5]:
                            print(
                                f"[DBG] qct_auto sample {k} "
                                f"q={v.get('q')} c={v.get('c')} t={v.get('t')} score={v.get('score')}"
                            )
                except Exception as e:
                    print(f"[DBG] qct_auto c_sanity_err={e!r}")

        # --- Build 180D series + 180D returns + trend rank (needed by mk_row) ---
        series_180: Dict[str, List[float]] = {}
        basis_180: Dict[str, str] = {}
        returns_180: Dict[str, float] = {}

        for cid in rated:
            try:
                s180, basis = get_series(cid, asof_local, days=210, keep=180)
            except Exception:
                s180, basis = [], "NO_DATA"

            series_180[cid] = s180 or []
            basis_180[cid] = basis or "NO_DATA"

            r180 = 0.0
            if s180 and len(s180) >= 2:
                try:
                    a = float(s180[0]) if s180[0] else 0.0
                    b = float(s180[-1]) if s180[-1] else 0.0
                    if a:
                        r180 = (b / a) - 1.0
                except Exception:
                    r180 = 0.0
            returns_180[cid] = r180

        all_r = list(returns_180.values())
        trend: Dict[str, float] = {cid: pct_rank(all_r, returns_180.get(cid, 0.0)) for cid in rated}

        def mk_row(
            rank: int, cid: str, score: float, qv: float, cv: float, tv: float, streak: int
        ) -> Row:
            it = reg.get(cid, {}) or {}
            o = stock_ov.get(cid, {}) if isinstance(stock_ov, dict) else {}
            name = str(o.get("display_name") or it.get("name") or cid).strip()

            qct = qct_map.get(cid) if isinstance(qct_map, dict) else None
            qct_src = ""
            q_share = c_share = t_share = ""

            if isinstance(qct, dict) and qct:
                score = float(qct.get("score", score))
                qv = float(qct.get("q", qv))
                cv = float(qct.get("c", cv))
                tv = float(qct.get("t", tv))
                q_share = f"{float(qct.get('q_share', 0.0)):.0f}%"
                c_share = f"{float(qct.get('c_share', 0.0)):.0f}%"
                t_share = f"{float(qct.get('t_share', 0.0)):.0f}%"
                qct_src = "auto"

            if not (q_share and c_share and t_share):
                q_contrib = float(w.get("Q", 0.4)) * qv
                c_contrib = float(w.get("C", 0.4)) * cv
                t_contrib = float(w.get("T", 0.2)) * tv
                tot = (q_contrib + c_contrib + t_contrib) or 1.0
                q_share = f"{(100 * q_contrib / tot):.0f}%"
                c_share = f"{(100 * c_contrib / tot):.0f}%"
                t_share = f"{(100 * t_contrib / tot):.0f}%"

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
            action = "BUY/ADD" if (buy_gate and rank <= 3 and score >= buy_score_min and streak >= buy_weeks) else "HOLD"

            return Row(
                cid=cid, name=name, score=float(score), q=float(qv), c=float(cv), t=float(tv),
                q_share=q_share, c_share=c_share, t_share=t_share, qct_src=qct_src,
                spark=spark, close=close, wow=wow, mom30=mom30, mom180=mom180, tr1y=tr1y,
                basis=basis, signal=signal, action=action, why=why, owners=owners, first_buy=first_buy
            )

        core = [x for x in scored[:core_n] if x[1] >= min_include]
        nxt  = [x for x in scored[core_n: core_n + next_n] if x[1] >= min_include]

        html.append("<h4 style='margin:12px 0 6px 0'>Core 10</h4>")
        streak = 1  # placeholder: wire to history later
        rows_out: List[Row] = []

        for i, (cid, sc, qv, cv, tv) in enumerate(core, start=1):
            r = mk_row(i, cid, sc, qv, cv, tv, streak if i <= 3 else 0)
            rows_out.append(r)
            html.append(stock_card(i, r))
            if r.action == "BUY/ADD":
                actions_buy.append(cid)

        html.append("<details style='margin:6px 0 0 0'>")
        html.append("<summary style='font-weight:600;margin:12px 0 6px 0'>Next 5 (click to expand)</summary>")
        for j, (cid, sc, qv, cv, tv) in enumerate(nxt, start=core_n + 1):
            r2 = mk_row(j, cid, sc, qv, cv, tv, 0)
            rows_out.append(r2)
            html.append(stock_card(j, r2))
        html.append("</details>")

        themes_out.append({"key": theme_key, "label": label, "rows": rows_out})


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

    # Write a fresh debug JSON alongside the HTML (derived from final Row objects).
    try:
        debug_path = Path(out_dir) / "weekly_nuclear_altpower.html.debug.json"
        debug_obj = {
            "generated_at_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "themes": [
                {
                    "label": th.get("label", "?"),
                    "rows": [row_to_debug(r) for r in (th.get("rows") or [])],
                }
                for th in themes_out
            ],
        }
        from src.utils.atomic_write import write_json_atomic
        write_json_atomic(debug_path, debug_obj, indent=2, ensure_ascii=False)
        print("[DBG] wrote:", str(debug_path))
    except Exception as e:
        print("[WARN] debug json not written:", repr(e))

    subject = f"{cfg['email']['subject_prefix']} | Friday Close: {asof_date}"
    if args.send:
        env = parse_env_file(cfg["email"]["smtp_env_file"])
        send_via_smtp(env, subject, "\n".join(html))
        print("Sent:", subject)

    return 0

if __name__ == "__main__":
    _regen_uranium_gated()
    _regen_alt_power_gated()
    raise SystemExit(main())



