#!/usr/bin/env bash
set -euo pipefail

# Directory where freeze archives are stored
FREEZE_DIR="/opt/daily-report-freeze"

# Ensure target dir exists
mkdir -p "${FREEZE_DIR}"

# Timestamp for this freeze
TS="$(date +"%Y%m%d-%H%M%S")"

# Output tarball path
FREEZE_TARBALL="${FREEZE_DIR}/daily-report-freeze_${TS}.tgz"

echo "Creating freeze archive at: ${FREEZE_TARBALL}"

# We want the tarball to contain a top-level 'daily-report/' directory,
# so we tar from /opt and include the daily-report folder by name.
cd /opt

tar -czf "${FREEZE_TARBALL}" daily-report

echo "Freeze complete."
echo "File: ${FREEZE_TARBALL}"

