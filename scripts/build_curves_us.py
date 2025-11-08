#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

def main():
    points = [
        {"tenor": "2Y", "yield": 3.98, "delta": 0.03},
        {"tenor": "10Y", "yield": 4.22, "delta": 0.01},
        {"tenor": "30Y", "yield": 4.32, "delta": -0.01},
    ]

    payload = {
        "as_of": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "points": points
    }

    outdir = Path("out/daily") / datetime.now().strftime("%F")
    outdir.mkdir(parents=True, exist_ok=True)
    outp = outdir / "curves_us.json"

    outp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"curves_us -> {outp} (points={len(points)})")

if __name__ == "__main__":
    main()
