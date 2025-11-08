from pathlib import Path
import csv

ROOT = Path(".")
OUT_UNI = ROOT / "out/universe"
CFG_DIR = ROOT / "config/us"
FILES = ["sp500.csv","nasdaq100.csv","dow30.csv"]

def latest_universe_csv() -> Path:
    dirs = sorted(OUT_UNI.glob("*/"), key=lambda p: p.name)
    if not dirs:
        raise SystemExit("No out/universe/*/ directory found")
    return dirs[-1] / "universe.csv"

def read_rows(p: Path):
    with p.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            yield {k:(v or "").strip() for k,v in row.items()}

def main():
    ucsv = latest_universe_csv()
    with ucsv.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        rows = list(r)
    have = { (row.get("ticker") or "").strip() for row in rows }

    added = 0
    for fn in FILES:
        f = CFG_DIR / fn
        if not f.exists():
            continue
        for row in read_rows(f):
            t = (row.get("ticker") or "").strip()
            if not t or t in have:
                continue
            rows.append({
                "isin":  (row.get("isin") or "").strip(),
                "ticker": t,
                "name":  (row.get("name") or "").strip(),
                "ccy":   (row.get("ccy") or "USD").strip() or "USD",
                "bucket":"US_FILL",
                "mktcap": (row.get("mktcap") or "").strip(),
            })
            have.add(t)
            added += 1

    with ucsv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["isin","ticker","name","ccy","bucket","mktcap"])
        w.writeheader()
        w.writerows(rows)

    print(f"merged US -> {ucsv} (added {added})")

if __name__ == "__main__":
    main()
