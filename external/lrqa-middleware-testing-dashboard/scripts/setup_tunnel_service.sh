#!/bin/bash
#
# Setup Systemd Service for Persistent SSH Tunnel
# This script creates a systemd service that automatically maintains
# the SSH tunnel to your lab devices, with automatic restart on failure
#
# Usage:
#   1. Edit setup_lab_tunnel.sh with your lab configuration
#   2. Run this script: sudo ./setup_tunnel_service.sh
#   3. The tunnel will start automatically and restart on failure/reboot

# ============================================================================
# CONFIGURATION
# ============================================================================

SERVICE_NAME="lab-tunnel"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TUNNEL_SCRIPT="${SCRIPT_DIR}/setup_lab_tunnel.sh"
RUN_USER="${SUDO_USER:-$USER}"

# ============================================================================
# CHECKS
# ============================================================================

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root: sudo $0"
    exit 1
fi

# Check if tunnel script exists
if [ ! -f "$TUNNEL_SCRIPT" ]; then
    echo "❌ Tunnel script not found: $TUNNEL_SCRIPT"
    echo "   Please ensure setup_lab_tunnel.sh exists in the same directory"
    exit 1
fi

# Check if tunnel script is executable
if [ ! -x "$TUNNEL_SCRIPT" ]; then
    echo "Making tunnel script executable..."
    chmod +x "$TUNNEL_SCRIPT"
fi

echo "=========================================="
echo "Lab Tunnel Systemd Service Setup"
echo "=========================================="
echo ""
echo "Service name: $SERVICE_NAME"
echo "Service file: $SERVICE_FILE"
echo "Tunnel script: $TUNNEL_SCRIPT"
echo "Run as user: $RUN_USER"
echo ""

# ============================================================================
# CREATE SERVICE FILE
# ============================================================================

echo "Creating systemd service file..."

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=SSH Tunnel to Lab Devices for Flask Dashboard
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$SCRIPT_DIR
ExecStart=$TUNNEL_SCRIPT
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Restart on failure
StartLimitInterval=0
StartLimitBurst=0

# Environment variables (if needed for SSH keys)
Environment="HOME=/home/$RUN_USER"

[Install]
WantedBy=multi-user.target
EOF

if [ $? -ne 0 ]; then
    echo "❌ Failed to create service file"
    exit 1
fi

echo "✅ Service file created: $SERVICE_FILE"
echo ""

# ============================================================================
# ENABLE AND START SERVICE
# ============================================================================

echo "Reloading systemd daemon..."
systemctl daemon-reload

echo "Enabling service to start on boot..."
systemctl enable "$SERVICE_NAME"

echo ""
echo "=========================================="
echo "Service installed successfully!"
echo "=========================================="
echo ""
echo "Available commands:"
echo "  Start tunnel:    sudo systemctl start $SERVICE_NAME"
echo "  Stop tunnel:     sudo systemctl stop $SERVICE_NAME"
echo "  Restart tunnel:  sudo systemctl restart $SERVICE_NAME"
echo "  Check status:    sudo systemctl status $SERVICE_NAME"
echo "  View logs:       sudo journalctl -u $SERVICE_NAME -f"
echo "  Disable service: sudo systemctl disable $SERVICE_NAME"
echo ""

read -p "Start the tunnel service now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Starting service..."
    systemctl start "$SERVICE_NAME"
    sleep 2
    
    echo ""
    echo "Service status:"
    systemctl status "$SERVICE_NAME" --no-pager
    
    echo ""
    echo "✅ Tunnel service is now running!"
    echo "   Check logs with: sudo journalctl -u $SERVICE_NAME -f"
else
    echo ""
    echo "Service not started. Start manually with:"
    echo "  sudo systemctl start $SERVICE_NAME"
fi

echo ""
echo "=========================================="
