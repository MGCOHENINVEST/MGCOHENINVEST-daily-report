from __future__ import annotations
import csv, json
from pathlib import Path
from datetime import datetime

CFG = Path("config/at1_uk.csv")
DDIR = Path("out/daily")/datetime.utcnow().date().isoformat()
DJ   = DDIR/"daily.json"

def read_at1_csv(p: Path):
    if not p.exists(): return []
    out=[]
    with p.open() as f:
        r = csv.DictReader(f)
        for row in r:
            sedol  = (row.get("sedol") or "").strip()
            isin   = (row.get("isin") or "").strip()
            issuer = (row.get("issuer") or "").strip()
            instr  = (row.get("instrument") or "").strip()
            ccy    = (row.get("ccy") or "").strip() or "GBP"
            size_m = row.get("size_m") or ""
            coup   = row.get("coupon_pct") or ""
            call   = (row.get("first_call") or "").strip()
            notes  = (row.get("notes") or "").strip()

            # normalize numbers if present
            def to_float(x):
                try:
                    return float(str(x).replace(",","")) if str(x).strip() else None
                except Exception:
                    return None

            out.append({
                "sedol": sedol,
                "isin": isin,
                "issuer": issuer,
                "instrument": instr,
                "ccy": ccy,
                "size_m": to_float(size_m),
                "coupon_pct": to_float(coup),
                "first_call": call,   # already YYYY-MM-DD from our loader
                "notes": notes
            })
    return out

def main():
    assert DJ.exists(), f"daily.json not found: {DJ}"
    data = json.loads(DJ.read_text())

    at1_list = read_at1_csv(CFG)
    # create/merge block
    data.setdefault("at1", {})
    data["at1"]["uk"] = at1_list
    data["at1"]["uk_count"] = len(at1_list)

    DDIR.mkdir(parents=True, exist_ok=True)
    DJ.write_text(json.dumps(data, indent=2))
    print(f"Injected {len(at1_list)} UK AT1s into {DJ}")

if __name__ == "__main__":
    main()
