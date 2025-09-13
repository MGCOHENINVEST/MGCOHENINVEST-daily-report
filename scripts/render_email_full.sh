#!/usr/bin/env bash
set -euo pipefail
cd /opt/daily-report

OUT_DIR="out"
OUT_JSON="$OUT_DIR/payload.json"
OUT_HTML="$OUT_DIR/daily_report.html"
OUT_BOND_JSON="$OUT_DIR/bond_analytics.json"

mkdir -p "$OUT_DIR"

# choose python
if [[ -x ".venv/bin/python" ]]; then PY=".venv/bin/python"; else PY="python3"; fi

# 0) Build bond analytics JSON (optional but preferred)
$PY src/analytics/bonds.py --csv data/bonds.csv --out "$OUT_BOND_JSON" >/dev/null || true

# 1) Build payload (will pull analytics if present)
$PY src/build_daily_payload.py > "$OUT_JSON"

# 2) Render HTML
$PY src/email_renderer.py \
  --template-dir templates/email \
  --data "$OUT_JSON" \
  --snapshot "LIVE" \
  --freeze "LIVE" \
  --out "$OUT_HTML"

echo "Rendered $OUT_HTML"
