#!/bin/bash
set -euo pipefail

FREEZE_ID=$1
FREEZE_DIR="freeze_${FREEZE_ID}"
ZIP_FILE="${FREEZE_DIR}.zip"
BUCKET="daily-report-freezes-michael"
KEY="daily-report/${ZIP_FILE}"
PROFILE="prod-admin"

echo ">>> Creating ${FREEZE_DIR} ..."
mkdir -p "${FREEZE_DIR}"

echo ">>> Copying files (excluding old freezes) ..."
rsync -a --exclude 'freeze_*' --exclude '.env' ./ "${FREEZE_DIR}/"

echo ">>> Zipping to ${ZIP_FILE} ..."
zip -r "${ZIP_FILE}" "${FREEZE_DIR}" >/dev/null

echo ">>> Calculating SHA-256 ..."
shasum -a 256 "${ZIP_FILE}"

echo ">>> Uploading to S3 with profile ${PROFILE} ..."
aws s3 cp "${ZIP_FILE}" "s3://${BUCKET}/${KEY}" --profile "${PROFILE}"

echo ">>> Verifying upload ..."
aws s3api head-object \
  --bucket "${BUCKET}" \
  --key "${KEY}" \
  --profile "${PROFILE}" \
  --query '{Size:ContentLength, ETag:ETag, LastModified:LastModified}'

echo ">>> Done. Freeze ${FREEZE_ID} available at s3://${BUCKET}/${KEY}"
