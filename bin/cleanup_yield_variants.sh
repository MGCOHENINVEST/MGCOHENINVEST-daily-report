#!/usr/bin/env bash
set -Eeuo pipefail
HTML=/opt/daily-report/out/email/email_body.html
[ -s "$HTML" ] || exit 0
perl -0777 -i -pe '
  s~<table[^>]*>\s*<thead>\s*<tr>\s*<th>US w1</th>.*?</table>\s*~~gs;
  s~<table[^>]*>\s*<thead>\s*<tr>\s*<th>US m1</th>.*?</table>\s*~~gs;
  s~<table[^>]*>\s*<thead>\s*<tr>\s*<th>UK w1</th>.*?</table>\s*~~gs;
  s~<table[^>]*>\s*<thead>\s*<tr>\s*<th>UK m1</th>.*?</table>\s*~~gs;
  s/(?:<br\/>\s*){2,}/<br\/>/g;
' "$HTML"
