#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=/opt/daily-report
PY="$ROOT/venv/bin/python3"

OUT_DIR="$ROOT/out/email"
RAW_BODY="$OUT_DIR/email_body.html"
WRAPPED_BODY="$OUT_DIR/email_body_wrapped.html"
TEMPLATE="$ROOT/templates/wrapper.html"

# env + dirs
[ -f "$ROOT/.env" ] && set -a && . "$ROOT/.env" && set +a
mkdir -p "$OUT_DIR" "$ROOT/out/data" "$ROOT/in" "$ROOT/assets"

# clean previous wrapped to force a fresh write
rm -f "$WRAPPED_BODY" || true

# 1) Data prep (all best-effort)
[ -x "$ROOT/scripts/fx_pairs_stub.py" ]      && "$PY" "$ROOT/scripts/fx_pairs_stub.py" || true
[ -x "$ROOT/scripts/fetch_eodhd_bundle.py" ] && "$PY" "$ROOT/scripts/fetch_eodhd_bundle.py" || true
[ -x "$ROOT/bin/yield_normalize.py" ]        && "$ROOT/bin/yield_normalize.py" || true
[ -x "$ROOT/scripts/at1_price_fill.py" ]     && "$PY" "$ROOT/scripts/at1_price_fill.py" || true

# 2) Compose raw body (only call if builder exists)
if [ -x "$ROOT/scripts/build_email_body.py" ]; then
  "$PY" "$ROOT/scripts/build_email_body.py"
fi

# 3) Sanity check
if [ ! -s "$RAW_BODY" ]; then
  echo "ERROR: $RAW_BODY not found or empty. Your composer didn't write anything." >&2
  exit 1
fi

# 4) Clean duplicates and CP1252 noise (best-effort)
[ -x "$ROOT/scripts/cleanup_body.py" ] && "$PY" "$ROOT/scripts/cleanup_body.py" || true

# 5) Wrap using template (requires args!)
if [ -x "$ROOT/scripts/wrap_email_html.py" ]; then
  if [ -f "$TEMPLATE" ]; then
    "$PY" "$ROOT/scripts/wrap_email_html.py" --in "$RAW_BODY" --out "$WRAPPED_BODY" --tpl "$TEMPLATE"
  else
    "$PY" "$ROOT/scripts/wrap_email_html.py" --in "$RAW_BODY" --out "$WRAPPED_BODY"
  fi
fi

# 6) Log
echo "Rendered (raw):    $RAW_BODY"
echo "Rendered (wrapped): $WRAPPED_BODY"
