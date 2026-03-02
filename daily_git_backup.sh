#!/bin/bash
# Daily git backup script

cd /root/.openclaw/workspace || exit 1

# Configure git if not already done
git config user.email "mybro999@openclaw.ai" 2>/dev/null
git config user.name "mybro999" 2>/dev/null

# Check if there are changes
if git diff --quiet && git diff --staged --quiet; then
    echo "No changes to commit"
    exit 0
fi

# Add all files
git add -A

# Commit with timestamp
git commit -m "Daily backup: $(date '+%Y-%m-%d %H:%M:%S')"

# Push to origin
git push origin main 2>/dev/null || git push origin master 2>/dev/null || echo "Push failed - check credentials"

echo "Backup completed at $(date)"
