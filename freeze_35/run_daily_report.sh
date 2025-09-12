#!/usr/bin/env bash
set -Eeuo pipefail

# single-instance lock (protects manual double-runs too)
exec 9>/tmp/daily-report.lock
flock -n 9 || { echo "Another run is in progress; exiting."; exit 0; }

cd /opt/daily-report

# optional venv
if [[ -d .venv ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

# env required
if [[ ! -f .env ]]; then
  echo "Missing .env at /opt/daily-report/.env" >&2
  exit 2
fi
set -a
# shellcheck disable=SC1091
source .env
set +a

# 2.5) EARLY idempotency: bail before any work if already sent today
TODAY=$(date +%F)
ARCHIVE_BUCKET="daily-report-freezes-michael"
ARCHIVE_PREFIX="archives"
if /usr/bin/aws s3 ls "s3://${ARCHIVE_BUCKET}/${ARCHIVE_PREFIX}/" | grep -q "daily_report_${TODAY}_"; then
  echo "Already sent for ${TODAY}; exiting before sync/render."
  exit 0
fi

# 1) Pull the freeze bundle (ONE LINE; excludes must be on this line)
/usr/bin/aws s3 sync "s3://daily-report-freezes-michael/daily-report/freeze_31/" . --exclude ".env" --exclude "send_report.py" --exclude "run_daily_report.sh" || true
# 3) Normalize news JSON into a predictable shape
normalize_news () {
  local infile="${1:-}"
  [[ -z "$infile" || ! -f "$infile" ]] && return 0
  local tmp="${infile}.tmp"
  if command -v iconv >/dev/null 2>&1; then
    iconv -f utf-8 -t ascii//TRANSLIT "$infile" -o "$tmp" || cp "$infile" "$tmp"
  else
    cp "$infile" "$tmp"
  fi
  if command -v jq >/dev/null 2>&1; then
    jq '{articles: (((if type=="array" then . else .articles end) // [])
          | map({title: (.title // .headline // .name // .summary // "Untitled"),
                 url:   (.url   // .link     // .href    // "#")})))}' \
       "$tmp" > "${infile}.normalized" && mv "${infile}.normalized" "$infile" || true
  fi
  rm -f "$tmp"
}
normalize_news news_general.json
normalize_news news_finance.json

# 4) Quote + default recommendation into macro.json
if [[ ! -f quotes.txt ]]; then
  cat > quotes.txt <<'TXT'
Everything compounds.|Charlie Munger
In investing, what is comfortable is rarely profitable.|Robert Arnott
It's supposed to be hard. If it were easy, everyone would do it.|Tom Hanks
The stock market transfers money from the impatient to the patient.|Warren Buffett
TXT
fi
if command -v shuf >/dev/null 2>&1 && [[ -f macro.json ]]; then
  IFS='|' read -r QTEXT QAUTH < <(shuf -n 1 quotes.txt)
  jq --arg qt "$QTEXT" --arg qa "$QAUTH" \
     '.QUOTE=$qt | .QUOTE_ATTR=$qa | .RECOMMENDATION //= "Maintain core positions; add selectively on weakness."' \
     macro.json > /tmp/m && mv /tmp/m macro.json
fi

# 5) Render HTML
python3 render_template.py daily_report_full.html daily_report_rendered.html

# 6) Refuse to send if placeholders remain
if grep -q "{{" daily_report_rendered.html; then
  echo "Refusing to send: unfilled placeholders remain in daily_report_rendered.html" >&2
  exit 2
fi

# 7) Send via Postmark
export HTML_PATH=daily_report_rendered.html
python3 send_report.py

echo "✅ Daily Report pipeline completed."
