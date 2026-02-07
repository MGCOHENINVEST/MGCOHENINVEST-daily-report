#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--in",  dest="src", required=True)
ap.add_argument("--out", dest="dst", required=True)
ap.add_argument("--tpl", dest="tpl", required=False)
args = ap.parse_args()

src = Path(args.src)
dst = Path(args.dst)
tpl = Path(args.tpl) if args.tpl else None

body = src.read_text(encoding="utf-8")

if tpl and tpl.exists() and tpl.stat().st_size > 0:
    # Template mode: we still protect iOS Mail by injecting format-detection + CSS
    # unless the template already contains them.
    html = tpl.read_text(encoding="utf-8").replace("{{BODY_HTML}}", body)

    lower = html.lower()
    if "format-detection" not in lower:
        html = html.replace(
            "<head>",
            '<head>\n<meta name="format-detection" content="telephone=no,address=no,email=no,date=no">\n',
            1,
        )
    if "x-apple-data-detectors" not in lower:
        # Insert CSS early, but inside <head>
        html = html.replace(
            "</head>",
            "<style>\n"
            "a[x-apple-data-detectors], a[href^=\"tel\"] { color: inherit !important; text-decoration: none !important; }\n"
            "</style>\n</head>",
            1,
        )
else:
    # Safe fallback template (also includes Apple-detector suppression)
    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Kairos Daily Report</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="format-detection" content="telephone=no,address=no,email=no,date=no">
<style>
a[x-apple-data-detectors], a[href^="tel"] {{ color: inherit !important; text-decoration: none !important; }}
body{{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;line-height:1.35;margin:0;padding:0;}}
.container{{max-width:780px;margin:0 auto;padding:24px}}
.card{{background:#fff;border:1px solid #e6e7ee;border-radius:12px;padding:20px;margin:16px 0}}
h1,h2,h3{{margin:0 0 8px 0}}
table{{border-collapse:collapse;width:100%}}
th,td{{padding:6px 8px;border:1px solid #ddd;font-size:14px}}
small{{color:#666}}
</style></head><body><div class="container"><div class="card">
{body}
</div></div></body></html>"""

dst.parent.mkdir(parents=True, exist_ok=True)
dst.write_text(html, encoding="utf-8")
print("wrap_email_html.py: wrote", dst)
