#!/bin/bash
cd /root/.openclaw/workspace || exit 1
git config user.name "OpenClaw Backup Bot"
git config user.email "backup@openclaw.ai"
git add .
git commit -m "Daily backup: $(date +%Y-%m-%d)" || echo "No changes to commit"
git push origin main || exit 1
