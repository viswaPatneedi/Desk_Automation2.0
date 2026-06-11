#!/bin/bash

################################################################################
# DOCKER DEPLOYMENT PACKAGE CREATOR FOR USB
# Creates a minimal, clean deployment package for new Raspberry Pi 4
# Size: ~100-150 MB (NOT 18GB!)
################################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SOURCE_DIR="/home/lrqa/Desktop/viswa/Latest_Enhancement/Enhancement"
USB_MOUNT="/media/lrqa/6077-248A"
DEPLOY_DIR="${USB_MOUNT}/Docker-Deployment-RPI4"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  🐳 CLEAN DOCKER DEPLOYMENT PACKAGE CREATOR FOR USB 🐳          ║${NC}"
echo -e "${BLUE}║                                                                  ║${NC}"
echo -e "${BLUE}║         Minimal deployment (~100-150MB, NOT 18GB!)              ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════╝${NC}"

################################################################################
# STEP 1: Verify USB is accessible
################################################################################

echo -e "\n${YELLOW}STEP 1: Verifying USB...${NC}"
if [ ! -d "$USB_MOUNT" ]; then
    echo -e "${RED}❌ USB not found at $USB_MOUNT${NC}"
    echo "Available mount points:"
    mount | grep /media/
    exit 1
fi

USB_SPACE=$(df -h "$USB_MOUNT" | tail -1 | awk '{print $4}')
echo -e "${GREEN}✅ USB found: $USB_SPACE available${NC}"

################################################################################
# STEP 2: Check source directory
################################################################################

echo -e "\n${YELLOW}STEP 2: Checking source directory...${NC}"
if [ ! -d "$SOURCE_DIR" ]; then
    echo -e "${RED}❌ Source directory not found: $SOURCE_DIR${NC}"
    exit 1
fi

SOURCE_SIZE=$(du -sh "$SOURCE_DIR" | awk '{print $1}')
echo -e "${GREEN}✅ Source found: $SOURCE_SIZE${NC}"

################################################################################
# STEP 3: Create deployment directory on USB
################################################################################

echo -e "\n${YELLOW}STEP 3: Creating deployment directory on USB...${NC}"
rm -rf "$DEPLOY_DIR" 2>/dev/null || true
mkdir -p "$DEPLOY_DIR"
echo -e "${GREEN}✅ Directory created: $DEPLOY_DIR${NC}"

################################################################################
# STEP 4: Copy ONLY essential files (CLEAN BUILD)
################################################################################

echo -e "\n${YELLOW}STEP 4: Copying essential deployment files...${NC}"
echo "(Excluding: venv, screenshots, logs, caches, old files)"

# Create subdirectories
mkdir -p "$DEPLOY_DIR"/{controllers,models,services,templates,static,methods}

# Copy Docker files
echo -e "  • Copying Docker files..."
cp -v "$SOURCE_DIR"/Dockerfile.rpi.clean "$DEPLOY_DIR/" 2>&1 | head -1
cp -v "$SOURCE_DIR"/docker-compose.rpi.clean.yml "$DEPLOY_DIR/" 2>&1 | head -1
cp -v "$SOURCE_DIR"/docker-entrypoint.sh "$DEPLOY_DIR/" 2>&1 | head -1
cp -v "$SOURCE_DIR"/.dockerignore.rpi.clean "$DEPLOY_DIR/" 2>&1 | head -1
cp -v "$SOURCE_DIR"/rpi4-setup-complete.sh "$DEPLOY_DIR/" 2>&1 | head -1
cp -v "$SOURCE_DIR"/docker-verify-setup.sh "$DEPLOY_DIR/" 2>&1 | head -1

# Copy application files
echo -e "  • Copying application files..."
cp -v "$SOURCE_DIR"/app.py "$DEPLOY_DIR/" 2>&1 | head -1
cp -v "$SOURCE_DIR"/requirements.txt "$DEPLOY_DIR/" 2>&1 | head -1
cp -v "$SOURCE_DIR"/log_patterns.json "$DEPLOY_DIR/" 2>&1 | head -1
cp -v "$SOURCE_DIR"/wsgi.py "$DEPLOY_DIR/" 2>/dev/null | head -1 || true

# Copy configuration files
echo -e "  • Copying configuration files..."
cp -v "$SOURCE_DIR"/config_*.py "$DEPLOY_DIR/" 2>&1 | head -3

# Copy source code directories
echo -e "  • Copying source directories..."
cp -rv "$SOURCE_DIR"/controllers/* "$DEPLOY_DIR"/controllers/ 2>&1 | head -3
cp -rv "$SOURCE_DIR"/models/* "$DEPLOY_DIR"/models/ 2>&1 | head -3
cp -rv "$SOURCE_DIR"/services/* "$DEPLOY_DIR"/services/ 2>&1 | head -3
cp -rv "$SOURCE_DIR"/templates/* "$DEPLOY_DIR"/templates/ 2>&1 | head -3
cp -rv "$SOURCE_DIR"/static/* "$DEPLOY_DIR"/static/ 2>&1 | head -3

# Copy methods if they exist
if [ -d "$SOURCE_DIR/methods" ]; then
    cp -rv "$SOURCE_DIR"/methods/* "$DEPLOY_DIR"/methods/ 2>&1 | head -3 || true
fi

# Copy documentation
echo -e "  • Copying documentation..."
cp -v "$SOURCE_DIR"/DOCKER_*.md "$DEPLOY_DIR/" 2>&1 | head -5
cp -v "$SOURCE_DIR"/DOCKER_*.txt "$DEPLOY_DIR/" 2>&1 | head -3
cp -v "$SOURCE_DIR"/USB_*.md "$DEPLOY_DIR/" 2>&1 | head -3
cp -v "$SOURCE_DIR"/USB_*.txt "$DEPLOY_DIR/" 2>&1 | head -2
cp -v "$SOURCE_DIR"/QUICK_DEPLOY_*.txt "$DEPLOY_DIR/" 2>&1 | head -1

echo -e "${GREEN}✅ Files copied${NC}"

################################################################################
# STEP 5: Make scripts executable
################################################################################

echo -e "\n${YELLOW}STEP 5: Making scripts executable...${NC}"
chmod +x "$DEPLOY_DIR"/rpi4-setup-complete.sh
chmod +x "$DEPLOY_DIR"/docker-verify-setup.sh
chmod +x "$DEPLOY_DIR"/docker-entrypoint.sh
echo -e "${GREEN}✅ Scripts are now executable${NC}"

################################################################################
# STEP 6: Verify deployment package
################################################################################

echo -e "\n${YELLOW}STEP 6: Verifying deployment package...${NC}"

echo -e "\n${BLUE}Deployment package contents:${NC}"
ls -lah "$DEPLOY_DIR" | head -20

echo -e "\n${BLUE}Total package size:${NC}"
PACKAGE_SIZE=$(du -sh "$DEPLOY_DIR" | awk '{print $1}')
echo -e "${GREEN}$PACKAGE_SIZE${NC}"

echo -e "\n${BLUE}Essential files present:${NC}"
echo -n "  Docker files: "
[ -f "$DEPLOY_DIR/Dockerfile.rpi.clean" ] && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}"
echo -n "  App files: "
[ -f "$DEPLOY_DIR/app.py" ] && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}"
echo -n "  Requirements: "
[ -f "$DEPLOY_DIR/requirements.txt" ] && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}"
echo -n "  Setup script: "
[ -f "$DEPLOY_DIR/rpi4-setup-complete.sh" ] && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}"
echo -n "  Configs: "
[ -f "$DEPLOY_DIR/config_commands.py" ] && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}"

################################################################################
# STEP 7: Create README
################################################################################

echo -e "\n${YELLOW}STEP 7: Creating deployment README...${NC}"

cat > "$DEPLOY_DIR/README_DEPLOYMENT.txt" << 'EOF'
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║      🐳 DOCKER DEPLOYMENT PACKAGE FOR NEW RASPBERRY PI 4 🐳                 ║
║                                                                              ║
║         Minimal, Clean Deployment (~100-150MB)                             ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

CONTENTS OF THIS USB:
═════════════════════════════════════════════════════════════════════════════

✓ Docker build files (Dockerfile, docker-compose, entrypoint)
✓ Complete application source code (latest version)
✓ All configuration files
✓ Requirements (Python dependencies)
✓ Deployment scripts (one-command setup)
✓ Documentation guides
✓ Log patterns database (15 patterns - FIXED)

NOT INCLUDED (Clean build):
✗ Virtual environment (rebuilt on target RPi)
✗ Execution logs/screenshots (created at runtime)
✗ Python cache (__pycache__)
✗ Old backup files or development artifacts
✗ Docker image (.tar file - will be built on target)

TOTAL SIZE: ~100-150 MB (extremely minimal!)

═════════════════════════════════════════════════════════════════════════════

HOW TO DEPLOY ON NEW RASPBERRY PI 4:

  STEP 1: Prepare new RPi
    1. Flash Raspberry Pi OS to microSD card
    2. Boot and enable SSH
    3. Connect to network

  STEP 2: Connect this USB to new RPi

  STEP 3: SSH to new RPi
    $ ssh pi@<new-rpi-ip>
    $ lsblk  (find USB, usually /dev/sda1)
    $ cd /mnt
    $ sudo mount /dev/sda1 /mnt/usb
    $ cd /mnt/usb/Docker-Deployment-RPI4

  STEP 4: RUN ONE-COMMAND DEPLOYMENT
    $ chmod +x rpi4-setup-complete.sh
    $ ./rpi4-setup-complete.sh

  STEP 5: WAIT 10-15 MINUTES
    Script will:
    - Check system requirements
    - Install Docker
    - Build Docker image
    - Start application
    - Verify health

  STEP 6: ACCESS DASHBOARD
    http://<new-rpi-ip>:11078

═════════════════════════════════════════════════════════════════════════════

QUICK REFERENCE:

View logs:
  $ docker logs -f rdk-middleware-dashboard

Check status:
  $ docker ps

Monitor:
  $ docker stats rdk-middleware-dashboard

Restart:
  $ docker-compose restart

═════════════════════════════════════════════════════════════════════════════

For detailed documentation, see:
  - DOCKER_DEPLOYMENT_NEW_RPI.md (complete guide)
  - QUICK_DEPLOY_NEW_RPI.txt (3-step summary)
  - DOCKER_IMAGE_SPECIFICATION.md (image details)
  - DOCKER_QUICK_REFERENCE.txt (Docker commands)

═════════════════════════════════════════════════════════════════════════════

Version: 2.0
Status: Production Ready
Ready for deployment!

EOF

echo -e "${GREEN}✅ README created${NC}"

################################################################################
# STEP 8: Final Summary
################################################################################

echo -e "\n${BLUE}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                   ✅ DEPLOYMENT PACKAGE READY ✅                  ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════╝${NC}"

echo -e "\n${GREEN}📊 Summary:${NC}"
echo "  Location:          $DEPLOY_DIR"
echo "  Package size:      $PACKAGE_SIZE"
echo "  USB available:     $USB_SPACE"
echo ""
echo -e "${GREEN}📋 Next steps:${NC}"
echo "  1. Connect this USB to new Raspberry Pi 4"
echo "  2. SSH to new RPi"
echo "  3. Mount USB: sudo mount /dev/sda1 /mnt/usb"
echo "  4. Navigate: cd /mnt/usb/Docker-Deployment-RPI4"
echo "  5. Deploy: ./rpi4-setup-complete.sh"
echo "  6. Wait 10-15 minutes"
echo "  7. Access: http://<new-rpi-ip>:11078"
echo ""
echo -e "${GREEN}📖 Documentation:${NC}"
echo "  - README_DEPLOYMENT.txt (this file)"
echo "  - DOCKER_DEPLOYMENT_NEW_RPI.md (complete guide)"
echo "  - QUICK_DEPLOY_NEW_RPI.txt (quick reference)"
echo ""
echo -e "${BLUE}Ready for deployment! 🚀${NC}"

EOF
