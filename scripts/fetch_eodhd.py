#!/usr/bin/env python3
import csv, json, os, re, sys, time, urllib.parse, urllib.request
from typing import Dict, List, Tuple, Optional

ROOT = "/opt/daily-report"
OUT_PATH = f"{ROOT}/out/data/market_eodhd.json"
UA = "daily-report/1.0"
API_BASE = "https://eodhd.com/api/real-time/{}?fmt=json&api_token={}"

def die(msg: str, code: int = 1):
    print(f"[ERROR] {msg}", file=sys.stderr)
    sys.exit(code)

def http_get_json(url: str, timeout: int = 15) -> Optional[dict]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read().decode("utf-8", "replace")
        try:
            return json.loads(data)
        except Exception:
            return None

def classify_code(code: str) -> str:
    c = code.upper()
    if c.endswith(".FOREX") or re.match(r"^[A-Z]{3}[A-Z]{3}\.FOREX$", c):
        return "fx"
    if re.search(r"\.(DE|FR|AS|BR|SW|SWX|MI|PA|BRU|BRX|OL|CO|HE|ES|LS|VX|LSE|L|US|TO|TSX|HK)$", c):
        return "equities"
    # fall back to equities
    return "equities"

def load_holdings_symbols() -> List[str]:
    symbols = []
    for name in os.listdir(f"{ROOT}/config"):
        if not name.startswith("holdings_") or not name.endswith(".csv"):
            continue
        path = os.path.join(ROOT, "config", name)
        try:
            with open(path, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    s = (row.get("symbol") or row.get("ticker") or "").strip()
                    if s:
                        symbols.append(s)
        except Exception as e:
            print(f"[WARN] could not read {path}: {e}", file=sys.stderr)
    return symbols

def load_mapping() -> Dict[str, str]:
    """Return local->eodhd code mapping from eodhd_map.valid.csv (column 'symbol_eodhd')."""
    mp = {}
    p = os.path.join(ROOT, "config", "eodhd_map.valid.csv")
    if not os.path.exists(p):
        return mp
    try:
        with open(p, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                left = (row.get("symbol") or "").strip()
                right = (row.get("symbol_eodhd") or "").strip()
                if left and right:
                    mp[left] = right
    except Exception as e:
        print(f"[WARN] could not parse {p}: {e}", file=sys.stderr)
    return mp

def unique_order(seq):
    seen = set()
    out = []
    for x in seq:
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out

def fetch_one(code: str, token: str, backoff_s: float = 0.0) -> Tuple[str, Optional[dict]]:
    url = API_BASE.format(urllib.parse.quote(code), urllib.parse.quote(token))
    if backoff_s > 0:
        time.sleep(backoff_s)
    try:
        j = http_get_json(url)
        if not isinstance(j, dict):
            return code, None
        # normalize a minimal "quote" dict
        q = {
            "code": j.get("code") or code,
            "timestamp": j.get("timestamp"),
            "gmtoffset": j.get("gmtoffset"),
            "open": j.get("open"),
            "high": j.get("high"),
            "low": j.get("low"),
            "close": j.get("close") if j.get("close") not in ("NA", "N/A") else None,
            "volume": j.get("volume"),
            "previousClose": j.get("previousClose"),
            "change": j.get("change"),
            "change_p": j.get("change_p"),
        }
        return code, q
    except Exception as e:
        print(f"[WARN] fetch {code}: {e}", file=sys.stderr)
        return code, None

def build_bundle() -> dict:
    token = (os.environ.get("EODHD_API_TOKEN") or "").strip()
    if not token:
        die("EODHD_API_TOKEN missing")

    symbols = load_holdings_symbols()
    mapping = load_mapping()

    # Translate via mapping; if no mapping, assume the holding symbol is already an EODHD code
    codes = [mapping.get(s, s) for s in symbols]

    # Keep a few obvious indices/fx if you like (optional; comment out if not used)
    # codes += ["SPY.US", "EURUSD.FOREX"]

    codes = unique_order([c for c in codes if c])

    buckets = {"equities": [], "indices": [], "fx": []}
    ok, miss = 0, 0
    for i, code in enumerate(codes, 1):
        # light pacing to be kind to the API
        _, quote = fetch_one(code, token, backoff_s=0.05)
        bucket = classify_code(code)
        rec = {"symbol": code}
        if quote:
            rec["quote"] = quote
            ok += 1
        else:
            miss += 1
        buckets[bucket].append(rec)

    buckets["_counts"] = {"equity": len(buckets["equities"]), "index": len(buckets["indices"]), "fx": len(buckets["fx"])}
    print(f"Wrote EODHD bundle candidates: ok={ok} missing={miss} totals={buckets['_counts']}")
    return buckets

if __name__ == "__main__":
    data = build_bundle()
    outdir = os.path.dirname(OUT_PATH)
    os.makedirs(outdir, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f)
    print(f"Wrote {OUT_PATH}")
