#!/bin/bash
# Install and enable the RDK Testing systemd service

echo "🔧 Installing RDK Testing Service..."

# Copy service file to systemd directory
sudo cp rdk-testing.service /etc/systemd/system/

# Reload systemd daemon
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable rdk-testing.service

# Start the service
sudo systemctl start rdk-testing.service

# Show status
echo ""
echo "✅ Service installed successfully!"
echo ""
echo "Service status:"
sudo systemctl status rdk-testing.service --no-pager

echo ""
echo "📋 Useful commands:"
echo "  View logs:        sudo journalctl -u rdk-testing.service -f"
echo "  Stop service:     sudo systemctl stop rdk-testing.service"
echo "  Restart service:  sudo systemctl restart rdk-testing.service"
echo "  Disable service:  sudo systemctl disable rdk-testing.service"
echo "  Service status:   sudo systemctl status rdk-testing.service"
