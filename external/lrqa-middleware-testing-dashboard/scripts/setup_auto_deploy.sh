#!/bin/bash
# Setup Auto-Deploy System
# This script configures automatic deployment from GitHub to R-Pi

set -e

REPO_DIR="/home/pi/Desktop/viswa/Latest_Enhancement/Enhancement"
SERVICE_FILE="/etc/systemd/system/auto-deploy.service"
TIMER_FILE="/etc/systemd/system/auto-deploy.timer"

echo "=========================================="
echo "Setting up Auto-Deploy System"
echo "=========================================="

# Make auto_deploy.sh executable
echo "Making auto_deploy.sh executable..."
chmod +x "$REPO_DIR/auto_deploy.sh"

# Create systemd service
echo "Creating systemd service..."
sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Auto Deploy from GitHub
After=network.target

[Service]
Type=oneshot
User=pi
WorkingDirectory=$REPO_DIR
ExecStart=/bin/bash $REPO_DIR/auto_deploy.sh
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Create systemd timer (checks every 5 minutes)
echo "Creating systemd timer..."
sudo tee "$TIMER_FILE" > /dev/null <<EOF
[Unit]
Description=Auto Deploy Timer - Check GitHub every 5 minutes
Requires=auto-deploy.service

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
AccuracySec=1min

[Install]
WantedBy=timers.target
EOF

# Reload systemd and enable services
echo "Enabling systemd services..."
sudo systemctl daemon-reload
sudo systemctl enable auto-deploy.timer
sudo systemctl start auto-deploy.timer

echo ""
echo "=========================================="
echo "✅ Auto-Deploy System Setup Complete!"
echo "=========================================="
echo ""
echo "📋 Configuration:"
echo "  • Checks GitHub every 5 minutes"
echo "  • Auto-pulls changes if detected"
echo "  • Restarts application service"
echo "  • Logs to: $REPO_DIR/auto_deploy.log"
echo ""
echo "🔧 Useful Commands:"
echo "  • Check timer status:    systemctl status auto-deploy.timer"
echo "  • Check last run:        systemctl status auto-deploy.service"
echo "  • View logs:             journalctl -u auto-deploy.service -f"
echo "  • Manual trigger:        sudo systemctl start auto-deploy.service"
echo "  • Stop auto-sync:        sudo systemctl stop auto-deploy.timer"
echo "  • Disable auto-sync:     sudo systemctl disable auto-deploy.timer"
echo ""
echo "📝 Deployment Logs:"
echo "  tail -f $REPO_DIR/auto_deploy.log"
echo ""
echo "=========================================="
