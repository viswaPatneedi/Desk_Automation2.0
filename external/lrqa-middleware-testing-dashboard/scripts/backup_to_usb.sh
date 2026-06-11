#!/bin/bash

#####################################################
# Backup Script for Flask RDK Device Manager
# Backs up essential application files to USB stick
#####################################################

set -e

echo "=========================================="
echo "Application Backup Script"
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

# Get current directory
SOURCE_DIR=$(pwd)
APP_NAME="RDK_Device_Manager"

# Auto-detect USB mount point (prioritize Lexar)
USB_MOUNT=$(df -h | grep -i "lexar\|/media/pi" | awk '{print $6}' | head -1)

if [ -z "$USB_MOUNT" ]; then
    print_error "No USB drive detected. Please insert USB drive and try again."
    echo "Available mount points:"
    df -h | grep -E "/media|/mnt"
    exit 1
fi

print_info "USB drive detected at: $USB_MOUNT"

# Create backup directory with timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="$USB_MOUNT/${APP_NAME}_Backup_$TIMESTAMP"

print_info "Creating backup directory: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

# Create subdirectories
mkdir -p "$BACKUP_DIR/app"
mkdir -p "$BACKUP_DIR/config"
mkdir -p "$BACKUP_DIR/data"
mkdir -p "$BACKUP_DIR/docs"

echo ""
echo "Starting backup..."

# Backup main application files
print_info "Backing up application files..."
cp app.py "$BACKUP_DIR/app/" 2>/dev/null || true
cp app_old.py "$BACKUP_DIR/app/" 2>/dev/null || true
cp session_utils.py "$BACKUP_DIR/app/" 2>/dev/null || true
cp -r controllers "$BACKUP_DIR/app/" 2>/dev/null || true
cp -r models "$BACKUP_DIR/app/" 2>/dev/null || true
cp -r services "$BACKUP_DIR/app/" 2>/dev/null || true
cp -r templates "$BACKUP_DIR/app/" 2>/dev/null || true
cp -r static "$BACKUP_DIR/app/" 2>/dev/null || true
print_status "Application files backed up"

# Backup method files
print_info "Backing up method files..."
cp method_*.py "$BACKUP_DIR/app/" 2>/dev/null || true
print_status "Method files backed up"

# Backup utility files
print_info "Backing up utility files..."
cp screenshot_utils.py "$BACKUP_DIR/app/" 2>/dev/null || true
cp screen_validation_utils.py "$BACKUP_DIR/app/" 2>/dev/null || true
cp screen_validator_lightweight.py "$BACKUP_DIR/app/" 2>/dev/null || true
cp ai_vision_ocr.py "$BACKUP_DIR/app/" 2>/dev/null || true
print_status "Utility files backed up"

# Backup configuration files
print_info "Backing up configuration files..."
cp config_*.py "$BACKUP_DIR/config/" 2>/dev/null || true
cp ir_keycodes.json "$BACKUP_DIR/config/" 2>/dev/null || true
cp reset_codes.json "$BACKUP_DIR/config/" 2>/dev/null || true
print_status "Configuration files backed up"

# Backup data files
print_info "Backing up data files..."
cp devices.json "$BACKUP_DIR/data/" 2>/dev/null || true
cp users.json "$BACKUP_DIR/data/" 2>/dev/null || true
cp jobs.json "$BACKUP_DIR/data/" 2>/dev/null || true
cp saved_sequences.json "$BACKUP_DIR/data/" 2>/dev/null || true
cp device_job_queue.json "$BACKUP_DIR/data/" 2>/dev/null || true
cp app_state.json "$BACKUP_DIR/data/" 2>/dev/null || true
cp test_results_history.json "$BACKUP_DIR/data/" 2>/dev/null || true
print_status "Data files backed up"

# Backup requirements and scripts
print_info "Backing up installation files..."
cp requirements.txt "$BACKUP_DIR/" 2>/dev/null || true
cp install_complete_system.sh "$BACKUP_DIR/" 2>/dev/null || true
cp install_service.sh "$BACKUP_DIR/" 2>/dev/null || true
cp install_screen_validation.sh "$BACKUP_DIR/" 2>/dev/null || true
cp setup_*.sh "$BACKUP_DIR/" 2>/dev/null || true
cp run_production.sh "$BACKUP_DIR/" 2>/dev/null || true
cp run_production_https.sh "$BACKUP_DIR/" 2>/dev/null || true
cp *.service "$BACKUP_DIR/" 2>/dev/null || true
print_status "Installation files backed up"

# Backup documentation
print_info "Backing up documentation..."
cp README.md "$BACKUP_DIR/docs/" 2>/dev/null || true
cp *.md "$BACKUP_DIR/docs/" 2>/dev/null || true
print_status "Documentation backed up"

# Backup base images if they exist
if [ -d "base_images" ] && [ "$(ls -A base_images)" ]; then
    print_info "Backing up base images..."
    mkdir -p "$BACKUP_DIR/base_images"
    cp -r base_images/* "$BACKUP_DIR/base_images/" 2>/dev/null || true
    print_status "Base images backed up"
fi

# Create a backup info file
cat > "$BACKUP_DIR/BACKUP_INFO.txt" << EOF
========================================
RDK Device Manager Backup Information
========================================

Backup Date: $(date)
Source Directory: $SOURCE_DIR
Backup Location: $BACKUP_DIR

========================================
Installation Instructions
========================================

1. Copy this backup folder to your new Raspberry Pi
2. Extract/navigate to the backup directory
3. Run: chmod +x install_complete_system.sh
4. Run: ./install_complete_system.sh
5. Copy configuration and data files:
   - cp config/* ./
   - cp data/* ./
6. Start the application:
   - source venv/bin/activate
   - python3 app.py

========================================
Contents
========================================

/app/               - Main application files
/config/            - Configuration files
/data/              - JSON data files (devices, users, jobs)
/docs/              - Documentation
/base_images/       - Baseline images for validation
requirements.txt    - Python dependencies
install_complete_system.sh - Installation script
*.service           - Systemd service files

========================================
Notes
========================================

- All SSH credentials are stored in data/devices.json
- User passwords are in data/users.json
- Modify config files as needed for your environment
- Default port: 5000 (HTTP), 5443 (HTTPS)
- SSH default port: 10022

EOF

print_status "Backup info file created"

# Calculate backup size
BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)

echo ""
echo "=========================================="
echo "Backup Complete!"
echo "=========================================="
echo ""
echo "Backup Location: $BACKUP_DIR"
echo "Backup Size: $BACKUP_SIZE"
echo ""
echo "To restore on a new Raspberry Pi:"
echo "1. Copy the backup folder to the new device"
echo "2. cd into the backup folder"
echo "3. Run: chmod +x install_complete_system.sh"
echo "4. Run: ./install_complete_system.sh"
echo ""
print_status "Backup completed successfully!"

# Create a "latest" symlink for convenience
LATEST_LINK="$USB_MOUNT/${APP_NAME}_Backup_Latest"
rm -f "$LATEST_LINK"
ln -s "$BACKUP_DIR" "$LATEST_LINK" 2>/dev/null || true

if [ -L "$LATEST_LINK" ]; then
    print_status "Latest backup symlink created at: $LATEST_LINK"
fi
