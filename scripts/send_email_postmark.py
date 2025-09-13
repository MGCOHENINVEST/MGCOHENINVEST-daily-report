#!/usr/bin/env python3
import os, json, argparse, urllib.request, base64, mimetypes, sys

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--from", dest="from_addr", required=True)
    p.add_argument("--to", dest="to_addr", required=True)
    p.add_argument("--subject", required=True)
    p.add_argument("--html", required=True)
    p.add_argument("--inline-logo", dest="inline_logo", default=None)
    args = p.parse_args()

    token = os.getenv("POSTMARK_TOKEN")
    if not token:
        print("POSTMARK_TOKEN env var not set", file=sys.stderr)
        sys.exit(1)

    with open(args.html, "r", encoding="utf-8") as f:
        html_body = f.read()

    payload = {
        "From": args.from_addr,
        "To": args.to_addr,
        "Subject": args.subject,
        "HtmlBody": html_body,
        "MessageStream": "outbound"
    }

    if args.inline_logo:
        path = args.inline_logo
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        ctype, _ = mimetypes.guess_type(path)
        if not ctype:
            ctype = "application/octet-stream"
        payload["Attachments"] = [{
            "Name": os.path.basename(path),
            "Content": b64,
            "ContentType": ctype,
            "ContentID": "cid:logo"
        }]

    req = urllib.request.Request(
        "https://api.postmarkapp.com/email",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Postmark-Server-Token": token
        }
    )
    with urllib.request.urlopen(req) as resp:
        body = resp.read().decode()
        print(f"{resp.status} {body}")

if __name__ == "__main__":
    main()
