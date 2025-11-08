from __future__ import annotations
import os, sys, csv
from pathlib import Path
from datetime import date
from typing import List, Dict, Tuple
from app.utils.eodhd import _get  # reuse configured client/cache/budget

# EODHD has multiple price endpoints; keep it simple with real-time where possible.
# Fallback to /eod/<ticker> if needed by changing PATH below.
PATH_FMT = "/real-time/{ticker}"

TOP_N = int(os.environ.get("PRICES_TOP_N","200"))
OUT_DIR = Path("out/prices")/date.today().isoformat()
OUT_DIR.mkdir(parents=True, exist_ok=True)

UNIVERSE = Path("out/universe/latest/universe.csv")
if not UNIVERSE.exists():
    # fallback to newest dated dir
    d = sorted((Path("out/universe")).glob("*"), reverse=True)
    for x in d:
        if x.name=="latest": continue
        p=x/"universe.csv"
        if p.exists(): UNIVERSE=p; break

def read_top_by_mktcap(p: Path, k: int) -> List[str]:
    rows=[]
    with p.open() as f:
        r=csv.DictReader(f)
        for row in r:
            t=(row.get("ticker") or "").strip()
            mc=row.get("mktcap")
            try: mc=float(mc) if mc else 0.0
            except: mc=0.0
            if t: rows.append((t, mc, row.get("bucket","")))
    # ensure diverse buckets but primarily by size
    rows.sort(key=lambda x: x[1], reverse=True)
    return [t for t,_,_ in rows[:k]]

def fetch_one(t: str) -> Dict[str,str]:
    try:
        data = _get(PATH_FMT.format(ticker=t))
        # Normalize a couple fields commonly present in real-time payloads
        px  = data.get("close") or data.get("last") or data.get("price")
        ts  = data.get("timestamp") or data.get("updated_at")
        return {"ticker": t, "price": f"{px}" if px is not None else "", "ts": f"{ts}" if ts is not None else ""}
    except Exception:
        return {"ticker": t, "price": "", "ts": ""}

def main():
    tickers = read_top_by_mktcap(UNIVERSE, TOP_N)
    outp = OUT_DIR/"prices_topN.csv"
    with outp.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["ticker","price","ts"])
        w.writeheader()
        for i,t in enumerate(tickers,1):
            if i % 25 == 0:
                print(f"HEARTBEAT prices: {i}/{len(tickers)}", file=sys.stderr, flush=True)
            w.writerow(fetch_one(t))
    print(f"prices -> {outp}")

if __name__ == "__main__":
    main()
