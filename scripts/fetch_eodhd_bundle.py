#!/usr/bin/env python3
import csv, json, time
from pathlib import Path

ROOT = Path("/opt/daily-report")
WATCHLIST_CSV = ROOT / "in" / "eodhd_watchlist.csv"
OUT_JSON = ROOT / "out" / "data" / "market_eodhd.json"

def load_watchlist_symbols(csv_path: Path):
    out = []
    if csv_path.exists():
        with csv_path.open(newline="") as f:
            rd = csv.DictReader(f)
            for r in rd:
                s = (r.get("Symbol") or "").strip()
                n = (r.get("Name") or s).strip()
                if s:
                    out.append((s, n))
    return out

symbols = load_watchlist_symbols(WATCHLIST_CSV)
if not symbols:
    # Defaults so the email never renders empty. Includes DE/LSE/SW.
    symbols = [
        ("AAPL.US","Apple"),("MSFT.US","Microsoft"),
        ("SAP.DE","SAP"),("BMW.DE","BMW"),
        ("AZN.LSE","AstraZeneca"),("VOD.LSE","Vodafone"),
        ("NESN.SW","Nestle"),("NOVN.SW","Novartis"),
    ]

# TODO: wire real prices. For now, names + symbols only.
equities = [{"symbol": s, "name": n} for s, n in symbols]

OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
with OUT_JSON.open("w", encoding="utf-8") as f:
    json.dump({"equities": equities, "ts": int(time.time())}, f)
print(f"Wrote {OUT_JSON} with {len(equities)} equities")
