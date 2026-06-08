#!/bin/bash
# Complete app restart with cache clearing

set -e

WORK_DIR="/home/viswa-pi4/Desktop/LRQA-DASHBOARD/lrqa-middleware-testing-dashboard"

echo "================================================"
echo "COMPLETE APP RESTART WITH CACHE CLEARING"
echo "================================================"
echo ""

cd "$WORK_DIR"

echo "1️⃣  Killing old processes..."
pkill -9 -f "python.*app.py" || echo "   (no processes found)"
sleep 2
echo "   ✅ Done"
echo ""

echo "2️⃣  Clearing Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
echo "   ✅ Done"
echo ""

echo "3️⃣  Clearing Flask template cache..."
rm -rf "$WORK_DIR/.jinja2_cache" 2>/dev/null || true
echo "   ✅ Done"
echo ""

echo "4️⃣  Starting fresh Flask app..."
source "$WORK_DIR/venv/bin/activate"
nohup python "$WORK_DIR/app.py" > "$WORK_DIR/logs/app-background.log" 2>&1 &
sleep 3
echo "   ✅ Done"
echo ""

echo "================================================"
echo "✅ APP RESTART COMPLETE"
echo "================================================"
echo ""
echo "📝 Log: logs/app-background.log"
echo "🌐 URL: http://10.0.0.32:11078"
echo ""
echo "🔧 Browser cache clear instructions:"
echo "  1. Press: Ctrl+Shift+Delete"
echo "  2. Select: All time"
echo "  3. Check: Cookies and other site data"
echo "  4. Click: Clear data"
echo "  5. Hard refresh: Ctrl+Shift+R"
