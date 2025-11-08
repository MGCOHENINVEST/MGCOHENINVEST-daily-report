#!/usr/bin/env python3
import os, re, csv, sys, argparse, subprocess
from pathlib import Path

def pick_col(headers, want_any):
    hl = [h.strip() for h in headers]
    lcl = [h.lower() for h in hl]
    for i, h in enumerate(lcl):
        for w in want_any:
            if w in h:
                return hl[i]
    return None

def log_decision(msg: str):
    # stderr for journald
    try:
        print(msg, file=sys.stderr, flush=True)
    except Exception:
        pass
    # syslog via logger (survives redirection)
    try:
        subprocess.run(["/usr/bin/logger", "-t", "inject_movers_alert", msg], check=False)
    except Exception:
        pass

p = argparse.ArgumentParser()
p.add_argument("--html", required=True, help="Path to out/daily_report.html")
p.add_argument("--stocks", required=True, help="Path to data/stock.csv")
p.add_argument("--threshold", type=float, default=float(os.environ.get("MOVERS_ALERT_THRESH", "4")))
args = p.parse_args()

stocks_csv = Path(args.stocks)
html_file = Path(args.html)
if not stocks_csv.exists() or not html_file.exists():
    print("inject_movers_alert: missing input files; nothing to do.", file=sys.stderr)
    sys.exit(0)

with stocks_csv.open(newline="", encoding="utf-8") as f:
    r = csv.DictReader(f)
    hdrs = r.fieldnames or []
    # Guess column names
    col_pct = pick_col(hdrs, ["change%", "chg%", "pct_change", "change_pct", "pct", "percent", "change"])
    col_sym = pick_col(hdrs, ["ticker", "symbol"])
    col_name = pick_col(hdrs, ["name", "company"])
    if not col_pct:
        print("inject_movers_alert: no pct-change column found; skipping.", file=sys.stderr)
        sys.exit(0)

    best = None  # (abs_pct, pct, symbol, name)
    for row in r:
        raw = (row.get(col_pct) or "").strip()
        val = raw.replace("%", "").replace("+", "")
        try:
            pct = float(val)
        except ValueError:
            continue
        abs_pct = abs(pct)
        sym = (row.get(col_sym) or "").strip() if col_sym else ""
        nm = (row.get(col_name) or "").strip() if col_name else ""
        if (best is None) or (abs_pct > best[0]):
            best = (abs_pct, pct, sym, nm)

if not best:
    print("inject_movers_alert: no valid rows; skipping.", file=sys.stderr)
    sys.exit(0)

abs_pct, pct, sym, nm = best
fired = abs_pct >= args.threshold

# Journal/syslog-friendly decision line
log_decision(f"ALERT_CHECK max_move={abs_pct:.2f}% threshold={args.threshold:.2f}% banner={'ON' if fired else 'OFF'}")

if not fired:
    print(f"inject_movers_alert: max move {abs_pct:.2f}% < threshold {args.threshold:.2f}%; no banner.", file=sys.stderr)
    sys.exit(0)

who = sym or nm or "Top mover"
label = f"{who} {pct:+.1f}% (≥{args.threshold:g}%)"
banner = f"""
<div style="padding:10px;border-radius:8px;margin:12px 0;
    font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;
    background:#fff3cd;border:1px solid #ffeeba;color:#856404;">
  <strong>Alert:</strong> Biggest mover today: {label}
</div>
""".strip()

html = html_file.read_text(encoding="utf-8", errors="ignore")
m = re.search(r"<body[^>]*>", html, flags=re.I)
if m:
    idx = m.end()
    new_html = html[:idx] + "\n" + banner + "\n" + html[idx:]
else:
    new_html = banner + "\n" + html

html_file.write_text(new_html, encoding="utf-8")
print(f"inject_movers_alert: injected banner -> {html_file}")
