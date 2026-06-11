#!/bin/bash
# Test script to verify app.py syntax and start app

cd /home/viswa-pi4/Desktop/LRQA-DASHBOARD/lrqa-middleware-testing-dashboard

echo "🔍 Checking Python syntax..."
python3 -m py_compile app.py
if [ $? -eq 0 ]; then
    echo "✅ app.py syntax is valid"
else
    echo "❌ app.py has syntax errors"
    exit 1
fi

echo "🛑 Stopping any running Flask instances..."
pkill -f "python.*app.py" 2>/dev/null

echo "⏳ Waiting for processes to stop..."
sleep 2

echo "🚀 Starting Flask app using startup script..."
./start_venv_with_email.sh

echo "⏳ Waiting for app to start..."
sleep 3

echo "🔍 Checking if app is running..."
if ps aux | grep -q "[p]ython.*app.py"; then
    echo "✅ Flask app started successfully"
    echo "📋 Logs location: /tmp/flask_prod.log"
    echo "📊 Recent logs:"
    tail -20 /tmp/flask_prod.log
else
    echo "❌ Flask app failed to start"
    echo "❌ Error logs:"
    tail -30 /tmp/flask_prod.log
fi
