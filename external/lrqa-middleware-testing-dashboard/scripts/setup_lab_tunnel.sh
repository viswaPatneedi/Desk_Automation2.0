#!/bin/bash
#
# SSH Tunnel Setup Script for Cloud/VPN Deployment
# This script creates persistent SSH tunnels from the Flask server to your lab devices
#
# Usage:
#   1. Copy this script to your Flask server (cloud/VPN host)
#   2. Update LAB_GATEWAY variables below with your lab's SSH details
#   3. Run: ./setup_lab_tunnel.sh
#   4. For persistent tunnel, install as systemd service (see setup_tunnel_service.sh)

# ============================================================================
# CONFIGURATION - UPDATE THESE VALUES
# ============================================================================

# Lab gateway SSH connection details
LAB_GATEWAY_HOST="your-lab-gateway-ip"      # e.g., "10.61.187.7" or "pi@home.example.com"
LAB_GATEWAY_PORT="22"                        # SSH port of lab gateway (default: 22, yours might be 60201)
LAB_GATEWAY_USER="pi"                        # SSH username for lab gateway

# Optional: SSH key file (recommended for production)
# SSH_KEY_FILE="$HOME/.ssh/id_rsa_lab"
# Leave empty to use password authentication
SSH_KEY_FILE=""

# ============================================================================
# DEVICE TUNNEL MAPPINGS
# ============================================================================
# Format: -R <local_port>:<remote_ip>:<remote_port>
# Local port will be available on Flask server, forwarding to remote device in lab

# SSH Tunnels for device access
SSH_TUNNELS=(
    "-R 10250:10.0.0.250:10022"    # Element-A4K-DESK
    "-R 10101:10.0.0.101:10022"    # WestingHouse-4K-DESK
    "-R 10195:10.0.0.195:10022"    # SHARP-DEVICE-DESK
    "-R 10249:10.0.0.249:10022"    # ES1-DESK-LAVANYA
    "-R 10238:10.0.0.238:10022"    # SKY-XIONE-UK-DEVICE
)

# VNC Tunnels for device viewing
VNC_TUNNELS=(
    "-R 5800:10.0.0.250:5800"      # Element-A4K-DESK VNC
    "-R 5801:10.0.0.101:5800"      # WestingHouse-4K-DESK VNC
    "-R 5802:10.0.0.195:5800"      # SHARP-DEVICE-DESK VNC
    "-R 5803:10.0.0.249:5800"      # ES1-DESK-LAVANYA VNC
    "-R 5804:10.0.0.238:5800"      # SKY-XIONE-UK-DEVICE VNC
)

# IR Blaster Tunnel
IR_TUNNEL="-R 5033:10.0.0.33:4998"  # iTach IR Blaster

# ============================================================================
# TUNNEL SETUP
# ============================================================================

echo "=========================================="
echo "SSH Tunnel Setup for Lab Devices"
echo "=========================================="
echo ""

# Build tunnel arguments
TUNNEL_ARGS=""
for tunnel in "${SSH_TUNNELS[@]}"; do
    TUNNEL_ARGS="$TUNNEL_ARGS $tunnel"
done

for tunnel in "${VNC_TUNNELS[@]}"; do
    TUNNEL_ARGS="$TUNNEL_ARGS $tunnel"
done

TUNNEL_ARGS="$TUNNEL_ARGS $IR_TUNNEL"

# Build SSH command
SSH_CMD="ssh -N"
SSH_CMD="$SSH_CMD -o ServerAliveInterval=60"
SSH_CMD="$SSH_CMD -o ServerAliveCountMax=3"
SSH_CMD="$SSH_CMD -o ExitOnForwardFailure=yes"
SSH_CMD="$SSH_CMD -p $LAB_GATEWAY_PORT"

if [ -n "$SSH_KEY_FILE" ] && [ -f "$SSH_KEY_FILE" ]; then
    SSH_CMD="$SSH_CMD -i $SSH_KEY_FILE"
    echo "Using SSH key: $SSH_KEY_FILE"
fi

SSH_CMD="$SSH_CMD $TUNNEL_ARGS"
SSH_CMD="$SSH_CMD $LAB_GATEWAY_USER@$LAB_GATEWAY_HOST"

# Display tunnel configuration
echo "Lab Gateway: $LAB_GATEWAY_USER@$LAB_GATEWAY_HOST:$LAB_GATEWAY_PORT"
echo ""
echo "Tunnels to be created:"
echo "----------------------"
echo "SSH Device Connections:"
for tunnel in "${SSH_TUNNELS[@]}"; do
    echo "  localhost:${tunnel#*-R } (on Flask server)"
done
echo ""
echo "VNC Device Viewers:"
for tunnel in "${VNC_TUNNELS[@]}"; do
    echo "  localhost:${tunnel#*-R } (on Flask server)"
done
echo ""
echo "IR Blaster:"
echo "  localhost:${IR_TUNNEL#*-R } (on Flask server)"
echo ""
echo "=========================================="
echo ""

# Check if tunnel is already running
if pgrep -f "ssh.*$LAB_GATEWAY_HOST" > /dev/null; then
    echo "⚠️  Warning: An SSH tunnel to $LAB_GATEWAY_HOST may already be running"
    echo "   Check with: pgrep -af 'ssh.*$LAB_GATEWAY_HOST'"
    echo "   Kill with: pkill -f 'ssh.*$LAB_GATEWAY_HOST'"
    echo ""
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Test connection first
echo "Testing SSH connection to lab gateway..."
if [ -n "$SSH_KEY_FILE" ] && [ -f "$SSH_KEY_FILE" ]; then
    ssh -i "$SSH_KEY_FILE" -p "$LAB_GATEWAY_PORT" -o ConnectTimeout=10 \
        "$LAB_GATEWAY_USER@$LAB_GATEWAY_HOST" "echo 'Connection successful'" 2>/dev/null
else
    ssh -p "$LAB_GATEWAY_PORT" -o ConnectTimeout=10 \
        "$LAB_GATEWAY_USER@$LAB_GATEWAY_HOST" "echo 'Connection successful'" 2>/dev/null
fi

if [ $? -ne 0 ]; then
    echo "❌ Failed to connect to lab gateway"
    echo "   Please check your connection settings and try again"
    exit 1
fi

echo "✅ Connection test successful"
echo ""

# Start tunnel
echo "Starting SSH tunnel..."
echo "Command: $SSH_CMD"
echo ""
echo "⚠️  This will run in the foreground. Press Ctrl+C to stop."
echo "   For background/persistent tunnel, use the systemd service (setup_tunnel_service.sh)"
echo ""
echo "Starting in 3 seconds..."
sleep 3

# Execute tunnel
exec $SSH_CMD
