#!/bin/bash
# Auto Deploy Script - DISABLED
# Auto-deploy has been disabled to prevent overwriting local development changes.
# This script now exits without running git fetch/pull.

set -e  # Exit on error

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Auto-deploy is DISABLED to preserve local changes."
exit 0

# Configuration
REPO_DIR="/home/pi/Desktop/viswa/Latest_Enhancement/Enhancement"
VENV_DIR="$REPO_DIR/venv"
LOG_FILE="$REPO_DIR/auto_deploy.log"
SERVICE_NAME="device-testing.service"  # Change if your service name is different

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Change to repository directory
cd "$REPO_DIR"

log_message "=========================================="
log_message "Starting auto-deploy check..."

# Fetch latest changes from GitHub
log_message "Fetching latest changes from GitHub..."
git fetch origin main 2>&1 | tee -a "$LOG_FILE"

# Check if there are new commits
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
    log_message "✅ Already up to date. No changes detected."
    exit 0
fi

log_message "🔄 New changes detected! Starting deployment..."
log_message "  Local:  $LOCAL"
log_message "  Remote: $REMOTE"

# Stash any local changes (like logs, JSON files)
log_message "Stashing local changes..."
git stash push -m "Auto-stash before deploy $(date '+%Y-%m-%d %H:%M:%S')" 2>&1 | tee -a "$LOG_FILE"

# Pull the latest changes
log_message "Pulling changes from GitHub..."
git pull origin main 2>&1 | tee -a "$LOG_FILE"

# Reapply stashed changes if any (optional - preserves local data files)
if git stash list | grep -q "Auto-stash"; then
    log_message "Reapplying stashed changes..."
    git stash pop 2>&1 | tee -a "$LOG_FILE" || log_message "⚠️  Warning: Could not reapply stash (may have conflicts)"
fi

# Activate virtual environment and update dependencies
if [ -d "$VENV_DIR" ]; then
    log_message "Activating virtual environment..."
    source "$VENV_DIR/bin/activate"
    
    log_message "Updating Python dependencies..."
    pip install -r requirements.txt --quiet 2>&1 | tee -a "$LOG_FILE"
else
    log_message "⚠️  Warning: Virtual environment not found at $VENV_DIR"
fi

# Make scripts executable
log_message "Setting permissions on scripts..."
chmod +x *.sh 2>/dev/null || true

# Restart the application service
log_message "Restarting application service: $SERVICE_NAME"
if systemctl is-active --quiet "$SERVICE_NAME"; then
    sudo systemctl restart "$SERVICE_NAME" 2>&1 | tee -a "$LOG_FILE"
    log_message "✅ Service restarted successfully"
else
    log_message "⚠️  Service $SERVICE_NAME is not running. Starting it..."
    sudo systemctl start "$SERVICE_NAME" 2>&1 | tee -a "$LOG_FILE"
fi

# Wait a moment and check service status
sleep 3
if systemctl is-active --quiet "$SERVICE_NAME"; then
    log_message "✅ Deployment completed successfully!"
    log_message "Service status: RUNNING"
else
    log_message "❌ Warning: Service may not have started correctly"
    sudo systemctl status "$SERVICE_NAME" --no-pager | tee -a "$LOG_FILE"
fi

log_message "=========================================="
