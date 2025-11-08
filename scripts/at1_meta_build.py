#!/usr/bin/env python3
import csv, os, re, io

BASE="/opt/daily-report"
COUP=f"{BASE}/in/at1_coupon_uploaded.csv"   # source
OUT=f"{BASE}/out/data/at1_meta.csv"
os.makedirs(f"{BASE}/out/data", exist_ok=True)

def canon(s): return re.sub(r'[^a-z0-9]+','', (s or '').lower())
def pick(r,*ns):
    for n in ns:
        for k in r:
            if canon(k)==canon(n) and r[k].strip(): return r[k].strip()
    return ''

def header_stream(path):
    raw=open(path,'rb').read().decode('utf-8','ignore').splitlines()
    # find first row that looks like the header
    hdr_idx=0
    for i in range(min(40, len(raw))):
        row=[c.strip().lower() for c in re.split(r'[,\t;|]', raw[i])]
        if 'identifier' in row or 'isin' in row:
            hdr_idx=i; break
    return io.StringIO("\n".join(raw[hdr_idx:]))

if not os.path.exists(COUP):
    open(OUT,'w').write("ISIN,AmountOutstanding,MinPiece,Spread_bp,Moody,SP,Fitch,IndustryGroup,BBComposite,CoCo,PaymentRank\n")
    print("Source not found; wrote header only:", OUT)
    raise SystemExit(0)

# autodetect delimiter
sample = open(COUP,'rb').read().decode('utf-8','ignore')
try: delim = csv.Sniffer().sniff(sample, delimiters=',;\t|').delimiter
except: delim = ','

rows=list(csv.DictReader(header_stream(COUP), delimiter=delim))
meta=[]
for r in rows:
    isin=(pick(r,'isin','identifier') or '').upper()
    if not isin: continue
    meta.append({
      'ISIN': isin,
      'AmountOutstanding': pick(r,'amt outstanding','amount outstanding'),
      'MinPiece': pick(r,'min piece','minpiece'),
      'Spread_bp': pick(r,'yas yld spread','spread'),
      'Moody': pick(r,'rtg_moody','moody'),
      'SP': pick(r,'rtg_sp','s&p','sp'),
      'Fitch': pick(r,'rtg_fitch','fitch'),
      'IndustryGroup': pick(r,'industry_group'),
      'BBComposite': pick(r,'bb_composite','bb composite'),
      'CoCo': pick(r,'capital_contingent_security','coco'),
      'PaymentRank': pick(r,'payment_rank'),
    })

with open(OUT,'w',newline='') as f:
    w=csv.DictWriter(f, fieldnames=['ISIN','AmountOutstanding','MinPiece','Spread_bp','Moody','SP','Fitch','IndustryGroup','BBComposite','CoCo','PaymentRank'])
    w.writeheader(); w.writerows(meta)

print(f"Wrote sidecar -> {OUT}  rows={len(meta)}")
