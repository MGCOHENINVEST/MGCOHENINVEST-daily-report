#!/usr/bin/env python3
import csv, pathlib
dst = pathlib.Path("/opt/daily-report/out/data/commodities.csv")
rows = [
  {"name":"Gold (XAUUSD)","last":"","chg_1d":"","wtd":""},
  {"name":"Silver (XAGUSD)","last":"","chg_1d":"","wtd":""},
  {"name":"WTI Crude","last":"","chg_1d":"","wtd":""},
  {"name":"Copper","last":"","chg_1d":"","wtd":""},
]
dst.parent.mkdir(parents=True, exist_ok=True)
with dst.open("w", newline="", encoding="utf-8") as f:
  w=csv.DictWriter(f, fieldnames=["name","last","chg_1d","wtd"])
  w.writeheader(); w.writerows(rows)
print(f"[commodities_stub] wrote {dst}")

