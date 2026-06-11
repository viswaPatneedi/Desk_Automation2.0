#!/bin/bash
# Installation script for SAM-CD Screen Validation dependencies
# For Raspberry Pi (ARM64/aarch64) with Python 3.12

set -e  # Exit on any error

echo "=========================================="
echo "SAM-CD Screen Validation Setup"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo -e "${RED}Error: Virtual environment 'venv' not found!${NC}"
    echo "Please create it first: python3 -m venv venv"
    exit 1
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Check Python version
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓ Python version: $PYTHON_VERSION${NC}"

# Check architecture
ARCH=$(uname -m)
echo -e "${GREEN}✓ Architecture: $ARCH${NC}"
echo ""

# Step 1: Install PyTorch (CPU version for ARM64)
echo -e "${YELLOW}[1/6] Installing PyTorch for ARM64 (CPU version)...${NC}"
echo "This may take 10-15 minutes..."
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
echo -e "${GREEN}✓ PyTorch installed${NC}"
echo ""

# Step 2: Install OpenMIM
echo -e "${YELLOW}[2/6] Installing OpenMIM (OpenMMLab package manager)...${NC}"
pip install -U openmim
echo -e "${GREEN}✓ OpenMIM installed${NC}"
echo ""

# Step 3: Install MMEngine
echo -e "${YELLOW}[3/6] Installing MMEngine...${NC}"
mim install mmengine
echo -e "${GREEN}✓ MMEngine installed${NC}"
echo ""

# Step 4: Install MMCV
echo -e "${YELLOW}[4/6] Installing MMCV (this may take 5-10 minutes)...${NC}"
mim install "mmcv>=2.0.0"
echo -e "${GREEN}✓ MMCV installed${NC}"
echo ""

# Step 5: Install MMPretrain and related packages
echo -e "${YELLOW}[5/6] Installing MMPretrain, MMSegmentation, and MMDetection...${NC}"
mim install "mmpretrain>=1.0.0rc7"
pip install "mmsegmentation>=1.2.2"
pip install "mmdet>=3.0.0"
echo -e "${GREEN}✓ OpenMMLab packages installed${NC}"
echo ""

# Step 6: Install additional dependencies
echo -e "${YELLOW}[6/6] Installing additional dependencies...${NC}"
pip install matplotlib packaging prettytable pillow opencv-python
echo -e "${GREEN}✓ Additional dependencies installed${NC}"
echo ""

# Step 7: Install SAM-CD package
echo -e "${YELLOW}Installing SAM-CD package...${NC}"
if [ -d "SAM-CD-2GB/SAM-CD_2GB" ]; then
    cd SAM-CD-2GB/SAM-CD_2GB
    pip install -v -e .
    cd "$SCRIPT_DIR"
    echo -e "${GREEN}✓ SAM-CD package installed${NC}"
else
    echo -e "${RED}⚠ SAM-CD-2GB directory not found, skipping package installation${NC}"
fi
echo ""

# Verify installations
echo -e "${YELLOW}Verifying installations...${NC}"
python -c "import torch; print('PyTorch:', torch.__version__)" || echo -e "${RED}✗ PyTorch not found${NC}"
python -c "import mmengine; print('MMEngine:', mmengine.__version__)" || echo -e "${RED}✗ MMEngine not found${NC}"
python -c "import mmcv; print('MMCV:', mmcv.__version__)" || echo -e "${RED}✗ MMCV not found${NC}"
python -c "import mmseg; print('MMSegmentation:', mmseg.__version__)" || echo -e "${RED}✗ MMSegmentation not found${NC}"
python -c "import cv2; print('OpenCV:', cv2.__version__)" || echo -e "${RED}✗ OpenCV not found${NC}"
echo ""

# Check model weights
echo -e "${YELLOW}Checking for model weights...${NC}"
if [ -f "SAM-CD-2GB/SAM-CD_2GB/stanet_bam_workdir/best_mIoU_iter_40000.pth" ]; then
    MODEL_SIZE=$(du -h SAM-CD-2GB/SAM-CD_2GB/stanet_bam_workdir/best_mIoU_iter_40000.pth | awk '{print $1}')
    echo -e "${GREEN}✓ Model weights found: $MODEL_SIZE${NC}"
else
    echo -e "${RED}⚠ Model weights not found${NC}"
    echo "Expected location: SAM-CD-2GB/SAM-CD_2GB/stanet_bam_workdir/best_mIoU_iter_40000.pth"
fi
echo ""

# Create reference_screens directory
echo -e "${YELLOW}Creating reference_screens directory...${NC}"
mkdir -p reference_screens
echo -e "${GREEN}✓ reference_screens directory created${NC}"
echo ""

# Display summary
echo "=========================================="
echo -e "${GREEN}Installation Complete!${NC}"
echo "=========================================="
echo ""
echo "Next Steps:"
echo "1. Capture reference screenshots for your screens (HOME, NETFLIX, etc.)"
echo "2. Place them in: reference_screens/"
echo "3. Test validation with your screenshots"
echo "4. Integrate into your device testing scripts"
echo ""
echo "For detailed usage, see: AI_SCREEN_VALIDATION_GUIDE.md"
echo ""
echo -e "${YELLOW}Note:${NC} On Raspberry Pi, AI validation may take 10-15 seconds per screenshot."
echo ""
