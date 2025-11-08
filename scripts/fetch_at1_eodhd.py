#!/usr/bin/env python3
# /opt/daily-report/scripts/fetch_at1_eodhd.py
#
# Build /opt/daily-report/out/data/at1.csv from your vendor list by fetching
# end-of-day prices for AT1s via EODHD's EOD API using ISIN.EUBOND (fallback .BOND).
#
# Env:
#   EODHD_API_TOKEN      (required)
#   AT1_VENDOR_FILE      default: /opt/daily-report/in/at1_vendor.csv
#   AT1_FILE             default: /opt/daily-report/out/data/at1.csv
#
# Vendor CSV can have flexible headers; we auto-detect:
#   name/issuer/description, coupon/cpn, next call date, isin/identifier
# Clean output header (what render_email.py expects):
#   name,clean_price,coupon_pct,next_call_date,delta_1d,isin

import csv, json, os, re, sys, datetime as dt
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

ROOT = "/opt/daily-report"
VENDOR = os.environ.get("AT1_VENDOR_FILE", f"{ROOT}/in/at1_vendor.csv")
OUT    = os.environ.get("AT1_FILE",        f"{ROOT}/out/data/at1.csv")
TOKEN  = os.environ.get("EODHD_API_TOKEN")

def log(msg):  print(f"[INFO] {msg}")
def warn(msg): print(f"[WARN] {msg}", file=sys.stderr)
def fail(msg): print(f"[ERROR] {msg}", file=sys.stderr); sys.exit(2)

if not TOKEN:
    fail("EODHD_API_TOKEN missing (set it in /opt/daily-report/.env)")

if not os.path.isfile(VENDOR):
    warn(f"AT1 vendor file not found: {VENDOR}")
    # still write an empty skeleton so the renderer doesn't break
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["name","clean_price","coupon_pct","next_call_date","delta_1d","isin"])
    print(f"[INFO] Wrote empty normalized file at {OUT}")
    sys.exit(0)

def pick(cols, pattern):
    rx = re.compile(pattern, re.I)
    for c in cols:
        if rx.search(c or ""):
            return c
    return None

def decommas(x):
    x = (x or "").strip()
    return x.replace(",", "")

def norm_date(s):
    s = (s or "").strip()
    if not s:
        return ""
    # accept YYYY-MM-DD already
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s
    # try DD/MM/YYYY or DD-MM-YYYY or DD/MM/YY
    m = re.match(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})$", s)
    if m:
        d, mth, y = map(int, m.groups())
        if y < 100: y += 2000
        try:
            return dt.date(y, mth, d).isoformat()
        except Exception:
            return s
    return s

def http_json(url, timeout=20):
    req = Request(url, headers={"User-Agent": "curl/8"})
    try:
        with urlopen(req, timeout=timeout) as r:
            data = r.read()
            return json.loads(data.decode("utf-8", "replace"))
    except HTTPError as e:
        if e.code != 404:
            warn(f"http {e.code} {url}")
        return None
    except URLError as e:
        warn(f"urlerr {e} {url}")
        return None

def fetch_eod_close_and_d1(isin):
    # Try EUBOND first (non-US), then BOND (US). We request two most recent bars.
    for exch in ("EUBOND", "BOND"):
        ticker = f"{isin}.{exch}"
        url = f"https://eodhd.com/api/eod/{ticker}?api_token={TOKEN}&fmt=json&order=d&limit=2"
        j = http_json(url)
        if isinstance(j, list) and j:
            try:
                px0 = float(j[0]["close"])
                d1  = ""
                if len(j) > 1 and j[1].get("close") not in (None, "", "NA"):
                    px1 = float(j[1]["close"])
                    if px1 != 0:
                        d1 = round((px0 - px1) / px1 * 100.0, 2)
                return round(px0, 2), d1
            except Exception:
                continue
    return "", ""  # not found

# --- read vendor file ---
with open(VENDOR, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)
if not rows:
    fail(f"Vendor file {VENDOR} has no rows")

cols = rows[0].keys()
k_name = pick(cols, r"^(name|issuer|security|bond|description)")
k_cpn  = pick(cols, r"^(coupon(_pct)?|cpn|rate)")
k_call = pick(cols, r"(first|next).*call")
k_isin = pick(cols, r"^(isin|identifier|id)$")

missing_keys = [k for k in [k_name, k_cpn, k_call, k_isin] if not k]
if missing_keys:
    warn(f"Header auto-detect: name:{k_name} cpn:{k_cpn} call:{k_call} isin:{k_isin}")
    fail("Could not detect all required columns (name/coupon/next call/isin) in vendor CSV")

# --- build output ---
os.makedirs(os.path.dirname(OUT), exist_ok=True)
out_rows = []
hit = miss = 0

for r in rows:
    name  = re.sub(r"\s{2,}", " ", (r.get(k_name) or "").strip())
    isin  = (r.get(k_isin) or "").strip()
    cpn_s = decommas(r.get(k_cpn))
    call  = norm_date(r.get(k_call))
    if not isin:
        continue

    px, d1 = fetch_eod_close_and_d1(isin)
    if px == "":
        miss += 1
    else:
        hit  += 1

    # coupon numeric, keep as text if blank
    try:
        cpn = float(cpn_s) if cpn_s else ""
    except:
        cpn = cpn_s

    out_rows.append([
        name,
        f"{px}" if px != "" else "",
        f"{cpn}" if cpn != "" else "",
        call,
        f"{d1}" if d1 != "" else "",
        isin
    ])

with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["name","clean_price","coupon_pct","next_call_date","delta_1d","isin"])
    w.writerows(out_rows)

log(f"Wrote normalized AT1 to {OUT}")
log(f"Rows: {len(out_rows)}; priced: {hit}; missing: {miss}")
log("Note: EODHD bond data is EOD only (no real-time) via ISIN.EUBOND / ISIN.BOND.")
