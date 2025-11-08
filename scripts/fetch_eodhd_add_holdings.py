#!/usr/bin/env python3
import csv, glob, json, os, sys, urllib.parse, urllib.request
from datetime import datetime, timezone

ROOT   = "/opt/daily-report"
OUTJ   = f"{ROOT}/out/data/market_eodhd.json"
MAPCSV = f"{ROOT}/config/eodhd_map.valid.csv"
UA     = "daily-report/holdings-enricher/1.0"
API    = "https://eodhd.com/api/real-time/{}?api_token={}&fmt=json"

def nowiso():
    return datetime.now(timezone.utc).isoformat()

def load_holdings_symbols():
    syms=set()
    for f in glob.glob(f"{ROOT}/config/holdings_*.csv"):
        try:
            for row in csv.DictReader(open(f, newline="", encoding="utf-8")):
                s=(row.get("symbol") or row.get("ticker") or "").strip()
                if s: syms.add(s)
        except Exception as e:
            print(f"[WARN] skip {f}: {e}", file=sys.stderr)
    return sorted(syms)

def load_map():
    mp={}
    if os.path.exists(MAPCSV):
        with open(MAPCSV, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                a=(row.get("symbol") or "").strip()
                b=(row.get("symbol_eodhd") or "").strip()
                if a and b: mp[a]=b
    return mp

def fetch_quote(code, token, timeout=12):
    url = API.format(urllib.parse.quote(code), urllib.parse.quote(token))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        j=json.loads(r.read().decode("utf-8","replace"))
    if not isinstance(j, dict): return None
    close = j.get("close")
    if close is None: return None
    j = dict(j)
    j["code"] = j.get("code") or code
    return j

def load_existing():
    try:
        obj=json.load(open(OUTJ, encoding="utf-8"))
        if not isinstance(obj, dict): raise ValueError("bad top-level")
    except Exception:
        obj={"ts": nowiso(), "equities": [], "indices": [], "fx": [], "_counts": {}}
    obj.setdefault("equities", []); obj.setdefault("_counts", {})
    return obj

def upsert_equities(obj, new_quotes):
    idx={}
    for r in obj.get("equities", []):
        q=r.get("quote") or {}
        code = q.get("code") or r.get("symbol") or r.get("ticker")
        if code: idx[str(code)] = r
    for code, q in new_quotes.items():
        idx[str(code)] = {"symbol": code, "quote": q}
    obj["equities"] = list(idx.values())
    obj["_counts"]["equity"] = len(obj["equities"])
    obj["ts"] = nowiso()
    return obj

def main():
    token=os.environ.get("EODHD_API_TOKEN","").strip()
    if not token:
        print("[ERROR] EODHD_API_TOKEN is missing", file=sys.stderr); sys.exit(1)

    syms = load_holdings_symbols()
    if not syms:
        print("[INFO] no holdings_*.csv; nothing to enrich"); return

    mp = load_map()
    codes = sorted({ mp.get(s, s) for s in syms })

    got, miss = {}, []
    for code in codes:
        try:
            q=fetch_quote(code, token)
            if q: got[code]=q
            else: miss.append(code)
        except Exception as e:
            print(f"[WARN] fetch {code}: {e}", file=sys.stderr); miss.append(code)

    base = load_existing()
    out  = upsert_equities(base, got)
    tmp  = OUTJ + ".tmp"
    with open(tmp,"w",encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",",":"))
    os.replace(tmp, OUTJ)

    print(f"[INFO] enriched: {len(got)} quotes upserted; missed={len(miss)}")
    if miss: print("[INFO] missed codes:", ", ".join(miss))

if __name__=="__main__":
    main()
