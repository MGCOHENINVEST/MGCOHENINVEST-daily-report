#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

def main():
    bullets = [
        "CPI release Thu 07:00",
        "GDP monthly est. Fri 09:30"
    ]

    payload = {
        "as_of": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "bullets": bullets
    }

    outdir = Path("out/daily") / datetime.now().strftime("%F")
    outdir.mkdir(parents=True, exist_ok=True)
    outp = outdir / "macro_uk.json"

    outp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"macro_uk -> {outp} (bullets={len(bullets)})")

if __name__ == "__main__":
    main()
