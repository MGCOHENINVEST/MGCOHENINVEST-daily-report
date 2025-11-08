#!/usr/bin/env python3
"""
Builds normalized AT1 CSV the renderer expects:
  name, clean_price, coupon_pct, next_call_date, delta_1d, isin

Inputs (optional, from .env):
  AT1_VENDOR_FILE=/opt/daily-report/in/at1_vendor.csv
    - columns like: Sedol,Identifier,issuer,Next Call Date,Currency,cpn
  AT1_PRICE_FILE=/opt/daily-report/in/at1_prices.csv
    - columns like: isin, clean_price, delta_1d
Output:
  AT1_FILE=/opt/daily-report/out/data/at1.csv
"""
import os, sys, csv, re, datetime as dt

ROOT="/opt/daily-report"
VENDOR=os.environ.get("AT1_VENDOR_FILE", f"{ROOT}/in/at1_vendor.csv")
PRICES=os.environ.get("AT1_PRICE_FILE", f"{ROOT}/in/at1_prices.csv")
OUT=os.environ.get("AT1_FILE", f"{ROOT}/out/data/at1.csv")

def pick(cols, pat):
    rx=re.compile(pat,re.I)
    for c in cols:
        if rx.search(c or ""): return c
    return None

def load_csv(path):
    if not os.path.exists(path): return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def decommas(x):
    x=(x or "").strip()
    return x.replace(",","")

def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    vendor=load_csv(VENDOR)
    prices=load_csv(PRICES)
    if not vendor:
        # still write a file so pipeline keeps going
        with open(OUT,"w",newline="",encoding="utf-8") as f:
            csv.writer(f).writerow(["name","clean_price","coupon_pct","next_call_date","delta_1d","isin"])
        print(f"[WARN] AT1 vendor file not found: {VENDOR}")
        print(f"Wrote empty normalized file at {OUT}")
        return

    vcols=vendor[0].keys()
    k_isin = pick(vcols, r"^(isin|identifier|id)$")
    k_name = pick(vcols, r"^(name|issuer|security|bond|description|instrument)")
    k_cpn  = pick(vcols, r"^(coupon(_pct)?|cpn|rate)")
    k_call = pick(vcols, r"(first|next).*call")
    if not (k_isin and k_name and k_cpn and k_call):
        print("[ERROR] Could not map vendor columns (need ISIN, name, coupon, next call).", file=sys.stderr)
        sys.exit(1)

    price_map={}
    if prices:
        pcols=prices[0].keys()
        p_isin = pick(pcols, r"^(isin|identifier|id)$") or "isin"
        p_px   = pick(pcols, r"^(clean[_ ]?price|mid|price|px|cleanPx)") or "clean_price"
        p_d1   = pick(pcols, r"^(delta[_ ]?1d|d1|change[_ ]?1d|chg1d|bp)") or "delta_1d"
        for r in prices:
            isin=(r.get(p_isin) or "").strip()
            if not isin: continue
            price_map[isin]={
                "clean_price": decommas(r.get(p_px)),
                "delta_1d":    decommas(r.get(p_d1)),
            }

    out=[]
    for r in vendor:
        isin=(r.get(k_isin) or "").strip()
        if not isin: continue
        name=(r.get(k_name) or "").strip()
        cpn=decommas(r.get(k_cpn))
        call=(r.get(k_call) or "").strip()
        # normalise date
        m=re.match(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})$", call)
        if m:
            d,mn,y=map(int,m.groups())
            if y<100: y+=2000
            try: call=dt.date(y,mn,d).isoformat()
            except: pass
        px=""; d1=""
        if isin in price_map:
            px=price_map[isin]["clean_price"]
            d1=price_map[isin]["delta_1d"]
        out.append([name, px, cpn, call, d1, isin])

    with open(OUT,"w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["name","clean_price","coupon_pct","next_call_date","delta_1d","isin"])
        w.writerows(out)
    miss=sum(1 for _,px,_,_,_,_ in out if not px)
    print(f"[INFO] Wrote normalized AT1 to {OUT}")
    print(f"[INFO] Rows: {len(out)}; with missing price: {miss}")

if __name__=="__main__":
    main()
