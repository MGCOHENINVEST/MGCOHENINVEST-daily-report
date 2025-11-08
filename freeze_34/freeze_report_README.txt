# 📌 Quick Reference (1-Page Summary)

**Daily Report System — Essentials for Operators**

### Daily Routine
- Cron runs at **06:00 GMT**, auto-sends report.
- Check inbox + logs each morning to confirm success.
- If failure: retry manually via `python3 send_report.py`.

### Key Files
- `daily_report_full.html` → main email template (logo, outlook, tables, watchlist).
- `send_report.py` → script to send via SMTP/SendGrid.
- `watchlist_with_sparklines.html` → snippet for stock watchlist (already embedded).
- `sparklines_base64.txt` → backup of sparkline image strings.
- `freeze_report_README.txt` → full manual (this file).

### Troubleshooting
- API failure → `(P)` placeholders remain (still sends).
- Email send fails → retry manually, check credentials.
- Cron fails → run manually and check server timezone.

### Go-Live Checklist (Condensed)
- ✅ Logo hosted on S3 and working in template.
- ✅ Placeholders `(P)` replaced with live data feeds.
- ✅ Tested 3+ consecutive days successfully.
- ✅ Recipient updated to Sir John’s email.
- ✅ Compliance + monitoring in place.

### Emergency Fallback
- If automation/server fails, manually send static version with rates, indices, FX, and headlines.
- Sir John must **always receive something** by morning.

---
# Daily Report System - Freeze Report (1 Sep 2025)

## Current Decisions
- HTML-only email
- Logo + tagline header (Kairos logo via S3 hosting)
- Title: Daily Report for Sir John Ritblat
- Timestamp auto-generated (06:00 GMT)
- Outlook blurb at top
- Sections: Rates, Indices, FX, News, Financial News, Watchlist (with sparklines), Company Announcements, Macro Announcements
- Watchlist: M&G, LGEN, Phoenix, Barclays, HSBC, Lloyds, Metals Exploration
- Placeholders marked with (P)
- Recipient: test mode (your inbox)
- Subject line: Daily Report for Sir John Ritblat — {date}

## ⏰ Cron Scheduling Example
To send the Daily Report automatically every day at 06:00 GMT, add the following line to your crontab:

0 6 * * * /usr/bin/python3 /path/to/send_report.py

- Ensure `daily_report_full.html` is in the same directory or update the path inside send_report.py.
- Adjust `/usr/bin/python3` if your Python binary is elsewhere.

## 🔑 SendGrid Variant
If you are using SendGrid instead of raw SMTP, your cron entry remains the same:

0 6 * * * /usr/bin/python3 /path/to/send_report.py

But inside `send_report.py`, swap out the SMTP section with:

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

message = Mail(
    from_email=FROM_EMAIL,
    to_emails=TO_EMAIL,
    subject=SUBJECT,
    html_content=html_body
)
sg = SendGridAPIClient("YOUR_SENDGRID_API_KEY")
sg.send(message)

- Replace "YOUR_SENDGRID_API_KEY" with your actual SendGrid API key.
- No SMTP_USER/SMTP_PASS needed when using SendGrid API client.

## 🖼 Hosting the Kairos Logo on S3
To host your Kairos logo for use in the Daily Report:

1. **Prepare the file**: Save as `kairos-logo.png` (small, web-friendly PNG/JPG).
2. **Upload to S3**:
   - Go to AWS Console → S3 → Create or select a bucket (e.g., `kairos-assets`).
   - Upload `kairos-logo.png`.
3. **Set permissions**:
   - In object settings, set ACL to allow public read access.
   - Confirm "Object URL" is available.
4. **Copy URL**: Example URL format:
   https://kairos-assets.s3.eu-west-1.amazonaws.com/kairos-logo.png
5. **Update HTML**: In `daily_report_full.html`, replace placeholder:
   <img src="LOGO_URL_HERE" alt="Kairos Logo" class="logo">
   with:
   <img src="https://kairos-assets.s3.eu-west-1.amazonaws.com/kairos-logo.png" alt="Kairos Logo" class="logo">

✅ Your logo will now appear inline in every Daily Report.

## 🔄 Replacing Placeholders (P) with Live Data

In the current Daily Report, some sections show `(P)` where data feeds were not available.
These are intended to be replaced automatically once API integrations are in place.

### Company Announcements
- **Source**: Dividend and earnings feeds from EODHD (`getDividends`, `getFundamentals`).
- **Process**:
  1. Query each watchlist ticker for dividends in the relevant window.
  2. Query earnings calendars for result dates.
  3. Replace `(P)` lines in "Company Announcements This Week" with actual entries.
- **Example**:
  - Before: `M&G — Interim Results (P)`
  - After:  `M&G — Interim Results, 4 Sep 2025`

### Macro Announcements
- **Source**: Macro indicators (EODHD `getMacro`) or public calendars (FRED, central banks).
- **Process**:
  1. Pull upcoming events (NFP, CPI, ECB/BoE/Fed meetings).
  2. Map them into the "Macro Announcements This Week" section.
  3. Replace `(P)` placeholders with exact dates/labels.
- **Example**:
  - Before: `US CPI Release — 12 Sep 2025 (P)`
  - After:  `US CPI Release — 12 Sep 2025`

### Automation Strategy
- Extend backend script (`send_report.py`) to run data fetch before assembling HTML.
- Insert fetched data into placeholders dynamically at runtime.
- Keep `(P)` as fallback only if feed fails.

✅ This ensures reports evolve from semi-static to fully data-driven without manual edits.

## ⚙️ Backend Data-Fetch Workflow (Pseudo-code)

To replace placeholders `(P)` and make the Daily Report fully automated, extend the backend as follows:

```python
# 1. Import clients
from eodhd_flask_proxy_onrender_com__jit_plugin import getDividends, getFundamentals, getMacro

# 2. Company Announcements
watchlist = ["MNG.LSE", "LGEN.LSE", "PHNX.LSE", "BARC.LSE", "HSBA.LSE", "LLOY.LSE", "MTL.LSE"]
for ticker in watchlist:
    dividends = getDividends(ticker=ticker, from="2025-08-01", to="2025-09-30")
    # Parse dividend ex-dates, payment dates, values
    # If none found → leave (P), else replace with real entry

# 3. Macro Announcements
macros = [
    {"code": "USNFP", "label": "US Nonfarm Payrolls"},
    {"code": "USCPI", "label": "US CPI"},
    {"code": "UKGDP", "label": "UK GDP Monthly Estimate"},
    {"code": "ECBMTG", "label": "ECB Policy Meeting"}
]
for m in macros:
    data = getMacro(code=m["code"], from="2025-09-01", to="2025-09-30")
    # Insert event dates into Macro Announcements section

# 4. Update HTML
with open("daily_report_full.html") as f:
    html = f.read()

html = html.replace("M&G — Interim Results (P)", "M&G — Interim Results, 4 Sep 2025")
# Do the same for other placeholders...

with open("daily_report_full.html", "w") as f:
    f.write(html)
```

### Key Notes
- Keep `(P)` as fallback if no data is returned (avoids empty lines).
- Run fetch step *before* sending email at 06:00 GMT.
- Consider caching API results for stability.

✅ This creates a dynamic pipeline: **data → HTML injection → send at 06:00 GMT**

## ➕ Expanding the Watchlist

The current Daily Report watchlist includes:
- M&G (MNG.LSE)
- Legal & General (LGEN.LSE)
- Phoenix Group (PHNX.LSE)
- Barclays (BARC.LSE)
- HSBC (HSBA.LSE)
- Lloyds (LLOY.LSE)
- Metals Exploration (MTL.LSE)

### How to Add New Tickers
1. **Update Backend Watchlist**
   - Extend the `watchlist` array in your backend script:
     ```python
     watchlist = ["MNG.LSE", "LGEN.LSE", "PHNX.LSE", "BARC.LSE", "HSBA.LSE", "LLOY.LSE", "MTL.LSE", "NEW.LSE"]
     ```

2. **Fetch Data**
   - Ensure new tickers go through the same data fetch process (dividends, fundamentals, prices).

3. **Generate Sparklines**
   - Run the sparkline generator for the new ticker’s 3M price series.
   - Output a base64 string and embed into HTML:
     ```html
     <img src="data:image/png;base64,BASE64_STRING_HERE" alt="sparkline" />
     ```

4. **Update HTML**
   - Add a new `<tr>` row to the watchlist table in `daily_report_full.html` with the correct fields:
     ```html
     <tr>
       <td>NEW.LSE</td><td>New Company</td><td>XLON</td><td>Price</td><td>MktCap</td>
       <td>DivYld%</td><td>TSR%</td><td>RP Action</td><td>[sparkline]</td>
     </tr>
     ```

### Notes
- Maintain the **same table schema** for consistency.
- If data is missing, mark entries with `(P)` as placeholder.
- Sparklines can be regenerated periodically or daily with updated price data.

✅ This keeps the Watchlist scalable and consistent as you add more companies.

## 🚨 Error Handling & Troubleshooting

To keep the Daily Report robust, here are common failure points and strategies:

### 1. API Failures (Data Fetch)
- **Problem**: API returns no data (empty response) or times out.
- **Solution**:
  - Default to `(P)` placeholder.
  - Log error for later review (e.g. to a log file or console).
  - Do not break email build; report still sends with placeholders.

```python
try:
    dividends = getDividends(ticker="MNG.LSE", from="2025-08-01", to="2025-09-30")
except Exception as e:
    print(f"Error fetching dividends for MNG.LSE: {e}")
    dividends = []
```

### 2. Sparkline Generation
- **Problem**: Missing or corrupted price data causes chart to fail.
- **Solution**:
  - Wrap sparkline generator in try/except.
  - If fail, insert a placeholder image or text like "n/a".

### 3. Email Send Failure
- **Problem**: SMTP or SendGrid rejects send.
- **Solution**:
  - Wrap `sendmail` or `sg.send` in try/except.
  - Log failure.
  - Optionally retry once after a short delay.

```python
try:
    server.sendmail(FROM_EMAIL, TO_EMAIL, msg.as_string())
except Exception as e:
    print(f"Send failed: {e}")
```

### 4. HTML Rendering Issues
- **Problem**: Some clients (e.g. Outlook) strip styles or block images.
- **Solution**:
  - Test template across Gmail, Outlook, and iOS Mail.
  - Inline critical CSS where possible.
  - Use absolute URLs for images (S3 hosting) instead of relying solely on base64.

### 5. Cron Job Doesn’t Fire
- **Problem**: Report not generated at 06:00 GMT.
- **Solution**:
  - Check `cron` log (`/var/log/cron.log` or `journalctl`).
  - Ensure correct timezone is set on server.
  - Confirm Python path (`/usr/bin/python3`) is valid.

✅ With these safeguards, the Daily Report will degrade gracefully (placeholders instead of crashes) and send reliably even if some feeds fail.

## 🚀 Go-Live Checklist

When ready to move from dummy/test reports to production delivery for Sir John, follow this checklist:

### 1. Branding
- [ ] Host Kairos logo on S3 and update `daily_report_full.html` with the public URL.
- [ ] Confirm tagline and header match corporate style guide.

### 2. Data
- [ ] Replace all `(P)` placeholders with live API data feeds for dividends, earnings, and macro events.
- [ ] Verify sparklines are generating correctly with **live price data** (not mock data).
- [ ] Confirm watchlist tickers are correct and up to date.

### 3. Email System
- [ ] Update `TO_EMAIL` in `send_report.py` from your inbox → Sir John’s real email.
- [ ] Test send to a secondary account to confirm formatting works in multiple clients (Gmail, Outlook, iOS Mail).
- [ ] Confirm subject line dynamically shows today’s date.

### 4. Scheduling
- [ ] Confirm cron job runs daily at **06:00 GMT**.
- [ ] Ensure server timezone is correct (use UTC/GMT to avoid drift).

### 5. Fail-Safes
- [ ] Ensure `(P)` remains as fallback if API data not available (no blank sections).
- [ ] Check error logging for failed sends or API errors.

### 6. Final Validation
- [ ] Send at least **3 consecutive days** of successful dummy reports with live data feeds before enabling Sir John’s email.
- [ ] Once validated, switch recipient to Sir John.

✅ Once all boxes are ticked, the system is production-ready.

## 🌟 Future Enhancements Roadmap

The Daily Report system is functional and production-ready, but here are potential enhancements to increase value over time:

### Data & Analytics
- [ ] **Peer Comparisons**: Add valuation vs. sector peers (P/E, EV/EBITDA).
- [ ] **Sentiment Analysis**: Pull news sentiment (positive/negative) per watchlist stock.
- [ ] **Broker Targets**: Integrate consensus analyst target prices and ratings.

### Visuals
- [ ] **Mini Charts**: Add bar/line charts for macro trends (e.g. CPI, bond yields).
- [ ] **Heatmaps**: Daily index sector performance in heatmap format.
- [ ] **Interactive Sparklines**: Upgrade from static images to live charts (if viewed in a web dashboard).

### Workflow
- [ ] **User Customisation**: Allow different watchlists per recipient.
- [ ] **Dynamic Filters**: Exclude/include sectors dynamically.
- [ ] **Multi-Language Support**: Reports in English + another language (e.g., French for EU recipients).

### Infrastructure
- [ ] **Database Logging**: Store each day’s report content for audit and review.
- [ ] **Web Dashboard**: Host a browser-accessible archive of past reports with charts and filters.
- [ ] **Push Notifications**: SMS or mobile alerts for key market events alongside the email.

✅ These are optional enhancements — the core pipeline (HTML email with tables, sparklines, and announcements) is stable and sufficient for production.

## 🗂 Version History

Use this section to track freezes/checkpoints as the system evolves.

### v1.0 — 1 Sep 2025
- First stable freeze.
- Core Daily Report format locked (HTML-only, logo, tagline, outlook, sections).
- Watchlist with sparklines embedded (MNG, LGEN, PHNX, BARC, HSBA, LLOY, MTL).
- Placeholder `(P)` system in place for missing data.
- SMTP + cron setup documented.
- SendGrid variant documented.
- S3 logo hosting instructions added.
- Error handling & troubleshooting included.
- Go-Live Checklist defined.
- Future Enhancements Roadmap added.

### v1.1 — (to be filled)
- Notes for future iterations here.

✅ Each new freeze, update this section with date + summary of changes. This becomes the release log for the Daily Report system.

## 🗃 File Map

This section explains the role of each file in the Daily Report system.

### 1. `daily_report_full.html`
- The **main email template**.
- Contains: logo, tagline, outlook blurb, tables (Rates, Indices, FX), News, Financial News, Watchlist with sparklines, Announcements.
- Placeholders `(P)` mark missing live data to be replaced later.
- Used directly as the email body in `send_report.py`.

### 2. `watchlist_with_sparklines.html`
- Standalone snippet containing the watchlist table only.
- Useful for testing or updating the watchlist independently before merging into full report.

### 3. `sparklines_base64.txt`
- Backup file of base64-encoded sparkline image strings.
- Each ticker labeled with its sparkline string.
- Redundant for daily use (already embedded in HTML), but useful for regeneration or debugging.

### 4. `send_report.py`
- Backend script to send the report via SMTP (Gmail, Office365, or other SMTP relay).
- Reads `daily_report_full.html` as body.
- Builds MIME message with plain-text fallback.
- Configurable with SMTP_USER, SMTP_PASS, TO_EMAIL.
- Includes subject line auto-stamped with today’s date.

### 5. `freeze_report_README.txt`
- This file.
- Acts as the **manual** for operators.
- Contains: setup instructions, cron/SendGrid/S3 guides, error handling, go-live checklist, enhancements roadmap, version history, file map.

### 6. `daily_report_freeze_package.zip`
- Archive containing all of the above.
- Used for checkpoints, backups, and to rehydrate the system in new environments or new chats.

✅ With this map, each component’s purpose and place in the pipeline is documented.

## 🏗 System Architecture Overview

The Daily Report pipeline can be understood in three layers: **Data Sources → Backend Processing → Delivery**.

### 1. Data Sources
- **Market Data & Fundamentals**: EODHD API (equities, dividends, macros).
- **Macro Data**: FRED, central bank feeds (CPI, NFP, GDP, policy meetings).
- **News**: Reuters, The Times, The Guardian (curated links).
- **FX**: EODHD Forex endpoints.

### 2. Backend Processing
- **Scheduler**: Cron job triggers at 06:00 GMT.
- **Data Fetch**:
  - Pull dividends/earnings per ticker (watchlist).
  - Pull macro announcements (NFP, CPI, ECB, BoE, Fed).
  - Generate sparklines (price series → base64 image).
- **HTML Assembly**:
  - Start with `daily_report_full.html` template.
  - Insert fetched data, replacing `(P)` placeholders.
  - Embed sparklines inline.
  - Insert news links dynamically (top 5 general + top 5 financial).
- **Error Handling**:
  - Any failed data fetch = `(P)` placeholder retained.
  - Logged errors for operator review.

### 3. Delivery
- **Email Script** (`send_report.py`):
  - Loads final HTML into MIME message.
  - Includes plain-text fallback (minimal).
  - Sends via:
    - **SMTP** (default, Gmail/Office365/other relay), OR
    - **SendGrid** (API key client).
- **Recipients**:
  - Test mode: operator inbox.
  - Production mode: Sir John Ritblat (plus optional CC/BCC).

### Diagram (Text Form)
```
[ APIs: EODHD / FRED / News ] 
          ↓
   [ Data Fetch Layer ]
          ↓
   [ HTML Assembly (daily_report_full.html) ]
          ↓
   [ send_report.py ]
          ↓
   [ Email via SMTP/SendGrid ]
          ↓
   [ Inbox: Operator (test) → Sir John (production) ]
```

✅ This architecture ensures modularity: each layer (data fetch, assembly, delivery) can be upgraded independently without breaking the pipeline.

## 🔐 Security & Compliance

To ensure the Daily Report system operates securely and within compliance requirements, follow these practices:

### API Keys & Credentials
- **Storage**: Never hardcode API keys or SMTP passwords in scripts.
  - Use environment variables (`export API_KEY=xxxx`).
  - Or load from a `.env` file (with proper `.gitignore` rules).
- **Rotation**: Rotate API keys and passwords periodically (every 90 days recommended).
- **Access Control**: Restrict API keys to required endpoints only (least privilege principle).

### Email Delivery
- **Sender Authentication**:
  - Use SPF, DKIM, and DMARC on sending domain to prevent spoofing.
  - Test deliverability with mail-tester.com before production rollout.
- **Recipient Safety**:
  - Test reports go only to operator inbox until live.
  - Explicit go-live checklist before adding Sir John as recipient.

### Data Handling
- **Personal Data**: The report currently includes no personal/sensitive data.
  - If expanded (e.g., recipient-specific portfolios), GDPR/UK DPA obligations apply.
- **Storage**:
  - If you log or archive past reports, ensure storage is encrypted and access-limited.
  - Retain logs only as long as needed for audit/troubleshooting.

### System Security
- **Server Hardening**:
  - Keep OS and Python libraries up to date.
  - Restrict cron job execution to authorized users only.
- **Error Logs**:
  - Logs may contain error messages but should not store credentials.
  - Review logs regularly for API errors or failed sends.

✅ Following these practices ensures compliance with security best practices and reduces operational risk.

## 🛡 Disaster Recovery & Backup Plan

To ensure continuity of the Daily Report system in case of server failure or data loss:

### 1. Code & Templates
- **Freeze Packages**: Keep a copy of each `daily_report_freeze_package.zip` in secure cloud storage (AWS S3, OneDrive, Google Drive).
- **Versioning**: Label each package by date/version (e.g., `daily_report_v1.0_2025-09-01.zip`).
- **Restore**: Unzip into a fresh environment and follow README instructions to rehydrate system.

### 2. Credentials
- **Storage**: Keep SMTP/API credentials in a secure password manager (1Password, Bitwarden).
- **Recovery**: If lost, regenerate API keys and reset SMTP passwords; update environment variables.

### 3. Server Failure
- **Rebuild Steps**:
  1. Spin up replacement server/VM/container.
  2. Install Python 3.x and required libraries (`pip install -r requirements.txt` if using one).
  3. Restore latest freeze package from backup.
  4. Reconfigure SMTP/API keys as environment variables.
  5. Restore cron job entry for 06:00 GMT.

### 4. Data & Logs
- **Storage**: If storing historical reports, back them up daily to cloud or external storage.
- **Recovery**: Reload archive for compliance/audit needs.

### 5. Manual Workaround
- If automation fails:
  - Manually run `send_report.py` from operator machine with local HTML file.
  - Ensures report delivery even if scheduler/server is down.

✅ With this plan, the system can be rebuilt and resumed within hours of failure, minimizing downtime.

## ⚡ Performance & Scalability

The Daily Report system is lightweight, but here are considerations for scaling up:

### 1. Watchlist Expansion
- **Impact**: More tickers = more API calls + more sparklines to generate.
- **Mitigation**:
  - Use batch API endpoints where available (reduce HTTP calls).
  - Cache price data if generating sparklines for overlapping tickers.
  - Parallelize API requests with async/threads if needed.

### 2. Recipients
- **Impact**: Sending to more users = higher SMTP/SendGrid throughput.
- **Mitigation**:
  - For <100 recipients: fine with standard SMTP relay.
  - For larger lists: use SendGrid (bulk delivery support, rate limiting).
  - Maintain one HTML template and send in bulk to avoid regenerating per user.

### 3. Report Size
- **Impact**: Large base64 images (sparklines, logo) increase email size.
- **Mitigation**:
  - Keep sparklines small (<10 KB each).
  - Consider external hosting (S3) for charts if email size exceeds ~1MB.

### 4. Processing Time
- **Impact**: More tickers/macros = longer build time.
- **Mitigation**:
  - Profile bottlenecks (API latency vs. local generation).
  - Run data fetch in parallel, assemble HTML at the end.

### 5. Future Enhancements
- **Scaling Path**:
  - For enterprise use: move from cron job → workflow manager (Airflow/Luigi).
  - For heavier analytics: offload to cloud function or container service (AWS Lambda, ECS).

✅ Current system easily scales to ~50 tickers and ~500 recipients daily with minimal changes.

## 🔄 Change Management

To ensure updates and new features don’t disrupt Sir John’s morning report, follow structured change control:

### 1. Development & Testing
- **Sandbox First**:
  - Test all changes (HTML, sparklines, scripts) in a non-production environment or local machine.
- **Dummy Recipients**:
  - Keep TO_EMAIL pointed at your own inbox until tested for at least 3 consecutive days.

### 2. Versioning
- **Freeze Reports**:
  - Before any major change, create a new `daily_report_freeze_package.zip` with version label (e.g., v1.1).
- **Track Changes**:
  - Update Version History section in README with what changed.

### 3. Deployment
- **Staged Rollout**:
  - Step 1: Deploy to test inbox only.
  - Step 2: Validate output formatting (tables, sparklines, news links).
  - Step 3: Confirm automation (cron 06:00 GMT runs without fail).
- **Final Step**:
  - Update TO_EMAIL → Sir John’s inbox once validated.

### 4. Rollback Plan
- **If an Update Fails**:
  - Revert to the last stable freeze package (unzipped and re-linked).
  - Logs/errors reviewed before retrying rollout.

### 5. Communication
- **Operator Log**:
  - Keep simple notes of changes and outcomes (date, version, issues).
- **Sir John**:
  - Inform recipient only after changes are validated and stable (avoid visible test errors).

✅ This ensures the Daily Report evolves safely, without risk of missed or broken reports in production.

## 📡 Monitoring & Alerting

To ensure issues are detected early (before the recipient notices), implement basic monitoring and alerts:

### 1. Logging
- **Email Sends**:
  - Log every attempt (success/failure) with timestamp.
  - Example: `2025-09-01 06:00:01 - Report sent successfully.`
- **API Calls**:
  - Log errors (timeouts, invalid responses) with ticker/code affected.

### 2. Alerts
- **Email Alerts**:
  - On send failure, trigger an alert email to operator inbox (separate from Daily Report).
- **Slack/Teams Alerts** (optional):
  - Use webhook integration to push errors directly into a monitoring channel.

### 3. Health Checks
- **Scheduled Verification**:
  - After cron job runs, send a small “ping” log entry (success/failure) to a file or monitoring system.
- **Self-Test Mode**:
  - Add a `--test` flag to `send_report.py` to run a dry-run without sending, just verifying HTML builds.

### 4. Metrics
- **Success Rate**: Track how many reports send successfully per month.
- **Latency**: Measure how long the build + send process takes (should remain <1 min).

### 5. Escalation
- **Immediate**: Operator notified of failed send within minutes.
- **Fallback**: If automation fails, operator can run `send_report.py` manually with local HTML.

✅ With monitoring and alerts in place, you’ll know if something fails at 06:00 GMT — and can act before Sir John ever notices.

## 📝 Compliance & Audit Trail

To ensure transparency and accountability, maintain a clear record of system runs and changes.

### 1. Run Logs
- **Daily Execution Log**:
  - Record each cron job run with timestamp, success/failure, and recipient.
  - Example: `2025-09-01 06:00 GMT - SUCCESS - Sent to operator@example.com`
- **Error Logs**:
  - Log API errors, send failures, and placeholder insertions.
  - Retain at least 90 days of logs for audit purposes.

### 2. Change Tracking
- **Version History**:
  - Update README "Version History" whenever freeze packages are created.
  - Note what was changed (templates, watchlist, code).  
- **Operator Log** (simple text file):
  - Date, operator, change, outcome.
  - Example: `2025-09-01 - Updated watchlist, added NEW.LSE, tested OK`.

### 3. Backups
- **Freeze Packages**:
  - Store each `daily_report_freeze_package.zip` in cloud storage with version labels.
- **Immutable Storage** (optional):
  - Archive key reports in write-once storage (AWS Glacier, corporate archive).

### 4. Compliance Alignment
- **GDPR/UK DPA**:
  - No personal data currently in use, so minimal compliance requirements.
  - If personalization added, ensure data subject rights (access, deletion) can be fulfilled.
- **Audit-Ready**:
  - System should be able to demonstrate:
    - When each report was generated.
    - To whom it was sent.
    - What data sources were queried.

✅ This creates a defensible audit trail for regulators, auditors, or internal compliance reviews.

## 👥 Roles & Responsibilities

To ensure smooth operation and accountability of the Daily Report system, assign clear roles:

### 1. Operator
- **Responsibilities**:
  - Maintain scripts, templates, and freeze packages.
  - Monitor daily sends at 06:00 GMT (check inbox + logs).
  - Troubleshoot API or send failures.
  - Implement updates (watchlist changes, formatting improvements).
- **Authority**:
  - Can make technical changes in test mode.
  - Must log changes in operator log and README version history.

### 2. Approver
- **Responsibilities**:
  - Validate major updates before go-live (e.g., new tickers, format changes).
  - Review go-live checklist before Sir John’s inbox is enabled.
- **Authority**:
  - Sign off on production deployment changes.

### 3. Recipient (Sir John Ritblat)
- **Responsibilities**:
  - None operationally.
  - Consumer of final Daily Report.
- **Authority**:
  - Feedback on clarity and relevance of content.

### 4. Compliance / Oversight (optional role)
- **Responsibilities**:
  - Ensure GDPR/UK DPA compliance if personalization introduced.
  - Review audit trail periodically.
- **Authority**:
  - Can mandate changes to process for regulatory alignment.

✅ Clear separation of duties ensures smooth operation, reduces risk of error, and provides auditability.

## 🧭 Business Continuity

To ensure the Daily Report continues even if the Operator is unavailable:

### 1. Documentation
- **Freeze Packages**:
  - Always keep the latest `daily_report_freeze_package.zip` accessible in shared secure storage.
- **README**:
  - This file serves as the full operations manual. Any competent replacement should be able to follow it.

### 2. Backup Operator
- **Assignment**:
  - Designate a secondary operator with access to scripts, credentials, and cron jobs.
- **Training**:
  - Backup operator should run through dummy sends at least once per month.

### 3. Fallback Delivery
- **Manual Send**:
  - If automation fails and both primary and backup operators unavailable, send a simplified version of the report (static template with placeholders) manually from local machine.
- **Minimum Viable Output**:
  - Rates, indices, FX, and headlines — even without sparklines or announcements — are acceptable as emergency fallback.

### 4. Escalation
- **Approver Role**:
  - Approver may temporarily act as Operator in exceptional cases (using README and freeze package as guide).
- **Compliance Oversight**:
  - Ensures continuity actions remain documented and compliant.

✅ With backup operator, fallback delivery, and shared documentation, the Daily Report can continue uninterrupted even if the primary Operator is unavailable.

## 📣 Stakeholder Communication

Clear and timely communication ensures trust and transparency with Sir John and other stakeholders.

### 1. Routine
- **Normal Operations**:
  - No need to notify Sir John of daily report mechanics — he should only see the polished output.
- **Minor Changes** (formatting tweaks, sparklines updates):
  - No direct notification required, unless it materially changes readability.

### 2. Disruptions
- **Report Delay (short)**:
  - If delivery will be delayed by <2 hours, no notification needed unless repeated.
- **Report Delay (extended)**:
  - If delivery will be missed or delayed beyond 2 hours, notify Sir John with a short note:
    - Example: *"Today’s Daily Report is delayed due to a system issue. A summary will follow shortly."*
- **Report Failure**:
  - Send emergency fallback (rates, indices, FX, headlines) and note that full version will resume tomorrow.

### 3. Major Changes
- **Watchlist Expansion**:
  - Notify Sir John when new companies are added, framed as an enhancement.
- **Section Additions (charts, sentiment, etc.)**:
  - Inform in advance so expectations are set.
- **Schedule Changes**:
  - Communicate if report timing (06:00 GMT) is altered.

### 4. Escalation
- **Operator → Approver**:
  - Operator informs Approver of extended disruptions before contacting Sir John.
- **Approver → Sir John**:
  - Approver delivers the client-facing communication if issue is prolonged or recurring.

✅ This approach keeps Sir John informed without burdening him with operational noise, while maintaining confidence in the report’s reliability.

## 📖 Glossary

Key terms and acronyms used in the Daily Report system:

### Financial Metrics
- **ADV**: Average Daily Volume (liquidity measure, in £m).
- **MktCap**: Market Capitalisation (total value of a company’s shares, in £m).
- **P/E**: Price-to-Earnings ratio (valuation metric).
- **EV/EBITDA**: Enterprise Value to Earnings Before Interest, Tax, Depreciation, and Amortisation (valuation multiple).
- **TSR**: Total Shareholder Return (price appreciation + dividends over 1 year, in %).
- **DivYld**: Dividend Yield (annual dividends ÷ current share price, in %).

### Market Terms
- **Sparklines**: Miniature charts showing recent price trends.
- **200D**: 200-day moving average (long-term trend indicator).
- **Tier 1/2/3**: Momentum grouping based on proximity to 52-week highs and moving averages.

### Technical / Infrastructure
- **SMTP**: Simple Mail Transfer Protocol (used for sending emails).
- **SendGrid**: Email delivery service via API.
- **Cron**: Linux scheduler used to automate daily sends (06:00 GMT).
- **Base64**: Encoding scheme used to embed images (sparklines, logo) directly into HTML emails.

### Compliance / Security
- **SPF/DKIM/DMARC**: Email authentication standards to prevent spoofing and improve deliverability.
- **GDPR / UK DPA**: Data protection regulations applying to personal information.

✅ With this glossary, new operators can understand both financial and technical terminology at a glance.

## 🏁 Onboarding Guide for New Operators

This guide provides a structured path for a new operator to get up to speed quickly and confidently.

### Day 1 Checklist
1. **Read the README**
   - Familiarise yourself with system overview, glossary, and roles.
   - Understand responsibilities of Operator vs. Approver.

2. **Environment Setup**
   - Install Python 3.x.
   - Install required libraries (`pip install -r requirements.txt` if available).
   - Set environment variables for SMTP/SendGrid credentials.

3. **Files & Templates**
   - Download latest `daily_report_freeze_package.zip`.
   - Extract contents into working directory.
   - Open `daily_report_full.html` to review report structure.

4. **Test Email Send**
   - Run `python3 send_report.py` in test mode (TO_EMAIL set to your own inbox).
   - Verify the email arrives correctly and renders with tables, sparklines, and placeholders.

5. **Review Logs**
   - Check console/log outputs for API errors or placeholders `(P)` left in place.
   - Confirm error handling is working (report should still send even with failed API calls).

### Week 1 Checklist
- **Practice**:
  - Trigger a few test runs manually at different times.
  - Edit watchlist and confirm sparklines regenerate correctly.
- **Backup/Recovery Drill**:
  - Rehydrate the system from a freeze package in a clean environment.
  - Confirm you can restore and send successfully.
- **Communication**:
  - Review stakeholder communication rules (when to notify Sir John or Approver).

### Ongoing Responsibilities
- Monitor daily 06:00 GMT sends (check inbox + logs).
- Apply version control when making changes (new freeze package + update README).
- Ensure compliance practices are followed (API key security, GDPR alignment).

✅ Following this guide, a new operator should be fully functional within **one day**, and confident in recovery and operations by the end of **week one**.

## 🌅 Decommissioning / Sunsetting

If the Daily Report system is ever retired or replaced, follow these steps to ensure a clean and compliant shutdown:

### 1. Notification
- **Stakeholders**:
  - Inform Sir John and other recipients that the Daily Report will be discontinued or replaced.
  - Provide clear end date for last report delivery.
- **Internal Teams**:
  - Notify Approver and Compliance of the decision and timeline.

### 2. Data & Archives
- **Freeze Package**:
  - Create a final `daily_report_freeze_package.zip` as an archival snapshot (last version).
- **Historical Reports**:
  - Archive past reports and logs in secure storage (cloud or corporate archive).
  - Retain according to compliance requirements (e.g., 1–7 years depending on jurisdiction).

### 3. Credentials
- **API Keys & SMTP/SendGrid**:
  - Revoke or delete keys no longer needed.
  - Remove credentials from environment variables and password managers.

### 4. Infrastructure
- **Servers**:
  - Disable cron job and any automation scripts.
  - Decommission or repurpose server/VM/container hosting the pipeline.
- **Monitoring**:
  - Remove alerts, Slack integrations, or email error notifications.

### 5. Documentation
- **Final Update**:
  - Update README with final version tag (e.g., v2.0 - Decommissioned).
  - Record reasons for retirement and replacement system details (if any).

✅ This ensures a professional, compliant, and risk-free retirement of the Daily Report system.

## 🖼 System Flowchart

Below is a visual diagram of the Daily Report pipeline:

![Daily Report Flowchart](daily_report_flowchart.png)

This complements the text-based architecture overview, showing the flow from:
**Data Sources → Backend Processing → HTML Assembly → Email Script → Delivery → Recipient**

## 🛠 Checklist for First-Time Deployment

If setting up the Daily Report system on a fresh server or environment, follow this step-by-step checklist:

### 1. Environment Setup
- [ ] Install **Python 3.x**.
- [ ] Install required libraries:
  ```bash
  pip install smtplib requests matplotlib
  ```
- [ ] Set up environment variables for credentials:
  ```bash
  export SMTP_USER="your.email@domain.com"
  export SMTP_PASS="your_app_password_here"
  export SENDGRID_API_KEY="your_sendgrid_key_here"  # if using SendGrid
  ```

### 2. Files & Templates
- [ ] Download and extract the latest `daily_report_freeze_package.zip`.
- [ ] Confirm presence of all files:
  - `daily_report_full.html`
  - `send_report.py`
  - `watchlist_with_sparklines.html`
  - `sparklines_base64.txt`
  - `freeze_report_README.txt`
  - `daily_report_flowchart.png`

### 3. Test Run
- [ ] Edit `send_report.py` → ensure correct paths and email addresses.
- [ ] Run:
  ```bash
  python3 send_report.py
  ```
- [ ] Confirm email received in test inbox.

### 4. Cron Setup
- [ ] Add cron job for daily sends at 06:00 GMT:
  ```bash
  0 6 * * * /usr/bin/python3 /path/to/send_report.py
  ```
- [ ] Verify cron job logs to ensure execution.

### 5. Validation
- [ ] Confirm sparklines render correctly in email client.
- [ ] Check `(P)` placeholders remain where no live data is available.
- [ ] Ensure logo loads from S3-hosted URL.

### 6. Go-Live
- [ ] Test at least **3 consecutive days** of dummy sends.
- [ ] Update `TO_EMAIL` in `send_report.py` to Sir John’s email once validated.
- [ ] Mark README Version History with new deployment.

✅ This ensures a clean, reproducible setup when deploying the system on new infrastructure.

## 📦 Requirements File

A `requirements.txt` file is included in this package.  
Install dependencies with:

```bash
pip install -r requirements.txt
```

This ensures the correct Python libraries are available for running the Daily Report system.

## 🔑 Environment Variables (.env)

A sample `.env` file is included in this package.  
Fill in your SMTP or SendGrid credentials before running the report.

Example:

```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your.email@domain.com
SMTP_PASS=your_app_password_here
SENDGRID_API_KEY=your_sendgrid_api_key_here
FROM_EMAIL=your.email@domain.com
TO_EMAIL=recipient@domain.com
```

Use `python-dotenv` to load these automatically in `send_report.py` if desired.
