"""
assemble_daily.py — build daily.json with universes, commodities, curves, and macro
"""

import json
from pathlib import Path
from datetime import date

def load_json_safe(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None

def main():
    today = date.today().isoformat()
    outdir = Path("out/daily") / today
    outdir.mkdir(parents=True, exist_ok=True)

    daily = {"as_of": today}

    # Universe
    uni_path = outdir / "universe.json"
    uni = load_json_safe(uni_path)
    daily["universe"] = uni or {}
    print(f"Universe: {len(uni or {})} entries" if uni else "Universe: none")

    # Commodities
    comms_path = outdir / "commodities.json"
    comms = load_json_safe(comms_path)
    if comms:
        daily["commodities"] = comms.get("commodities", [])
        daily["commodities_as_of"] = comms.get("as_of") or comms.get("date")
        print(f"Commodities: {len(daily['commodities'])} rows")
    else:
        daily["commodities"] = []
        daily["commodities_as_of"] = today
        print("Commodities: none")

    # Curves
    curves = {}
    curves["uk"] = load_json_safe(outdir / "curves_uk.json") or []
    curves["us"] = load_json_safe(outdir / "curves_us.json") or []
    daily["curves"] = curves
    print(f"Curves UK: {len(curves['uk'])} rows")
    print(f"Curves US: {len(curves['us'])} rows")

    # Macro UK
    macro_uk = load_json_safe(outdir / "macro_uk.json") or {"as_of": today, "bullets": []}
    daily["macro_uk"] = macro_uk
    print(f"Macro UK: {len(macro_uk.get('bullets', []))} bullets")

    # Macro US
    macro_us = load_json_safe(outdir / "macro_us.json") or {"as_of": today, "bullets": []}
    daily["macro_us"] = macro_us
    print(f"Macro US: {len(macro_us.get('bullets', []))} bullets")

    # Write daily.json
    out_path = outdir / "daily.json"
    out_path.write_text(json.dumps(daily, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")

if __name__ == "__main__":
    main()
