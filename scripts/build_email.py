#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys, json, yaml
from pathlib import Path
from datetime import datetime, timezone

# Optional: use your existing renderers module if you have one
try:
    from renderers import render_section_by_name  # your project’s function
except Exception:
    # Fallback stub so this file doesn't explode during edits
    def render_section_by_name(name: str) -> str | None:
        return None

def now_iso() -> string:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ UTC")

def uniq(seq):
    seen = set()
    for x in seq:
        if x not in seen:
            seen.add(x)
            yield x

def load_sections() -> list[str]:
    cfg = Path("/opt/daily-report/config/email_sections.yaml")
    if not cfg.exists():
        return []
    with cfg.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    order = raw.get("sections", []) or []
    return list(uniq(order))

def safe(html: str | None) -> str | None:
    if not html: 
        return None
    s = str(html).strip()
    return s if s else None

def main():
    try:
        out_path = Path(sys.argv[sys.argv.index("--out")+1])
    except Exception:
        print("Usage: build_email.py --out /opt/daily-report/out/email/email_body.html")
        sys.exit(2)

    parts = []
    parts.append(f"<p class='generated-at'>Generated at {now_iso()}</p>")

    for sec in load_sections():
        frag = safe(render_section_by_name(sec))
        if frag:
            parts.append(frag)

    html = "\n".join(parts)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Overwrite (single write), UTF-8, no append shenanigans
    out_path.write_text(html, encoding="utf-8")

if __name__ == "__main__":
    main()
