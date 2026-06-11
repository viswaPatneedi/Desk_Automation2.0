#!/bin/bash
set -e

SCRIPT_DIR="/home/viswa-pi4/Desktop/LRQA-DASHBOARD/lrqa-middleware-testing-dashboard"
cd "$SCRIPT_DIR"

echo "🛑 Killing all Python processes..."
pkill -9 -f "python.*app.py" || true
sleep 2

echo "✅ All processes killed"
echo ""
echo "🚀 Starting fresh app with venv..."

# Use nohup to start in background
cd "$SCRIPT_DIR"
source venv/bin/activate
nohup python app.py > logs/app-background.log 2>&1 &

sleep 3
echo "✅ App started successfully!"
echo "📝 Log file: logs/app-background.log"
echo "🌐 Access: http://10.0.0.32:11078"
