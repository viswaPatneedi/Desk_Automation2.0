#!/bin/bash
# Gmail SMTP Configuration for LRQA MW Testing Dashboard

echo "=========================================="
echo "Gmail SMTP Configuration"
echo "=========================================="
echo ""

SMTP_SERVER="smtp.gmail.com"
SMTP_PORT="587"
SENDER_EMAIL="cperdkemiddleware@gmail.com"

echo "Email: cperdkemiddleware@gmail.com"
echo ""
read -sp "Enter your Gmail App Password (16 characters): " SENDER_PASSWORD
echo ""
echo ""

# Export for current session
export SMTP_SERVER="$SMTP_SERVER"
export SMTP_PORT="$SMTP_PORT"
export SENDER_EMAIL="$SENDER_EMAIL"
export SENDER_PASSWORD="$SENDER_PASSWORD"

# Create systemd override directory
echo "Creating systemd service configuration..."
sudo mkdir -p /etc/systemd/system/device-testing.service.d

# Create environment file for systemd service
sudo tee /etc/systemd/system/device-testing.service.d/email.conf > /dev/null <<EOF
[Service]
Environment="SMTP_SERVER=smtp.gmail.com"
Environment="SMTP_PORT=587"
Environment="SENDER_EMAIL=cperdkemiddleware@gmail.com"
Environment="SENDER_PASSWORD=$SENDER_PASSWORD"
EOF

echo ""
echo "✓ Gmail SMTP configured successfully!"
echo ""
echo "Configuration saved:"
echo "  SMTP Server: smtp.gmail.com"
echo "  Port: 587"
echo "  Email: cperdkemiddleware@gmail.com"
echo ""
echo "To apply changes to the service:"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl restart device-testing"
echo ""
echo "To run the app with these settings now:"
echo "  python3 app.py"
echo ""
