#!/usr/bin/env python3
import csv, math, os, sys

ROOT = "/opt/daily-report"
IN   = os.path.join(ROOT, "out/data/at1.csv")
OUT  = os.path.join(ROOT, "out/data/at1_priced.csv")

# Toggle: if True, require BOTH price and YTC; if False, allow price-only rows (ytc blank)
REQUIRE_YTC = False

def f2(x):
    try:
        # accept 99, 99.0, "99.0", "" (-> None), "NA" (-> None)
        s = (x or "").strip()
        if not s: return None
        v = float(s.replace(",", ""))
        if math.isnan(v): return None
        return v
    except Exception:
        return None

def pick(d, *keys, default=""):
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return default

total = kept = 0
rows_out = []

try:
    with open(IN, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            total += 1
            # normalise keys to lowercase
            dl = { (k or "").strip().lower(): (v or "").strip() for k, v in row.items() }

            name   = pick(dl, "name", "issuer", "security", default="")
            isin   = pick(dl, "isin", default="")
            price  = pick(dl, "clean_price", "price", "last_price", "mid", "px_last", default="")
            coupon = pick(dl, "coupon_pct", "coupon", default="")
            ncall  = pick(dl, "next_call_date", "next_call", "first_call_date", default="")
            # ytc variants if present
            ytc    = pick(dl, "ytc", "yield_to_call", "ytc_pct", default="")

            p = f2(price)
            y = f2(ytc) if ytc else None

            if p is None:
                continue
            if REQUIRE_YTC and y is None:
                continue

            rows_out.append({
                "name": name,
                "clean_price": f"{p:.4f}",
                "coupon_pct": coupon,
                "next_call_date": ncall,
                "ytc": ("" if y is None else f"{y:.4f}"),
                "isin": isin
            })

    # ensure output dir exists
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as g:
        w = csv.DictWriter(g, fieldnames=["name","clean_price","coupon_pct","next_call_date","ytc","isin"])
        w.writeheader()
        for row in rows_out:
            w.writerow(row)
        kept = len(rows_out)

    print(f"[at1_filter_priced] kept={kept}/{total} -> {OUT}")
    sys.exit(0)
except FileNotFoundError:
    print(f"[at1_filter_priced] input not found: {IN}", file=sys.stderr)
    sys.exit(0)  # non-fatal
except Exception as e:
    print(f"[at1_filter_priced] ERROR: {e}", file=sys.stderr)
    sys.exit(1)
