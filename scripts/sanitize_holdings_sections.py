#!/usr/bin/env python3
import re
from pathlib import Path

ROOT   = Path("/opt/daily-report")
EMAIL  = ROOT / "out" / "email" / "email_body.html"

# Matches entire <div class="section"><div class="section__title">Holdings · …</div> ... </table></div>
BLOCK = re.compile(
    r'<div class="section">\s*<div class="section__title">Holdings · [^<]+</div>.*?</table>\s*</div>',
    re.DOTALL | re.IGNORECASE
)

def main():
    if not EMAIL.exists():
        print("[WARN] email_body.html not found")
        return
    html = EMAIL.read_text()
    html2, n = BLOCK.subn("", html)
    if n:
        EMAIL.write_text(html2)
        print(f"[INFO] Removed {n} duplicate Holdings sections")
    else:
        print("[INFO] No Holdings sections found to remove")

if __name__ == "__main__":
    main()
