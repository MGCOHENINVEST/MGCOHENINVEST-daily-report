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

echo ">>> Uploading to S3 ..."
aws s3 cp "$ZIP" s3://daily-report-freezes-michael/daily-report/

echo ">>> Freeze $NUM completed and uploaded as $ZIP"
