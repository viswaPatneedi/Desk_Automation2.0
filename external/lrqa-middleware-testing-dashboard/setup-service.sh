#!/bin/bash
# Setup script to enable Flask app as a systemd service for persistent background execution

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SERVICE_FILE="$SCRIPT_DIR/flask-app.service"
LOGS_DIR="$SCRIPT_DIR/logs"

echo "========================================================"
echo "Flask App - Systemd Service Setup"
echo "========================================================"

# Create logs directory
echo "[1/5] Creating logs directory..."
mkdir -p "$LOGS_DIR"
echo "✓ Logs directory: $LOGS_DIR"

# Stop any existing Flask processes
echo "[2/5] Stopping existing Flask processes..."
pkill -9 -f "python.*app.py" 2>/dev/null || echo "  (No existing processes)"
sleep 1

# Copy service file to systemd directory
echo "[3/5] Installing systemd service file..."
sudo cp "$SERVICE_FILE" /etc/systemd/system/flask-app.service
echo "✓ Service file installed to /etc/systemd/system/flask-app.service"

# Reload systemd daemon
echo "[4/5] Reloading systemd configuration..."
sudo systemctl daemon-reload
echo "✓ Systemd daemon reloaded"

# Enable and start the service
echo "[5/5] Enabling and starting the service..."
sudo systemctl enable flask-app.service
sudo systemctl start flask-app.service
echo "✓ Service enabled and started"

echo ""
echo "========================================================"
echo "✅ Setup Complete!"
echo "========================================================"
echo ""
echo "Service Control Commands:"
echo "  Start:    sudo systemctl start flask-app.service"
echo "  Stop:     sudo systemctl stop flask-app.service"
echo "  Restart:  sudo systemctl restart flask-app.service"
echo "  Status:   sudo systemctl status flask-app.service"
echo "  Logs:     sudo journalctl -u flask-app.service -n 100 -f"
echo ""
echo "Your Flask app will now:"
echo "  ✓ Start automatically on system boot"
echo "  ✓ Keep running even when VS Code is closed"
echo "  ✓ Auto-restart if the process crashes"
echo "  ✓ Be managed by systemd for reliability"
echo ""
