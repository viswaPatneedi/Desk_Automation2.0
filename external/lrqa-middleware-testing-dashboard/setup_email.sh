#!/bin/bash
# Email Configuration Script for LRQA MW Testing Dashboard
# This script sets up SMTP email configuration

echo "=========================================="
echo "Email Configuration Setup"
echo "=========================================="
echo ""
echo "Choose your email provider:"
echo "1) Gmail (recommended for testing)"
echo "2) Comcast/Xfinity SMTP"
echo "3) Custom SMTP Server"
echo ""
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo ""
        echo "=== Gmail SMTP Setup ==="
        echo "You need to create an App Password:"
        echo "1. Go to: https://myaccount.google.com/apppasswords"
        echo "2. Sign in with your Gmail account"
        echo "3. Create an app password for 'Mail'"
        echo "4. Copy the 16-character password"
        echo ""
        read -p "Enter your Gmail address: " gmail_address
        read -p "Enter your Gmail App Password (16 chars): " gmail_password
        
        export SMTP_HOST="smtp.gmail.com" 
        export SMTP_PORT="587"
        export SENDER_EMAIL="$gmail_address"
        export SENDER_PASSWORD="$gmail_password"
        
        # Add to systemd service
        sudo mkdir -p /etc/systemd/system/device-testing.service.d
        sudo tee /etc/systemd/system/device-testing.service.d/email.conf > /dev/null <<EOF
[Service]
Environment="SMTP_HOST=smtp.gmail.com"
Environment="SMTP_PORT=587"
Environment="SENDER_EMAIL=$gmail_address"
Environment="SENDER_PASSWORD=$gmail_password"
EOF
        
        echo "✓ Gmail SMTP configured"
        ;;
        
    2)
        echo ""
        echo "=== Comcast Mail Relay Setup ==="
        echo "Using Comcast internal mail relay (no authentication required)"
        echo "Server: mailrelay.comcast.com"
        echo "Default sender: viswachaithanya_patneedi@comcast.com"
        echo ""
        read -p "Use default sender email? (y/n): " use_default
        
        if [ "$use_default" = "y" ] || [ "$use_default" = "Y" ]; then
            comcast_email="viswachaithanya_patneedi@comcast.com"
        else
            read -p "Enter your Comcast email: " comcast_email
        fi
        
        export SMTP_HOST="mailrelay.comcast.com"
        export SMTP_PORT="25"
        export SENDER_EMAIL="$comcast_email"
        export SENDER_PASSWORD=""
        
        sudo mkdir -p /etc/systemd/system/device-testing.service.d
        sudo tee /etc/systemd/system/device-testing.service.d/email.conf > /dev/null <<EOF
[Service]
Environment="SMTP_HOST=mailrelay.comcast.com"
Environment="SMTP_PORT=25"
Environment="SENDER_EMAIL=$comcast_email"
Environment="SENDER_PASSWORD="
EOF
        
        echo "✓ Comcast Mail Relay configured (no authentication required)"
        ;;
        
    3)
        echo ""
        echo "=== Custom SMTP Setup ==="
        read -p "SMTP Server: " smtp_server
        read -p "SMTP Port (usually 587): " smtp_port
        read -p "Sender Email: " sender_email
        read -p "SMTP Password: " smtp_password
        
        export SMTP_HOST="$smtp_server"
        export SMTP_PORT="$smtp_port"
        export SENDER_EMAIL="$sender_email"
        export SENDER_PASSWORD="$smtp_password"
        
        sudo mkdir -p /etc/systemd/system/device-testing.service.d
        sudo tee /etc/systemd/system/device-testing.service.d/email.conf > /dev/null <<EOF
[Service]
Environment="SMTP_HOST=$smtp_server"
Environment="SMTP_PORT=$smtp_port"
Environment="SENDER_EMAIL=$sender_email"
Environment="SENDER_PASSWORD=$smtp_password"
EOF
        
        echo "✓ Custom SMTP configured"
        ;;
        
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "Reloading systemd and restarting service..."
sudo systemctl daemon-reload
sudo systemctl restart device-testing.service

echo ""
echo "=========================================="
echo "✓ Email configuration complete!"
echo "=========================================="
echo ""
echo "Test your configuration:"
echo "1. Go to http://10.0.0.32:8080/forgot-password"
echo "2. Enter your NTID and email"
echo "3. Check your email inbox for the verification code"
echo ""
echo "To view logs:"
echo "sudo journalctl -u device-testing.service -f"
