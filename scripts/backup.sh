#!/usr/bin/env bash
set -euo pipefail
STAMP="$(date +%Y%m%d-%H%M%S)"
DEST="${1:-backups/webpanel-${STAMP}}"
mkdir -p "$DEST"
cp -a .env "$DEST/.env" 2>/dev/null || true
cp -a instance "$DEST/" 2>/dev/null || true
cp -a app "$DEST/app"
echo "Backup erstellt: $DEST"
