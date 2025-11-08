#!/usr/bin/env python3
import os, csv, json, datetime as dt, time
from urllib.request import urlopen
from urllib.parse import quote
from urllib.error import URLError, HTTPError

BASE="/opt/daily-report"
V=f"{BASE}/in/at1_vendor.csv"
P=f"{BASE}/in/at1_prices.csv"
NORM=f"{BASE}/out/data/at1.csv"  # use yesterday’s normalized as carry

def get_api():
    for k in ("EODHD_API_KEY","EODHD_API_TOKEN"):
        v=os.environ.get(k)
        if v: return v.strip().strip('\'"')
    if os.path.exists(f"{BASE}/.env"):
        for line in open(f"{BASE}/.env"):
            s=line.strip()
            if s.startswith(("EODHD_API_KEY","EODHD_API_TOKEN")):
                return s.split("=",1)[1].strip().strip('\'"')
    return None

API=get_api()

def safe_open(url, timeout=15):
    try:
        with urlopen(url, timeout=timeout) as r:
            return r.read().decode("utf-8","ignore")
    except (HTTPError, URLError, TimeoutError, ValueError):
        return None

def fetch_eod(ticker, days=21):
    today=dt.date.today(); frm=(today-dt.timedelta(days=days)).isoformat()
    url=f"https://eodhd.com/api/eod/{quote(ticker)}?from={frm}&to={today}&order=d&fmt=json&api_token={API}"
    raw=safe_open(url, timeout=15)
    if not raw: return None
    try:
        data=json.loads(raw)
    except Exception:
        return None
    if isinstance(data, dict) and data.get("code"):  # API error payload
        return None
    rows=sorted(data, key=lambda x:x.get("date",""), reverse=True)
    for row in rows:
        c=row.get("close")
        try:
            c=float(c)
            if c>0: return (c, row.get("date"))
        except Exception:
            pass
    return None

def fetch_rt(ticker):
    url=f"https://eodhd.com/api/real-time/{quote(ticker)}?fmt=json&api_token={API}"
    raw=safe_open(url, timeout=10)
    if not raw: return None
    try:
        d=json.loads(raw)
        px = d.get("close") or d.get("previousClose") or d.get("open")
        if px is None: return None
        px=float(px)
        if px<=0: return None
        ts = d.get("timestamp") or d.get("date")
        if isinstance(ts,(int,float)):
            ts=dt.datetime.utcfromtimestamp(ts).date().isoformat()
        return (px, ts or dt.date.today().isoformat())
    except Exception:
        return None

def try_price(isin):
    for t in (f"{isin}.EUBOND", f"{isin}.BOND"):
        got = fetch_eod(t)
        if got: return got[0], got[1], f"EODHD:{t}"
        time.sleep(0.12)
        got = fetch_rt(t)
        if got: return got[0], got[1], f"EODHD_RT:{t}"
        time.sleep(0.12)
    return None, None, None

vendor=list(csv.DictReader(open(V,newline='')))
isins=[(r.get("ISIN") or "").strip().upper() for r in vendor if (r.get("ISIN") or "").strip()]

prior={}
if os.path.exists(P):
    for r in csv.DictReader(open(P,newline='')):
        prior[(r.get("ISIN") or "").strip().upper()] = r

# carry from normalized
carry={}
if os.path.exists(NORM):
    for r in csv.DictReader(open(NORM,newline='')):
        isin=(r.get('isin') or r.get('ISIN') or '').strip().upper()
        px=(r.get('clean_price') or r.get('Price') or '').strip()
        if isin and px: carry[isin]=px

rows=[]; hits=0
for isin in isins:
    # keep any existing manual/non-empty price
    if isin in prior and (prior[isin].get("Price") or "").strip():
        r=prior[isin]
        rows.append({'ISIN':isin,'Price':r.get('Price',''),'Accrued':r.get('Accrued',''),
                     'LastPriceDate':r.get('LastPriceDate',''),'Source':r.get('Source','Manual')})
        continue
    px=d=src=None
    if API:
        px,d,src = try_price(isin)
    if px:
        hits+=1
        rows.append({'ISIN':isin,'Price':f"{px:.4f}",'Accrued':"0.00",'LastPriceDate':d or dt.date.today().isoformat(),'Source':src})
    else:
        c=carry.get(isin,"")
        rows.append({'ISIN':isin,'Price':c,'Accrued':"",'LastPriceDate':dt.date.today().isoformat(),'Source':("carry" if c else "")})

with open(P,'w',newline='') as f:
    w=csv.DictWriter(f, fieldnames=['ISIN','Price','Accrued','LastPriceDate','Source'])
    w.writeheader(); w.writerows(rows)

print(f"Priced {hits}/{len(isins)} (kept prior; carried if present) -> {P}")
