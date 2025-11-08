#!/usr/bin/env python3
import sys, pathlib

ROOT = pathlib.Path("/opt/daily-report")
EMAILDIR = ROOT / "out/email"

def latest_html():
    # Prefer canonical name if present
    p = EMAILDIR / "email_body.html"
    if p.exists():
        return p
    # Else pick newest *.html, ignoring broken symlinks
    files = []
    for q in EMAILDIR.glob("*.html"):
        try:
            st = q.stat()  # will raise on broken symlinks
            files.append((st.st_mtime, q))
        except FileNotFoundError:
            continue
    files.sort(reverse=True)
    return files[0][1] if files else None

def wrap(src: pathlib.Path, dst: pathlib.Path):
    s = src.read_text(encoding="utf-8", errors="ignore")
    low = s.lower()
    # If already full HTML doc, pass-through
    if "<html" in low and "<body" in low:
        dst.write_text(s, encoding="utf-8")
        return
    html = f"""<!doctype html>
<html>
<head><meta charset="UTF-8"><title>Daily Report</title></head>
<body>
<div class="content">
{s}
</div>
</body>
</html>"""
    dst.write_text(html, encoding="utf-8")

def main():
    args = sys.argv[1:]
    dst = EMAILDIR / "email_body_wrapped.html"
    if len(args) >= 1:
        src = pathlib.Path(args[0])
        if len(args) >= 2:
            dst = pathlib.Path(args[1])
    else:
        src = latest_html()
        if not src:
            raise SystemExit("wrap_email: no source HTML found")

    dst.parent.mkdir(parents=True, exist_ok=True)
    wrap(src, dst)

    # Refresh 'latest.html' symlink safely
    sl = EMAILDIR / "latest.html"
    try:
        if sl.exists() or sl.is_symlink():
            sl.unlink()
        sl.symlink_to(dst.name)
    except Exception:
        pass

if __name__ == "__main__":
    main()
