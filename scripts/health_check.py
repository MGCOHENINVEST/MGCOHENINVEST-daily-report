#!/usr/bin/env python3
import sys, json, datetime
from pathlib import Path

BASE = Path("/opt/daily-report")
TODAY = datetime.date.today().isoformat()
OUT = BASE / "out" / "daily" / TODAY

def load(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return None

def must_exist(path):
    if not path.exists():
        print(f"[FAIL] missing: {path}", flush=True); return False
    if path.is_file() and path.stat().st_size == 0:
        print(f"[FAIL] empty:   {path}", flush=True); return False
    return True

def main():
    ok = True
    # required files
    need = [
        OUT / "daily.json",
        OUT / "commodities.json",
        OUT / "macro_uk.json",
        OUT / "macro_us.json",
        OUT / "curves_uk.json",
        OUT / "curves_us.json",
        OUT / "universe.json",
        OUT / "preview.html",
    ]
    for p in need:
        ok &= must_exist(p)

    if not ok:
        sys.exit(2)

    uni = load(OUT / "universe.json") or {}
    counts = uni.get("counts", {})
    total = uni.get("count", sum(counts.values()) if counts else 0)

    comm = load(OUT / "commodities.json") or {}
    n_comm = len(comm.get("commodities", []) or [])

    cu_uk = load(OUT / "curves_uk.json") or {}
    cu_us = load(OUT / "curves_us.json") or {}

    n_cu_uk = len(cu_uk.get("points", []) or [])
    n_cu_us = len(cu_us.get("points", []) or [])

    # thresholds — bump later when you load full US universe
    if total < 150:
        print(f"[FAIL] universe too small: {total} < 150", flush=True); ok = False
    if n_comm < 1:
        print(f"[FAIL] commodities rows: {n_comm} < 1", flush=True); ok = False
    if n_cu_uk < 1 or n_cu_us < 1:
        print(f"[FAIL] curves points: UK={n_cu_uk} US={n_cu_us}", flush=True); ok = False

    if ok:
        print(f"[OK] {TODAY} universe={total} commodities={n_comm} curves(UK/US)={n_cu_uk}/{n_cu_us}", flush=True)
        sys.exit(0)
    sys.exit(3)

if __name__ == "__main__":
    sys.exit(main())
