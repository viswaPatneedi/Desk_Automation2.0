#!/bin/bash
# Cleanup redundant startup scripts
# Keep only: start-app.sh, start-rdk-app.sh, start_cloud_mode.sh

cd /home/viswa-pi4/Desktop/LRQA-DASHBOARD/lrqa-middleware-testing-dashboard

echo "🗑️  Cleaning up redundant startup scripts..."

# List of files to delete
files_to_delete=(
    "start_venv_with_email.sh"
    "start_with_email.sh"
    "start_bg.sh"
    "start_app_with_email.sh"
    "start_background.sh"
    "start_with_gmail.sh"
    "run_app.sh"
)

# Delete each file
for file in "${files_to_delete[@]}"; do
    if [ -f "$file" ]; then
        rm -f "$file"
        echo "  ❌ Deleted: $file"
    fi
done

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "📋 Remaining startup scripts:"
ls -1 start*.sh start_*.sh run_*.sh 2>/dev/null || echo "None"
echo ""
echo "🎯 Keep using:"
echo "  • ./start-app.sh          (Primary - local/production)"
echo "  • ./start-rdk-app.sh      (Docker - container deployment)"
echo "  • ./start_cloud_mode.sh   (Cloud - tunnel mode)"
