#!/usr/bin/env bash
set -euo pipefail
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p exports
tar --exclude='.git' --exclude='.venv' --exclude='.env' --exclude='backups' --exclude='exports' -czf "exports/wow-gm-webpanel-${STAMP}.tar.gz" .
echo "exports/wow-gm-webpanel-${STAMP}.tar.gz"
