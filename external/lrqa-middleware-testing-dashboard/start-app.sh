#!/bin/bash
#========================================
# RDK Middleware Testing Dashboard
# Background Startup Script with venv
#========================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration
VENV_PATH="$SCRIPT_DIR/venv"
APP_FILE="app.py"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/app-background.log"
PID_FILE="$SCRIPT_DIR/app.pid"

# SMTP Configuration
export SMTP_SERVER='smtp.gmail.com'
export SMTP_PORT='587'
export SENDER_EMAIL='cperdkemiddleware@gmail.com'
export SENDER_PASSWORD='tbbwaifvmtzovqcs'

#========================================
# Functions
#========================================

ensure_logs_dir() {
    if [ ! -d "$LOG_DIR" ]; then
        mkdir -p "$LOG_DIR"
        echo "✅ Created logs directory: $LOG_DIR"
    fi
}

check_venv() {
    if [ ! -d "$VENV_PATH" ]; then
        echo "❌ ERROR: venv not found at $VENV_PATH"
        echo "Creating venv..."
        python3 -m venv "$VENV_PATH"
        echo "✅ venv created"
    fi
}

activate_venv() {
    source "$VENV_PATH/bin/activate"
    echo "✅ venv activated"
}

install_deps() {
    if [ -f "requirements.txt" ]; then
        echo "📦 Installing dependencies..."
        pip install --upgrade pip setuptools wheel > /dev/null 2>&1
        pip install -r requirements.txt > /dev/null 2>&1
        echo "✅ Dependencies installed"
    fi
}

is_port_free() {
    ! netstat -tuln 2>/dev/null | grep -q ":11078 " && return 0 || return 1
}

wait_for_port_free() {
    local max_attempts=15
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if is_port_free; then
            return 0
        fi
        echo "⏳ Waiting for port 11078 to be free... ($attempt/$max_attempts)"
        sleep 1
        attempt=$((attempt + 1))
    done
    
    return 1
}

verify_process_dead() {
    local pid=$1
    local max_attempts=10
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if ! kill -0 "$pid" 2>/dev/null; then
            return 0  # Process is dead
        fi
        echo "  ⏳ Waiting for process $pid to terminate... ($attempt/$max_attempts)"
        sleep 1
        attempt=$((attempt + 1))
    done
    
    return 1  # Process still alive
}

force_kill_app() {
    # Kill by PID file if exists
    if [ -f "$PID_FILE" ]; then
        OLD_PID=$(cat "$PID_FILE")
        if kill -0 "$OLD_PID" 2>/dev/null; then
            echo "  🛑 Terminating process $OLD_PID (SIGTERM)..."
            kill -15 "$OLD_PID" 2>/dev/null || true
            
            # Verify it dies
            if ! verify_process_dead "$OLD_PID"; then
                echo "  💥 Process didn't die gracefully, force killing..."
                kill -9 "$OLD_PID" 2>/dev/null || true
                sleep 1
                
                # Final verification
                if ! verify_process_dead "$OLD_PID"; then
                    echo "  ⚠️  Process $OLD_PID still alive after force kill!"
                    return 1
                fi
            fi
            echo "  ✅ Process $OLD_PID terminated"
        fi
        rm -f "$PID_FILE"
    fi
    
    # Kill all stray app processes (by name pattern)
    local stray_pids=$(pgrep -f "python.*app\.py" 2>/dev/null || true)
    if [ -n "$stray_pids" ]; then
        echo "  🔍 Found stray app processes: $stray_pids"
        pkill -9 -f "python.*app\.py" 2>/dev/null || true
        sleep 1
        echo "  ✅ Stray processes killed"
    fi
    
    return 0
}

stop_app() {
    echo "🛑 Stopping app..."
    if force_kill_app; then
        echo "✅ App stopped successfully"
        return 0
    else
        echo "⚠️  App stop completed with warnings"
        return 0
    fi
}

start_app() {
    echo "🚀 Starting Flask app in background with venv..."
    
    # Make sure no old process is running
    force_kill_app
    
    # Wait for port to be free
    echo "⏳ Checking if port 11078 is free..."
    if ! wait_for_port_free; then
        echo "❌ Port 11078 is still in use. Cannot start app."
        exit 1
    fi
    echo "✅ Port 11078 is free"
    
    # Start the app
    nohup "$VENV_PATH/bin/python3" "$APP_FILE" > "$LOG_FILE" 2>&1 &
    NEW_PID=$!
    echo "$NEW_PID" > "$PID_FILE"
    
    # Wait for startup
    sleep 3
    
    # Verify the process started successfully
    if ! kill -0 "$NEW_PID" 2>/dev/null; then
        echo "❌ Failed to start app (process died immediately). Check logs:"
        tail -20 "$LOG_FILE"
        rm -f "$PID_FILE"
        exit 1
    fi
    
    # Verify port is bound
    if is_port_free; then
        echo "⚠️  Port 11078 not responding yet, waiting..."
        sleep 2
    fi
    
    if kill -0 "$NEW_PID" 2>/dev/null; then
        echo "✅ App started successfully (PID: $NEW_PID)"
        echo "📝 Log file: $LOG_FILE"
        echo "📍 PID file: $PID_FILE"
        
        # Get IP address
        IP_ADDR=$(hostname -I | awk '{print $1}')
        if [ -z "$IP_ADDR" ]; then
            IP_ADDR="127.0.0.1"
        fi
        echo "🌐 Access: http://$IP_ADDR:11078"
        return 0
    else
        echo "❌ App process died after startup"
        rm -f "$PID_FILE"
        exit 1
    fi
}

status_app() {
    echo "📊 Checking app status..."
    
    local running=0
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "✅ App is RUNNING (PID: $PID from PID file)"
            running=1
        else
            echo "❌ PID file exists but process dead: $PID"
            rm -f "$PID_FILE"
        fi
    fi
    
    # Check for stray processes
    local stray=$(pgrep -f "python.*app\.py" 2>/dev/null || true)
    if [ -n "$stray" ]; then
        echo "⚠️  Found stray app process(es): $stray"
        if [ $running -eq 0 ]; then
            running=1
        fi
    fi
    
    if [ $running -eq 1 ]; then
        if [ -f "$LOG_FILE" ]; then
            echo "📝 Recent logs:"
            tail -10 "$LOG_FILE"
        fi
        return 0
    else
        echo "❌ App is NOT RUNNING"
        return 1
    fi
}

restart_app() {
    echo "🔄 Restarting app..."
    echo ""
    
    # Stop (with force kill verification)
    stop_app
    echo ""
    
    # Wait for cleanup
    echo "⏳ Waiting for cleanup..."
    sleep 2
    
    # Start fresh
    start_app
}

tail_logs() {
    if [ -f "$LOG_FILE" ]; then
        echo "📺 Following app logs (Ctrl+C to exit)..."
        tail -f "$LOG_FILE"
    else
        echo "❌ Log file not found: $LOG_FILE"
    fi
}

#========================================
# Main
#========================================

case "${1:-start}" in
    start)
        ensure_logs_dir
        check_venv
        activate_venv
        install_deps
        start_app
        ;;
    stop)
        stop_app
        ;;
    restart)
        restart_app
        ;;
    status)
        status_app
        ;;
    logs)
        tail_logs
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "Commands:"
        echo "  start   - Start the Flask app in background with venv"
        echo "  stop    - Stop the Flask app"
        echo "  restart - Restart the Flask app"
        echo "  status  - Check if app is running"
        echo "  logs    - Follow app logs"
        exit 1
        ;;
esac
