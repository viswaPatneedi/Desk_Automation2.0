#!/bin/bash

################################################################################
# Universal App Restart Script - Works from any cloned location
# This script restarts the Flask application in a venv in the background
#
# Usage: ./restart.sh [options]
# Options:
#   --force      Force restart without confirmation
#   --no-cache   Don't clear cache
#   --logs       Show logs after restart
#   --help       Show this help message
#
# Author: Team
# Version: 1.0
################################################################################

set -e

# Get the directory where this script is located (works anywhere)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR"
VENV_DIR="$APP_DIR/venv"
VENV_PYTHON="$VENV_DIR/bin/python"
PID_FILE="$APP_DIR/app.pid"
LOG_FILE="$APP_DIR/app.log"
NOHUP_LOG="$APP_DIR/logs/app-background.log"
PORT=11079

# PostgreSQL health-check / auto-heal settings
DB_HOST="localhost"
DB_PORT=5432
DB_HEALTH_LOG="$APP_DIR/logs/db-health.log"
DB_WATCHDOG_PID_FILE="$APP_DIR/logs/db_watchdog.pid"
DB_WATCHDOG_LOG="$APP_DIR/logs/db_watchdog.log"
DB_WATCHDOG_INTERVAL=60

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default options
FORCE_RESTART=false
CLEAR_CACHE=true
SHOW_LOGS=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE_RESTART=true
            shift
            ;;
        --no-cache)
            CLEAR_CACHE=false
            shift
            ;;
        --logs)
            SHOW_LOGS=true
            shift
            ;;
        --help)
            grep "^# " "$0" | head -20
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Helper functions
print_header() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_step() {
    echo -e "${YELLOW}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Returns 0 if Postgres is accepting TCP connections, 1 otherwise.
check_db_connection() {
    (exec 3<>"/dev/tcp/$DB_HOST/$DB_PORT") 2>/dev/null
    local result=$?
    exec 3<&- 2>/dev/null || true
    exec 3>&- 2>/dev/null || true
    return $result
}

# Tries to (re)start Postgres via non-interactive sudo. Logs outcome either way.
# Requires a NOPASSWD sudoers rule for 'service postgresql restart' to succeed unattended
# (see README/print_info hint below if it's not configured).
heal_db_connection() {
    echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] Postgres unreachable on $DB_HOST:$DB_PORT - attempting restart" >> "$DB_HEALTH_LOG"
    if sudo -n service postgresql restart >> "$DB_HEALTH_LOG" 2>&1; then
        sleep 3
        if check_db_connection; then
            echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] Postgres restart succeeded" >> "$DB_HEALTH_LOG"
            return 0
        fi
        echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] Postgres restart command ran but port still unreachable" >> "$DB_HEALTH_LOG"
        return 1
    else
        echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] Postgres restart failed - passwordless sudo not configured. Run: sudo service postgresql restart" >> "$DB_HEALTH_LOG"
        return 1
    fi
}

# Background loop: rechecks DB connectivity every DB_WATCHDOG_INTERVAL seconds
# and self-heals if it drops. Runs detached from the terminal via nohup.
start_db_watchdog() {
    if [ -f "$DB_WATCHDOG_PID_FILE" ] && kill -0 "$(cat "$DB_WATCHDOG_PID_FILE" 2>/dev/null)" 2>/dev/null; then
        print_info "DB watchdog already running (PID $(cat "$DB_WATCHDOG_PID_FILE"))"
        return 0
    fi

    nohup bash -c "
        while true; do
            sleep $DB_WATCHDOG_INTERVAL
            (exec 3<>/dev/tcp/$DB_HOST/$DB_PORT) 2>/dev/null
            if [ \$? -ne 0 ]; then
                echo \"[\$(date -u '+%Y-%m-%d %H:%M:%S UTC')] Postgres unreachable - attempting restart\" >> '$DB_WATCHDOG_LOG'
                if sudo -n service postgresql restart >> '$DB_WATCHDOG_LOG' 2>&1; then
                    echo \"[\$(date -u '+%Y-%m-%d %H:%M:%S UTC')] Postgres restart succeeded\" >> '$DB_WATCHDOG_LOG'
                else
                    echo \"[\$(date -u '+%Y-%m-%d %H:%M:%S UTC')] Postgres restart failed - passwordless sudo not configured\" >> '$DB_WATCHDOG_LOG'
                fi
            fi
            exec 3<&- 2>/dev/null || true
            exec 3>&- 2>/dev/null || true
        done
    " > /dev/null 2>&1 &
    echo $! > "$DB_WATCHDOG_PID_FILE"
    print_success "DB watchdog started (PID $!, checks every ${DB_WATCHDOG_INTERVAL}s)"
}

# Main restart logic
main() {
    print_header "FLASK APP RESTART SCRIPT"

    # Verify we're in the right directory
    if [ ! -f "$APP_DIR/app.py" ]; then
        print_error "app.py not found in $APP_DIR"
        print_info "Make sure you run this script from the application root directory"
        exit 1
    fi
    print_success "Found app.py in: $APP_DIR"

    # Check if venv exists
    if [ ! -d "$VENV_DIR" ]; then
        print_error "Virtual environment not found at: $VENV_DIR"
        print_info "Please create it with: python3 -m venv venv"
        print_info "Then install dependencies: ./venv/bin/pip install -r requirements.txt"
        exit 1
    fi
    print_success "Virtual environment found"

    # Confirmation (unless --force flag is used)
    if [ "$FORCE_RESTART" = false ]; then
        echo ""
        echo "This will:"
        echo "  1. Kill any existing app processes"
        if [ "$CLEAR_CACHE" = true ]; then
            echo "  2. Clear Python cache (__pycache__, .pyc files)"
            echo "  3. Clear Flask template cache"
        fi
        echo "  4. Start app in background"
        echo "  5. Save PID and logs"
        echo ""
        read -p "Continue? (y/n) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Cancelled."
            exit 0
        fi
    fi

    # Step 1: Kill existing processes
    print_step "Killing existing app processes..."
    pkill -f "python.*app.py" 2>/dev/null || true
    # Also kill by venv python path
    pkill -f "$VENV_PYTHON" 2>/dev/null || true
    # Remove old PID file
    rm -f "$PID_FILE" 2>/dev/null || true
    # Stop any stale DB watchdog so we don't end up with duplicates
    if [ -f "$DB_WATCHDOG_PID_FILE" ]; then
        kill "$(cat "$DB_WATCHDOG_PID_FILE" 2>/dev/null)" 2>/dev/null || true
        rm -f "$DB_WATCHDOG_PID_FILE"
    fi
    sleep 2
    print_success "Old processes killed"

    # Step 2: Clear cache if requested
    if [ "$CLEAR_CACHE" = true ]; then
        print_step "Clearing Python cache..."
        find "$APP_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find "$APP_DIR" -name "*.pyc" -delete 2>/dev/null || true
        print_success "Python cache cleared"

        print_step "Clearing Flask template cache..."
        rm -rf "$APP_DIR/.jinja2_cache" 2>/dev/null || true
        print_success "Flask cache cleared"
    fi

    # Step 3: Create logs directory if it doesn't exist
    print_step "Setting up log directory..."
    mkdir -p "$APP_DIR/logs" 2>/dev/null || true
    print_success "Log directory ready"

    # Step 4: Start the app
    print_step "Starting Flask app in background..."
    cd "$APP_DIR"

    # Check if venv activation script exists
    if [ ! -f "$VENV_DIR/bin/activate" ]; then
        print_error "Virtual environment activation script not found"
        exit 1
    fi

    # Start app using source and nohup
    nohup bash -c "source '$VENV_DIR/bin/activate' && python app.py" > "$NOHUP_LOG" 2>&1 &
    APP_PID=$!
    echo $APP_PID > "$PID_FILE"

    sleep 3

    # Verify app started
    if kill -0 "$APP_PID" 2>/dev/null; then
        print_success "App started successfully"
        print_info "Process ID: $APP_PID"
    else
        print_error "App failed to start. Check logs:"
        tail -20 "$NOHUP_LOG"
        exit 1
    fi

    # Step 4.5: Verify PostgreSQL is reachable and self-heal if it dropped,
    # then leave a background watchdog running so it recovers automatically later.
    print_step "Checking PostgreSQL connectivity..."
    if check_db_connection; then
        print_success "PostgreSQL is reachable on $DB_HOST:$DB_PORT"
    else
        print_error "PostgreSQL is unreachable on $DB_HOST:$DB_PORT - attempting auto-restart..."
        if heal_db_connection; then
            print_success "PostgreSQL restarted and is now reachable"
        else
            print_error "Could not auto-restart PostgreSQL (see $DB_HEALTH_LOG)"
            print_info "Passwordless sudo not set up - run manually: sudo service postgresql restart"
            print_info "To enable auto-heal, add via 'sudo visudo': $(whoami) ALL=(root) NOPASSWD: /usr/sbin/service postgresql restart, /usr/sbin/service postgresql start, /usr/sbin/service postgresql status"
        fi
    fi
    start_db_watchdog

    # Step 5: Display information
    print_header "RESTART COMPLETE"
    echo ""
    print_info "App Status:"
    echo "  PID: $APP_PID"
    echo "  Port: $PORT"
    echo "  Directory: $APP_DIR"
    echo ""

    # Get host IP
    HOST_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
    if [ -z "$HOST_IP" ]; then
        HOST_IP="127.0.0.1"
    fi

    print_info "Access the app:"
    echo "  http://localhost:$PORT"
    echo "  http://$HOST_IP:$PORT"
    echo ""

    print_info "Log files:"
    echo "  Background: $NOHUP_LOG"
    echo "  Main log: $LOG_FILE"
    echo ""

    print_info "Useful commands:"
    echo "  Check status: ps aux | grep app.py"
    echo "  View logs: tail -f $NOHUP_LOG"
    echo "  Kill app: pkill -f app.py"
    echo "  DB watchdog log: tail -f $DB_WATCHDOG_LOG"
    echo "  Stop DB watchdog: kill \$(cat $DB_WATCHDOG_PID_FILE)"
    echo ""

    # Show logs if requested
    if [ "$SHOW_LOGS" = true ]; then
        echo ""
        print_header "RECENT LOG OUTPUT"
        sleep 2
        if [ -f "$NOHUP_LOG" ]; then
            tail -20 "$NOHUP_LOG"
        else
            print_info "Log file not yet created"
        fi
    fi

    echo ""
}

# Run main function
main
