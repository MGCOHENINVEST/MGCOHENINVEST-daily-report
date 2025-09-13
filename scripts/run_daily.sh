#!/usr/bin/env bash
set -euo pipefail
cd /opt/daily-report

OUT_HTML="out/daily_report.html"
OUT_JSON="out/payload.json"
OUT_BOND_JSON="out/bond_analytics.json"
mkdir -p out

if [[ -x ".venv/bin/python" ]]; then PY=".venv/bin/python"; else PY="python3"; fi

# Analytics first
$PY src/analytics/bonds.py --csv data/bonds.csv --out "$OUT_BOND_JSON" >/dev/null || true

# Build payload
$PY src/build_daily_payload.py > "$OUT_JSON"

# Render HTML
$PY src/email_renderer.py \
  --template-dir templates/email \
  --data "$OUT_JSON" \
  --snapshot "LIVE" \
  --freeze "LIVE" \
  --out "$OUT_HTML"

echo "Rendered $OUT_HTML"

# Send
./scripts/send_email_postmark.py \
  --from reports@cohenuk.com \
  --to michael@cohenuk.com \
  --subject "Daily Report" \
  --html "$OUT_HTML"
