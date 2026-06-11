#!/bin/bash
# ============================================================
# RDK Dashboard - Quick Reference Commands
# ============================================================

SCRIPT_DIR="/home/viswa-pi4/Desktop/LRQA-DASHBOARD/lrqa-middleware-testing-dashboard"
START_SCRIPT="$SCRIPT_DIR/start-app.sh"

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   RDK Middleware Testing Dashboard - Quick Ref     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════╝${NC}\n"

echo -e "${GREEN}✓ APP STATUS:${NC}"
$START_SCRIPT status

echo -e "\n${GREEN}✓ COMMON COMMANDS:${NC}"
echo ""
echo -e "${YELLOW}Start app:${NC}"
echo "  $START_SCRIPT start"
echo ""
echo -e "${YELLOW}Stop app:${NC}"
echo "  $START_SCRIPT stop"
echo ""
echo -e "${YELLOW}Restart app:${NC}"
echo "  $START_SCRIPT restart"
echo ""
echo -e "${YELLOW}View logs:${NC}"
echo "  $START_SCRIPT logs"
echo ""

echo -e "${GREEN}✓ ACCESS URLs:${NC}"
IP=$(hostname -I | awk '{print $1}')
echo "  http://$IP:11078  (Dashboard)"
echo "  http://localhost:11078  (Local access)"
echo ""

echo -e "${GREEN}✓ AUTO-START ON BOOT:${NC}"
echo "  Option 1: Add to crontab"
echo "    crontab -e"
echo "    @reboot $START_SCRIPT start"
echo ""
echo "  Option 2: Use system startup"
echo "    sudo systemctl enable rdk-flask-app"
echo ""

echo -e "${GREEN}✓ USEFUL FILES:${NC}"
echo "  Startup Script:     $START_SCRIPT"
echo "  Logs:               $SCRIPT_DIR/logs/app-background.log"
echo "  PID File:           $SCRIPT_DIR/app.pid"
echo "  Setup Guide:        $SCRIPT_DIR/BACKGROUND_SERVICE_SETUP.md"
echo ""

echo -e "${GREEN}✓ PORT VERIFICATION:${NC}"
ss -tlnp 2>/dev/null | grep 11078 || echo "  Port 11078: NOT LISTENING"
echo ""

echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo -e "Setup Complete! App is running in venv at background."
echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
