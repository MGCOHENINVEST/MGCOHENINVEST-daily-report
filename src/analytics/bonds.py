#!/usr/bin/env python3
"""
Lightweight bond analytics:
- running_yield = (coupon / price) * 100
- ytm_approx   = (coupon + (100 - price)/T) / ((100 + price)/2) * 100
  (face=100, annual coupon rate; clean price)
- duration_mod (approx) using a simple cashflow model and yield guess
- ladder buckets: 0-1y, 1-3y, 3-5y, 5-10y, 10y+
Outputs JSON summary for email/report usage.
"""

import csv, json, math, sys
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Any

FACE = 100.0

def parse_date(s: str) -> date | None:
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%d").date()
    except Exception:
        return None

def years_between(a: date, b: date) -> float:
    return (b - a).days / 365.25

def running_yield(coupon_rate: float, price: float) -> float | None:
    if price and price > 0:
        return (coupon_rate / 100.0) * FACE / price * 100.0
    return None

def ytm_approx(coupon_rate: float, price: float, years: float) -> float | None:
    # Coupon in currency per year
    c = (coupon_rate / 100.0) * FACE
    if price and years and price > 0 and years > 0:
        # Classic approximation; good enough for screening
        return ((c + (FACE - price) / years) / ((FACE + price) / 2.0)) * 100.0
    return None

def macaulay_duration_approx(coupon_rate: float, ytm_pct: float, years: float, freq: int = 2) -> float | None:
    """
    Approximate Macaulay duration using standard cashflow PV weighting.
    freq=2 semi-annual by default. Inputs:
    - coupon_rate: % per annum
    - ytm_pct: % per annum
    - years: time to maturity in years
    """
    if years is None or years <= 0 or ytm_pct is None:
        return None
    n = max(1, int(round(years * freq)))
    y = (ytm_pct / 100.0) / freq
    c = (coupon_rate / 100.0) * FACE / freq
    t_weights = []
    pv_cf = 0.0
    for k in range(1, n + 1):
        t = k / freq
        cf = c if k < n else c + FACE
        df = (1 + y) ** (-k)
        pv = cf * df
        pv_cf += pv
        t_weights.append((t, pv))
    if pv_cf <= 0:
        return None
    mac_dur = sum(t * pv for t, pv in t_weights) / pv_cf
    # Modified duration = Macaulay / (1 + y_per_period) converted to annual
    mod_dur = mac_dur / (1 + y)
    return mod_dur  # already in years

def bucket(years: float) -> str:
    if years < 0:
        return "past"
    if years <= 1: return "0-1y"
    if years <= 3: return "1-3y"
    if years <= 5: return "3-5y"
    if years <= 10: return "5-10y"
    return "10y+"

def read_bonds(path: str) -> List[Dict[str, Any]]:
    if not Path(path).is_file():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        out = []
        today = date.today()
        for row in r:
            try:
                price = float(row.get("price", "") or row.get("price_clean", "") or 0.0)
            except Exception:
                price = 0.0
            try:
                coupon = float(row.get("coupon", "") or 0.0)
            except Exception:
                coupon = 0.0
            mat = parse_date(row.get("maturity") or row.get("maturity_date") or "")
            yrs = years_between(today, mat) if mat else None

            # If CSV already has ytm/running_yield, use it; else compute approximation
            try:
                ytm_csv = float(row.get("ytm", "") or 0.0) or None
            except Exception:
                ytm_csv = None
            try:
                r_yield_csv = float(row.get("running_yield", "") or 0.0) or None
            except Exception:
                r_yield_csv = None

            ytm = ytm_csv if ytm_csv is not None else (ytm_approx(coupon, price, yrs) if yrs else None)
            r_yield = r_yield_csv if r_yield_csv is not None else running_yield(coupon, price)
            dur_mod = macaulay_duration_approx(coupon, ytm, yrs) if (ytm is not None and yrs is not None) else None

            out.append({
                "ticker": row.get("ticker") or "",
                "isin": row.get("isin") or "",
                "issuer": row.get("issuer") or row.get("name") or "",
                "currency": row.get("currency") or "",
                "coupon": coupon if coupon else None,
                "maturity": mat.isoformat() if mat else "",
                "years_to_maturity": round(yrs, 2) if yrs is not None else None,
                "price": price if price else None,
                "running_yield": round(r_yield, 3) if r_yield is not None else None,
                "ytm": round(ytm, 3) if ytm is not None else None,
                "duration_mod": round(dur_mod, 3) if dur_mod is not None else None,
                "bucket": bucket(yrs) if yrs is not None else "unknown",
            })
        return out

def summarize(bonds: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not bonds:
        return {
            "count": 0,
            "avg_running_yield": None,
            "avg_ytm": None,
            "avg_duration_mod": None,
            "ladder": {},
            "next_maturities": [],
        }
    def avg(key):
        vals = [b[key] for b in bonds if isinstance(b.get(key), (int, float))]
        return round(sum(vals)/len(vals), 3) if vals else None

    # ladder counts
    ladder = {}
    order = ["0-1y","1-3y","3-5y","5-10y","10y+"]
    for b in bonds:
        ladder[b["bucket"]] = ladder.get(b["bucket"], 0) + 1
    ladder = {k: ladder.get(k,0) for k in order}

    # next 5 maturities
    nm = [b for b in bonds if b.get("years_to_maturity") is not None]
    nm.sort(key=lambda x: x["years_to_maturity"])
    next_mats = nm[:5]

    return {
        "count": len(bonds),
        "avg_running_yield": avg("running_yield"),
        "avg_ytm": avg("ytm"),
        "avg_duration_mod": avg("duration_mod"),
        "ladder": ladder,
        "next_maturities": next_mats,
    }

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--csv", default="data/bonds.csv")
    p.add_argument("--out", default="")
    args = p.parse_args()

    bonds = read_bonds(args.csv)
    summary = summarize(bonds)
    payload = {"bonds": bonds, "summary": summary}
    text = json.dumps(payload, ensure_ascii=False)

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)

if __name__ == "__main__":
    sys.exit(main())
