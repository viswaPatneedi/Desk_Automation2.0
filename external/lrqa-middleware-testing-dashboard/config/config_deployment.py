"""
Deployment Configuration for Cloud/VPN Hosting
Manages dynamic VNC URL generation and tunnel port mappings
"""

import os

# ============================================================================
# SERVER CONFIGURATION
# ============================================================================

# Flask server hostname/IP that users will access via VPN
# This should be set via environment variable in production
# Example: export FLASK_SERVER_HOST='flask.company.com' or '10.61.187.7'
FLASK_SERVER_HOST = os.environ.get('FLASK_SERVER_HOST', 'localhost')

# Whether the app is running in cloud/tunnel mode
# When True, VNC URLs will use FLASK_SERVER_HOST
# When False, VNC URLs will use device IPs directly (local mode)
TUNNEL_MODE = os.environ.get('TUNNEL_MODE', 'false').lower() == 'true'

# ============================================================================
# VNC PORT MAPPINGS FOR TUNNEL MODE
# ============================================================================

# Maps device IPs to their tunneled VNC ports on the Flask server
# Used when TUNNEL_MODE=true
# Format: 'device_ip': tunnel_port
VNC_PORT_MAPPING = {
    '10.0.0.250': 5800,  # Element-A4K-DESK
    '10.0.0.101': 5801,  # WestingHouse-4K-DESK
    '10.0.0.195': 5802,  # SHARP-DEVICE-DESK
    '10.0.0.249': 5803,  # ES1-DESK-LAVANYA
    '10.0.0.238': 5804,  # SKY-XIONE-UK-DEVICE
}

# Default VNC port for devices not in mapping (local mode)
DEFAULT_VNC_PORT = 5800

# ============================================================================
# SSH PORT MAPPINGS FOR TUNNEL MODE
# ============================================================================

# Maps device IPs to their tunneled SSH ports on the Flask server
# Used when TUNNEL_MODE=true to update device IPs to 'localhost'
SSH_PORT_MAPPING = {
    '10.0.0.250': 10250,  # Element-A4K-DESK
    '10.0.0.101': 10101,  # WestingHouse-4K-DESK
    '10.0.0.195': 10195,  # SHARP-DEVICE-DESK
    '10.0.0.249': 10249,  # ES1-DESK-LAVANYA
    '10.0.0.238': 10238,  # SKY-XIONE-UK-DEVICE
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_vnc_url(device_ip, original_vnc_url=''):
    """
    Generate dynamic VNC URL based on deployment mode
    
    Args:
        device_ip: IP address of the device
        original_vnc_url: Original VNC URL from devices.json (optional)
    
    Returns:
        str: VNC URL for the device
    """
    if TUNNEL_MODE:
        # Cloud/tunnel mode: Use Flask server host with mapped port
        vnc_port = VNC_PORT_MAPPING.get(device_ip, DEFAULT_VNC_PORT)
        return f"http://{FLASK_SERVER_HOST}:{vnc_port}/"
    else:
        # Local mode: Use device IP with default port
        if original_vnc_url:
            return original_vnc_url
        return f"http://{device_ip}:{DEFAULT_VNC_PORT}/"


def get_device_connection_params(device_ip, device_port):
    """
    Get device connection parameters based on deployment mode
    
    Args:
        device_ip: Original device IP
        device_port: Original device port
    
    Returns:
        tuple: (connection_ip, connection_port)
    """
    if TUNNEL_MODE:
        # Cloud/tunnel mode: Use localhost with mapped port
        ssh_port = SSH_PORT_MAPPING.get(device_ip, device_port)
        return ('localhost', ssh_port)
    else:
        # Local mode: Use original IP and port
        return (device_ip, device_port)


def print_deployment_info():
    """Print current deployment configuration"""
    print("\n" + "="*60)
    print("DEPLOYMENT CONFIGURATION")
    print("="*60)
    print(f"Mode: {'TUNNEL (Cloud/VPN)' if TUNNEL_MODE else 'LOCAL'}")
    print(f"Flask Server Host: {FLASK_SERVER_HOST}")
    
    if TUNNEL_MODE:
        print("\nVNC Port Mappings:")
        for device_ip, port in VNC_PORT_MAPPING.items():
            print(f"  {device_ip} → {FLASK_SERVER_HOST}:{port}")
        
        print("\nSSH Port Mappings:")
        for device_ip, port in SSH_PORT_MAPPING.items():
            print(f"  {device_ip}:10022 → localhost:{port}")
    else:
        print("\nUsing direct device connections (no tunneling)")
    
    print("="*60 + "\n")
