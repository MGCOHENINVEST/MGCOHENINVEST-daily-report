#!/usr/bin/env python3
import json, os, sys, time, urllib.request, urllib.error

UA  = "daily-report/1.0"

def die(msg, code=1):
    print(f"[ERROR] {msg}", file=sys.stderr); sys.exit(code)

def http_json(method, path, token, payload=None, timeout=20):
    req = urllib.request.Request(
        API + path,
        data=(json.dumps(payload).encode("utf-8") if payload is not None else None),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": UA,
        },
        method=method,
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", "replace")
        return json.loads(body)

def main():
    if len(sys.argv) != 5:

    FROM, TO, SUBJECT, HTML_FILE = sys.argv[1:]

    token = os.environ.get("POSTMARK_SERVER_TOKEN", "").strip()
    if not token:
        die("POSTMARK_SERVER_TOKEN missing")

    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            html = f.read()
    except Exception as e:
        die(f"failed to read HTML: {e}")

    payload = {
        "From": FROM,
        "To": TO,
        "Subject": SUBJECT,
        "HtmlBody": html,
        "MessageStream": os.environ.get("POSTMARK_MESSAGE_STREAM", "outbound"),
        "Tag": os.environ.get("POSTMARK_TAG", "DailyReport"),
        # "TrackOpens": True,  # uncomment if you want per-message open tracking
    }

    # --- Send ---
    try:
        resp = http_json("POST", "/email", token, payload, timeout=25)
    except Exception as e:

    err = int(resp.get("ErrorCode") or 0)
    if err != 0:

    msg_id = resp.get("MessageID")
    to_addr = resp.get("To")
    submitted = resp.get("SubmittedAt")

    # --- Optional verify (poll /details for Delivered/Bounced) ---
    if os.environ.get("POSTMARK_VERIFY_DELIVERY", "").strip().lower() in ("1","true","yes"):
        # Config via env (defaults tuned for low noise)
        try:
            initial_delay = int(os.environ.get("POSTMARK_VERIFY_DELAY", "3"))
        except ValueError:
            initial_delay = 3
        try:
            poll_s = int(os.environ.get("POSTMARK_VERIFY_POLL_S", "3"))
        except ValueError:
            poll_s = 3
        try:
            max_wait_s = int(os.environ.get("POSTMARK_VERIFY_MAX_WAIT_S", "45"))
        except ValueError:
            max_wait_s = 45

        if initial_delay > 0:
            time.sleep(initial_delay)

        waited = 0
        last_status = "Sent"
        details_path = f"/messages/outbound/{msg_id}/details"

        while waited <= max_wait_s:
            try:
                d = http_json("GET", details_path, token, timeout=15)
            except urllib.error.HTTPError as e:
                # 422/404 = not indexed yet; wait and retry quietly
                if e.code in (404, 422):
                    time.sleep(poll_s); waited += poll_s
                    continue
                # other HTTP errors: warn once and break
                print(f"[WARN] verify fetch failed: HTTP Error {e.code}: {e.reason}")
                break
            except Exception as e:
                print(f"[WARN] verify fetch failed: {e}")
                time.sleep(poll_s); waited += poll_s
                continue

            last_status = d.get("Status") or last_status
            events = d.get("MessageEvents") or []
            delivered = next((ev for ev in events if ev.get("Type") == "Delivered"), None)
            bounced   = next((ev for ev in events if ev.get("Type") == "Bounced"), None)

            if delivered:
                ts = delivered.get("ReceivedAt")
                print(f"[INFO] Delivery verified: Delivered @ {ts}")
                break
            if bounced:
                ts = bounced.get("ReceivedAt")
                print(f"[ERROR] Delivery failed: Bounced @ {ts}")
                break

            time.sleep(poll_s); waited += poll_s

        if waited > max_wait_s:
            print(f"[WARN] No Delivered event within {max_wait_s}s (last Status={last_status})")

if __name__ == "__main__":
    main()
