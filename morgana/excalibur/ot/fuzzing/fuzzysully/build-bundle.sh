#!/bin/bash
# build-bundle.sh — Build self-contained FuzzySully runtime bundle for Linux Morgana Agent.
# Run this on a Linux build machine (MorganaICSBuild WSL or CI).
# Output: fuzzysully-runtime-linux-amd64.tar.gz (verified asset)
#
# Usage:
#   bash build-bundle.sh [SOURCE_COMMIT]
#
set -euo pipefail

SOURCE_COMMIT="${1:-50a0631178331d2cc39b6ed554b9b68050580f92}"
SOURCE_URL="https://github.com/ANSSI-FR/fuzzysully"
BUNDLE_NAME="fuzzysully-runtime-linux-amd64"
WORK_DIR="$(mktemp -d)"
OUT_DIR="${2:-$(pwd)}"

echo "[INFO] Building FuzzySully runtime bundle"
echo "[INFO] Commit: $SOURCE_COMMIT"
echo "[INFO] Work dir: $WORK_DIR"

# 1. Clone pinned source
git clone "$SOURCE_URL" "$WORK_DIR/fuzzysully-src"
cd "$WORK_DIR/fuzzysully-src"
git checkout "$SOURCE_COMMIT"
ACTUAL_COMMIT="$(git rev-parse HEAD)"
echo "[INFO] Actual commit: $ACTUAL_COMMIT"

# 2. Create isolated venv
python3 -m venv "$WORK_DIR/$BUNDLE_NAME"
"$WORK_DIR/$BUNDLE_NAME/bin/pip" install --upgrade pip --quiet

# 3. Install fuzzysully + all deps from lock
"$WORK_DIR/$BUNDLE_NAME/bin/pip" install . --quiet

# 4. Copy runner into bundle
cp "$(dirname "$0")/morgana_fuzzysully_runner.py" "$WORK_DIR/$BUNDLE_NAME/"
cp "$(dirname "$0")/requirements-lock.txt" "$WORK_DIR/$BUNDLE_NAME/"

# 5. Record metadata
python3 -c "
import json, datetime, subprocess, hashlib, os, sys
commit = '$ACTUAL_COMMIT'
print(json.dumps({'source_commit': commit, 'python': sys.version, 'built_at': datetime.datetime.utcnow().isoformat()}))
" > "$WORK_DIR/$BUNDLE_NAME/bundle-meta.json"

# 6. Verify import
"$WORK_DIR/$BUNDLE_NAME/bin/python" -c "
from fuzzysully import FuzzySully, OPCUAMode
funcs = FuzzySully.list_available_functions(OPCUAMode.SERVER)
print(f'[OK] FuzzySully imported; {len(funcs)} server functions available')
"

# 7. Archive
cd "$WORK_DIR"
tar czf "$OUT_DIR/$BUNDLE_NAME.tar.gz" "$BUNDLE_NAME/"
SHA256=$(sha256sum "$OUT_DIR/$BUNDLE_NAME.tar.gz" | awk '{print $1}')
echo "$SHA256  $BUNDLE_NAME.tar.gz" > "$OUT_DIR/$BUNDLE_NAME.tar.gz.sha256"

echo "[SUCCESS] Bundle: $OUT_DIR/$BUNDLE_NAME.tar.gz"
echo "[SUCCESS] SHA256: $SHA256"
echo "[SUCCESS] Install on agent: tar xzf $BUNDLE_NAME.tar.gz && source $BUNDLE_NAME/bin/activate"
