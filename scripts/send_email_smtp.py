#!/usr/bin/env python3
import os, smtplib, ssl, sys, re
from email.mime.text import MIMEText

BASE="/opt/daily-report"
HTML=f"{BASE}/out/email/email_body_wrapped.html"

def env(name, default=""):
    v=os.environ.get(name, default)
    if not v and os.path.exists(f"{BASE}/.env"):
        for line in open(f"{BASE}/.env"):
            line=line.strip()
            if not line or line.startswith("#"): continue
            if line.split("=",1)[0]==name:
                v=line.split("=",1)[1].strip().strip('"').strip("'")
                break
    return v

host = env("SMTP_HOST"); port = int(env("SMTP_PORT","587"))
user = env("SMTP_USER"); pwd = env("SMTP_PASS")
use_tls = env("SMTP_TLS","1") in ("1","true","TRUE","yes","YES")
from_addr = env("FROM") or env("REPORTS_FROM_ADDR")
to_addr   = env("TO")   or env("MICHAEL_TO_ADDR")
cfg_set   = env("SES_CONFIG_SET","").strip()

if not (host and user and pwd and from_addr and to_addr):
    print("SMTP config incomplete", file=sys.stderr); sys.exit(2)

html = open(HTML, encoding="utf-8", errors="ignore").read()
subj = "Daily Market Report"
msg = MIMEText(html, "html", "utf-8")
msg["From"] = from_addr
msg["To"]   = to_addr
msg["Subject"] = subj
if cfg_set:
    msg["X-SES-CONFIGURATION-SET"] = cfg_set

ctx = ssl.create_default_context()
with smtplib.SMTP(host, port, timeout=30) as s:
    if use_tls:
        s.starttls(context=ctx)
    s.login(user, pwd)
    s.sendmail(from_addr, [to_addr], msg.as_string())
print("SES SMTP send OK ->", to_addr)
