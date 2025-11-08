from __future__ import annotations
import os, sys, csv, json
from pathlib import Path
from datetime import date
from typing import List, Dict, Tuple, Iterable

# vendor helpers (we already have these on the server)
from app.utils.eodhd import (
    exchange_symbols, fundamentals, extract_components, safe_mktcap
)

# --------- knobs (env overrides) ----------
EURO_TARGET           = int(os.environ.get("EURO_TARGET", "200"))
EURO_MAX_FUND_CALLS   = int(os.environ.get("EURO_MAX_FUND_CALLS", "600"))   # hard cap for Euro ranking fallback
CH_MAX_FUND_CALLS     = int(os.environ.get("CH_MAX_FUND_CALLS", "150"))    # Swiss cap
US_MAX_FUND_CALLS     = int(os.environ.get("US_MAX_FUND_CALLS", "900"))    # US fill cap
HEARTBEAT_EVERY       = int(os.environ.get("HEARTBEAT_EVERY", "25"))       # progress prints to stderr
OUT_DIR               = Path(os.environ.get("OUT_DIR", "out/universe"))

TODAY = date.today().isoformat()
DEST  = OUT_DIR / TODAY
DEST.mkdir(parents=True, exist_ok=True)

# --------- tiny utils ----------
def hb(tag: str, i: int, n: int):
    if HEARTBEAT_EVERY and i % HEARTBEAT_EVERY == 0:
        print(f"HEARTBEAT {tag}: {i}/{n}", file=sys.stderr, flush=True)

def load_csv_list(path: Path) -> List[str]:
    if not path.exists(): return []
    out=[]
    with path.open() as f:
        r=csv.DictReader(f)
        for row in r:
            t=(row.get("ticker") or "").strip()
            if t: out.append(t)
    return out

def write_csv(rows: List[Dict[str,str]]) -> Path:
    dest = DEST / "universe.csv"
    with dest.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["isin","ticker","name","ccy","bucket","mktcap"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return dest

def write_summary(counts: Dict[str,int]) -> Path:
    dest = DEST / "summary.json"
    with dest.open("w") as f:
        json.dump({"as_of": TODAY, "counts": counts}, f, indent=2)
    return dest

def bucket_rows(tickers: Iterable[str], bucket: str) -> List[Dict[str,str]]:
    out=[]
    for t in tickers:
        out.append({"isin":"","ticker":t,"name":"","ccy":"","bucket":bucket,"mktcap":""})
    return out

def dedupe_keep_order(seq: Iterable[str]) -> List[str]:
    seen=set(); out=[]
    for x in seq:
        if x not in seen:
            seen.add(x); out.append(x)
    return out

# ---------- ranking with call budget ----------
def rank_by_mktcap_limited(symbols: List[str], top_k: int, max_fund_calls: int, tag: str) -> List[Tuple[str,float]]:
    out: Dict[str,float] = {}
    calls=0
    n=len(symbols)
    for i,t in enumerate(symbols, 1):
        hb(tag, i, n)
        if t in out:  # unlikely
            continue
        try:
            f = fundamentals(t)
            mc = safe_mktcap(f)
            if mc: out[t]=mc
        except Exception:
            pass
        calls += 1
        if len(out) >= top_k and calls >= max_fund_calls:
            break
    return sorted(out.items(), key=lambda kv: kv[1], reverse=True)[:top_k]

# ---------- curated helpers ----------
CFG_EURO = Path("config/euro")
CURATED_EURO_LISTS = {
    "dax":  CFG_EURO/"dax.csv",
    "cac":  CFG_EURO/"cac.csv",
    "aex":  CFG_EURO/"aex.csv",
    "ibex": CFG_EURO/"ibex.csv",
    "mib":  CFG_EURO/"mib.csv",
    "bel":  CFG_EURO/"bel.csv",
    "psi":  CFG_EURO/"psi.csv",
}

def curated_euro() -> List[str]:
    tickers=[]
    for _,p in CURATED_EURO_LISTS.items():
        tickers += load_csv_list(p)
    return dedupe_keep_order(tickers)

# ---------- universe build ----------
def main():
    rows=[]
    counts={"core":0,"ad_hoc":100,"uk":0,"ch":0,"ez":0,"us":0,"uranium":20}

    # FTSE100 (index components or curated ftse100.csv handled earlier by your other builder;
    # we keep the seed small here, you can merge lists later)
    ftse100=[]
    try:
        comps = extract_components(fundamentals("UKX.LSE")) or extract_components(fundamentals("UKX.L"))
        if comps:
            for i,c in enumerate(comps, 1):
                hb("FTSE100", i, len(comps))
                code = (c.get("Code") or "").strip()
                ex   = (c.get("Exchange") or "").strip()
                if not code or not ex: continue
                suf = ".L" if ex in ("LSE","XLON","L") else ""
                ftse100.append(code + suf)
    except Exception:
        pass
    ftse100 = dedupe_keep_order(ftse100)[:100]
    rows += bucket_rows(ftse100, "FTSE100"); counts["uk"]+=len(ftse100)

    # FTSE250 next 100 by mkt cap after FTSE100 (fallback: curated config/ftse250.csv if you want)
    ftse250=[]
    try:
        comps = extract_components(fundamentals("MCX.LSE")) or extract_components(fundamentals("MCX.L"))
        if comps:
            for i,c in enumerate(comps, 1):
                hb("FTSE250", i, len(comps))
                code=(c.get("Code") or "").strip()
                if code: ftse250.append(code + ".L")
    except Exception:
        pass
    ftse250 = [t for t in dedupe_keep_order(ftse250) if t not in set(ftse100)][:100]
    rows += bucket_rows(ftse250, "FTSE250_TOP100"); counts["uk"]+=len(ftse250)

    # Swiss 30 — try SMI components; fallback to exchange list + limited ranking
    smi=[]
    try:
        comps = extract_components(fundamentals("SMI.SW")) or extract_components(fundamentals("^SSMI"))
        if comps:
            for i,c in enumerate(comps, 1):
                hb("SMI", i, len(comps))
                code=(c.get("Code") or "").strip()
                if code: smi.append(code + ".SW")
    except Exception:
        pass
    if not smi:
        try:
            sw = [ d["Code"] + ".SW" for d in exchange_symbols("SW") if d.get("Type")=="Common Stock" ]
        except Exception:
            sw = []
        smi = [t for t,_ in rank_by_mktcap_limited(sw, 30, CH_MAX_FUND_CALLS, "SMI_FALLBACK")]
    rows += bucket_rows(smi, "SWISS30"); counts["ch"]+=len(smi)

    # Euro 200 — curated lists first; if empty, fallback to exchange lists + capped ranking
    euro = curated_euro()
    if euro:
        euro = euro[:EURO_TARGET]
    else:
        euro_ex = ["XETRA","PA","BR","AS","MI","LS"]  # drop Frankfurt "F" to reduce junk
        euro_all=[]
        suf = {"XETRA":".XETRA","PA":".PA","BR":".BR","AS":".AS","MI":".MI","LS":".LS"}
        for ex in euro_ex:
            try:
                syms = exchange_symbols(ex)
                euro_all += [ s["Code"] + suf.get(ex,"") for s in syms if s.get("Type")=="Common Stock" ]
            except Exception:
                pass
        euro = [t for t,_ in rank_by_mktcap_limited(dedupe_keep_order(euro_all), EURO_TARGET, EURO_MAX_FUND_CALLS, "EURO_FALLBACK")]
    rows += bucket_rows(euro, "EURO200"); counts["ez"]+=len(euro)

    # US fill to 800
    target = 800
    have = len({r["ticker"] for r in rows})
    need = max(0, target - have)
    if need:
        us=[]
        for ex in ("NYSE","NASDAQ"):
            try:
                syms = exchange_symbols(ex)
                us += [ s["Code"] for s in syms if s.get("Type")=="Common Stock" ]
            except Exception:
                pass
        ranked = rank_by_mktcap_limited(dedupe_keep_order(us), need+100, US_MAX_FUND_CALLS, "US_FILL")
        us_fill = [t for t,_ in ranked if t not in {r["ticker"] for r in rows}][:need]
        rows += bucket_rows(us_fill, "US_FILL"); counts["us"]+=len(us_fill)

    # finalize
    core = len({r["ticker"] for r in rows})
    counts["core"] = core
    csv_path = write_csv(rows)
    write_summary(counts)
    print(f"universe -> {csv_path} ({counts})")

if __name__ == "__main__":
    main()
