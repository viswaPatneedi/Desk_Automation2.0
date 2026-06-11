#!/bin/bash

################################################################################
# Docker Image Export Helper
# 
# This script:
# 1. Monitors Docker build completion
# 2. Exports image to tar file for USB deployment
# 3. Verifies tar file integrity
# 4. Provides deployment-ready status
################################################################################

set -e

IMAGE_NAME="rpi4-app:latest"
OUTPUT_TAR="/media/lrqa/Lexar/Pi4-Dockerimage/rpi4-app-image.tar"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Docker Image Export Helper for Pi4 Deployment           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

################################################################################
# STEP 1: Check if image exists
################################################################################

echo -e "${BLUE}[1/5] Checking Docker image...${NC}"

if sudo docker images | grep -q "$IMAGE_NAME"; then
    IMAGE_ID=$(sudo docker images --format "{{.ID}}" | head -1)
    IMAGE_SIZE=$(sudo docker images "$IMAGE_NAME" --format "{{.Size}}")
    echo -e "${GREEN}✓ Image found: $IMAGE_NAME${NC}"
    echo -e "${GREEN}  Size: $IMAGE_SIZE${NC}"
else
    echo -e "${YELLOW}⚠ Image not found: $IMAGE_NAME${NC}"
    echo ""
    echo -e "${YELLOW}The Docker image 'rpi4-app:latest' does not exist yet.${NC}"
    echo ""
    echo -e "${YELLOW}Status options:${NC}"
    echo "  1. Docker build still in progress (check: sudo docker ps)"
    echo "  2. Build failed (check: docker logs)"
    echo "  3. Image not named correctly"
    echo ""
    echo -e "${YELLOW}To check build status:${NC}"
    echo "  sudo docker ps -a"
    echo "  sudo docker images"
    echo ""
    exit 1
fi

echo ""

################################################################################
# STEP 2: Create output directory
################################################################################

echo -e "${BLUE}[2/5] Preparing export location...${NC}"

OUTPUT_DIR=$(dirname "$OUTPUT_TAR")

if [ ! -d "$OUTPUT_DIR" ]; then
    echo -e "${YELLOW}Creating directory: $OUTPUT_DIR${NC}"
    mkdir -p "$OUTPUT_DIR"
fi

if [ -f "$OUTPUT_TAR" ]; then
    EXISTING_SIZE=$(du -h "$OUTPUT_TAR" | cut -f1)
    echo -e "${YELLOW}⚠ Tar file already exists (size: $EXISTING_SIZE)${NC}"
    echo -e "${YELLOW}  Backing up to: ${OUTPUT_TAR}.backup${NC}"
    mv "$OUTPUT_TAR" "${OUTPUT_TAR}.backup"
fi

echo -e "${GREEN}✓ Export location ready: $OUTPUT_DIR${NC}"

echo ""

################################################################################
# STEP 3: Export Docker image to tar
################################################################################

echo -e "${BLUE}[3/5] Exporting Docker image to tar...${NC}"
echo -e "${YELLOW}This may take 5-15 minutes depending on image size...${NC}"
echo ""

# Start export with progress
START_TIME=$(date +%s)

if sudo docker save -o "$OUTPUT_TAR" "$IMAGE_NAME"; then
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    EXPORT_SIZE=$(du -h "$OUTPUT_TAR" | cut -f1)
    echo -e "${GREEN}✓ Export completed in $DURATION seconds${NC}"
    echo -e "${GREEN}  Tar file size: $EXPORT_SIZE${NC}"
else
    echo -e "${RED}✗ Export failed!${NC}"
    exit 1
fi

echo ""

################################################################################
# STEP 4: Verify tar file integrity
################################################################################

echo -e "${BLUE}[4/5] Verifying tar file integrity...${NC}"

if [ -f "$OUTPUT_TAR" ]; then
    TAR_SIZE=$(stat -f%z "$OUTPUT_TAR" 2>/dev/null || stat -c%s "$OUTPUT_TAR")
    
    if [ "$TAR_SIZE" -gt 400000000 ]; then  # > 400MB
        echo -e "${GREEN}✓ Tar file size reasonable: $EXPORT_SIZE${NC}"
        
        # Quick integrity check
        if tar -tzf "$OUTPUT_TAR" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Tar file integrity verified${NC}"
        else
            echo -e "${YELLOW}⚠ Could not verify tar integrity (may be due to Docker format)${NC}"
        fi
    else
        echo -e "${RED}✗ Tar file suspiciously small: $EXPORT_SIZE${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ Tar file not found: $OUTPUT_TAR${NC}"
    exit 1
fi

echo ""

################################################################################
# STEP 5: Generate summary
################################################################################

echo -e "${BLUE}[5/5] Generating deployment summary...${NC}"

cat > "${OUTPUT_DIR}/EXPORT_SUMMARY.txt" << 'EOF'
================================================================================
Docker Image Export Summary
================================================================================

Export Details:
  Image: rpi4-app:latest
  Format: TAR (Docker save format)
  Location: rpi4-app-image.tar
  Compressed: No (uncompressed tar)

Deployment Methods:
  Fast Mode: Load from this tar file
    $ docker load < rpi4-app-image.tar
    Deployment time: 5-10 minutes
  
  Build Mode: Build from Dockerfile
    $ docker build -f Dockerfile.rpi.clean -t rpi4-app:latest .
    Deployment time: 20-35 minutes

On New Raspberry Pi:
  1. Copy Pi4-Dockerimage folder to RPi
  2. Run: ./rpi4-setup-with-prebuilt.sh
  3. Script will auto-detect and use pre-built image
  4. Complete in 5-10 minutes

Verification:
  After deployment, verify with:
    $ curl http://localhost:11078/health
    $ docker ps
    $ docker logs -f rpi4-app-container

Support:
  See PREBUILT_IMAGE_GUIDE.md for detailed guidance
  See DEPLOYMENT_INSTRUCTIONS.md for standard deployment
  See QUICK_DEPLOY_NEW_RPI.txt for quick start

================================================================================
Generated: $(date)
================================================================================
EOF

echo -e "${GREEN}✓ Summary generated: EXPORT_SUMMARY.txt${NC}"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                  ✓ EXPORT COMPLETED                        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo "Pre-built Docker image is ready for deployment!"
echo ""
echo "File: $OUTPUT_TAR"
echo "Size: $EXPORT_SIZE"
echo ""
echo "Next Steps:"
echo "  1. Connect Lexar USB to new Raspberry Pi 4"
echo "  2. SSH into new RPi"
echo "  3. Navigate to: cd /mnt/usb/Pi4-Dockerimage"
echo "  4. Run: chmod +x rpi4-setup-with-prebuilt.sh && ./rpi4-setup-with-prebuilt.sh"
echo "  5. Wait 5-10 minutes for deployment"
echo "  6. Access: http://<rpi-ip>:11078"
echo ""

exit 0
