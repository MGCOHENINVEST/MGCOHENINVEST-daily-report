#!/usr/bin/env python3
import json, time, pathlib, random
OUT = pathlib.Path("/opt/daily-report/out/data/fx_cross.json")
cross = [
    {"pair":"EUR/CHF","last":0.9251,"chg1d":-0.0018},
    {"pair":"EUR/JPY","last":177.60,"chg1d": 0.0172},
    {"pair":"GBP/CHF","last":1.0573,"chg1d":-0.0022},
    {"pair":"GBP/JPY","last":202.65,"chg1d": 0.0211},
    {"pair":"CHF/JPY","last":191.42,"chg1d":-0.0101},
]
for c in cross:
    c["last"] = round(c["last"]*(1+random.uniform(-0.001,0.001)), 5)
    c["chg1d"] = round(c["chg1d"]*(1+random.uniform(-0.02,0.02)), 5)
OUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUT, "w") as f:
    json.dump({"generated": int(time.time()), "cross": cross}, f)
print(f"fx_cross_stub: wrote {OUT} with {len(cross)} crosses")
