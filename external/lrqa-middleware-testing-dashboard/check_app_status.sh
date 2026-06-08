#!/bin/bash
# Check if application is running with email service enabled

echo "============================================"
echo "APPLICATION & EMAIL SERVICE STATUS CHECK"
echo "============================================"
echo ""

# Check if app is running
APP_PID=$(pgrep -f "python.*app.py" | head -1)
if [ -z "$APP_PID" ]; then
    echo "❌ Application: NOT RUNNING"
    echo ""
    echo "To start with email enabled:"
    echo "  ./start_with_email.sh"
    exit 1
else
    echo "✅ Application: RUNNING (PID: $APP_PID)"
    echo "   Port: 8080"
    echo "   URL: http://10.0.0.32:8080"
fi

echo ""

# Check email service status from logs
if [ -f "app.log" ]; then
    if grep -q "✅ Email Service: ENABLED" app.log 2>/dev/null; then
        echo "✅ Email Service: ENABLED"
        SMTP_SERVER=$(grep "SMTP Server:" app.log | tail -1 | awk '{print $3}')
        SENDER_EMAIL=$(grep "Sender Email:" app.log | tail -1 | awk '{print $3}')
        echo "   SMTP: $SMTP_SERVER"
        echo "   Sender: $SENDER_EMAIL"
        echo "   → Emails will be sent after test executions"
    elif grep -q "⚠️  Email Service: DISABLED" app.log 2>/dev/null; then
        echo "⚠️  Email Service: DISABLED"
        echo "   → Start with: ./start_with_email.sh"
    else
        echo "⚠️  Email Service: STATUS UNKNOWN"
    fi
else
    echo "⚠️  Cannot check email status - app.log not found"
fi

echo ""
echo "============================================"
