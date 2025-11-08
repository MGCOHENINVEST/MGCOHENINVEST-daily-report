#!/usr/bin/env bash
set -Eeuo pipefail

cd /opt/daily-report

# 0) Optional venv
if [[ -d .venv ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

# 1) Pull the freeze bundle (keep your current source; change when you version-bump)
aws s3 sync "s3://daily-report-freezes-michael/daily-report/freeze_31/" . --exclude ".env" || true

# 2) Load mail/env settings for Postmark
set -a
# shellcheck disable=SC1091
source .env
set +a

# 3) Normalize news JSON into a predictable { "articles": [ {title,url} ] } shape
if command -v jq >/dev/null 2>&1; then
  jq '{articles: ((.articles? // .items? // .news? // .data?.articles? // .payload?.items? // .results?)
        | map({title: (.title // .headline // .name // .summary // ""),
                url:   (.url   // .link     // .href    // "#")})))}' \
    news_general.json > news_general.normalized.json && mv news_general.normalized.json news_general.json || true

  jq '{articles: ((.articles? // .items? // .news? // .data?.articles? // .payload?.items? // .results?)
        | map({title: (.title // .headline // .name // .summary // ""),
                url:   (.url   // .link     // .href    // "#")})))}' \
    news_finance.json > news_finance.normalized.json && mv news_finance.normalized.json news_finance.json || true
fi

# 4) Quote + default recommendation into macro.json (cheap, reliable)
if [[ ! -f quotes.txt ]]; then
  cat > quotes.txt <<'TXT'
Everything compounds.|Charlie Munger
In investing, what is comfortable is rarely profitable.|Robert Arnott
It's supposed to be hard. If it were easy, everyone would do it.|Tom Hanks
The stock market transfers money from the impatient to the patient.|Warren Buffett
TXT
fi
if command -v shuf >/dev/null 2>&1; then
  IFS='|' read -r QTEXT QAUTH < <(shuf -n 1 quotes.txt)
  jq --arg qt "$QTEXT" --arg qa "$QAUTH" \
     '.QUOTE=$qt | .QUOTE_ATTR=$qa | .RECOMMENDATION //= "Maintain core positions; add selectively on weakness."' \
     macro.json > /tmp/m && mv /tmp/m macro.json
fi

# 5) Render HTML from the template + data
#    This writes daily_report_rendered.html and fails if placeholders remain.
python3 render_template.py daily_report_full.html daily_report_rendered.html

# 6) Sanity guard – refuse to send a template
if grep -q "{{" daily_report_rendered.html; then
  echo "Refusing to send: unfilled placeholders remain in daily_report_rendered.html" >&2
  exit 2
fi

# 7) Send via Postmark
export HTML_PATH=daily_report_rendered.html
python3 send_report.py

echo "✅ Daily Report pipeline completed."
