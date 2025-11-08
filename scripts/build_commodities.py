#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

def main():
    # Example rows — your real fetch/parse logic goes here
    rows = [
        {"instrument": "CL — WTI Crude", "price": 90.25, "delta": None},
        {"instrument": "CO — Brent Crude", "price": 92.10, "delta": None},
        {"instrument": "GC — Gold", "price": 2450.3, "delta": None},
        {"instrument": "SI — Silver", "price": 30.1, "delta": None},
        {"instrument": "HG — Copper", "price": 4.08, "delta": None},
    ]

    payload = {
        "commodities": rows,
        "count": len(rows),
        "as_of": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }

    outdir = Path("out/daily") / datetime.now().strftime("%F")
    outdir.mkdir(parents=True, exist_ok=True)
    outp = outdir / "commodities.json"

    outp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"commodities -> {outp} (rows={len(rows)})")

if __name__ == "__main__":
    main()
