#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=/opt/daily-report
PY="$ROOT/venv/bin/python3"
OUT="$ROOT/out/email"
EMAIL_HTML="$OUT/email_body.html"
EMAIL_WRAPPED="$OUT/email_body_wrapped.html"

[ -f "$ROOT/.env" ] && set -a && . "$ROOT/.env" && set +a
mkdir -p "$OUT" "$ROOT/out/data" "$ROOT/in" "$ROOT/assets"
rm -f "$EMAIL_WRAPPED" || true

# ----- data prep -----
[ -x "$ROOT/scripts/fx_pairs_stub.py" ]       && "$PY" "$ROOT/scripts/fx_pairs_stub.py" || true
[ -x "$ROOT/scripts/fx_cross_stub.py" ]       && "$PY" "$ROOT/scripts/fx_cross_stub.py" || true
[ -x "$ROOT/scripts/fetch_eodhd_bundle.py" ]  && "$PY" "$ROOT/scripts/fetch_eodhd_bundle.py" || true
[ -x "$ROOT/bin/yield_normalize.py" ]         && "$ROOT/bin/yield_normalize.py" || true
[ -x "$ROOT/scripts/build_commodities.py" ]   && "$PY" "$ROOT/scripts/build_commodities.py" || true
[ -x "$ROOT/scripts/fetch_news_unified.py" ]  && "$PY" "$ROOT/scripts/fetch_news_unified.py" || true
[ -x "$ROOT/scripts/at1_price_fill.py" ]      && "$PY" "$ROOT/scripts/at1_price_fill.py" || true
[ -x "$ROOT/scripts/at1_meta_build.py" ]      && "$PY" "$ROOT/scripts/at1_meta_build.py" || true
# run json->csv only if the source exists
if [ -x "$ROOT/scripts/at1_json_to_csv.py" ] && [ -s "$ROOT/out/data/at1.json" ]; then
  "$PY" "$ROOT/scripts/at1_json_to_csv.py" || true
fi
[ -x "$ROOT/scripts/at1_filter_priced.py" ]   && "$PY" "$ROOT/scripts/at1_filter_priced.py" || true

# normalize commodities path into out/data if a dated file was written
latest_com="$(ls -1t $ROOT/out/**/commodities.json 2>/dev/null | head -n1 || true)"
if [ -n "${latest_com:-}" ]; then cp -f "$latest_com" "$ROOT/out/data/commodities.json" || true; fi

# ----- compose core -----
"$PY" "$ROOT/scripts/build_email_body.py"

# ----- enforce single-variant yields -----
[ -x "$ROOT/bin/cleanup_yield_variants.sh" ] && "$ROOT/bin/cleanup_yield_variants.sh" || true

# ----- enrich blocks (reliable appenders) -----
[ -x "$ROOT/scripts/append_fx_crosses.py" ]      && "$PY" "$ROOT/scripts/append_fx_crosses.py" || true
[ -x "$ROOT/scripts/append_commodities_once.py" ]&& "$PY" "$ROOT/scripts/append_commodities_once.py" || true
[ -x "$ROOT/scripts/append_at1_once.py" ]        && "$PY" "$ROOT/scripts/append_at1_once.py" || true
[ -x "$ROOT/scripts/append_news_once.py" ]       && "$PY" "$ROOT/scripts/append_news_once.py" || true

# ----- clean + wrap -----
"$PY" "$ROOT/scripts/cleanup_body.py"
"$PY" "$ROOT/scripts/wrap_email_html.py" --in "$EMAIL_HTML" --out "$EMAIL_WRAPPED"

echo "Rendered (raw):    $EMAIL_HTML"
echo "Rendered (wrapped): $EMAIL_WRAPPED"
