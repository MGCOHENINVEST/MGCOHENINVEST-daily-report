#!/usr/bin/env python3
import os, smtplib, ssl, sys, time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def fail(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.postmarkapp.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS") or os.getenv("SMTP_PASSWORD") or ""

FROM = os.getenv("MAIL_FROM") or os.getenv("FROM_EMAIL") or ""
TO = os.getenv("TO_EMAILS") or os.getenv("TO_EMAIL") or os.getenv("MAIL_TO") or ""
SUBJECT = os.getenv("SUBJECT", "Daily Report")
HTML_PATH = os.getenv("HTML_PATH", "daily_report_rendered.html")
PM_TAG = os.getenv("POSTMARK_TAG", "daily-report-v2")
PM_STREAM = os.getenv("POSTMARK_STREAM", "outbound")

if not SMTP_USER:
    fail("Missing SMTP_USER (Postmark Server Token).")
if not FROM:
    fail("Missing FROM_EMAIL/MAIL_FROM.")
if not TO:
    fail("Missing recipient (TO_EMAIL / TO_EMAILS / MAIL_TO).")

recipients = [a.strip() for a in TO.replace(";", ",").split(",") if a.strip()]
if not recipients:
    fail("Recipient list is empty after parsing.")

try:
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()
except Exception as e:
    fail(f"Failed to read HTML_PATH '{HTML_PATH}': {e}")

msg = MIMEMultipart("alternative")
msg["From"] = FROM
msg["To"] = ", ".join(recipients)
msg["Subject"] = SUBJECT
msg["X-PM-Tag"] = PM_TAG
msg["X-PM-Message-Stream"] = PM_STREAM
msg.attach(MIMEText("HTML report inline.", "plain"))
msg.attach(MIMEText(html, "html"))

# Candidate ports: configured first, then alternates
_ports = []
try:
    first = int(SMTP_PORT)
except Exception:
    first = 587
for p in (first, 2525, 25, 465):
    if p not in _ports:
        _ports.append(p)

last_error = None
for p in _ports:
    for attempt in (1, 2, 3):
        try:
            if p == 465:
                with smtplib.SMTP_SSL(SMTP_HOST, p, timeout=20, context=ssl.create_default_context()) as s:
                    s.ehlo()
                    s.login(SMTP_USER, SMTP_PASS or SMTP_USER)
                    s.sendmail(FROM, recipients, msg.as_string())
                    print(f"✅ Daily Report sent via port {p} (SSL).")
                    sys.exit(0)
            else:
                with smtplib.SMTP(SMTP_HOST, p, timeout=20) as s:
                    s.ehlo()
                    try:
                        s.starttls(context=ssl.create_default_context()); s.ehlo()
                    except Exception:
                        pass
                    s.login(SMTP_USER, SMTP_PASS or SMTP_USER)
                    s.sendmail(FROM, recipients, msg.as_string())
                    print(f"✅ Daily Report sent via port {p}.")
                    sys.exit(0)
        except Exception as e:
            last_error = e
            time.sleep(2)

raise last_error
