#!/usr/bin/env python3
import csv
import sys
from pathlib import Path

BOND_FILE = Path("data/bonds.csv")

def validate_bond_row(row, lineno):
    errors = []

    # Required fields
    required_fields = [
        "isin", "issuer", "coupon", "maturity",
        "price", "ytm", "running_yield"
    ]
    for field in required_fields:
        if not row.get(field):
            errors.append(f"Line {lineno}: Missing {field}")

    # Numeric checks
    try:
        coupon = float(row.get("coupon", 0))
        if coupon < 0:
            errors.append(f"Line {lineno}: Negative coupon {coupon}")
    except ValueError:
        errors.append(f"Line {lineno}: Invalid coupon {row.get('coupon')}")

    try:
        price = float(row.get("price", 0))
        if price <= 0:
            errors.append(f"Line {lineno}: Non-positive price {price}")
    except ValueError:
        errors.append(f"Line {lineno}: Invalid price {row.get('price')}")

    for field in ["ytm", "running_yield"]:
        try:
            float(row.get(field, 0))
        except ValueError:
            errors.append(f"Line {lineno}: Invalid {field} {row.get(field)}")

    return errors

def main():
    if not BOND_FILE.exists():
        print("⚠️ bonds.csv not found — skipping bond validation.")
        sys.exit(0)

    with BOND_FILE.open() as f:
        reader = csv.DictReader(f)
        all_errors = []
        for lineno, row in enumerate(reader, start=2):
            all_errors.extend(validate_bond_row(row, lineno))

    if all_errors:
        print("❌ Bond CSV validation failed:")
        for e in all_errors:
            print(" -", e)
        sys.exit(1)

    print("✅ Bond CSV validation passed.")

if __name__ == "__main__":
    main()
