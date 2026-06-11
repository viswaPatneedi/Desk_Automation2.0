#!/bin/bash

# =============================================================================
# RDK-E Middleware Dashboard - STOP APPLICATION
# =============================================================================
# This script stops the Docker container safely
# Usage: ./stop-rdk-app.sh
# =============================================================================

set -e

APP_NAME="rdk-middleware-dashboard"
COMPOSE_FILE="docker-files/docker-compose.rpi.clean.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  RDK-E Middleware QA Dashboard - STOP                         ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed!${NC}"
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

# Check if container is running
if ! docker ps | grep -q "$APP_NAME"; then
    echo -e "${YELLOW}ℹ️  Container is not running${NC}"
    exit 0
fi

# Stop the container
echo -e "${BLUE}🛑 Stopping application...${NC}"
$DOCKER_COMPOSE -f "$COMPOSE_FILE" down

# Wait for container to stop
sleep 2

# Verify it stopped
if docker ps | grep -q "$APP_NAME"; then
    echo -e "${YELLOW}⚠️  Container still running. Force stopping...${NC}"
    docker stop "$APP_NAME" 2>/dev/null || true
    docker rm "$APP_NAME" 2>/dev/null || true
fi

echo -e "${GREEN}✅ Application stopped successfully!${NC}"
echo ""
echo -e "${BLUE}📝 Data volumes preserved at:${NC}"
echo "   • iteration_logs/"
echo "   • screenshots/"
echo "   • data/"
echo "   • reference_screens/"
echo "   • Json/"
echo ""
echo -e "${BLUE}🔄 To start again, run: ./start-rdk-app.sh${NC}"
