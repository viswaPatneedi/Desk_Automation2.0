#!/bin/bash

# =============================================================================
# RDK-E Middleware Dashboard - STATUS CHECK
# =============================================================================
# This script shows the application status and logs
# Usage: ./status-rdk-app.sh
# =============================================================================

APP_NAME="rdk-middleware-dashboard"
COMPOSE_FILE="docker-files/docker-compose.rpi.clean.yml"
PORT=11078

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  RDK-E Middleware QA Dashboard - STATUS                       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"

# Check if container is running
echo -e "${BLUE}📊 Container Status:${NC}"
if docker ps | grep -q "$APP_NAME"; then
    echo -e "   ${GREEN}✅ RUNNING${NC}"
    
    # Get container details
    CONTAINER_ID=$(docker ps | grep "$APP_NAME" | awk '{print $1}')
    UP_TIME=$(docker ps | grep "$APP_NAME" | awk '{print $(NF-1), $NF}')
    
    echo -e "   ID: ${GREEN}$CONTAINER_ID${NC}"
    echo -e "   Status: ${GREEN}$UP_TIME${NC}"
else
    echo -e "   ${RED}❌ STOPPED${NC}"
fi

# Check port
echo ""
echo -e "${BLUE}🌐 Port Status:${NC}"
if netstat -tlnp 2>/dev/null | grep -q ":$PORT"; then
    echo -e "   ${GREEN}✅ Port $PORT is listening${NC}"
    curl -s http://localhost:$PORT > /dev/null 2>&1 && \
        echo -e "   ${GREEN}✅ Application responding${NC}" || \
        echo -e "   ${YELLOW}⚠️  Port open but application not responding${NC}"
else
    echo -e "   ${YELLOW}⚠️  Port $PORT not listening${NC}"
fi

# Show data volumes
echo ""
echo -e "${BLUE}💾 Data Volumes:${NC}"
for dir in iteration_logs screenshots data reference_screens Json; do
    if [ -d "$dir" ]; then
        SIZE=$(du -sh "$dir" 2>/dev/null | cut -f1)
        COUNT=$(find "$dir" -type f 2>/dev/null | wc -l)
        echo -e "   ${GREEN}✅${NC} $dir (${SIZE}, $COUNT files)"
    else
        echo -e "   ${RED}❌${NC} $dir (missing)"
    fi
done

# Show recent logs
echo ""
echo -e "${BLUE}📝 Recent Logs (last 15 lines):${NC}"
if docker ps | grep -q "$APP_NAME"; then
    echo "───────────────────────────────────────────────────────────────"
    docker logs "$APP_NAME" --tail=15 2>/dev/null | tail -15
    echo "───────────────────────────────────────────────────────────────"
else
    echo -e "   ${YELLOW}Container not running - no logs available${NC}"
fi

# Show useful commands
echo ""
echo -e "${BLUE}📖 Useful Commands:${NC}"
echo "   Start:          ./start-rdk-app.sh"
echo "   Stop:           ./stop-rdk-app.sh"
echo "   Restart:        ./restart-rdk-app.sh"
echo "   View full logs: docker logs -f $APP_NAME"
echo "   Shell access:   docker exec -it $APP_NAME bash"
echo ""
