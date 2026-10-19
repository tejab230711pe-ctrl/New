#!/bin/bash
# Auto-push script: commits and pushes changes every 5 minutes
# Run with: bash .git-autopush.sh &

REPO_DIR="/home/teja/Videos/a28796a1-f5f2-42d5-ad41-3bb346f082b6"
INTERVAL=300  # 5 minutes in seconds

echo "🚀 Auto-push started for: $REPO_DIR"
echo "   Checking every $((INTERVAL / 60)) minutes..."
echo "   To stop: kill $$ or press Ctrl+C"

while true; do
    sleep "$INTERVAL"

    cd "$REPO_DIR" || exit 1

    # Check if there are any changes (staged, unstaged, or untracked)
    if [[ -n $(git status --porcelain) ]]; then
        TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
        
        git add .
        git commit -m "Auto-sync: $TIMESTAMP"
        
        if git push; then
            echo "✅ [$TIMESTAMP] Changes pushed successfully"
        else
            echo "❌ [$TIMESTAMP] Push failed — will retry next cycle"
        fi
    fi
done
