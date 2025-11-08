#!/usr/bin/env python3
import os, sys, subprocess, json, shutil, datetime, csv
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SCRIPTS = BASE / "scripts"
OUTDIR = BASE / "out" / "daily" / datetime.date.today().isoformat()
TMP_HTML = Path("/tmp/email_sections.html")
PREVIEW_HTML = OUTDIR / "preview.html"

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

def colorize(val):
    return f"{GREEN}{val}{RESET}" if val else f"{RED}{val}{RESET}"

def run(label, args, out_file=None):
    print(f"== {label} ==")
    try:
        if out_file:
            with open(out_file, "w") as f:
                subprocess.run(args, check=True, stdout=f)
        else:
            subprocess.run(args, check=True)
    except subprocess.CalledProcessError as e:
        print(f"[WARN] {label} failed: {e}")

def count_json(path, key):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if key in data:
            return len(data[key])
        return data.get("count", 0)
    except Exception:
        return 0

def show_json_counts():
    daily = OUTDIR / "daily.json"
    if daily.exists():
        try:
            data = json.loads(daily.read_text(encoding="utf-8"))
            counts = data.get("universe", {}).get("counts", {})
            print(f"\n== daily.json counts ==")
            for k, v in counts.items():
                print(f"{k:10} → {v}")
        except Exception as e:
            print(f"{RED}Failed to parse daily.json: {e}{RESET}")
    else:
        print(f"{RED}No daily.json found in {OUTDIR}{RESET}")

def clean_today():
    """Remove today’s out/daily dir to avoid stale JSONs"""
    if OUTDIR.exists():
        shutil.rmtree(OUTDIR)
        print(f"{YELLOW}Cleaned stale directory {OUTDIR}{RESET}")
    OUTDIR.mkdir(parents=True, exist_ok=True)

def main():
    quick = "--quick" in sys.argv
    tail = "--tail" in sys.argv
    show_json = "--json" in sys.argv
    clean = "--clean" in sys.argv
    demo = "--demo" in sys.argv
    save_html = "--save-html" in sys.argv

    # Clean today's dir first
    clean_today()

    if clean:
        shutil.rmtree(OUTDIR, ignore_errors=True)
        OUTDIR.mkdir(parents=True, exist_ok=True)

    if demo:
        print(f"{YELLOW}Demo mode not implemented{RESET}")

    if not demo:
        run("Commodities", ["python3", str(SCRIPTS/"build_commodities.py")])
        run("Macro UK", ["python3", str(SCRIPTS/"build_macro_uk.py")])
        run("Macro US", ["python3", str(SCRIPTS/"build_macro_us.py")])
        run("Curves UK", ["python3", str(SCRIPTS/"build_curves_uk.py")])
        run("Curves US", ["python3", str(SCRIPTS/"build_curves_us.py")])

    if not quick and not demo:
        run("Universe merge", ["python3", str(SCRIPTS/"merge_universe.py")])
        run("Assemble daily", ["python3", str(SCRIPTS/"assemble_daily.py")])
    elif quick and not demo:
        print(f"\n{YELLOW}[INFO]{RESET} Quick mode: skipping universe merge + daily assembly")

    # Always emit sections → /tmp/email_sections.html
    run("Emit sections", ["python3", str(SCRIPTS/"emit_email_sections.py")], out_file=TMP_HTML)

    # Optionally save to preview.html
    if save_html and TMP_HTML.exists():
        shutil.copy(TMP_HTML, PREVIEW_HTML)
        print(f"{GREEN}Saved preview to {PREVIEW_HTML}{RESET}")

    # Sanity counts
    print("\n== Sanity counts ==")
    for fname, key in [
        ("commodities.json", "commodities"),
        ("macro_uk.json", "bullets"),
        ("macro_us.json", "bullets"),
        ("curves_uk.json", "points"),
        ("curves_us.json", "points"),
        ("universe.json", "rows"),
    ]:
        path = OUTDIR / fname
        if path.exists():
            val = count_json(path, key)
            print(f"{fname:20} → {colorize(val)}")
        else:
            print(f"{fname:20} → {RED}MISSING{RESET}")

    if show_json:
        show_json_counts()

    # Auto-preview email
    if TMP_HTML.exists():
        if tail:
            print(f"\n== Email preview (full file) ==")
            print(TMP_HTML.read_text())
        else:
            print(f"\n== Email preview (first 40 lines) ==")
            for i, line in enumerate(TMP_HTML.read_text().splitlines()):
                if i >= 40:
                    print("... (truncated)")
                    break
                print(line)
    else:
        print(f"{RED}No email_sections.html found{RESET}")

if __name__ == "__main__":
    sys.exit(main())
