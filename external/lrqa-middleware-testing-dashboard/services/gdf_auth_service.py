#!/usr/bin/env python3
"""
GDF SSO Authentication Service
Handles Comcast GDF API SSO login and session management
"""

import os
import requests
import json
from datetime import datetime, timezone
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from methods.method_utils import log_message

try:
    from config.config_gdf_api import (
        GDF_USERNAME, GDF_PASSWORD, GDF_API_BASE, 
        GDF_AUTH_ENDPOINT, GDF_SSO_ENDPOINT, GDF_CONFIG
    )
except ImportError:
    # Fallback if config not available
    GDF_USERNAME = os.getenv('GDF_USERNAME', '')
    GDF_PASSWORD = os.getenv('GDF_PASSWORD', '')
    GDF_API_BASE = "https://app.catsprd.comcast.net/gdf/gateway/rest"
    GDF_AUTH_ENDPOINT = "https://app.catsprd.comcast.net/gdf/gateway/rest/auth/login"
    GDF_SSO_ENDPOINT = "https://app.catsprd.comcast.net/gdf/gateway/rest/ssologin"
    GDF_CONFIG = {'request_timeout': 15}


class GDFAuthService:
    """
    Manages authentication with Comcast GDF ECATS API
    Supports SSO login and session cookie management
    """
    
    def __init__(self, gdf_username=None, gdf_password=None):
        """
        Initialize GDF Auth Service
        
        Args:
            gdf_username: GDF SSO username (from env: GDF_USERNAME)
            gdf_password: GDF SSO password (from env: GDF_PASSWORD)
        """
        self.gdf_username = gdf_username or GDF_USERNAME
        self.gdf_password = gdf_password or GDF_PASSWORD
        self.gdf_api_base = GDF_API_BASE
        self.gdf_auth_endpoint = GDF_AUTH_ENDPOINT
        self.gdf_sso_endpoint = GDF_SSO_ENDPOINT
        self.request_timeout = GDF_CONFIG.get('request_timeout', 15)
        
        # Create session with retry strategy
        self.session = requests.Session()
        self.session.verify = True  # SSL verification enabled
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.is_authenticated = False
        self.auth_token = None
        self.session_cookie = None
        self.last_auth_time = None
    
    def login_with_credentials(self):
        """
        Authenticate with GDF API using username/password
        
        Returns:
            Tuple: (success: bool, message: str, token: str or None)
        """
        if not self.gdf_username or not self.gdf_password:
            log_message("❌ [GDF AUTH] GDF_USERNAME and GDF_PASSWORD environment variables not set")
            return False, "GDF credentials not configured", None
        
        try:
            log_message(f"[GDF AUTH] Attempting SSO login for user: {self.gdf_username}")
            
            # Prepare login payload
            login_payload = {
                "username": self.gdf_username,
                "password": self.gdf_password
            }
            
            # Try direct auth endpoint first
            response = self.session.post(
                self.gdf_auth_endpoint,
                json=login_payload,
                timeout=self.request_timeout,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
            
            if response.status_code == 200 or response.status_code == 302:
                log_message(f"✓ [GDF AUTH] Authentication successful (HTTP {response.status_code})")
                
                # Try to extract token from response
                try:
                    resp_data = response.json()
                    self.auth_token = resp_data.get('token') or resp_data.get('access_token')
                    if self.auth_token:
                        log_message(f"✓ [GDF AUTH] Auth token obtained")
                        self.is_authenticated = True
                        self.last_auth_time = datetime.now(timezone.utc)
                        return True, "Authentication successful", self.auth_token
                except:
                    pass
                
                # Check for session cookies
                if self.session.cookies:
                    log_message(f"✓ [GDF AUTH] Session cookies obtained")
                    self.is_authenticated = True
                    self.last_auth_time = datetime.now(timezone.utc)
                    return True, "Authentication successful (cookie-based)", None
                
                return True, "Authentication successful", self.auth_token
            
            else:
                log_message(f"❌ [GDF AUTH] Authentication failed (HTTP {response.status_code})")
                log_message(f"   Response: {response.text[:300]}")
                return False, f"Auth failed: HTTP {response.status_code}", None
        
        except requests.Timeout:
            log_message("❌ [GDF AUTH] Authentication timeout (>15s)")
            return False, "Authentication timeout", None
        
        except requests.ConnectionError as e:
            log_message(f"❌ [GDF AUTH] Connection error: {e}")
            return False, f"Connection error: {str(e)[:100]}", None
        
        except Exception as e:
            log_message(f"❌ [GDF AUTH] Unexpected error: {e}")
            import traceback
            log_message(f"   Traceback: {traceback.format_exc()}")
            return False, f"Unexpected error: {str(e)[:100]}", None
    
    def get_authorization_header(self):
        """
        Get authorization header for GDF API requests
        
        Returns:
            Dict: Header dict with Authorization or empty if not authenticated
        """
        if self.auth_token:
            return {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            }
        
        # Session cookies will be sent automatically by requests.Session
        return {
            "Content-Type": "application/json"
        }
    
    def make_gdf_request(self, endpoint, method="GET", **kwargs):
        """
        Make authenticated request to GDF API
        
        Args:
            endpoint: API endpoint path (e.g., '/settop/{mac}/ir/pressKey')
            method: HTTP method (GET, POST, etc.)
            **kwargs: Additional arguments for requests (data, json, params, etc.)
        
        Returns:
            Tuple: (success: bool, status_code: int, response_text: str)
        """
        if not self.is_authenticated:
            log_message("⚠ [GDF API] Not authenticated, attempting login...")
            success, msg, _ = self.login_with_credentials()
            if not success:
                return False, 401, f"Not authenticated: {msg}"
        
        try:
            url = f"{self.gdf_api_base}{endpoint}"
            headers = self.get_authorization_header()
            
            if method.upper() == "GET":
                response = self.session.get(url, headers=headers, timeout=10, **kwargs)
            elif method.upper() == "POST":
                response = self.session.post(url, headers=headers, timeout=10, **kwargs)
            elif method.upper() == "PUT":
                response = self.session.put(url, headers=headers, timeout=10, **kwargs)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, headers=headers, timeout=10, **kwargs)
            else:
                return False, 0, f"Unsupported method: {method}"
            
            if response.status_code == 401:
                # Try to re-authenticate
                log_message("⚠ [GDF API] Got 401, re-authenticating...")
                success, msg, _ = self.login_with_credentials()
                if success:
                    # Retry the request
                    headers = self.get_authorization_header()
                    if method.upper() == "GET":
                        response = self.session.get(url, headers=headers, timeout=10, **kwargs)
                    elif method.upper() == "POST":
                        response = self.session.post(url, headers=headers, timeout=10, **kwargs)
            
            return True, response.status_code, response.text
        
        except requests.Timeout:
            log_message(f"❌ [GDF API] Timeout: {endpoint}")
            return False, 0, "Timeout"
        
        except requests.ConnectionError as e:
            log_message(f"❌ [GDF API] Connection error: {e}")
            return False, 0, f"Connection error: {str(e)[:100]}"
        
        except Exception as e:
            log_message(f"❌ [GDF API] Error: {e}")
            return False, 0, f"Error: {str(e)[:100]}"
    
    def send_ir_command(self, mac_address, ir_key, keyset):
        """
        Send IR command via GDF API
        
        Args:
            mac_address: Device MAC address
            ir_key: IR key command
            keyset: Remote type (PR1_T2 or LC103)
        
        Returns:
            Tuple: (success: bool, status_code: int, message: str)
        """
        endpoint = f"/settop/{mac_address}/ir/pressKey?command={ir_key}&keySet={keyset}"
        success, status_code, response = self.make_gdf_request(endpoint, method="GET")
        
        if success and status_code == 200:
            log_message(f"✓ [GDF IR] Key '{ir_key}' sent successfully")
            return True, status_code, response[:100]
        else:
            log_message(f"❌ [GDF IR] Failed to send key '{ir_key}' (HTTP {status_code})")
            return False, status_code, response[:200]
    
    def close(self):
        """Close the session"""
        if self.session:
            self.session.close()
            log_message("[GDF AUTH] Session closed")


# Global instance
_gdf_auth_instance = None


def get_gdf_auth_service():
    """Get or create GDF auth service instance"""
    global _gdf_auth_instance
    if _gdf_auth_instance is None:
        _gdf_auth_instance = GDFAuthService()
    return _gdf_auth_instance


def authenticate_gdf():
    """
    Authenticate with GDF API
    
    Returns:
        Tuple: (success: bool, message: str)
    """
    service = get_gdf_auth_service()
    success, message, _ = service.login_with_credentials()
    return success, message
