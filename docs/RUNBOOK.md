# Daily Email Runbook
- Manual run: `sudo systemctl start daily-email.service`
- Timer schedule: `systemctl list-timers | grep daily-email`
- Logs: `journalctl -u daily-email.service --no-pager -n 200`
- Env: `/etc/daily-report.env` (POSTMARK_TOKEN)
- Wrapper: `/opt/daily-report/scripts/run_daily.sh`
- Render artifact: `out/daily_smoke_test.html`
