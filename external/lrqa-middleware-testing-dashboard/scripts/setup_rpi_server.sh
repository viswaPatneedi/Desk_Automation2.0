#!/bin/bash
# Raspberry Pi Flask Server Setup Script
# Run this on your Raspberry Pi to configure the server for LAN access

echo "=========================================="
echo "Device Test Automation - RPi Server Setup"
echo "=========================================="

# Update system
echo "[1/6] Updating system packages..."
sudo apt update

# Install Python dependencies
echo "[2/6] Installing Python dependencies..."
sudo apt install -y python3-pip python3-venv

# Create virtual environment (recommended)
echo "[3/6] Setting up Python virtual environment..."
cd /home/pi/Device-Connect/New/Enhancement || exit
python3 -m venv venv
source venv/bin/activate

# Install required Python packages
echo "[4/6] Installing Python packages..."
pip install flask paramiko pytesseract pillow

# Configure firewall (if UFW is enabled)
echo "[5/6] Configuring firewall..."
if command -v ufw &> /dev/null; then
    sudo ufw allow 5000/tcp
    echo "Firewall rule added for port 5000"
else
    echo "UFW not installed, skipping firewall configuration"
fi

# Create systemd service
echo "[6/6] Creating systemd service..."
sudo tee /etc/systemd/system/device-test-server.service > /dev/null <<EOF
[Unit]
Description=Device Test Automation Flask Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/Device-Connect/New/Enhancement
Environment="PATH=/home/pi/Device-Connect/New/Enhancement/venv/bin"
ExecStart=/home/pi/Device-Connect/New/Enhancement/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable device-test-server.service

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Commands to manage the server:"
echo "  Start:   sudo systemctl start device-test-server"
echo "  Stop:    sudo systemctl stop device-test-server"
echo "  Restart: sudo systemctl restart device-test-server"
echo "  Status:  sudo systemctl status device-test-server"
echo "  Logs:    sudo journalctl -u device-test-server -f"
echo ""
echo "To find your Raspberry Pi's IP address:"
echo "  hostname -I"
echo ""
echo "Access the web interface from any device on your LAN:"
echo "  http://<RASPBERRY_PI_IP>:5000"
echo ""
