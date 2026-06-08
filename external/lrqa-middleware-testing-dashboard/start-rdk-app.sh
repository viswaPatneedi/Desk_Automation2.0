#!/bin/bash

# =============================================================================
# RDK-E Middleware Dashboard - START APPLICATION
# =============================================================================
# This script starts the Docker container with the application
# Usage: ./start-rdk-app.sh
# =============================================================================

set -e

APP_NAME="rdk-middleware-dashboard"
IMAGE_NAME="rdk-middleware:latest"
COMPOSE_FILE="docker-files/docker-compose.rpi.clean.yml"
PORT=11078

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  RDK-E Middleware QA Dashboard - START                        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed!${NC}"
    echo "Please install Docker first: https://docs.docker.com/install/"
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}⚠️  docker-compose not found, using 'docker compose' instead${NC}"
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

# Create required directories
echo -e "${BLUE}📁 Setting up directories...${NC}"
mkdir -p iteration_logs screenshots data reference_screens Json

# Set proper permissions
chmod 777 iteration_logs screenshots data reference_screens Json 2>/dev/null || true

# Check if compose file exists
if [ ! -f "$COMPOSE_FILE" ]; then
    echo -e "${RED}❌ Error: $COMPOSE_FILE not found!${NC}"
    exit 1
fi

# Check if image exists
if ! docker images | grep -q "$IMAGE_NAME"; then
    echo -e "${YELLOW}⚠️  Image not found locally. Please build it first:${NC}"
    echo -e "${YELLOW}    docker build -f docker-files/Dockerfile.production -t $IMAGE_NAME docker-files/${NC}"
    echo ""
    echo -e "${BLUE}🔨 Building Docker image now...${NC}"
    docker build -f docker-files/Dockerfile.production -t "$IMAGE_NAME" docker-files/
fi

# Stop existing container if running
if docker ps | grep -q "$APP_NAME"; then
    echo -e "${YELLOW}⚠️  Container already running. Stopping it first...${NC}"
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" down
    sleep 2
fi

# Start the container
echo -e "${BLUE}🚀 Starting application...${NC}"
$DOCKER_COMPOSE -f "$COMPOSE_FILE" up -d

# Wait for container to be ready
echo -e "${BLUE}⏳ Waiting for application to start...${NC}"
sleep 5

# Check if container is running
if docker ps | grep -q "$APP_NAME"; then
    echo -e "${GREEN}✅ Container started successfully!${NC}"
    
    # Get container IP
    CONTAINER_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$APP_NAME" 2>/dev/null || echo "")
    HOST_IP=$(hostname -I | awk '{print $1}')
    
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✅ APPLICATION STARTED SUCCESSFULLY!                         ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}🌐 Access the dashboard at:${NC}"
    echo -e "   ${GREEN}http://${HOST_IP}:${PORT}${NC}"
    echo ""
    echo -e "${BLUE}📊 Container Info:${NC}"
    echo "   Container: $APP_NAME"
    echo "   Image: $IMAGE_NAME"
    echo "   Port: $PORT"
    echo ""
    echo -e "${BLUE}📝 Useful commands:${NC}"
    echo "   View logs:        $DOCKER_COMPOSE -f $COMPOSE_FILE logs -f"
    echo "   Stop app:         ./stop-rdk-app.sh"
    echo "   Restart app:      ./restart-rdk-app.sh"
    echo "   Check status:     ./status-rdk-app.sh"
    echo ""
else
    echo -e "${RED}❌ Failed to start container!${NC}"
    echo -e "${BLUE}🔍 Checking logs:${NC}"
    docker logs "$APP_NAME" --tail=20
    exit 1
fi

echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
