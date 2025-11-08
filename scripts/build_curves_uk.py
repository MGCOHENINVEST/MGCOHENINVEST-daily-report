#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

def main():
    points = [
        {"tenor": "2Y", "yield": 4.67, "delta": 0.01},
        {"tenor": "5Y", "yield": 4.35, "delta": -0.02},
        {"tenor": "10Y", "yield": 4.23, "delta": 0.00},
    ]

    payload = {
        "as_of": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "points": points
    }

    outdir = Path("out/daily") / datetime.now().strftime("%F")
    outdir.mkdir(parents=True, exist_ok=True)
    outp = outdir / "curves_uk.json"

    outp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"curves_uk -> {outp} (points={len(points)})")

if __name__ == "__main__":
    main()
