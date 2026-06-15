#!/bin/bash
# Hermes Enhanced Pack - Sanitize personal information
set -e
PACK_DIR="/mnt/m/hermes-enhanced-pack"

echo "=== Sanitizing personal information ==="

# 1. Replace personal names (Chinese)
find "$PACK_DIR" -type f \( -name '*.py' -o -name '*.md' -o -name '*.yaml' -o -name '*.sh' -o -name '*.json' -o -name '*.txt' -o -name '*.service' \) -print0 | xargs -0 sed -i \
    -e 's/USER/USER/g' \
    -e 's/USER/USER/g'
echo "[1/6] Personal names replaced"

# 2. Replace API keys with placeholders
find "$PACK_DIR" -type f \( -name '*.py' -o -name '*.yaml' -o -name '*.json' \) -print0 | xargs -0 sed -i \
    -e 's/sk-[a-zA-Z0-9]\{32,\}/YOUR_API_KEY_HERE/g' \
    -e 's/api_key: .*/api_key: YOUR_API_KEY_HERE/g'
echo "[2/6] API keys sanitized"

# 3. Replace hardcoded paths
find "$PACK_DIR" -type f \( -name '*.py' -o -name '*.yaml' -o -name '*.sh' -o -name '*.service' -o -name '*.txt' -o -name '*.md' \) -print0 | xargs -0 sed -i \
    -e 's|~|~|g' \
    -e 's|/path/to/hermes-backup|/path/to/hermes-backup|g'
echo "[3/6] Paths generalized"

# 4. Remove sensitive DB files
find "$PACK_DIR" \( -name '*.db' -o -name '*.sqlite' -o -name '*.db-shm' -o -name '*.db-wal' \) -print -delete 2>/dev/null
echo "[4/6] Sensitive DB files removed"

# 5. Remove __pycache__ and .pyc
find "$PACK_DIR" -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null
find "$PACK_DIR" -name '*.pyc' -delete 2>/dev/null
echo "[5/6] Cache files cleaned"

# 6. Clean config.yaml sensitive fields
if [ -f "$PACK_DIR/config/config.yaml" ]; then
    sed -i 's/api_key: .*/api_key: YOUR_API_KEY_HERE/g' "$PACK_DIR/config/config.yaml"
    sed -i 's/token: .*/token: YOUR_TOKEN_HERE/g' "$PACK_DIR/config/config.yaml"
    sed -i '/pushplus:/,/token:/s/token: .*/token: YOUR_TOKEN_HERE/' "$PACK_DIR/config/config.yaml"
fi
echo "[6/6] Config sanitized"

echo ""
echo "=== Sanitization complete ==="
echo "Total files in package:"
find "$PACK_DIR" -type f | wc -l
