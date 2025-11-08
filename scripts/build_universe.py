#!/usr/bin/env python3
import csv, json
from datetime import date
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from app.utils.eodhd import fundamentals, exchange_symbols, extract_components, safe_mktcap

TODAY = date.today().isoformat()
ROOT  = Path(".")
OUT   = ROOT / f"out/universe/{TODAY}"
OUT.mkdir(parents=True, exist_ok=True)

CURATED_DIR = ROOT / "config"  # optional curated lists
CURATED_DIR.mkdir(exist_ok=True)

def ticker_key(code: str, exch: str) -> str:
    suffix = exch
    if exch.upper() in ("LSE","IOB"): suffix = "L"
    if exch.upper() in ("SIX","SWX"): suffix = "SW"
    return f"{code}.{suffix}"

def load_curated(name: str) -> List[str]:
    f = CURATED_DIR / f"{name}.csv"
    if not f.exists(): return []
    out=[]
    with f.open(encoding="utf-8") as fh:
        r = csv.DictReader(fh)
        for row in r:
            t = (row.get("ticker") or "").strip()
            if t: out.append(t)
    return out

def fundamentals_map(tickers: List[str]) -> Dict[str, dict]:
    out={}
    for t in tickers:
        try: out[t]=fundamentals(t)
        except Exception: pass
    return out

def best_name(f: dict) -> str:
    g=f.get("General",{})
    return g.get("Name") or f.get("Code") or ""

def best_isin(f: dict) -> str:
    g=f.get("General",{})
    return g.get("ISIN") or g.get("ISINCode") or ""

def best_ccy(f: dict) -> str:
    g=f.get("General",{})
    return g.get("Currency") or g.get("CurrencyCode") or ""

def rank_by_mktcap(fmap: Dict[str,dict], limit: int) -> List[Tuple[str,float]]:
    rows=[]
    for t,f in fmap.items():
        mc=safe_mktcap(f)
        if mc: rows.append((t,mc))
    rows.sort(key=lambda x:x[1], reverse=True)
    return rows[:limit]

def bucket_rows(tickers: List[str], bucket: str) -> List[Dict[str,str]]:
    fmap = fundamentals_map(tickers)
    rows=[]
    for t,f in fmap.items():
        rows.append({
            "isin":  best_isin(f),
            "ticker":t,
            "name":  best_name(f),
            "ccy":   best_ccy(f),
            "bucket":bucket,
            "mktcap": str(safe_mktcap(f) or "")
        })
    return rows

def dedupe_keep_max(rows: List[Dict[str,str]]) -> List[Dict[str,str]]:
    by_t={}
    for r in rows:
        t=r["ticker"]; mc=float(r["mktcap"] or 0)
        if (t not in by_t) or mc>float(by_t[t]["mktcap"] or 0):
            by_t[t]=r
    return list(by_t.values())

def write_csv(rows: List[Dict[str,str]]):
    fn = OUT/"universe.csv"
    hdr=["isin","ticker","name","ccy","bucket","mktcap"]
    with fn.open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=hdr); w.writeheader(); w.writerows(rows)
    return fn

def write_summary(counts: Dict[str,int]):
    (OUT/"summary.json").write_text(
        json.dumps({"as_of":TODAY,"counts":counts}, indent=2), encoding="utf-8"
    )

def fetch_index_members(index_ticker: str) -> List[str]:
    try:
        c = extract_components(fundamentals(index_ticker))
        if not c: return []
        return [ticker_key((i.get("Code") or "").strip(), (i.get("Exchange") or "").strip())
                for i in c if i.get("Code") and i.get("Exchange")]
    except Exception:
        return []

def swiss_list():
    from app.utils.eodhd import exchange_symbols
    # Try SW (XSWX) then VX; return [] if vendor sulks
    for ex in ("SW", "VX"):
        try:
            return [
                d["Code"] + ".SW"
                for d in exchange_symbols(ex)
                if d.get("Type") == "Common Stock"
            ]
        except Exception:
            pass
    return []


def rank_by_mktcap_limited(symbols, top_k, max_fund_calls=900):
    from app.utils.eodhd import fundamentals, safe_mktcap
    out = {}
    calls = 0
    for t in symbols:
        if t in out:
            continue
        try:
            f = fundamentals(t)
            mc = safe_mktcap(f)
            if mc:
                out[t] = mc
        except Exception:
            pass
        calls += 1
        if len(out) >= top_k and calls >= max_fund_calls:
            break
    return sorted(out.items(), key=lambda kv: kv[1], reverse=True)[:top_k]


def euro_component_list():
    from app.utils.eodhd import fundamentals, extract_components
    # Aliases per index (first that returns Components wins)
    INDEX_CANDIDATES = {
        "DAX":  ["DAX.XETRA", "^GDAXI"],
        "CAC":  ["PX1.PA", "^FCHI"],
        "AEX":  ["AEX.AS", "^AEX"],
        "IBEX": ["IBEX.MC", "^IBEX"],
        "MIB":  ["FTSEMIB.MI", "^FTSEMIB"],
        "BEL":  ["BEL20.BR", "^BFX"],
        "PSI":  ["PSI20.LS", "^PSI20"],
    }
    out = []
    for name, tickers in INDEX_CANDIDATES.items():
        comp = []
        for t in tickers:
            try:
                c = extract_components(fundamentals(t))
                if c:
                    comp = c
                    break
            except Exception:
                pass
        if comp:
            # build exchange-qualified tickers via the script's ticker_key()
            from scripts.build_universe import ticker_key  # self-import ok at runtime
            out += [
                ticker_key((i.get("Code") or "").strip(), (i.get("Exchange") or "").strip())
                for i in comp if i.get("Code") and i.get("Exchange")
            ]
    # de-dup preserving order
    seen, uniq = set(), []
    for t in out:
        if t not in seen:
            seen.add(t); uniq.append(t)
    return uniq

def main():
    all_rows=[]
    counts={"core":0,"ad_hoc":100,"uk":0,"ch":0,"ez":0,"us":0,"uranium":20}

    # FTSE100
    ftse100 = fetch_index_members("UKX.L") or load_curated("ftse100")
    if not ftse100:
        lse = [ s["Code"]+".L" for s in exchange_symbols("LSE") if s.get("Type")=="Common Stock" ]
        ranked = rank_by_mktcap(fundamentals_map(lse), 100)
        ftse100 = [t for t,_ in ranked]
    rows = bucket_rows(ftse100, "FTSE100"); counts["uk"]+=len(rows); all_rows+=rows

    # FTSE250 Top 100 (next after FTSE100)
    ftse250 = fetch_index_members("MCX.L") or load_curated("ftse250")
    if not ftse250:
        lse = [ s["Code"]+".L" for s in exchange_symbols("LSE") if s.get("Type")=="Common Stock" ]
        ranked = [t for t,_ in rank_by_mktcap(fundamentals_map(lse), 250)]
        ftse250 = [t for t in ranked if t not in set(ftse100)][:100]
    rows = bucket_rows(ftse250, "FTSE250_TOP100"); counts["uk"]+=len(rows); all_rows+=rows

    # Swiss 30
    smi = fetch_index_members("SMI.SW") or load_curated("smi30")
    if not smi:
        six = swiss_list()
        smi = [t for t,_ in rank_by_mktcap(fundamentals_map(six), 30)]
    rows = bucket_rows(smi, "SWISS30"); counts["ch"]+=len(rows); all_rows+=rows

    # Euro 200 (coarse)
    euro_ex = ["XETRA","PA","BR","AS","MI","LS"]
    euro_all=[]
    suf = {"XETRA":".DE","F":".F","PA":".PA","BR":".BR","AS":".AS","MI":".MI","LS":".LS"}
    for ex in euro_ex:
        try:
            syms = exchange_symbols(ex)
            euro_all += [ s["Code"] + suf.get(ex,"") for s in syms if s.get("Type")=="Common Stock" ]
        except Exception:
            pass
    euro_top = [t for t,_ in rank_by_mktcap_limited(euro_all, 220, max_fund_calls=900)][:200]
    rows = bucket_rows(euro_top, "EURO200"); counts["ez"]+=len(rows); all_rows+=rows

    # US fill to 800
    target = 800
    have = len({r["ticker"] for r in all_rows})
    need = max(0, target - have)
    if need:
        us=[]
        for ex in ("NYSE","NASDAQ"):
            try:
                us += [ s["Code"] for s in exchange_symbols(ex) if s.get("Type")=="Common Stock" ]
            except Exception:
                pass
        us_fill = [t for t,_ in rank_by_mktcap(fundamentals_map(us), need+50)
                   if t not in {r["ticker"] for r in all_rows}][:need]
        rows = bucket_rows(us_fill, "US_FILL"); counts["us"]+=len(rows); all_rows+=rows

    all_rows = dedupe_keep_max(all_rows)
    counts["core"] = len({r["ticker"] for r in all_rows})
    fn = write_csv(all_rows)
    write_summary(counts)
    print(f"universe -> {fn} ({counts})")

if __name__ == "__main__":
    main()
