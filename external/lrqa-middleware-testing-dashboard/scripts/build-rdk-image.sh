#!/bin/bash

# =============================================================================
# RDK-E Middleware Dashboard - BUILD DOCKER IMAGE
# =============================================================================
# This script builds the production Docker image with all application code
# Usage: ./build-rdk-image.sh [--no-cache] [--platform arm64]
# =============================================================================

set -e

IMAGE_NAME="rdk-middleware:latest"
DOCKERFILE="Dockerfile.production"
BUILD_CONTEXT="."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  RDK-E Middleware QA Dashboard - BUILD DOCKER IMAGE           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"

# Parse arguments
NO_CACHE=""
PLATFORM=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-cache)
            NO_CACHE="--no-cache"
            echo -e "${YELLOW}⚠️  Building without cache${NC}"
            shift
            ;;
        --platform)
            PLATFORM="--platform $2"
            echo -e "${YELLOW}Building for platform: $2${NC}"
            shift 2
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed!${NC}"
    exit 1
fi

# Check if Dockerfile exists
if [ ! -f "$DOCKERFILE" ]; then
    echo -e "${RED}❌ Dockerfile not found: $DOCKERFILE${NC}"
    exit 1
fi

# Check requirements.txt exists
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ requirements.txt not found!${NC}"
    exit 1
fi

echo -e "${BLUE}📋 Build Information:${NC}"
echo "   Image Name: $IMAGE_NAME"
echo "   Dockerfile: $DOCKERFILE"
echo "   Context: $BUILD_CONTEXT"
echo ""

# Start build
echo -e "${BLUE}🔨 Building Docker image...${NC}"
echo -e "${YELLOW}This may take several minutes on RPi...${NC}"
echo ""

START_TIME=$(date +%s)

docker build $PLATFORM $NO_CACHE \
    -f "$DOCKERFILE" \
    -t "$IMAGE_NAME" \
    --label "built-date=$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
    --label "version=2.0.1" \
    "$BUILD_CONTEXT"

BUILD_STATUS=$?
END_TIME=$(date +%s)
BUILD_TIME=$((END_TIME - START_TIME))

if [ $BUILD_STATUS -eq 0 ]; then
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✅ BUILD SUCCESSFUL!                                         ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Get image size
    IMAGE_SIZE=$(docker images | grep rdk-middleware | awk '{print $(NF-1), $NF}' | head -1)
    
    echo -e "${BLUE}📦 Image Information:${NC}"
    echo "   Image: $IMAGE_NAME"
    echo "   Size: $IMAGE_SIZE"
    echo "   Build Time: ${BUILD_TIME}s"
    echo ""
    
    echo -e "${BLUE}🚀 Next Steps:${NC}"
    echo "   1. Verify image: docker images | grep rdk-middleware"
    echo "   2. Start app: ./start-rdk-app.sh"
    echo "   3. Check status: ./status-rdk-app.sh"
    echo ""
    
    echo -e "${BLUE}💾 To export as tar (for distribution):${NC}"
    echo "   docker save $IMAGE_NAME -o rdk-middleware-image.tar"
    echo ""
    
else
    echo ""
    echo -e "${RED}❌ Build failed!${NC}"
    exit 1
fi
