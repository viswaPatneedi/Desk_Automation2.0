#!/usr/bin/env python3
"""
GDF SSO Authentication Test Script
Verifies that Comcast GDF API SSO authentication is configured correctly
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

def test_gdf_credentials():
    """Test if GDF credentials are configured"""
    print("\n" + "="*70)
    print("[TEST 1] GDF Credentials Configuration")
    print("="*70)
    
    gdf_username = os.getenv('GDF_USERNAME', '')
    gdf_password = os.getenv('GDF_PASSWORD', '')
    
    if not gdf_username:
        print("❌ GDF_USERNAME not set in environment")
        return False
    
    if not gdf_password:
        print("❌ GDF_PASSWORD not set in environment")
        return False
    
    print(f"✓ GDF_USERNAME: {gdf_username[:3]}{'*' * (len(gdf_username)-3)}")
    print(f"✓ GDF_PASSWORD: {'*' * len(gdf_password)}")
    print("✓ Credentials configured\n")
    return True


def test_gdf_config_import():
    """Test if GDF config can be imported"""
    print("="*70)
    print("[TEST 2] Import GDF Configuration Module")
    print("="*70)
    
    try:
        from config.config_gdf_api import (
            GDF_USERNAME, GDF_PASSWORD, GDF_API_BASE,
            GDF_AUTH_ENDPOINT, is_gdf_configured
        )
        print("✓ Successfully imported config_gdf_api")
        print(f"  - API Base: {GDF_API_BASE}")
        print(f"  - Auth Endpoint: {GDF_AUTH_ENDPOINT}")
        print(f"  - Config Status: {'Configured' if is_gdf_configured() else 'Not configured'}\n")
        return True
    
    except ImportError as e:
        print(f"❌ Failed to import config_gdf_api: {e}\n")
        return False
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}\n")
        return False


def test_gdf_auth_service_import():
    """Test if GDF auth service can be imported"""
    print("="*70)
    print("[TEST 3] Import GDF Authentication Service")
    print("="*70)
    
    try:
        from services.gdf_auth_service import GDFAuthService, get_gdf_auth_service
        print("✓ Successfully imported GDFAuthService")
        
        # Try to get instance
        service = get_gdf_auth_service()
        print("✓ Successfully created auth service instance")
        print(f"  - Username: {service.gdf_username[:3] if service.gdf_username else 'Not set'}***")
        print(f"  - Session: {type(service.session).__name__}")
        print(f"  - Authenticated: {service.is_authenticated}\n")
        return True
    
    except ImportError as e:
        print(f"❌ Failed to import GDFAuthService: {e}\n")
        return False
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}\n")
        return False


def test_gdf_authentication():
    """Test actual authentication with GDF API"""
    print("="*70)
    print("[TEST 4] GDF API Authentication (SSO Login)")
    print("="*70)
    
    try:
        from services.gdf_auth_service import get_gdf_auth_service
        from methods.method_utils import log_message
        
        service = get_gdf_auth_service()
        
        if not service.gdf_username or not service.gdf_password:
            print("❌ GDF credentials not configured")
            print("   Set GDF_USERNAME and GDF_PASSWORD environment variables\n")
            return False
        
        print(f"Attempting login with username: {service.gdf_username[:3]}***")
        success, message, token = service.login_with_credentials()
        
        if success:
            print(f"✓ Authentication successful!")
            print(f"  - Message: {message}")
            if token:
                print(f"  - Token: {token[:20]}***")
            print(f"  - Session authenticated: {service.is_authenticated}\n")
            return True
        else:
            print(f"❌ Authentication failed!")
            print(f"  - Message: {message}\n")
            return False
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        print(traceback.format_exc())
        return False


def test_gdf_ir_command_import():
    """Test if GDF IR test method can be imported"""
    print("="*70)
    print("[TEST 5] Import GDF IR Test Method")
    print("="*70)
    
    try:
        from methods.method_gdf_ir_test import (
            determine_keyset, send_gdf_ir_command, execute_gdf_ir_test_process
        )
        print("✓ Successfully imported method_gdf_ir_test functions")
        
        # Test keyset determination
        keyset_xumo = determine_keyset("XUMO")
        keyset_sky = determine_keyset("SKYSTREAM")
        
        print(f"  - XUMO -> KeySet: {keyset_xumo}")
        print(f"  - SKYSTREAM -> KeySet: {keyset_sky}")
        print(f"  - Mapping correct: {keyset_xumo == 'PR1_T2' and keyset_sky == 'LC103'}\n")
        return True
    
    except ImportError as e:
        print(f"❌ Failed to import method_gdf_ir_test: {e}\n")
        return False
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}\n")
        return False


def test_network_connectivity():
    """Test connectivity to GDF API endpoint"""
    print("="*70)
    print("[TEST 6] Network Connectivity to GDF API")
    print("="*70)
    
    try:
        import socket
        
        host = "app.catsprd.comcast.net"
        port = 443
        
        print(f"Testing connection to {host}:{port}...")
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        
        try:
            result = sock.connect_ex((host, port))
            if result == 0:
                print(f"✓ Connected to {host}:{port}")
                sock.close()
                return True
            else:
                print(f"❌ Cannot connect to {host}:{port}")
                print(f"   Error code: {result}")
                return False
        
        finally:
            sock.close()
    
    except Exception as e:
        print(f"❌ Network test failed: {e}\n")
        return False


def test_ssl_certificate():
    """Test SSL certificate validity"""
    print("="*70)
    print("[TEST 7] SSL Certificate Validation")
    print("="*70)
    
    try:
        import ssl
        import socket
        
        host = "app.catsprd.comcast.net"
        port = 443
        
        context = ssl.create_default_context()
        
        with socket.create_connection((host, port), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                
                if cert:
                    subject = dict(x[0] for x in cert.get('subject', ()))
                    common_name = subject.get('commonName', 'Unknown')
                    
                    print(f"✓ SSL Certificate Valid")
                    print(f"  - Common Name: {common_name}")
                    print(f"  - Issuer: {dict(x[0] for x in cert.get('issuer', ()))}")
                    print(f"  - Certificate: Valid\n")
                    return True
                else:
                    print(f"❌ No certificate found\n")
                    return False
    
    except Exception as e:
        print(f"❌ SSL certificate check failed: {e}\n")
        return False


def main():
    """Run all tests"""
    print("\n")
    print("╔" + "═"*68 + "╗")
    print("║" + " "*15 + "GDF SSO AUTHENTICATION TEST SUITE" + " "*20 + "║")
    print("╚" + "═"*68 + "╝")
    
    tests = [
        ("Credentials Config", test_gdf_credentials),
        ("Config Import", test_gdf_config_import),
        ("Auth Service Import", test_gdf_auth_service_import),
        ("GDF Authentication", test_gdf_authentication),
        ("IR Test Method Import", test_gdf_ir_command_import),
        ("Network Connectivity", test_network_connectivity),
        ("SSL Certificate", test_ssl_certificate),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' failed with exception: {e}\n")
            results.append((test_name, False))
    
    # Summary
    print("="*70)
    print("[SUMMARY] Test Results")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print("="*70)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All tests passed! GDF SSO is properly configured.\n")
        return 0
    else:
        print("❌ Some tests failed. Please review the errors above.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
