#!/bin/bash
# Setup local DNS server for lrqa-testing-tool.com on local network

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🌐 Local DNS Setup for lrqa-testing-tool.com${NC}"
echo "================================================"
echo ""

# Get current IP
CURRENT_IP=$(hostname -I | awk '{print $1}')
echo "Current Raspberry Pi IP: $CURRENT_IP"
echo ""

# Install dnsmasq
echo -e "${YELLOW}📦 Installing dnsmasq...${NC}"
sudo apt-get update
sudo apt-get install -y dnsmasq

# Stop dnsmasq to configure
sudo systemctl stop dnsmasq

# Backup original config
if [ ! -f /etc/dnsmasq.conf.backup ]; then
    sudo cp /etc/dnsmasq.conf /etc/dnsmasq.conf.backup
fi

# Create custom dnsmasq configuration
echo -e "${YELLOW}📝 Configuring dnsmasq...${NC}"
sudo tee /etc/dnsmasq.d/lrqa-testing-tool.conf > /dev/null <<EOF
# Local DNS entry for lrqa-testing-tool.com
address=/lrqa-testing-tool.com/$CURRENT_IP

# Also handle www subdomain
address=/www.lrqa-testing-tool.com/$CURRENT_IP

# DNS upstream servers (use your router or public DNS)
server=8.8.8.8
server=8.8.4.4

# Don't read /etc/hosts for DNS (optional)
no-hosts

# Log queries for debugging (optional, comment out in production)
log-queries
log-facility=/var/log/dnsmasq.log
EOF

# Enable and start dnsmasq
echo -e "${YELLOW}🚀 Starting dnsmasq...${NC}"
sudo systemctl enable dnsmasq
sudo systemctl restart dnsmasq

# Check status
if sudo systemctl is-active --quiet dnsmasq; then
    echo -e "${GREEN}✅ dnsmasq is running${NC}"
else
    echo -e "${RED}❌ dnsmasq failed to start${NC}"
    echo "Check logs: sudo journalctl -u dnsmasq -n 50"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Local DNS server configured!${NC}"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Configure devices to use this DNS server:"
echo "   - Go to Network Settings on each laptop"
echo "   - Set DNS server to: $CURRENT_IP"
echo "   - (Keep secondary DNS as 8.8.8.8 for internet access)"
echo ""
echo "2. Or configure your router to use $CURRENT_IP as DNS server"
echo "   - This will apply to all devices on the network automatically"
echo ""
echo "3. Set up Nginx reverse proxy:"
echo "   ./setup_domain.sh"
echo "   Enter: lrqa-testing-tool.com"
echo ""
echo "4. Test DNS resolution from any laptop:"
echo "   nslookup lrqa-testing-tool.com $CURRENT_IP"
echo "   ping lrqa-testing-tool.com"
echo ""
echo "🔧 Useful Commands:"
echo "   Check dnsmasq status: sudo systemctl status dnsmasq"
echo "   View logs:            sudo tail -f /var/log/dnsmasq.log"
echo "   Restart dnsmasq:      sudo systemctl restart dnsmasq"
echo "   Test DNS:             dig @$CURRENT_IP lrqa-testing-tool.com"
echo ""
echo -e "${GREEN}🎉 Done!${NC}"
