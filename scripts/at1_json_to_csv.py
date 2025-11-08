#!/usr/bin/env python3
import json, csv, sys, pathlib

ROOT = pathlib.Path("/opt/daily-report")
src = ROOT / "out" / "data" / "at1.json"
dst = ROOT / "out" / "data" / "at1.csv"

rows = []
j = json.load(src.open(encoding="utf-8"))
rows = j if isinstance(j, list) else (j.get("rows") or j.get("data") or j.get("items") or j.get("at1") or [])

# Map to renderer-friendly headers
out_rows = []
for r in rows:
    out_rows.append({
        "name":            r.get("name"),
        "clean_price":     r.get("price"),
        "coupon_pct":      r.get("coupon"),
        "next_call_date":  r.get("next_call_date"),
        "delta_1d":        r.get("d1"),
        "isin":            r.get("isin"),
    })

dst.parent.mkdir(parents=True, exist_ok=True)
with dst.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["name","clean_price","coupon_pct","next_call_date","delta_1d","isin"])
    w.writeheader(); w.writerows(out_rows)

print(f"Wrote {len(out_rows)} AT1 rows to {dst}")
