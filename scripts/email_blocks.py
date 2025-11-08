"""
email_blocks.py — render HTML sections for the daily report email
"""

THEME_CSS = """
<style>
  .blk { font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif; font-size: 13px; line-height: 1.25; color: #111; }
  .tbl { border-collapse: collapse; width: 100%; }
  .tbl th, .tbl td { padding: 6px 8px; border-bottom: 1px solid #e6e6e6; }
  .tbl th { text-align: left; font-weight: 600; font-size: 12px; color: #333; }
  .num { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; text-align: right; }
  .chip { display: inline-block; padding: 2px 6px; border-radius: 999px; font-size: 11px; background: #f3f4f6; color: #374151; }
  .pos { color: #116329; }
  .neg { color: #b42318; }
  .muted { color: #6b7280; }
  .sec-h { margin: 0 0 6px 0; font-size: 14px; }
</style>
""".strip()

def ensure_theme_once(buf: list):
    if not any("<style>" in s and ".blk" in s for s in buf):
        buf.append(THEME_CSS)

def fmt_num(x, dp=2):
    try:
        return f"{float(x):,.{dp}f}"
    except Exception:
        return "—"

def fmt_bp(x):
    try:
        return f"{float(x):+.0f} bp"
    except Exception:
        return "—"

def delta_span(x, kind="pct"):
    try:
        v = float(x)
    except Exception:
        return '<span class="muted">—</span>'
    cls = "pos" if v > 0 else ("neg" if v < 0 else "muted")
    arrow = "▲" if v > 0 else ("▼" if v < 0 else "•")
    if kind == "bp":
        label = fmt_bp(v)
    else:
        label = f"{v:+.2f}%"
    return f'<span class="{cls}">{arrow} {label}</span>'

def render_curves_html(curves: dict) -> str:
    """
    curves: {
      "uk": [{"tenor":"2Y","yield":4.21,"chg_bp":-3}, ...],
      "us": [{"tenor":"2Y","yield":3.98,"chg_bp":+2}, ...],
      "as_of":"2025-09-20"
    }
    """
    parts = []
    ensure_theme_once(parts)
    parts.append('<div class="blk">')
    parts.append(f'<h3 class="sec-h">Curves <span class="chip">as of {curves.get("as_of","—")}</span></h3>')
    for key, title in (("uk","UK"), ("us","US")):
        rows = curves.get(key) or []
        if not rows:
            continue
        parts.append(f'<div style="margin:8px 0 14px 0;"><div class="chip">{title}</div>')
        parts.append('<table class="tbl"><tr><th>Tenor</th><th class="num">Yield</th><th class="num">Δ</th></tr>')
        for r in rows:
            parts.append(
                "<tr>"
                f"<td>{r.get('tenor','—')}</td>"
                f"<td class='num'>{fmt_num(r.get('yield'),2)}%</td>"
                f"<td class='num'>{delta_span(r.get('chg_bp'), kind='bp')}</td>"
                "</tr>"
            )
        parts.append("</table></div>")
    parts.append("</div>")
    return "\n".join(parts)

def render_commodities_html(comms: list, as_of: str) -> str:
    """
    comms: [{"name":"Brent","px":93.4,"chg_pct":+0.82}, ...]
    """
    parts = []
    ensure_theme_once(parts)
    parts.append('<div class="blk">')
    parts.append(f'<h3 class="sec-h">Commodities <span class="chip">as of {as_of or "—"}</span></h3>')
    parts.append('<table class="tbl"><tr><th>Instrument</th><th class="num">Price</th><th class="num">Δ</th></tr>')
    for r in comms or []:
        parts.append(
            "<tr>"
            f"<td>{r.get('name','—')}</td>"
            f"<td class='num'>{fmt_num(r.get('px'),2)}</td>"
            f"<td class='num'>{delta_span(r.get('chg_pct'), kind='pct')}</td>"
            "</tr>"
        )
    parts.append("</table></div>")
    return "\n".join(parts)

def render_macro_html(data: dict) -> str:
    """
    Minimal placeholder with chips for upcoming prints or notes.
    data: {"bullets":["FOMC next Wed","CPI prints Thu"], "as_of":"2025-09-20"}
    """
    parts = []
    ensure_theme_once(parts)
    parts.append('<div class="blk">')
    parts.append(f'<h3 class="sec-h">Macro <span class="chip">updated {data.get("as_of","—")}</span></h3>')
    bullets = data.get("bullets") or []
    if not bullets:
        parts.append('<div class="muted">No macro highlights provided.</div>')
    else:
        parts.append("<ul style='margin:6px 0 0 18px;'>")
        for b in bullets:
            parts.append(f"<li>{b}</li>")
        parts.append("</ul>")
    parts.append("</div>")
    return "\n".join(parts)
