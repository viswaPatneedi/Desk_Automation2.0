#!/bin/bash
# Flask App Watchdog - Auto-restart on crash
# Run this in background: nohup ./watchdog.sh > watchdog.log 2>&1 &

APP_DIR="/home/viswa-pi4/Desktop/LRQA-DASHBOARD/lrqa-middleware-testing-dashboard"
VENV_PATH="$APP_DIR/venv"
LOG_FILE="$APP_DIR/app.log"
WATCHDOG_LOG="$APP_DIR/watchdog.log"
PORT=11078
CHECK_INTERVAL=10

cd "$APP_DIR"

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$WATCHDOG_LOG"
}

is_app_running() {
    curl -s -m 3 http://localhost:$PORT > /dev/null 2>&1
    return $?
}

start_app() {
    log_message "🚀 Starting Flask application..."
    source "$VENV_PATH/bin/activate"
    nohup python app.py > "$LOG_FILE" 2>&1 &
    APP_PID=$!
    log_message "✅ App started with PID: $APP_PID"
    sleep 5
}

log_message "=================================================="
log_message "🔍 Flask Watchdog Started (Check interval: ${CHECK_INTERVAL}s)"
log_message "=================================================="

# Start app initially if not running
if ! is_app_running; then
    start_app
else
    log_message "✅ App already running on port $PORT"
fi

# Monitor loop
while true; do
    sleep $CHECK_INTERVAL
    
    if ! is_app_running; then
        log_message "❌ App crashed! Restarting..."
        pkill -f "python app.py" 2>/dev/null || true
        sleep 2
        start_app
    else
        log_message "✓ App healthy"
    fi
done
