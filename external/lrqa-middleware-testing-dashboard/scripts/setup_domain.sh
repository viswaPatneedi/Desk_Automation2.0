#!/bin/bash
# Setup script for domain-based access to RDK Testing Dashboard

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🌐 RDK Testing Dashboard - Domain Setup${NC}"
echo "=========================================="
echo ""

# Check if nginx is installed
if ! command -v nginx &> /dev/null; then
    echo -e "${YELLOW}📦 Installing Nginx...${NC}"
    sudo apt-get update
    sudo apt-get install -y nginx
fi

echo -e "${GREEN}✅ Nginx installed${NC}"
echo ""

# Prompt for domain name
read -p "Enter your domain name (e.g., rdk-testing.example.com): " DOMAIN

if [ -z "$DOMAIN" ]; then
    echo -e "${RED}❌ Domain name is required${NC}"
    exit 1
fi

echo ""
read -p "Setup SSL certificate with Let's Encrypt? (y/n): " SETUP_SSL

# Update nginx configuration with domain
echo -e "${YELLOW}📝 Creating Nginx configuration...${NC}"
CONFIG_FILE="/etc/nginx/sites-available/rdk-testing"

sudo tee $CONFIG_FILE > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support for SSE
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
        
        # Disable buffering for SSE
        proxy_buffering off;
        proxy_cache off;
    }
    
    location /static/ {
        alias $PWD/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Enable the site
echo -e "${YELLOW}🔗 Enabling site...${NC}"
sudo ln -sf $CONFIG_FILE /etc/nginx/sites-enabled/rdk-testing

# Remove default site if exists
sudo rm -f /etc/nginx/sites-enabled/default

# Test nginx configuration
echo -e "${YELLOW}🧪 Testing Nginx configuration...${NC}"
sudo nginx -t

# Restart nginx
echo -e "${YELLOW}♻️  Restarting Nginx...${NC}"
sudo systemctl restart nginx
sudo systemctl enable nginx

echo -e "${GREEN}✅ Nginx configured successfully${NC}"
echo ""

# Setup SSL if requested
if [ "$SETUP_SSL" = "y" ]; then
    echo -e "${YELLOW}🔒 Setting up SSL with Let's Encrypt...${NC}"
    
    # Install certbot
    if ! command -v certbot &> /dev/null; then
        echo "Installing certbot..."
        sudo apt-get install -y certbot python3-certbot-nginx
    fi
    
    # Get SSL certificate
    echo "Obtaining SSL certificate for $DOMAIN..."
    read -p "Enter your email address for Let's Encrypt: " EMAIL
    
    sudo certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email $EMAIL --redirect
    
    # Setup auto-renewal
    sudo systemctl enable certbot.timer
    sudo systemctl start certbot.timer
    
    echo -e "${GREEN}✅ SSL certificate installed${NC}"
    echo -e "${GREEN}🔒 Auto-renewal enabled${NC}"
fi

echo ""
echo -e "${GREEN}✅ Domain setup complete!${NC}"
echo ""
echo "📋 Access Information:"
if [ "$SETUP_SSL" = "y" ]; then
    echo "   URL: https://$DOMAIN"
else
    echo "   URL: http://$DOMAIN"
fi
echo ""
echo "📝 DNS Configuration:"
echo "   Make sure your domain '$DOMAIN' points to this server's IP address"
echo "   Server IP: $(hostname -I | awk '{print $1}')"
echo ""
echo "   Add this DNS record:"
echo "   Type: A"
echo "   Name: rdk-testing (or @ for root domain)"
echo "   Value: $(hostname -I | awk '{print $1}')"
echo "   TTL: 3600"
echo ""
echo "📝 For local testing (before DNS propagation):"
echo "   Add to /etc/hosts on your computer:"
echo "   $(hostname -I | awk '{print $1}')  $DOMAIN"
echo ""
echo "🔧 Useful Commands:"
echo "   Check Nginx status:  sudo systemctl status nginx"
echo "   Restart Nginx:       sudo systemctl restart nginx"
echo "   View Nginx logs:     sudo tail -f /var/log/nginx/access.log"
echo "   Test SSL renewal:    sudo certbot renew --dry-run"
echo ""
echo -e "${GREEN}🎉 Done!${NC}"
