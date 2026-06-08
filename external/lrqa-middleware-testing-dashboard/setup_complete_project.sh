#!/bin/bash
#############################################################################
# Complete Project Setup Script for Raspberry Pi
# Device Testing & Management Application - Full Installation
#############################################################################

set -e  # Exit on any error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "========================================================================="
echo "  Device Testing & Management Application - Full Setup"
echo "  For Raspberry Pi (ARM64/aarch64)"
echo "========================================================================="
echo -e "${NC}"

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo -e "${RED}Please do not run this script as root/sudo${NC}"
    exit 1
fi

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check architecture
ARCH=$(uname -m)
if [[ "$ARCH" != "aarch64" && "$ARCH" != "arm64" ]]; then
    echo -e "${YELLOW}Warning: This script is optimized for ARM64 architecture${NC}"
    echo -e "${YELLOW}Current architecture: $ARCH${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}Architecture: $ARCH${NC}"
echo ""

#############################################################################
# STEP 1: System Updates and Dependencies
#############################################################################

echo -e "${BLUE}[1/10] Updating system packages...${NC}"
sudo apt-get update
echo -e "${GREEN}✓ System updated${NC}"
echo ""

echo -e "${BLUE}[2/10] Installing system dependencies...${NC}"
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    git \
    curl \
    wget \
    libssl-dev \
    libffi-dev \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    libfreetype6-dev \
    libopenblas-dev \
    liblapack-dev \
    gfortran \
    libhdf5-dev \
    openssh-client \
    rsync

echo -e "${GREEN}✓ System dependencies installed${NC}"
echo ""

#############################################################################
# STEP 2: Python Virtual Environment
#############################################################################

echo -e "${BLUE}[3/10] Setting up Python virtual environment...${NC}"

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}Python version: $PYTHON_VERSION${NC}"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${YELLOW}Virtual environment already exists${NC}"
fi

# Activate virtual environment
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo ""

#############################################################################
# STEP 3: Upgrade pip and setuptools
#############################################################################

echo -e "${BLUE}[4/10] Upgrading pip and setuptools...${NC}"
pip install --upgrade pip setuptools wheel
echo -e "${GREEN}✓ pip and setuptools upgraded${NC}"
echo ""

#############################################################################
# STEP 4: Core Python Dependencies
#############################################################################

echo -e "${BLUE}[5/10] Installing core Python packages...${NC}"

# Install from requirements.txt if it exists
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo -e "${GREEN}✓ Installed from requirements.txt${NC}"
else
    # Install core packages manually
    echo "Installing core packages..."
    
    # Flask and web dependencies
    pip install Flask==3.0.0
    pip install Flask-SocketIO==5.3.5
    pip install python-socketio==5.10.0
    
    # SSH and networking
    pip install paramiko==3.4.0
    pip install requests==2.31.0
    
    # Image processing
    pip install Pillow==10.1.0
    pip install opencv-python==4.8.1.78
    
    # Data processing
    pip install numpy==1.24.3
    pip install pandas==2.0.3
    
    # Utilities
    pip install python-dateutil==2.8.2
    pip install pytz==2023.3
    
    echo -e "${GREEN}✓ Core packages installed${NC}"
fi
echo ""

#############################################################################
# STEP 5: OCR Dependencies (if needed)
#############################################################################

echo -e "${BLUE}[6/10] Installing OCR dependencies...${NC}"

# Check if Tesseract is needed
if grep -q "tesseract\|pytesseract" requirements.txt 2>/dev/null || [ -f "ai_vision_ocr.py" ]; then
    sudo apt-get install -y tesseract-ocr tesseract-ocr-eng
    pip install pytesseract
    echo -e "${GREEN}✓ Tesseract OCR installed${NC}"
else
    echo -e "${YELLOW}Tesseract OCR not required, skipping...${NC}"
fi
echo ""

#############################################################################
# STEP 6: Additional Python Packages
#############################################################################

echo -e "${BLUE}[7/10] Installing additional Python packages...${NC}"

# Email support
pip install secure-smtplib || echo "secure-smtplib already installed or not needed"

# JSON and data handling
pip install jsonschema || echo "jsonschema already installed or not needed"

# Logging and monitoring
pip install colorlog || echo "colorlog already installed or not needed"

# Testing utilities
pip install pytest pytest-cov || echo "pytest already installed or not needed"

echo -e "${GREEN}✓ Additional packages installed${NC}"
echo ""

#############################################################################
# STEP 7: Screen Validation - Lightweight Alternative
#############################################################################

echo -e "${BLUE}[8/10] Installing lightweight screen validation dependencies...${NC}"

# Install image comparison libraries (lightweight alternatives to SAM-CD)
pip install imagehash==4.3.1
pip install scikit-image==0.21.0
pip install scipy==1.11.4

echo -e "${GREEN}✓ Screen validation dependencies installed${NC}"
echo -e "${YELLOW}Note: Using lightweight image comparison (ImageHash + OpenCV)${NC}"
echo -e "${YELLOW}      SAM-CD requires x86_64 hardware and is not compatible with ARM64${NC}"
echo ""

#############################################################################
# STEP 8: Create Required Directories
#############################################################################

echo -e "${BLUE}[9/10] Creating project directories...${NC}"

# Create directory structure
mkdir -p logs
mkdir -p logs/jobs
mkdir -p device_logs
mkdir -p iteration_logs
mkdir -p screenshots
mkdir -p execution_outputs
mkdir -p reference_screens
mkdir -p ssl
mkdir -p static/css
mkdir -p templates
mkdir -p controllers
mkdir -p models
mkdir -p services

echo -e "${GREEN}✓ Project directories created${NC}"
echo ""

#############################################################################
# STEP 9: Initialize Configuration Files
#############################################################################

echo -e "${BLUE}[10/10] Initializing configuration files...${NC}"

# Create empty JSON files if they don't exist
[ ! -f "devices.json" ] && echo "[]" > devices.json
[ ! -f "users.json" ] && echo "[]" > users.json
[ ! -f "jobs.json" ] && echo "[]" > jobs.json
[ ! -f "saved_sequences.json" ] && echo "[]" > saved_sequences.json
[ ! -f "device_locks.json" ] && echo "{}" > device_locks.json
[ ! -f "test_results_history.json" ] && echo "[]" > test_results_history.json
[ ! -f "app_state.json" ] && echo "{}" > app_state.json

echo -e "${GREEN}✓ Configuration files initialized${NC}"
echo ""

#############################################################################
# STEP 10: Verify Installation
#############################################################################

echo -e "${BLUE}Verifying installation...${NC}"
echo ""

# Test Python imports
python3 << 'PYEOF'
import sys
print("Python version:", sys.version)
print("\nTesting imports...")

packages = {
    'flask': 'Flask',
    'paramiko': 'Paramiko (SSH)',
    'PIL': 'Pillow',
    'cv2': 'OpenCV',
    'numpy': 'NumPy',
    'requests': 'Requests',
    'imagehash': 'ImageHash',
    'skimage': 'scikit-image',
}

success = 0
failed = []

for module, name in packages.items():
    try:
        __import__(module)
        print(f"  ✓ {name}")
        success += 1
    except ImportError as e:
        print(f"  ✗ {name}: {e}")
        failed.append(name)

print(f"\nResult: {success}/{len(packages)} packages imported successfully")

if failed:
    print(f"Failed packages: {', '.join(failed)}")
    sys.exit(1)
PYEOF

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ All core packages verified${NC}"
else
    echo ""
    echo -e "${RED}✗ Some packages failed to import${NC}"
    exit 1
fi

echo ""

#############################################################################
# Installation Complete
#############################################################################

echo -e "${GREEN}"
echo "========================================================================="
echo "  ✓✓✓ INSTALLATION COMPLETE! ✓✓✓"
echo "========================================================================="
echo -e "${NC}"
echo ""
echo -e "${BLUE}Project Structure:${NC}"
echo "  • Python Virtual Environment: venv/"
echo "  • Application Entry: app.py"
echo "  • Configuration Files: config_*.py"
echo "  • Controllers: controllers/"
echo "  • Models: models/"
echo "  • Services: services/"
echo "  • Templates: templates/"
echo "  • Logs: logs/, iteration_logs/, device_logs/"
echo "  • Screenshots: screenshots/"
echo "  • Reference Images: reference_screens/"
echo ""

echo -e "${BLUE}Installed Packages:${NC}"
pip list | grep -E "Flask|paramiko|Pillow|opencv|numpy|requests|imagehash|scikit-image"
echo ""

echo -e "${BLUE}Next Steps:${NC}"
echo "  1. Configure devices in devices.json"
echo "  2. Set up users in users.json"
echo "  3. Configure application settings in config_*.py files"
echo "  4. Start the application:"
echo -e "     ${GREEN}source venv/bin/activate${NC}"
echo -e "     ${GREEN}python app.py${NC}"
echo "  5. Access web interface at: http://<raspberry-pi-ip>:8080"
echo ""

echo -e "${BLUE}Optional - Set up as system service:${NC}"
echo "  • Copy and configure: device-testing.service"
echo "  • Enable service: sudo systemctl enable device-testing"
echo "  • Start service: sudo systemctl start device-testing"
echo ""

echo -e "${BLUE}For Production with HTTPS:${NC}"
echo "  • Run: ./run_production_https.sh"
echo "  • Or: ./run_production.sh"
echo ""

echo -e "${YELLOW}Documentation:${NC}"
echo "  • README.md - Project overview"
echo "  • QUICK_REFERENCE.md - Quick start guide"
echo "  • FEATURES_IMPLEMENTED_NOV20.md - Feature list"
echo "  • PASSWORD_RESET_GUIDE.md - Password management"
echo "  • SCREENSHOT_GUIDE.md - Screenshot functionality"
echo "  • SCREEN_VALIDATION_STATUS.md - Screen validation options"
echo ""

echo -e "${GREEN}Setup completed successfully!${NC}"
echo ""
