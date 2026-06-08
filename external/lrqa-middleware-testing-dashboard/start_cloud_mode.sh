#!/bin/bash
#
# Start Flask App in Cloud/Tunnel Mode
# This script sets up the environment and starts the Flask application
# configured for cloud deployment with SSH tunnels
#
# Usage: ./start_cloud_mode.sh

# ============================================================================
# CONFIGURATION - UPDATE THESE VALUES
# ============================================================================

# Flask server hostname/IP that users will access
# This should be the hostname or IP of your cloud/company server
FLASK_SERVER_HOST="${FLASK_SERVER_HOST:-localhost}"

# Prompt for hostname if not set
if [ "$FLASK_SERVER_HOST" == "localhost" ]; then
    echo "=========================================="
    echo "Flask Server Hostname Configuration"
    echo "=========================================="
    echo ""
    echo "Enter the hostname or IP address where Flask will be accessible"
    echo "Examples:"
    echo "  - flask.company.com"
    echo "  - 10.61.187.7"
    echo "  - $(hostname -I | awk '{print $1}')"
    echo ""
    read -p "Flask Server Host: " FLASK_SERVER_HOST
    
    if [ -z "$FLASK_SERVER_HOST" ]; then
        echo "❌ Hostname cannot be empty"
        exit 1
    fi
fi

# ============================================================================
# ENVIRONMENT SETUP
# ============================================================================

echo ""
echo "=========================================="
echo "Starting Flask App in CLOUD/TUNNEL Mode"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  Mode: TUNNEL (Cloud/VPN Deployment)"
echo "  Flask Server: $FLASK_SERVER_HOST"
echo "  Port: 5000"
echo ""

# Set environment variables
export TUNNEL_MODE=true
export FLASK_SERVER_HOST="$FLASK_SERVER_HOST"

# Optional: Load additional environment variables from .env file
if [ -f ".env" ]; then
    echo "Loading environment variables from .env file..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# ============================================================================
# PRE-FLIGHT CHECKS
# ============================================================================

echo "Pre-flight checks:"
echo ""

# Check if tunnel service is running
if systemctl is-active --quiet lab-tunnel 2>/dev/null; then
    echo "✅ Lab tunnel service: RUNNING"
else
    echo "⚠️  Lab tunnel service: NOT RUNNING"
    echo "   Start with: sudo systemctl start lab-tunnel"
    echo ""
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if tunnel ports are listening
TUNNEL_PORTS=(10250 10101 10195 10249 10238 5800 5801 5802 5803 5804)
PORT_CHECK_PASSED=true

for port in "${TUNNEL_PORTS[@]}"; do
    if ss -tuln | grep -q ":$port "; then
        : # Port is listening, continue silently
    else
        if [ "$PORT_CHECK_PASSED" = true ]; then
            echo "⚠️  Some tunnel ports are not listening:"
            PORT_CHECK_PASSED=false
        fi
        echo "   - Port $port"
    fi
done

if [ "$PORT_CHECK_PASSED" = true ]; then
    echo "✅ Tunnel ports: ALL LISTENING"
else
    echo ""
    echo "   Check tunnel status: sudo systemctl status lab-tunnel"
    echo ""
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if Python virtual environment exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found"
    echo "   Creating virtual environment..."
    python3 -m venv venv
    echo "   Installing dependencies..."
    source venv/bin/activate
    pip install -r requirements.txt
else
    echo "✅ Virtual environment: EXISTS"
    source venv/bin/activate
fi

# Check if devices.json exists
if [ ! -f "devices.json" ]; then
    echo "⚠️  devices.json not found"
    echo "   Please create devices.json with your device configuration"
    exit 1
else
    echo "✅ devices.json: EXISTS"
fi

echo ""
echo "=========================================="
echo ""

# ============================================================================
# START APPLICATION
# ============================================================================

echo "Starting Flask application..."
echo ""
echo "Access the dashboard at:"
echo "  http://$FLASK_SERVER_HOST:5000"
echo ""
echo "Users must be connected to VPN to access"
echo ""
echo "Press Ctrl+C to stop"
echo ""
echo "=========================================="
echo ""

# Start Flask application
python app.py
