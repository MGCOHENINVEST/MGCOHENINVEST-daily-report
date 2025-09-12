#!/usr/bin/env python3
import os, json, argparse, urllib.request

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--from", dest="from_addr", required=True)
    p.add_argument("--to", dest="to_addr", required=True)
    p.add_argument("--subject", required=True)
    p.add_argument("--html", required=True)
    args = p.parse_args()

    token = os.getenv("POSTMARK_TOKEN")
    if not token:
        raise SystemExit("POSTMARK_TOKEN env var not set")

    with open(args.html, "r", encoding="utf-8") as f:
        html_body = f.read()

    payload = {
        "From": args.from_addr,
        "To": args.to_addr,
        "Subject": args.subject,
        "HtmlBody": html_body
    }

    req = urllib.request.Request(
        "https://api.postmarkapp.com/email",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Postmark-Server-Token": token
        },
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        print(resp.status, resp.read().decode())

if __name__ == "__main__":
    main()
