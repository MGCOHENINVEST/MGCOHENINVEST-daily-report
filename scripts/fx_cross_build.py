#!/usr/bin/env python3
import csv, pathlib, math
root = pathlib.Path("/opt/daily-report")
src = root / "out/data/fx_pairs.csv"
dst = root / "out/data/fx_cross.csv"
if not src.exists():
    print("[fx_cross] missing fx_pairs.csv"); exit(0)

rates={}
with src.open() as f:
    for r in csv.DictReader(f):
        p=str(r["pair"]).upper(); v=r.get("last") or ""
        try: rates[p]=float(v)
        except: pass

# Build USD legs for GBP, EUR, CHF, JPY
legs={}
def inv(x): return (1.0/x) if x and x!=0 else None

if "GBPUSD" in rates: legs[("GBP","USD")] = rates["GBPUSD"]; legs[("USD","GBP")] = inv(rates["GBPUSD"])
if "EURUSD" in rates: legs[("EUR","USD")] = rates["EURUSD"]; legs[("USD","EUR")] = inv(rates["EURUSD"])
if "USDCHF" in rates: legs[("USD","CHF")] = rates["USDCHF"]; legs[("CHF","USD")] = inv(rates["USDCHF"])
if "USDJPY" in rates: legs[("USD","JPY")] = rates["USDJPY"]; legs[("JPY","USD")] = inv(rates["USDJPY"])

ccy=["USD","EUR","GBP","CHF","JPY"]
rows=[]
for a in ccy:
    row={"base":a}
    for b in ccy:
        if a==b: row[b]="—"
        else:
            r=None
            if (a,b) in legs: r=legs[(a,b)]
            elif (a,"USD") in legs and ("USD",b) in legs: r=legs[(a,"USD")]*legs[("USD",b)]
            elif (b,"USD") in legs and ("USD",a) in legs: r=1.0/(legs[(b,"USD")]*legs[("USD",a)])
            row[b] = f"{r:.4f}" if isinstance(r,(int,float)) and r>0 else ""
    rows.append(row)

dst.parent.mkdir(parents=True, exist_ok=True)
with dst.open("w", newline="", encoding="utf-8") as f:
    w=csv.DictWriter(f, fieldnames=["base"]+ccy)
    w.writeheader(); w.writerows(rows)
print(f"[fx_cross] wrote {dst}")
