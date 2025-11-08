from __future__ import annotations
import csv, json
from pathlib import Path
from datetime import date

CFG_DIR = Path("config")

def latest_universe_csv(base=Path("out/universe")) -> Path:
    today = base / date.today().isoformat() / "universe.csv"
    if today.exists():
        return today
    cand = sorted(base.glob("*/universe.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not cand:
        raise SystemExit("No universe CSV found under out/universe/*/universe.csv")
    return cand[0]

def load_curated(path: Path):
    if not path.exists(): return []
    out=[]
    with path.open() as f:
        r=csv.DictReader(f)
        for row in r:
            t=(row.get("ticker") or "").strip()
            if t: out.append(t)
    return out

def read_csv(p: Path):
    with p.open() as f:
        r=csv.DictReader(f)
        rows=list(r)
    return r.fieldnames, rows

def write_csv(p: Path, fieldnames, rows):
    with p.open("w", newline="") as f:
        w=csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(row)

def read_counts_json(p: Path):
    if not p.exists(): return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None

def write_counts_json(p: Path, counts: dict):
    p.write_text(json.dumps({"as_of": str(p.parent.name), "counts": counts}, indent=2))

def main():
    base = Path("out/universe")
    csv_path = latest_universe_csv(base)
    counts_path = csv_path.parent / "summary.json"

    fieldnames, rows = read_csv(csv_path)
    want_fields = ["isin","ticker","name","ccy","bucket","mktcap"]
    if fieldnames != want_fields:
        fieldnames = want_fields
        norm=[]
        for r in rows:
            norm.append({k: r.get(k,"") for k in want_fields})
        rows = norm

    have = { (r.get("ticker") or "").strip() for r in rows if (r.get("ticker") or "").strip() }

    ftse100  = load_curated(CFG_DIR/"ftse100.csv")
    ftse250  = load_curated(CFG_DIR/"ftse250.csv")

    added_ftse100=0
    for t in ftse100:
        if t not in have:
            rows.append({"isin":"","ticker":t,"name":"","ccy":"","bucket":"FTSE100","mktcap":""})
            have.add(t); added_ftse100+=1

    added_ftse250=0
    for t in ftse250[:100]:
        if t not in have:
            rows.append({"isin":"","ticker":t,"name":"","ccy":"","bucket":"FTSE250_TOP100","mktcap":""})
            have.add(t); added_ftse250+=1

    write_csv(csv_path, fieldnames, rows)

    by_bucket={}
    for r in rows:
        b=r.get("bucket") or ""
        if not b: continue
        by_bucket[b]=by_bucket.get(b,0)+1

    existing = read_counts_json(counts_path) or {"counts":{}}
    counts = existing.get("counts", {})
    counts["uk"]       = by_bucket.get("FTSE100",0) + by_bucket.get("FTSE250_TOP100",0)
    counts["ch"]       = by_bucket.get("SWISS30",0)
    counts["ez"]       = by_bucket.get("EURO200",0)
    counts["us"]       = by_bucket.get("US_FILL",0)
    counts["uranium"]  = counts.get("uranium", 20)
    counts["ad_hoc"]   = counts.get("ad_hoc", 100)
    core_set = { (r.get("ticker") or "").strip()
                 for r in rows
                 if (r.get("bucket") or "") in {"FTSE100","FTSE250_TOP100","SWISS30","EURO200","US_FILL"} }
    counts["core"] = len(core_set)

    write_counts_json(counts_path, counts)

    print(f"merge: added FTSE100={added_ftse100}, FTSE250_TOP100={added_ftse250}")
    print(f"csv -> {csv_path}")
    print(f"counts -> {counts_path}  {counts}")

if __name__ == "__main__":
    main()
