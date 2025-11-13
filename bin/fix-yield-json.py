#!/usr/bin/env python3
import json
from pathlib import Path
from typing import Any
import sys

def coerce_value(v: Any) -> Any:
    """Recursively convert numeric-looking strings to floats."""
    if isinstance(v, str):
        try:
            f = float(v)
            return round(f, 4)
        except ValueError:
            return v
    if isinstance(v, list):
        return [coerce_value(x) for x in v]
    if isinstance(v, dict):
        return {k: coerce_value(val) for k, val in v.items()}
    return v

def fix_file(path: Path) -> None:
    if not path.exists():
        print(f"Skipping missing file: {path}")
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    new_data = coerce_value(data)
    path.write_text(json.dumps(new_data, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Normalised: {path}")

def main() -> None:
    root = Path(__file__).resolve().parent.parent  # /opt/daily-report
    default_files = [
        root / "out" / "data" / "yield_US.json",
        root / "out" / "data" / "yield_UK.json",
    ]
    files = [Path(p) for p in sys.argv[1:]] if len(sys.argv) > 1 else default_files
    for p in files:
        fix_file(p)

if __name__ == "__main__":
    main()
