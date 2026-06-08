#!/bin/bash

# Docker Commands Quick Reference Generator
# This script displays the most commonly used Docker commands for this application

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Functions
show_header() {
    echo -e "${BLUE}${BOLD}================================${NC}"
    echo -e "${BLUE}${BOLD}$1${NC}"
    echo -e "${BLUE}${BOLD}================================${NC}"
    echo
}

show_section() {
    echo -e "${CYAN}${BOLD}$1${NC}"
    echo -e "${CYAN}---${NC}"
}

show_command() {
    echo -e "${GREEN}$1${NC}"
    echo "  $2"
    echo
}

# Main content
show_header "Docker Commands Reference - RDK-E Middleware Testing Dashboard"

show_section "⚡ FASTEST WAY TO START"
echo -e "  ${YELLOW}Just run the automated script:${NC}"
echo
show_command "bash docker-rpi-quickstart.sh" "Builds, configures, and starts everything automatically"

echo
show_header "📦 INSTALLATION & SETUP"

show_section "1. Install Docker (First Time Only)"
show_command "curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh" \
    "Install Docker Engine"
show_command "sudo usermod -aG docker \$USER && newgrp docker" \
    "Add user to docker group (avoid sudo)"
show_command "sudo apt-get install -y docker-compose-plugin" \
    "Install Docker Compose"

show_section "2. Verify Installation"
show_command "docker --version && docker compose version" \
    "Check both are installed"
show_command "docker run hello-world" \
    "Test Docker installation"

echo
show_header "🏗️ BUILD COMMANDS"

show_section "Option A: Using Docker Compose (Recommended)"
show_command "docker compose -f docker-compose.rpi.yml build" \
    "Build the image"
show_command "docker compose -f docker-compose.rpi.yml build --no-cache --pull" \
    "Clean rebuild (pulls latest base image)"

show_section "Option B: Using Docker CLI"
show_command "docker build -f Dockerfile.rpi -t rdk-middleware:rpi ." \
    "Standard build"
show_command "docker build --no-cache -f Dockerfile.rpi -t rdk-middleware:rpi ." \
    "Fresh rebuild (slow but clean)"

echo
show_header "🚀 START/STOP COMMANDS"

show_section "Option A: Using Docker Compose (Recommended)"
show_command "docker compose -f docker-compose.rpi.yml up -d" \
    "Start container in background"
show_command "docker compose -f docker-compose.rpi.yml up" \
    "Start container (show logs)"
show_command "docker compose -f docker-compose.rpi.yml down" \
    "Stop container"
show_command "docker compose -f docker-compose.rpi.yml restart" \
    "Restart container"

show_section "Option B: Using Make (Simplest)"
show_command "make -f Makefile.rpi build" \
    "Build"
show_command "make -f Makefile.rpi up" \
    "Start"
show_command "make -f Makefile.rpi down" \
    "Stop"
show_command "make -f Makefile.rpi logs" \
    "View logs"

echo
show_header "📋 LOGS & STATUS"

show_command "docker compose -f docker-compose.rpi.yml logs -f" \
    "View logs in real-time"
show_command "docker compose -f docker-compose.rpi.yml logs --tail=100" \
    "View last 100 lines"
show_command "docker ps | grep rdk-middleware" \
    "Check if running"
show_command "docker stats rdk-middleware" \
    "View resource usage (CPU, RAM)"

echo
show_header "📊 USEFUL QUERIES"

show_command "docker compose -f docker-compose.rpi.yml ps" \
    "Show all services status"
show_command "docker inspect rdk-middleware | grep -E 'IP|Mounts'" \
    "Show container IP and volumes"
show_command "docker exec rdk-middleware pip list" \
    "List Python packages inside container"
show_command "docker exec rdk-middleware tesseract --version" \
    "Verify Tesseract is installed"

echo
show_header "🔧 MAINTENANCE"

show_section "Cleanup"
show_command "docker system prune -a" \
    "Remove unused images/containers"
show_command "docker volume prune" \
    "Remove unused volumes"

show_section "Backup"
show_command "make -f Makefile.rpi backup" \
    "Backup all data"
show_command "docker save rdk-middleware:rpi | gzip > backup.tar.gz" \
    "Backup Docker image"

echo
show_header "💻 SHELL & DEBUG"

show_command "docker exec -it rdk-middleware /bin/bash" \
    "Open shell in container"
show_command "docker exec rdk-middleware cat /app/devices.json" \
    "View configuration"
show_command "docker logs rdk-middleware 2>&1 | grep ERROR" \
    "Find errors in logs"

echo
show_header "✅ HOW TO ACCESS THE APPLICATION"

echo
show_section "Get Your Raspberry Pi IP:"
show_command "hostname -I" \
    "Find your Pi's IP address"

show_section "Access in Browser:"
echo -e "  ${GREEN}http://<YOUR_PI_IP>:11078${NC}"
echo -e "  Example: http://192.168.1.100:11078"
echo

show_section "Test Health Endpoint:"
show_command "curl http://localhost:11078/health" \
    "Check if web server is responding"

echo
show_header "📋 COMPLETE WORKFLOW"

echo -e "${YELLOW}Step 1: Build${NC}"
echo "  docker compose -f docker-compose.rpi.yml build"
echo

echo -e "${YELLOW}Step 2: Configure${NC}"
echo "  nano .env  # Add your email settings"
echo

echo -e "${YELLOW}Step 3: Start${NC}"
echo "  docker compose -f docker-compose.rpi.yml up -d"
echo

echo -e "${YELLOW}Step 4: Verify${NC}"
echo "  docker compose -f docker-compose.rpi.yml ps"
echo "  curl http://localhost:11078/health"
echo

echo -e "${YELLOW}Step 5: View Logs${NC}"
echo "  docker compose -f docker-compose.rpi.yml logs -f"
echo

echo -e "${YELLOW}Step 6: Open in Browser${NC}"
echo "  http://<your-pi-ip>:11078"
echo

echo
show_header "📦 ALL DEPENDENCIES INCLUDED"

echo -e "${GREEN}System Dependencies (Auto-Installed):${NC}"
echo "  ✓ Python 3.11"
echo "  ✓ Tesseract OCR"
echo "  ✓ OpenCV"
echo "  ✓ GCC/G++"
echo "  ✓ Build tools"
echo "  ✓ Math libraries (BLAS/LAPACK)"
echo

echo -e "${GREEN}Python Dependencies (Auto-Installed):${NC}"
echo "  ✓ Flask==3.0.0"
echo "  ✓ paramiko==3.4.0 (SSH)"
echo "  ✓ PIL/Pillow==10.1.0"
echo "  ✓ opencv-python==4.8.1.78"
echo "  ✓ pytesseract==0.3.10"
echo "  ✓ gunicorn==21.2.0"
echo "  ✓ gevent==24.2.1"
echo "  ✓ And 8 more packages (see requirements.txt)"
echo

echo
show_header "✨ That's it! You're all set!"
echo
