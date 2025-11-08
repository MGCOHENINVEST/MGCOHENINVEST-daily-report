#!/usr/bin/env python3
import os, json, time, urllib.request, urllib.error, csv, pathlib
root = pathlib.Path("/opt/daily-report")
out = root / "out/data/fx_pairs.csv"
base = os.getenv("EODHD_BASE","https://eodhd.com")
token = os.getenv("EODHD_API_TOKEN") or os.getenv("EODHD_API_KEY")
pairs = {
  "GBPUSD":"GBPUSD.FOREX", "EURUSD":"EURUSD.FOREX", "USDCHF":"USDCHF.FOREX",
  "EURGBP":"EURGBP.FOREX", "GBPCHF":"GBPCHF.FOREX", "EURCHF":"EURCHF.FOREX",
  "USDJPY":"USDJPY.FOREX", "CHFJPY":"CHFJPY.FOREX",
}
def get(sym):
    url = f"{base}/api/real-time/{sym}?api_token={token}&fmt=json"
    try:
        with urllib.request.urlopen(url, timeout=8) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"code": sym, "close": "", "change_p": "", "error": str(e)}
rows=[]
for k,v in pairs.items():
    d = get(v)
    last = d.get("close") or d.get("Close") or d.get("last") or ""
    chg = d.get("change_p") or d.get("Change_p") or d.get("change") or ""
    rows.append({"pair":k,"last":last,"chg_1d":chg,"wtd":""})
    time.sleep(0.2)
out.parent.mkdir(parents=True, exist_ok=True)
with out.open("w", newline="", encoding="utf-8") as f:
    w=csv.DictWriter(f, fieldnames=["pair","last","chg_1d","wtd"])
    w.writeheader(); w.writerows(rows)
print(f"[fx_fetch_eodhd] wrote {out} rows={len(rows)}")
