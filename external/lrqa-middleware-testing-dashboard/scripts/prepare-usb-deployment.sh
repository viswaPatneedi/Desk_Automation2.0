#!/bin/bash

##############################################################################
# RDK Middleware Deployment - USB Preparation Script
# Purpose: Prepare all necessary files for Raspberry Pi deployment on USB
# Usage: sudo ./prepare-usb-deployment.sh /mnt/usb
##############################################################################

set -e

# Configuration
USB_PATH="${1:-.}"
DEPLOY_DIR="$USB_PATH/rdk-middleware-deployment"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$USB_PATH/deployment_prep_$TIMESTAMP.log"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

success() {
    echo -e "${GREEN}[✓]${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[⚠]${NC} $1" | tee -a "$LOG_FILE"
}

##############################################################################
# Main Deployment Preparation
##############################################################################

log "=== RDK Middleware USB Deployment Preparation ==="
log "Target USB: $USB_PATH"
log "Deployment Directory: $DEPLOY_DIR"
log "Logging to: $LOG_FILE"

# Check if USB path exists and is writable
if [ ! -d "$USB_PATH" ]; then
    error "USB path does not exist: $USB_PATH"
fi

if [ ! -w "$USB_PATH" ]; then
    error "USB path is not writable. Please check permissions or mount the USB correctly."
fi

# Create deployment directory
log "Creating deployment directory..."
mkdir -p "$DEPLOY_DIR"
success "Deployment directory created: $DEPLOY_DIR"

# Function to copy directory
copy_dir() {
    local src=$1
    local name=$2
    if [ -d "$src" ]; then
        log "Copying $name..."
        cp -r "$src" "$DEPLOY_DIR/" 2>>"$LOG_FILE"
        success "✓ Copied $name"
    else
        warning "⚠ Directory not found: $src"
    fi
}

# Function to copy file
copy_file() {
    local src=$1
    local name=$2
    if [ -f "$src" ]; then
        log "Copying $name..."
        cp "$src" "$DEPLOY_DIR/" 2>>"$LOG_FILE"
        success "✓ Copied $name"
    else
        warning "⚠ File not found: $src"
    fi
}

##############################################################################
# Copy Essential Directories
##############################################################################

log ""
log "=== Copying Essential Directories ==="

copy_dir "./controllers" "Business Logic (controllers)"
copy_dir "./models" "Data Models (models)"
copy_dir "./services" "Background Services (services)"
copy_dir "./utils" "Utility Modules (utils)"
copy_dir "./templates" "HTML Templates (templates)"
copy_dir "./static" "Static Assets (static)"
copy_dir "./ssl" "SSL Certificates (ssl)"

##############################################################################
# Copy Python Files and Requirements
##############################################################################

log ""
log "=== Copying Python Application Files ==="

copy_file "./app.py" "Main Application (app.py)"
copy_file "./requirements.txt" "Python Dependencies (requirements.txt)"

##############################################################################
# Copy Docker Configuration
##############################################################################

log ""
log "=== Copying Docker Configuration ==="

copy_file "./Dockerfile.rpi" "Docker Image (Dockerfile.rpi)"
copy_file "./docker-compose.rpi.yml" "Docker Compose (docker-compose.rpi.yml)"
copy_file "./.dockerignore" "Docker Ignore (.dockerignore)"
create_file "./docker-rpi-quickstart.sh" "Deployment Script (docker-rpi-quickstart.sh)"

if [ -f "./docker-rpi-quickstart.sh" ]; then
    chmod +x "$DEPLOY_DIR/docker-rpi-quickstart.sh"
    success "✓ Made deployment script executable"
fi

##############################################################################
# Copy Configuration Files
##############################################################################

log ""
log "=== Copying Configuration Files ==="

for config_file in config_*.py; do
    if [ -f "$config_file" ]; then
        cp "$config_file" "$DEPLOY_DIR/" 2>>"$LOG_FILE"
        success "✓ Copied $config_file"
    fi
done

##############################################################################
# Copy Data Files (Optional)
##############################################################################

log ""
log "=== Copying Data/Configuration Files ==="

copy_file "./devices.json" "Device Configuration (devices.json)"
copy_file "./saved_sequences.json" "Test Sequences (saved_sequences.json)"
copy_file "./log_patterns.json" "Log Patterns (log_patterns.json)"

##############################################################################
# Copy Documentation
##############################################################################

log ""
log "=== Copying Documentation ==="

for doc_file in DOCKER_RPI_*.md README_DOCKER_RPI.md; do
    if [ -f "$doc_file" ]; then
        cp "$doc_file" "$DEPLOY_DIR/" 2>>"$LOG_FILE"
        success "✓ Copied $doc_file"
    fi
done

copy_file "./USB_DEPLOYMENT_GUIDE.md" "USB Deployment Guide (USB_DEPLOYMENT_GUIDE.md)"

##############################################################################
# Create Deployment Manifest
##############################################################################

log ""
log "=== Creating Deployment Manifest ==="

MANIFEST="$DEPLOY_DIR/DEPLOYMENT_MANIFEST.txt"
cat > "$MANIFEST" << 'EOF'
================================
RDK Middleware Deployment Package
================================

Generated: $(date)
Platform: Raspberry Pi (ARM64)

REQUIRED DIRECTORIES:
✓ controllers/ - Business logic
✓ models/ - Data models
✓ services/ - Background services
✓ utils/ - Utility modules
✓ templates/ - HTML templates
✓ static/ - CSS, JavaScript, images
✓ ssl/ - SSL certificates (optional)

REQUIRED FILES:
✓ app.py - Main Flask application
✓ requirements.txt - Python dependencies
✓ config_*.py - Configuration files
✓ Dockerfile.rpi - Docker image definition
✓ docker-compose.rpi.yml - Docker compose configuration
✓ docker-rpi-quickstart.sh - Quick deployment script
✓ .dockerignore - Docker build optimization
✓ devices.json - Device configuration
✓ saved_sequences.json - Test sequences
✓ log_patterns.json - Log patterns

OPTIONAL FILES:
⚠ DOCKER_RPI_SETUP.md - Setup guide
⚠ DOCKER_RPI_QUICKSTART.md - Quick start guide
⚠ USB_DEPLOYMENT_GUIDE.md - This deployment guide

DEPLOYMENT INSTRUCTIONS:

1. On Target Raspberry Pi:
   - Insert USB drive
   - Mount USB: mkdir ~/usb && mount /dev/sda1 ~/usb
   - Copy files: cp -r ~/usb/rdk-middleware-deployment ~/
   - Enter directory: cd ~/rdk-middleware-deployment

2. Deploy using Docker:
   - Make script executable: chmod +x docker-rpi-quickstart.sh
   - Run deployment: sudo ./docker-rpi-quickstart.sh
   - Or use docker-compose: docker-compose -f docker-compose.rpi.yml up -d

3. Configure:
   - Edit devices.json for your device IPs
   - Update config_*.py files as needed
   - Set environment variables in docker-compose.rpi.yml

4. Access Application:
   - Open browser: http://your-rpi-ip:11078
   - Default login: (check your configuration)

TROUBLESHOOTING:
- Check /app/logs directory for application logs
- Use 'docker logs <container_id>' for Docker logs
- Ensure devices.json has correct IP addresses
- Verify SSH connectivity to target devices

Generated on: $(date)
EOF

success "✓ Created deployment manifest"

##############################################################################
# Create Quick Start Script for Target Pi
##############################################################################

log ""
log "=== Creating Target Quick Start Script ==="

QUICKSTART="$DEPLOY_DIR/QUICKSTART_ON_PI.sh"
cat > "$QUICKSTART" << 'EOF'
#!/bin/bash
# Quick startup script for Raspberry Pi

echo "🚀 RDK Middleware Quick Start"
echo "=============================="

# Check Docker installation
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not installed. Installing Docker..."
    sudo apt-get update
    sudo apt-get install -y docker.io docker-compose
fi

# Build and run
echo "🔨 Building Docker image..."
sudo docker build -f Dockerfile.rpi -t rdk-middleware:rpi .

echo "🚀 Starting application..."
sudo docker-compose -f docker-compose.rpi.yml up -d

echo "⏳ Waiting for application to start..."
sleep 10

# Check if running
if sudo docker ps | grep -q rdk-middleware; then
    echo "✅ Application is running!"
    echo "🌐 Access at: http://$(hostname -I | awk '{print $1}'):11078"
else
    echo "❌ Application failed to start. Check logs:"
    sudo docker logs$(sudo docker ps -aq -f "ancestor=rdk-middleware:rpi")
fi
EOF

chmod +x "$QUICKSTART"
success "✓ Created quick start script (QUICKSTART_ON_PI.sh)"

##############################################################################
# Calculate Size and Statistics
##############################################################################

log ""
log "=== Deployment Package Statistics ==="

TOTAL_SIZE=$(du -sh "$DEPLOY_DIR" | cut -f1)
FILE_COUNT=$(find "$DEPLOY_DIR" -type f | wc -l)
DIR_COUNT=$(find "$DEPLOY_DIR" -type d | wc -l)

success "✓ Total size: $TOTAL_SIZE"
success "✓ Files: $FILE_COUNT"
success "✓ Directories: ($DIR_COUNT directories)"

# USB Free Space
log ""
log "Checking USB free space..."
USB_SPACE=$(df -h "$USB_PATH" | awk 'NR==2 {print $4}')
success "Available space on USB: $USB_SPACE"

##############################################################################
# Create Summary Report
##############################################################################

log ""
log "=== Creating Summary Report ==="

SUMMARY="$USB_PATH/DEPLOYMENT_SUMMARY_$TIMESTAMP.txt"
cat > "$SUMMARY" << EOF
╔════════════════════════════════════════════════════════════════╗
║     RDK MIDDLEWARE - USB DEPLOYMENT PREPARATION REPORT        ║
╚════════════════════════════════════════════════════════════════╝

DEPLOYMENT COMPLETED: $(date)
Preparation Duration: $SECONDS seconds

DEPLOYMENT PACKAGE LOCATION:
  $DEPLOY_DIR

PACKAGE CONTENTS:
  - Total Size: $TOTAL_SIZE
  - Files: $FILE_COUNT
  - Directories: $DIR_COUNT
  - USB Free Space: $USB_SPACE

INCLUDED COMPONENTS:
  ✓ Application Code (controllers, models, services, utils)
  ✓ User Interface (templates, static assets)
  ✓ Docker Configuration (Dockerfile, docker-compose, scripts)
  ✓ Python Dependencies (requirements.txt)
  ✓ Configuration Files (config_*.py, *.json)
  ✓ Documentation (guides, manifests)
  ✓ Deployment Scripts (quickstart, utilities)

NEXT STEPS ON RASPBERRY PI:
  1. Insert USB drive into Raspberry Pi
  2. Mount USB: mkdir ~/usb && sudo mount /dev/sda1 ~/usb
  3. Copy to home: cp -r ~/usb/rdk-middleware-deployment ~/
  4. Navigate: cd ~/rdk-middleware-deployment
  5. Deploy: sudo ./docker-rpi-quickstart.sh
  
  OR use manually:
  - sudo docker build -f Dockerfile.rpi -t rdk-middleware:rpi .
  - sudo docker-compose -f docker-compose.rpi.yml up -d

CONFIGURATION REQUIRED:
  1. devices.json - Update device IP addresses
  2. config_ssh_connection.py - Configure SSH settings
  3. docker-compose.rpi.yml - Set environment variables
  4. config_email.py - Configure email settings (optional)

SUPPORT:
  - See USB_DEPLOYMENT_GUIDE.md for detailed instructions
  - Check DEPLOYMENT_MANIFEST.txt for file listing
  - Review DOCKER_RPI_QUICKSTART.md for Docker specifics
  - Access logs at: /app/logs (inside container)

Generated: $(date)
═══════════════════════════════════════════════════════════════
EOF

log ""
success "✓ Summary report created: $SUMMARY"

##############################################################################
# Final Report
##############################################################################

log ""
log "╔════════════════════════════════════════════════════════════════╗"
log "║         ✅ USB DEPLOYMENT PREPARATION COMPLETE                ║"
log "╚════════════════════════════════════════════════════════════════╝"
log ""
log "📦 Package Location: $DEPLOY_DIR"
log "📊 Package Size: $TOTAL_SIZE"
log "📋 Files Included: $FILE_COUNT"
log "📁 USB Free Space: $USB_SPACE"
log "📝 Log File: $LOG_FILE"
log "📄 Summary Report: $SUMMARY"
log ""
log "🚀 NEXT STEPS:"
log "   1. Safely eject USB"
log "   2. Insert USB into target Raspberry Pi"
log "   3. Mount and copy to Pi home directory"
log "   4. Run: cd ~/rdk-middleware-deployment && sudo ./docker-rpi-quickstart.sh"
log ""
log "📖 For detailed instructions, see: USB_DEPLOYMENT_GUIDE.md"
log ""

# Create a checklist file
CHECKLIST="$USB_PATH/PRE_DEPLOYMENT_CHECKLIST.txt"
cat > "$CHECKLIST" << 'EOF'
═══════════════════════════════════════════════════════════════
PRE-DEPLOYMENT CHECKLIST FOR RASPBERRY PI
═══════════════════════════════════════════════════════════════

BEFORE DEPLOYMENT:
❏ Verify Raspberry Pi is connected to network (Ethernet recommended)
❏ Ensure Raspberry Pi has Docker installed
❏ Check available storage (minimum 50GB recommended)
❏ Ensure power supply is stable (5V 3A minimum)
❏ Test SSH access to target devices

DEPLOYMENT ON PI:
❏ Mount USB drive
❏ Copy deployment files to home directory
❏ Make deployment script executable (chmod +x *.sh)
❏ Update devices.json with target device IPs
❏ Configure config_*.py files as needed
❏ Edit docker-compose.rpi.yml environment variables

DEPLOYMENT EXECUTION:
❏ Run deployment script (./docker-rpi-quickstart.sh)
❏ Monitor Docker build process
❏ Check container logs after startup
❏ Verify web interface is accessible (http://pi-ip:11078)
❏ Test device connection in web UI

POST-DEPLOYMENT:
❏ Verify all devices show online status
❏ Test running a simple method on each device
❏ Check iteration logs are being created
❏ Verify screenshots are being captured
❏ Monitor system resources (CPU, memory, disk)
❏ Set up log rotation to prevent disk fill

TROUBLESHOOTING:
❏ If Docker build fails:
  - Check internet connection
  - Verify package availability for ARM64
  - Check disk space (minimum 30GB free)
  
❏ If application won't start:
  - Check Docker logs: docker logs <container_id>
  - Verify port 11078 is not in use
  - Check environment variables in docker-compose.rpi.yml
  
❏ If devices show offline:
  - Verify device IPs in devices.json
  - Check SSH connectivity: ssh user@device_ip
  - Verify SSH port (default 10022)

═══════════════════════════════════════════════════════════════
EOF

success "✓ Pre-deployment checklist created"
log ""
log "All preparation files are ready on USB! 🎉"
EOF
chmod +x /home/lrqa/Desktop/viswa/Latest_Enhancement/Enhancement/prepare-usb-deployment.sh
```

Wait, I made an error. Let me create the script correctly:
</thinking>

Now let me create the automated USB preparation script:
<function_calls>
<invoke name="create_file">
<parameter name="content">#!/bin/bash

##############################################################################
# RDK Middleware Deployment - USB Preparation Script
# Purpose: Prepare all necessary files for Raspberry Pi deployment on USB
# Usage: sudo ./prepare-usb-deployment.sh /mnt/usb
##############################################################################

set -e

# Configuration
USB_PATH="${1:-.}"
DEPLOY_DIR="$USB_PATH/rdk-middleware-deployment"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$USB_PATH/deployment_prep_$TIMESTAMP.log"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

success() {
    echo -e "${GREEN}[✓]${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[⚠]${NC} $1" | tee -a "$LOG_FILE"
}

##############################################################################
# Main Deployment Preparation
##############################################################################

log "=== RDK Middleware USB Deployment Preparation ==="
log "Target USB: $USB_PATH"
log "Deployment Directory: $DEPLOY_DIR"
log "Logging to: $LOG_FILE"

# Check if USB path exists and is writable
if [ ! -d "$USB_PATH" ]; then
    error "USB path does not exist: $USB_PATH"
fi

if [ ! -w "$USB_PATH" ]; then
    error "USB path is not writable. Please check permissions or mount the USB correctly."
fi

# Create deployment directory
log "Creating deployment directory..."
mkdir -p "$DEPLOY_DIR"
success "Deployment directory created: $DEPLOY_DIR"

# Function to copy directory
copy_dir() {
    local src=$1
    local name=$2
    if [ -d "$src" ]; then
        log "Copying $name..."
        cp -r "$src" "$DEPLOY_DIR/" 2>>"$LOG_FILE"
        success "Copied $name"
    else
        warning "Directory not found: $src"
    fi
}

# Function to copy file
copy_file() {
    local src=$1
    local name=$2
    if [ -f "$src" ]; then
        log "Copying $name..."
        cp "$src" "$DEPLOY_DIR/" 2>>"$LOG_FILE"
        success "Copied $name"
    else
        warning "File not found: $src"
    fi
}

##############################################################################
# Copy Essential Directories
##############################################################################

log ""
log "=== Copying Essential Directories ==="

copy_dir "./controllers" "Business Logic (controllers)"
copy_dir "./models" "Data Models (models)"
copy_dir "./services" "Background Services (services)"
copy_dir "./utils" "Utility Modules (utils)"
copy_dir "./templates" "HTML Templates (templates)"
copy_dir "./static" "Static Assets (static)"

##############################################################################
# Copy Python Files and Requirements
##############################################################################

log ""
log "=== Copying Python Application Files ==="

copy_file "./app.py" "Main Application (app.py)"
copy_file "./requirements.txt" "Python Dependencies (requirements.txt)"

##############################################################################
# Copy Docker Configuration
##############################################################################

log ""
log "=== Copying Docker Configuration ==="

copy_file "./Dockerfile.rpi" "Docker Image (Dockerfile.rpi)"
copy_file "./docker-compose.rpi.yml" "Docker Compose (docker-compose.rpi.yml)"
copy_file "./.dockerignore" "Docker Ignore (.dockerignore)"

##############################################################################
# Copy Configuration Files
##############################################################################

log ""
log "=== Copying Configuration Files ==="

for config_file in config_*.py; do
    if [ -f "$config_file" ]; then
        cp "$config_file" "$DEPLOY_DIR/" 2>>"$LOG_FILE"
        success "Copied $config_file"
    fi
done

##############################################################################
# Copy Data Files (Optional)
##############################################################################

log ""
log "=== Copying Data/Configuration Files ==="

copy_file "./devices.json" "Device Configuration (devices.json)"
copy_file "./saved_sequences.json" "Test Sequences (saved_sequences.json)"
copy_file "./log_patterns.json" "Log Patterns (log_patterns.json)"

##############################################################################
# Copy Documentation
##############################################################################

log ""
log "=== Copying Documentation ==="

for doc_file in DOCKER_RPI_*.md README_DOCKER_RPI.md; do
    if [ -f "$doc_file" ]; then
        cp "$doc_file" "$DEPLOY_DIR/" 2>>"$LOG_FILE"
        success "Copied $doc_file"
    fi
done

copy_file "./USB_DEPLOYMENT_GUIDE.md" "USB Deployment Guide"

##############################################################################
# Calculate Size and Statistics
##############################################################################

log ""
log "=== Deployment Package Statistics ==="

TOTAL_SIZE=$(du -sh "$DEPLOY_DIR" | cut -f1)
FILE_COUNT=$(find "$DEPLOY_DIR" -type f | wc -l)

success "Total size: $TOTAL_SIZE"
success "Files: $FILE_COUNT"

# USB Free Space
USB_SPACE=$(df -h "$USB_PATH" | awk 'NR==2 {print $4}')
success "Available space on USB: $USB_SPACE"

##############################################################################
# Final Report
##############################################################################

log ""
log "╔════════════════════════════════════════════════════════════════╗"
log "║         ✅ USB DEPLOYMENT PREPARATION COMPLETE                ║"
log "╚════════════════════════════════════════════════════════════════╝"
log ""
log "📦 Package Location: $DEPLOY_DIR"
log "📊 Package Size: $TOTAL_SIZE"
log "📋 Files Included: $FILE_COUNT"
log "📁 USB Free Space: $USB_SPACE"
log ""
log "🚀 NEXT STEPS:"
log "   1. Safely eject USB"
log "   2. Insert USB into target Raspberry Pi"
log "   3. Mount USB and copy files to home directory"
log "   4. Run deployment from the copied directory"
log ""

success "Preparation complete! See $LOG_FILE for details."
