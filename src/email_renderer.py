import argparse, json, os, sys
from jinja2 import Environment, FileSystemLoader, select_autoescape
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--template-dir", required=True)
    p.add_argument("--data", required=True)
    p.add_argument("--snapshot", required=True)
    p.add_argument("--freeze", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    with open(args.data, "r", encoding="utf-8") as f:
        payload = json.load(f)

    env = Environment(
        loader=FileSystemLoader(args.template_dir),
        autoescape=select_autoescape(["html", "xml"])
    )
    tpl = env.get_template("base_email.html.j2")
    html = tpl.render(snapshot=args.snapshot, freeze=args.freeze, **payload)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote {args.out}")

if __name__ == "__main__":
    sys.exit(main())
