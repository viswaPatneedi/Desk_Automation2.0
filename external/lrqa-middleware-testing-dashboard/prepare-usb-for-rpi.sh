#!/bin/bash

###############################################################################
# USB Deployment Preparation Script
# Purpose: Automatically copy all necessary files from project to USB stick
# Usage: ./prepare-usb-for-rpi.sh /mnt/usb
# Author: RDK Middleware Team
# Date: April 2026
###############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SOURCE_DIR="$(pwd)"
USB_MOUNT_POINT="${1:-.}/usb-deployment"
DEPLOYMENT_DIR="$USB_MOUNT_POINT/rdk-middleware-deployment"

# Functions
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}→ $1${NC}"
}

# Check if running from correct directory
check_environment() {
    print_header "Checking Environment"
    
    if [ ! -f "app.py" ]; then
        print_error "app.py not found in current directory!"
        print_info "Please run this script from the Enhancement directory"
        print_info "Usage: cd /home/lrqa/Desktop/viswa/Latest_Enhancement/Enhancement && ./prepare-usb-for-rpi.sh /mnt/usb"
        exit 1
    fi
    
    print_success "app.py found - correct directory"
    
    if [ ! -d "controllers" ] || [ ! -d "models" ] || [ ! -d "services" ]; then
        print_error "Required directories not found!"
        exit 1
    fi
    
    print_success "All required directories present"
}

# Create deployment directory structure
create_deployment_structure() {
    print_header "Creating Deployment Directory Structure"
    
    print_info "Creating: $DEPLOYMENT_DIR"
    mkdir -p "$DEPLOYMENT_DIR"
    
    print_success "Deployment directory created"
}

# Copy main application files
copy_main_files() {
    print_header "Copying Main Application Files"
    
    local files=(
        "app.py"
        "requirements.txt"
        "Dockerfile.rpi"
        "docker-compose.rpi.yml"
        "docker-rpi-quickstart.sh"
        ".dockerignore"
    )
    
    for file in "${files[@]}"; do
        if [ -f "$file" ]; then
            cp "$file" "$DEPLOYMENT_DIR/"
            print_success "Copied: $file"
        else
            print_warning "Not found: $file (skipping)"
        fi
    done
}

# Copy directories
copy_directories() {
    print_header "Copying Code Directories"
    
    local dirs=(
        "controllers"
        "models"
        "services"
        "utils"
        "templates"
        "static"
    )
    
    for dir in "${dirs[@]}"; do
        if [ -d "$dir" ]; then
            cp -r "$dir" "$DEPLOYMENT_DIR/"
            local file_count=$(find "$DEPLOYMENT_DIR/$dir" -type f | wc -l)
            print_success "Copied: $dir ($file_count files)"
        else
            print_warning "Directory not found: $dir (skipping)"
        fi
    done
}

# Copy configuration files
copy_config_files() {
    print_header "Copying Configuration Files"
    
    local config_files=$(find . -maxdepth 1 -name "config_*.py" -type f)
    local count=0
    
    for config in $config_files; do
        cp "$config" "$DEPLOYMENT_DIR/"
        count=$((count + 1))
    done
    
    print_success "Copied $count config files"
}

# Copy optional configuration files
copy_optional_files() {
    print_header "Copying Optional Configuration Files"
    
    local optional_files=(
        "devices.json"
        "saved_sequences.json"
        "log_patterns.json"
        "system_commands.json"
        "ir_keycodes.json"
    )
    
    for file in "${optional_files[@]}"; do
        if [ -f "$file" ]; then
            cp "$file" "$DEPLOYMENT_DIR/"
            print_success "Copied: $file"
        else
            print_warning "Optional file not found: $file"
        fi
    done
}

# Copy documentation
copy_documentation() {
    print_header "Copying Documentation"
    
    local doc_files=$(find . -maxdepth 1 -name "DOCKER_RPI*.md" -o -name "USB*.md" -o -name "README_RPi*.md")
    local count=0
    
    for doc in $doc_files; do
        if [ -f "$doc" ]; then
            cp "$doc" "$DEPLOYMENT_DIR/"
            count=$((count + 1))
        fi
    done
    
    if [ $count -gt 0 ]; then
        print_success "Copied $count documentation files"
    else
        print_warning "No documentation files found (optional)"
    fi
    
    # Copy the complete guide we just created
    if [ -f "USB_TO_RPi_COMPLETE_GUIDE.md" ]; then
        cp "USB_TO_RPi_COMPLETE_GUIDE.md" "$DEPLOYMENT_DIR/"
        print_success "Copied: USB_TO_RPi_COMPLETE_GUIDE.md"
    fi
}

# Exclude unnecessary files
create_exclude_list() {
    print_header "Verifying Excluded Files"
    
    # Check that excluded directories were NOT copied
    local excluded_dirs=(
        "venv"
        ".git"
        "__pycache__"
        "node_modules"
        "logs"
        "screenshots"
        "iteration_logs"
        "device_logs"
        "backups"
        "updated_code"
        "SAM-CD-2GB"
    )
    
    local excluded_count=0
    for dir in "${excluded_dirs[@]}"; do
        if [ -d "$DEPLOYMENT_DIR/$dir" ]; then
            print_warning "Found excluded directory: $dir (should be removed)"
            rm -rf "$DEPLOYMENT_DIR/$dir"
            excluded_count=$((excluded_count + 1))
        fi
    done
    
    print_success "Excluded directories verified"
}

# Verify file counts and sizes
verify_deployment() {
    print_header "Verifying Deployment Contents"
    
    # Count files
    local file_count=$(find "$DEPLOYMENT_DIR" -type f | wc -l)
    print_info "Total files: $file_count"
    
    # Count directories
    local dir_count=$(find "$DEPLOYMENT_DIR" -type d | wc -l)
    print_info "Total directories: $dir_count"
    
    # Check for critical files
    local critical=(
        "app.py"
        "requirements.txt"
        "Dockerfile.rpi"
        "docker-compose.rpi.yml"
    )
    
    local missing=0
    for file in "${critical[@]}"; do
        if [ ! -f "$DEPLOYMENT_DIR/$file" ]; then
            print_error "CRITICAL: Missing $file"
            missing=$((missing + 1))
        fi
    done
    
    if [ $missing -eq 0 ]; then
        print_success "All critical files present"
    else
        print_error "$missing critical files missing!"
        exit 1
    fi
    
    # Check for critical directories
    local critical_dirs=("controllers" "models" "services" "templates" "static")
    missing=0
    for dir in "${critical_dirs[@]}"; do
        if [ ! -d "$DEPLOYMENT_DIR/$dir" ]; then
            print_error "CRITICAL: Missing directory $dir"
            missing=$((missing + 1))
        fi
    done
    
    if [ $missing -eq 0 ]; then
        print_success "All critical directories present"
    else
        print_error "$missing critical directories missing!"
        exit 1
    fi
    
    # Calculate total size
    local total_size=$(du -sh "$DEPLOYMENT_DIR" | cut -f1)
    print_info "Total deployment size: $total_size"
    
    print_success "Deployment verification complete!"
}

# Display summary and next steps
show_summary() {
    print_header "Deployment Ready!"
    
    echo ""
    echo -e "${GREEN}✓ Files prepared successfully!${NC}"
    echo ""
    echo "Deployment Location: $DEPLOYMENT_DIR"
    echo ""
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "1. Safely eject USB:"
    echo "   sudo umount $USB_MOUNT_POINT"
    echo "   sudo eject /dev/sda1"
    echo ""
    echo "2. Insert USB into Raspberry Pi"
    echo ""
    echo "3. On Raspberry Pi, follow: USB_TO_RPi_COMPLETE_GUIDE.md"
    echo ""
    echo -e "${BLUE}Quick Start on Pi:${NC}"
    echo "  cd ~ && cp -r /mnt/usb/rdk-middleware-deployment ~/rdk-app"
    echo "  cd ~/rdk-app && cat USB_TO_RPi_COMPLETE_GUIDE.md | head -50"
    echo ""
}

# Main execution
main() {
    clear
    
    print_header "RDK Middleware - USB Deployment Preparation"
    echo ""
    echo "This script will prepare all necessary files for Raspberry Pi deployment"
    echo "Source directory: $SOURCE_DIR"
    echo "Deployment directory: $DEPLOYMENT_DIR"
    echo ""
    
    read -p "Continue? (y/n) " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "Operation cancelled"
        exit 0
    fi
    
    echo ""
    
    check_environment
    create_deployment_structure
    copy_main_files
    copy_directories
    copy_config_files
    copy_optional_files
    copy_documentation
    create_exclude_list
    verify_deployment
    
    echo ""
    
    # Ask about syncing USB
    read -p "Sync USB stick to ensure all data is written? (y/n) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Syncing USB..."
        sync
        print_success "USB sync complete"
    fi
    
    echo ""
    show_summary
}

# Run main function
main "$@"
