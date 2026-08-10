#!/usr/bin/env python3
"""
GDF API Configuration
Comcast GDF ECATS API credentials and endpoint configuration
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# GDF SSO Credentials (from environment variables or .env file)
GDF_USERNAME = os.getenv('GDF_USERNAME', '')
GDF_PASSWORD = os.getenv('GDF_PASSWORD', '')

# GDF API Endpoints
GDF_API_BASE = "https://app.catsprd.comcast.net/gdf/gateway/rest"
GDF_AUTH_ENDPOINT = "https://app.catsprd.comcast.net/gdf/gateway/rest/auth/login"
GDF_SSO_ENDPOINT = "https://app.catsprd.comcast.net/gdf/gateway/rest/ssologin"
GDF_SETTOP_ENDPOINT = "https://app.catsprd.comcast.net/gdf/gateway/rest/settop"

# GDF API Configuration
GDF_CONFIG = {
    'api_base': GDF_API_BASE,
    'auth_endpoint': GDF_AUTH_ENDPOINT,
    'sso_endpoint': GDF_SSO_ENDPOINT,
    'settop_endpoint': GDF_SETTOP_ENDPOINT,
    'request_timeout': 15,  # seconds
    'retry_attempts': 3,
    'ssl_verify': True,  # Enable SSL certificate verification
}

# KeySet Mappings (Device Type -> KeySet ID)
GDF_KEYSET_MAP = {
    'XUMO': 'PR1_T2',           # XUMO remote
    'ELEMENT': 'PR1_T2',         # ELEMENT remote (same as XUMO)
    'SKYSTREAM': 'LC103',        # SKY STREAM remote
    'SKY_STREAM': 'LC103',       # Alternative naming
    'SKY': 'LC103',              # Short name
    'STREAM': 'LC103',           # Another variant
}

# IR Key Delay (seconds between sending each key)
GDF_KEY_DELAY = 0.5

# SSH Verification Configuration
GDF_SSH_VERIFY = {
    'enabled': True,  # Enable post-IR SSH verification
    'wait_seconds': 7,  # Wait time before attempting SSH (device wake-up time)
    'log_file': '/opt/logs/sky-messages.log',  # Device log file path
    'timeout': 10,  # SSH timeout in seconds
}


def get_gdf_credentials():
    """
    Get GDF credentials from environment
    
    Returns:
        Tuple: (username, password) or (None, None) if not configured
    """
    return GDF_USERNAME, GDF_PASSWORD


def is_gdf_configured():
    """
    Check if GDF is properly configured with credentials
    
    Returns:
        bool: True if both username and password are set
    """
    return bool(GDF_USERNAME and GDF_PASSWORD)


def describe_gdf_config():
    """Print GDF configuration status"""
    print("\n" + "=" * 70)
    print("[GDF CONFIG] GDF API Configuration Status")
    print("=" * 70)
    print(f"[GDF] SSO Configured: {'✓ YES' if is_gdf_configured() else '✗ NO'}")
    print(f"[GDF] Username: {'***' if GDF_USERNAME else 'Not set (set GDF_USERNAME env)'}")
    print(f"[GDF] Password: {'***' if GDF_PASSWORD else 'Not set (set GDF_PASSWORD env)'}")
    print(f"[GDF] API Base: {GDF_API_BASE}")
    print(f"[GDF] Auth Endpoint: {GDF_AUTH_ENDPOINT}")
    print(f"[GDF] SSH Verify: {'Enabled' if GDF_SSH_VERIFY['enabled'] else 'Disabled'}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    describe_gdf_config()
