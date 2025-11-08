#!/usr/bin/env python3
import json, datetime
from pathlib import Path

TODAY = datetime.date.today().isoformat()
BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "out" / "daily" / TODAY

CSS = """<!doctype html><meta charset='utf-8'>
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
  .tiny { font-size: 11px; color: #6b7280; }
</style>
"""

def jload(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}

def fmt_delta(x):
    if x is None:
        return "", "muted"
    try:
        f = float(x)
    except Exception:
        return "", "muted"
    sign = "+" if f > 0 else ""
    cls = "pos" if f > 0 else ("neg" if f < 0 else "muted")
    # Keep it tight; 2dp for normal, 4dp for tiny numbers like copper deltas
    if abs(f) < 0.1:
        return f"{sign}{f:.4f}", cls
    return f"{sign}{f:.2f}", cls

def render_commodities():
    data = jload(OUT / "commodities.json")
    rows = data.get("commodities", [])
    as_of = data.get("as_of", "")
    html = [CSS, "<div class='blk'>",
            f"<h3 class='sec-h'>Commodities <span class='chip'>as of {as_of}</span></h3>",
            "<table class='tbl'><tr><th>Instrument</th><th class='num'>Price</th><th class='num'>Δ</th></tr>"]
    for r in rows:
        # Accept either a prebuilt 'instrument' or fallback to symbol/name
        inst = r.get("instrument")
        if not inst:
            sym = r.get("symbol") or ""
            name = r.get("name") or ""
            inst = f"{sym} \u2014 {name}".strip() if (sym or name) else ""
        delta_txt, cls = fmt_delta(r.get("delta"))
        price = r.get("price")
        price_txt = f"{price:g}" if isinstance(price, (int, float)) else (price or "")
        html.append(f"<tr><td>{inst or '—'}</td>"
                    f"<td class='num'>{price_txt}</td>"
                    f"<td class='num {cls}'>{delta_txt}</td></tr>")
    html.append("</table></div><hr style='border:none;border-top:1px solid #eee;margin:20px 0'>")
    return "\n".join(html)

def render_macro(label, fname):
    data = jload(OUT / fname)
    bullets = data.get("bullets", [])
    as_of = data.get("as_of", "")
    html = [CSS,
            "<div class='blk'>",
            f"<h3 class='sec-h'>{label} <span class='chip'>updated {as_of}</span></h3>"]
    if bullets:
        html.append("<ul style='margin:0 0 6px 18px;padding:0'>")
        for b in bullets[:8]:
            html.append(f"<li>{b}</li>")
        html.append("</ul>")
    else:
        html.append("<div class='muted'>No macro highlights provided.</div>")
    html.append("</div><hr style='border:none;border-top:1px solid #eee;margin:20px 0'>")
    return "\n".join(html)

def arrow(delta):
    try:
        d = float(delta)
    except Exception:
        return "", "muted"
    if d > 0: return "▲", "pos"
    if d < 0: return "▼", "neg"
    return "■", "muted"

def render_curve_block(title, fname):
    data = jload(OUT / fname)
    pts = data.get("points", [])
    as_of = data.get("as_of", "")
    html = [CSS,
            "<div class='blk'>",
            f"<h3 class='sec-h'>{title} <span class='chip'>as of {as_of}</span></h3>"]
    if pts:
        html.append("<table class='tbl'><tr><th>Tenor</th><th class='num'>Yield</th><th class='num'>Δ</th></tr>")
        for p in pts:
            dtxt, cls = fmt_delta(p.get("delta"))
            sym, scls = arrow(p.get("delta"))
            y = p.get("yield")
            ytxt = f"{y:.2f}" if isinstance(y, (int, float)) else (y or "")
            html.append(
                f"<tr><td>{p.get('tenor','')}</td>"
                f"<td class='num'>{ytxt}</td>"
                f"<td class='num {cls}'>{sym} {dtxt}</td></tr>"
            )
        html.append("</table>")
    else:
        html.append("<div class='muted'>No curve points.</div>")
    html.append("</div>")
    return "\n".join(html)

def render_universe_summary():
    uni = jload(OUT / "universe.json")
    counts = uni.get("counts", {})
    if not counts: 
        return ""
    chips = " ".join([f"<span class='chip'>{k.upper()}: {v}</span>" for k, v in counts.items()])
    return f"<div class='blk tiny' style='margin-top:6px'>{chips}</div>"

def main():
    parts = []
    parts.append(render_commodities())
    parts.append(render_macro("Macro UK", "macro_uk.json"))
    parts.append(render_macro("Macro US", "macro_us.json"))
    parts.append(CSS + "<div class='blk'><h3 class='sec-h'>Curves</h3></div>")
    parts.append(render_curve_block("UK Gilts", "curves_uk.json"))
    parts.append(render_curve_block("US Treasuries", "curves_us.json"))
    parts.append(render_universe_summary())
    print("\n".join(parts))

if __name__ == "__main__":
    main()
