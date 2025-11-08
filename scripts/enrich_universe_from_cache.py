from __future__ import annotations
import csv
from pathlib import Path
from datetime import date
from app.utils.eodhd import fundamentals, safe_mktcap

def latest_csv(base=Path("out/universe")) -> Path:
    today = base / date.today().isoformat() / "universe.csv"
    if today.exists(): return today
    cand = sorted(base.glob("*/universe.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not cand: raise SystemExit("No universe CSV found")
    return cand[0]

def pick_name(f):
    for path in [("General","Name"), ("General","Code"), ("Highlights","CompanyName")]:
        cur=f; ok=True
        for k in path:
            if not isinstance(cur, dict) or k not in cur:
                ok=False; break
            cur=cur[k]
        if ok and isinstance(cur, str) and cur.strip():
            return cur.strip()
    return ""

def pick_ccy(f):
    for path in [("General","CurrencyCode"), ("General","Currency")]:
        cur=f; ok=True
        for k in path:
            if not isinstance(cur, dict) or k not in cur:
                ok=False; break
            cur=cur[k]
        if ok and isinstance(cur, str) and cur.strip():
            return cur.strip()
    return ""

def main():
    csv_path = latest_csv()
    out_path = csv_path

    with csv_path.open() as f:
        r = csv.DictReader(f)
        rows = list(r)
        fields = r.fieldnames or ["isin","ticker","name","ccy","bucket","mktcap"]

    enriched=0; cache_hits=0; misses=0
    new_rows=[]
    for row in rows:
        t = (row.get("ticker") or "").strip()
        if not t:
            new_rows.append(row); continue
        try:
            fj = fundamentals(t)  # served from cache if present
            cache_hits += 1
            name = row.get("name") or pick_name(fj)
            ccy  = row.get("ccy")  or pick_ccy(fj)
            mc   = row.get("mktcap") or (safe_mktcap(fj) if fj else None)
            if name or ccy or mc:
                if name: row["name"] = name
                if ccy:  row["ccy"]  = ccy
                if isinstance(mc,(int,float)): row["mktcap"] = f"{mc:.0f}"
                enriched += 1
        except Exception:
            misses += 1
        new_rows.append(row)

    with out_path.open("w", newline="") as g:
        w = csv.DictWriter(g, fieldnames=fields)
        w.writeheader()
        w.writerows(new_rows)

    print(f"enriched rows: {enriched}  (cache_hits={cache_hits}, misses={misses})")
    print(f"updated -> {out_path}")

if __name__ == "__main__":
    main()
