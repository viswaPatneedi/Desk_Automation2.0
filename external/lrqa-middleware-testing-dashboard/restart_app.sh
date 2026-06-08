#!/bin/bash
# Quick restart with cache clearing

WORK_DIR="/home/viswa-pi4/Desktop/LRQA-DASHBOARD/lrqa-middleware-testing-dashboard"

echo "🛑 Stopping old processes..."
pkill -9 -f "python.*app.py" 2>/dev/null || true
sleep 2

echo "🧹 Clearing cache..."
cd "$WORK_DIR"
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

echo "🚀 Starting app..."
cd "$WORK_DIR"
source venv/bin/activate
nohup python app.py > logs/app-background.log 2>&1 &

sleep 3

echo ""
echo "✅ App started successfully!"
echo "📝 Log file: logs/app-background.log"
echo "🌐 URL: http://10.0.0.32:11078"
echo ""
echo "Latest log lines:"
tail -10 logs/app-background.log
