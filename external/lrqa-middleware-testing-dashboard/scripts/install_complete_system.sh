#!/bin/bash

#####################################################
# Complete System Installation Script for Flask RDK Device Manager
# This script installs all dependencies and sets up the application
# on a fresh Raspberry Pi
#####################################################

set -e  # Exit on any error

echo "=========================================="
echo "Flask RDK Device Manager - Complete Setup"
echo "=========================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

print_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    print_error "Please do not run this script as root or with sudo"
    echo "The script will ask for sudo password when needed"
    exit 1
fi

echo "Step 1: Updating system packages..."
sudo apt-get update
print_status "System package list updated"

echo ""
echo "Step 2: Installing system dependencies..."

# Install Python 3 and pip if not present
if ! command -v python3 &> /dev/null; then
    print_info "Installing Python 3..."
    sudo apt-get install -y python3 python3-pip python3-venv
else
    print_status "Python 3 is already installed ($(python3 --version))"
fi

# Install Tesseract OCR for screenshot text recognition
if ! command -v tesseract &> /dev/null; then
    print_info "Installing Tesseract OCR..."
    sudo apt-get install -y tesseract-ocr libtesseract-dev
else
    print_status "Tesseract OCR is already installed"
fi

# Install image processing libraries
print_info "Installing image processing libraries..."
sudo apt-get install -y libjpeg-dev zlib1g-dev libpng-dev

# Install OpenSSL for secure connections
print_info "Installing OpenSSL and security libraries..."
sudo apt-get install -y openssl libssl-dev

# Install networking tools
print_info "Installing networking tools..."
sudo apt-get install -y net-tools curl wget

# Install git if not present
if ! command -v git &> /dev/null; then
    print_info "Installing Git..."
    sudo apt-get install -y git
else
    print_status "Git is already installed"
fi

print_status "All system dependencies installed"

echo ""
echo "Step 3: Setting up Python virtual environment..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    print_info "Creating virtual environment..."
    python3 -m venv venv
    print_status "Virtual environment created"
else
    print_status "Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate
print_status "Virtual environment activated"

echo ""
echo "Step 4: Upgrading pip and installing Python packages..."
pip install --upgrade pip setuptools wheel
print_status "Pip upgraded"

# Install Python requirements
if [ -f "requirements.txt" ]; then
    print_info "Installing Python packages from requirements.txt..."
    pip install -r requirements.txt
    print_status "All Python packages installed"
else
    print_error "requirements.txt not found!"
    exit 1
fi

echo ""
echo "Step 5: Setting up application directories..."

# Create necessary directories
mkdir -p screenshots
mkdir -p iteration_logs
mkdir -p base_images
mkdir -p templates
mkdir -p controllers
mkdir -p models
mkdir -p services
mkdir -p static/css
mkdir -p static/js

print_status "Application directories created"

echo ""
echo "Step 6: Setting up configuration files..."

# Check if critical configuration files exist
REQUIRED_FILES=(
    "devices.json"
    "users.json"
    "jobs.json"
    "saved_sequences.json"
    "config_commands.py"
    "config_timing.py"
    "config_screenshot.py"
    "config_log_patterns.py"
    "config_ir_blaster.py"
)

missing_files=0
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        print_warning "Missing: $file (will be created on first run)"
        missing_files=$((missing_files + 1))
    fi
done

if [ $missing_files -eq 0 ]; then
    print_status "All configuration files present"
fi

echo ""
echo "Step 7: Setting file permissions..."
chmod +x *.sh 2>/dev/null || true
chmod +x method_*.py 2>/dev/null || true
print_status "Executable permissions set"

echo ""
echo "Step 8: Setting up systemd service (optional)..."
read -p "Do you want to install the systemd service for auto-start? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -f "install_service.sh" ]; then
        bash install_service.sh
        print_status "Systemd service installed"
    else
        print_warning "install_service.sh not found, skipping service installation"
    fi
else
    print_info "Skipping systemd service installation"
fi

echo ""
echo "Step 9: Verifying installation..."

# Test imports
python3 -c "import flask, paramiko, PIL, pytesseract, bcrypt" 2>/dev/null
if [ $? -eq 0 ]; then
    print_status "All Python modules can be imported successfully"
else
    print_error "Some Python modules failed to import"
    exit 1
fi

# Check Tesseract
if tesseract --version &> /dev/null; then
    print_status "Tesseract OCR is working"
else
    print_warning "Tesseract OCR may not be properly configured"
fi

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Configure devices in devices.json"
echo "3. Run the application:"
echo "   - Development: python3 app.py"
echo "   - Production: bash run_production.sh"
echo ""
echo "Access the application at: http://localhost:5000"
echo ""

# Deactivate virtual environment
deactivate 2>/dev/null || true

print_status "Installation script completed successfully!"
