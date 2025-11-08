#!/usr/bin/env python3
import json, time
from pathlib import Path

OUT = Path("/opt/daily-report/out/data/fx_pairs.json")
OUT.parent.mkdir(parents=True, exist_ok=True)

# Minimal, deterministic placeholders so the section renders
pairs = [
    {"pair": "GBPUSD", "last": "1.3151", "chg_1d": "-0.0608"},
    {"pair": "EURUSD", "last": "1.1543", "chg_1d": "-0.1989"},
    {"pair": "USDCHF", "last": "0.8042", "chg_1d": "0.2743"},
    {"pair": "USDJPY", "last": "153.94", "chg_1d": "0.0260"},
]

payload = {
    "generated": int(time.time()),
    "pairs": pairs
}

with OUT.open("w", encoding="utf-8") as f:
    json.dump(payload, f, separators=(",", ":"))

print(f"fx_pairs_stub: wrote {OUT} with {len(pairs)} pairs")


