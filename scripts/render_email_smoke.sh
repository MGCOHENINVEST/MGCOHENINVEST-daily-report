#!/usr/bin/env bash
set -euo pipefail
python --version >/dev/null 2>&1 || python3 --version >/dev/null 2>&1
PYBIN="$(command -v python || command -v python3)"

TEMPL_DIR="templates/email"
RENDERER="src/email_renderer.py"
OUT_HTML="out/daily_smoke_test.html"
DATA_JSON="out/email_smoke_payload.json"

mkdir -p out

# tiny payload if missing
if [ ! -f "$DATA_JSON" ]; then
  cat > "$DATA_JSON" <<'JSON'
{
  "subject":"Daily Report — CI Smoke",
  "headline":"Daily Report — CI Smoke",
  "exec_summary":["CI render path exercised."],
  "movers":[{"ticker":"ULVR","name":"Unilever","delta_pct":1.0}],
  "dividends":[],
  "news":[]
}
JSON
fi

$PYBIN "$RENDERER" --template-dir "$TEMPL_DIR" --data "$DATA_JSON" --snapshot "CI" --freeze "37" --out "$OUT_HTML"
echo "Rendered $OUT_HTML"
test -s "$OUT_HTML"
