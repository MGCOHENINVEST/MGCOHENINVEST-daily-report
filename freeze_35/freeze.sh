#!/bin/bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <freeze_number>"
  exit 1
fi

NUM=$1
DIR="freeze_$NUM"
ZIP="$DIR.zip"

echo ">>> Creating $DIR ..."
mkdir -p "$DIR"

echo ">>> Copying files (excluding old freezes) ..."
rsync -av --exclude 'freeze_*' ./ "$DIR/"

echo ">>> Zipping to $ZIP ..."
zip -r "$ZIP" "$DIR" >/dev/null

echo ">>> Calculating SHA-256 ..."
SHA256=$(sha256sum "$ZIP" | awk '{print $1}')
echo "SHA-256: $SHA256"

echo ">>> Uploading to S3 ..."
if aws s3 cp "$ZIP" s3://daily-report-freezes-michael/daily-report/; then
  echo ">>> Freeze $NUM completed and uploaded as $ZIP"
  echo ">>> SHA-256: $SHA256"
else
  echo "S3 upload failed. Zip is at: $(pwd)/$ZIP"
  exit 1
fi
