#!/bin/bash
# ============================================================================
# Docker Entrypoint Script for RDK-E Middleware QA Dashboard
# ============================================================================
# Handles:
# - Environment initialization
# - Configuration validation
# - Database/file structure setup
# - Service startup
# ============================================================================

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║       RDK-E Middleware QA Dashboard - Docker Startup Script                 ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"

# ============================================================================
# COLORS FOR OUTPUT
# ============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# LOGGING FUNCTIONS
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# ============================================================================
# STARTUP PHASE: Environment Validation
# ============================================================================

log_info "Starting application initialization..."

# Check Python executable
if ! command -v python &> /dev/null; then
    log_error "Python not found in PATH"
    exit 1
fi

log_success "Python available: $(python --version)"

# ============================================================================
# STARTUP PHASE: Configuration Files
# ============================================================================

log_info "Validating configuration files..."

REQUIRED_CONFIGS=(
    "config_commands.py"
    "config_ir_blaster.py"
    "config_log_patterns.py"
    "config_timing.py"
    "config_screenshot.py"
    "log_patterns.json"
)

for config in "${REQUIRED_CONFIGS[@]}"; do
    if [ -f "/app/$config" ]; then
        log_success "Found: $config"
    else
        log_error "Missing: $config"
        exit 1
    fi
done

# ============================================================================
# STARTUP PHASE: Environment Setup
# ============================================================================

log_info "Setting up environment..."

# Create application state directories
mkdir -p /app/data/{screenshots,iteration_logs,execution_logs,device_logs,app_logs,sessions,uploads}
mkdir -p /app/reference_screens

log_success "Data directories created"

# Initialize empty JSON files if they don't exist
if [ ! -f "/app/devices.json" ]; then
    echo "[]" > /app/devices.json
    log_success "Created empty devices.json"
fi

if [ ! -f "/app/device_locks.json" ]; then
    echo "{}" > /app/device_locks.json
    log_success "Created empty device_locks.json"
fi

if [ ! -f "/app/jobs.json" ]; then
    echo "[]" > /app/jobs.json
    log_success "Created empty jobs.json"
fi

if [ ! -f "/app/saved_sequences.json" ]; then
    echo "{}" > /app/saved_sequences.json
    log_success "Created empty saved_sequences.json"
fi

# ============================================================================
# STARTUP PHASE: Environment Variables
# ============================================================================

log_info "Configuring environment variables..."

# Flask Configuration
export FLASK_APP=${FLASK_APP:-app.py}
export FLASK_ENV=${FLASK_ENV:-production}
export FLASK_DEBUG=${FLASK_DEBUG:-0}

# Application Configuration
export APP_HOST=${APP_HOST:-0.0.0.0}
export APP_PORT=${APP_PORT:-11078}
export LOG_LEVEL=${LOG_LEVEL:-INFO}

# Email Configuration (defaults to disabled)
export SMTP_HOST=${SMTP_HOST:-smtp.gmail.com}
export SMTP_PORT=${SMTP_PORT:-587}
export SMTP_USER=${SMTP_USER:-}
export SMTP_PASSWORD=${SMTP_PASSWORD:-}
export SMTP_FROM_EMAIL=${SMTP_FROM_EMAIL:-}

# SSH Configuration
export SSH_PORT=${SSH_PORT:-10022}
export SSH_USERNAME=${SSH_USERNAME:-root}
export SSH_TIMEOUT=${SSH_TIMEOUT:-30}

# Database/Storage
export DATA_PATH=${DATA_PATH:-/app/data}
export LOG_PATH=${DATA_PATH}/app_logs

# Security
export SECRET_KEY=${SECRET_KEY:-rdke-qa-dashboard-secret-key-change-in-production}
export SESSION_TIMEOUT=${SESSION_TIMEOUT:-86400}

log_success "Environment configured"

# ============================================================================
# STARTUP PHASE: Display Configuration Info
# ============================================================================

log_info "Application Configuration:"
echo "  Flask App: $FLASK_APP"
echo "  Environment: $FLASK_ENV"
echo "  Host: $APP_HOST"
echo "  Port: $APP_PORT"
echo "  Data Path: $DATA_PATH"
echo "  SSH Configuration: user=$SSH_USERNAME, port=$SSH_PORT, timeout=${SSH_TIMEOUT}s"

if [ -n "$SMTP_USER" ]; then
    echo "  Email Service: ENABLED (${SMTP_USER}@${SMTP_HOST}:${SMTP_PORT})"
else
    echo "  Email Service: DISABLED (set SMTP_USER to enable)"
fi

# ============================================================================
# STARTUP PHASE: Log Initialization
# ============================================================================

log_info "Initializing logging..."

mkdir -p $LOG_PATH
LOG_FILE="$LOG_PATH/startup-$(date +%Y%m%d-%H%M%S).log"

log_success "Log file: $LOG_FILE"

# ============================================================================
# STARTUP PHASE: Application startup
# ============================================================================

log_info "Starting Flask application..."
log_info "Command: $@"
echo ""
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                    APPLICATION STARTUP IN PROGRESS                         ║"
echo "║  Access the dashboard at: http://$(hostname -I | awk '{print $1}'):11078   ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Execute the command passed to the container
exec "$@"
