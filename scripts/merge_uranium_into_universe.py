from pathlib import Path
import csv

def latest_universe_csv() -> Path:
    u = sorted(Path("out/universe").glob("*/universe.csv"))
    if not u:
        raise SystemExit("No universe CSV found under out/universe/*/universe.csv")
    return u[-1]

def main():
    ucsv  = latest_universe_csv()
    urcsv = Path("config/uranium.csv")
    assert urcsv.exists(), f"Missing {urcsv}"

    with ucsv.open() as f:
        r = csv.DictReader(f)
        fields = r.fieldnames or ["isin","ticker","name","ccy","bucket","mktcap"]
        rows   = list(r)

    have = { (row.get("ticker") or "").strip() for row in rows }
    with urcsv.open() as f:
        r = csv.DictReader(f)
        for row in r:
            t = (row.get("ticker") or "").strip()
            if t and t not in have:
                rows.append({"isin":"","ticker":t,"name":"","ccy":"","bucket":"URANIUM_ENSURE","mktcap":""})
                have.add(t)

    with ucsv.open("w", newline="") as g:
        w = csv.DictWriter(g, fieldnames=fields)
        w.writeheader(); w.writerows(rows)
    print(f"merged uranium -> {ucsv}")
if __name__ == "__main__":
    main()
