#!/usr/bin/env python3
import os, sys, smtplib, ssl
from email.mime.text import MIMEText

# 1) Load .env if python-dotenv is available (optional, but helpful)
try:
    from dotenv import load_dotenv
    load_dotenv("/opt/daily-report/.env")
except Exception:
    pass  # if not installed, we rely on shell-exported env


# 2) Required inputs
HTML_PATH   = os.getenv("HTML_PATH", "daily_report_full.html")

SMTP_HOST   = os.getenv("SMTP_HOST", "smtp.postmarkapp.com")
SMTP_PORT   = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER   = os.getenv("SMTP_USER")  # Postmark Server Token
# Postmark accepts empty password, but your older code wanted SMTP_PASS.
SMTP_PASS   = os.getenv("SMTP_PASS", os.getenv("SMTP_PASSWORD", ""))

FROM_EMAIL  = os.getenv("FROM_EMAIL")
TO_EMAILS   = [e.strip() for e in os.getenv("TO_EMAIL", "").split(",") if e.strip()]
CC_EMAILS   = [e.strip() for e in os.getenv("CC_EMAIL", "").split(",") if e.strip()]
BCC_EMAILS  = [e.strip() for e in os.getenv("BCC_EMAIL", "").split(",") if e.strip()]
SUBJECT     = os.getenv("SUBJECT", "Daily Report")

def fail(msg, code=1):
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(code)

# 3) Sanity checks
if not SMTP_USER:
    fail("Missing SMTP_USER (Postmark Server Token).")
if not FROM_EMAIL:
    fail("Missing FROM_EMAIL.")
if not TO_EMAILS:
    fail("Missing TO_EMAIL (comma-separated allowed).")
if not os.path.exists(HTML_PATH):
    fail(f"Missing HTML file at {HTML_PATH}.")

# 4) Read HTML body
with open(HTML_PATH, "r", encoding="utf-8") as f:
    html = f.read()

# 5) Build MIME email
msg = MIMEText(html, "html", "utf-8")
msg["Subject"] = SUBJECT
msg["From"]    = FROM_EMAIL
msg["To"]      = ", ".join(TO_EMAILS)
if CC_EMAILS:
    msg["Cc"]  = ", ".join(CC_EMAILS)

# 6) Connect and send via SMTP (STARTTLS)
ctx = ssl.create_default_context()
try:
    s = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30)
    s.ehlo()
    s.starttls(context=ctx)
    s.ehlo()
    # Postmark: username = server token, password can be empty string
    s.login(SMTP_USER, SMTP_PASS)
    recipients = TO_EMAILS + CC_EMAILS + BCC_EMAILS
    s.sendmail(FROM_EMAIL, recipients, msg.as_string())
    s.quit()
    print("✅ Daily Report sent via Postmark SMTP.")
except smtplib.SMTPAuthenticationError as e:
    fail(f"SMTP auth failed: {e}")
except Exception as e:
    fail(f"SMTP send failed: {e}")
