#!/bin/bash

# =============================================================================
# RDK-E Middleware Dashboard - RESTART APPLICATION
# =============================================================================
# This script restarts the Docker container
# Usage: ./restart-rdk-app.sh
# =============================================================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  RDK-E Middleware QA Dashboard - RESTART                      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo -e "${BLUE}🛑 Stopping application...${NC}"
"$SCRIPT_DIR/stop-rdk-app.sh"

echo ""
echo -e "${BLUE}⏳ Waiting 3 seconds...${NC}"
sleep 3

echo ""
echo -e "${BLUE}🚀 Starting application...${NC}"
"$SCRIPT_DIR/start-rdk-app.sh"

echo ""
echo -e "${GREEN}✅ Restart complete!${NC}"
