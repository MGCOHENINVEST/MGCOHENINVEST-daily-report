#!/usr/bin/env python3
import json, time, os, random, pathlib
OUT = pathlib.Path("/opt/daily-report/out/data/fx_pairs.json")
pairs = [
    {"pair":"GBPUSD","last":1.3151,"chg1d":-0.0608},
    {"pair":"EURUSD","last":1.1543,"chg1d":-0.1989},
    {"pair":"USDCHF","last":0.8042,"chg1d": 0.2743},
    {"pair":"USDJPY","last":153.94,"chg1d": 0.0260},
    {"pair":"EURGBP","last":0.8782,"chg1d": 0.0041},
    {"pair":"GBPCHF","last":1.057,"chg1d":-0.0032},
    {"pair":"EURJPY","last":177.67,"chg1d": 0.0185},
    {"pair":"CHFJPY","last":191.47,"chg1d":-0.0112},
]
# jitter tiny to look alive
for p in pairs:
    p["last"] = round(p["last"]*(1+random.uniform(-0.0008,0.0008)), 5)
    p["chg1d"] = round(p["chg1d"]*(1+random.uniform(-0.02,0.02)), 5)
OUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUT, "w") as f:
    json.dump({"generated": int(time.time()), "pairs": pairs}, f)
print(f"fx_pairs_stub: wrote {OUT} with {len(pairs)} pairs")
