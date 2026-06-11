#!/usr/bin/env python3
"""
Test the updated password reset feature with enhanced validation
"""

import requests

BASE_URL = "http://10.0.0.32:8080"

def test_invalid_email_domain():
    """Test that invalid email domains are rejected"""
    print("\n" + "="*70)
    print("TEST 1: Invalid Email Domain")
    print("="*70)
    
    session = requests.Session()
    
    # Try with gmail.com email
    response = session.post(
        f"{BASE_URL}/forgot-password",
        data={
            'ntid': 'vpatne290',
            'email': 'test@gmail.com'
        }
    )
    
    if 'valid Comcast email address' in response.text:
        print("✓ PASS: Invalid email domain rejected (@gmail.com)")
    else:
        print("✗ FAIL: Invalid email domain not properly rejected")
    print()

def test_nonexistent_user():
    """Test that non-existent users are prompted to register"""
    print("="*70)
    print("TEST 2: Non-existent User")
    print("="*70)
    
    session = requests.Session()
    
    response = session.post(
        f"{BASE_URL}/forgot-password",
        data={
            'ntid': 'nonexistent_user',
            'email': 'nonexistent@comcast.com'
        }
    )
    
    if 'No account found' in response.text and 'create an account' in response.text:
        print("✓ PASS: Non-existent user prompted to create account")
    else:
        print("✗ FAIL: Non-existent user not handled correctly")
    print()

def test_mismatched_email():
    """Test that mismatched NTID/email combination is rejected"""
    print("="*70)
    print("TEST 3: Mismatched NTID and Email")
    print("="*70)
    
    session = requests.Session()
    
    response = session.post(
        f"{BASE_URL}/forgot-password",
        data={
            'ntid': 'vpatne290',
            'email': 'wrongemail@comcast.com'
        }
    )
    
    if 'does not match the NTID' in response.text:
        print("✓ PASS: Mismatched NTID/email rejected")
    else:
        print("✗ FAIL: Mismatched NTID/email not properly rejected")
    print()

def test_valid_reset_request():
    """Test that valid NTID/email sends verification code"""
    print("="*70)
    print("TEST 4: Valid Password Reset Request")
    print("="*70)
    print("NTID: vpatne290")
    print("Email: viswachaithanya_patneedi@comcast.com")
    
    session = requests.Session()
    
    response = session.post(
        f"{BASE_URL}/forgot-password",
        data={
            'ntid': 'vpatne290',
            'email': 'viswachaithanya_patneedi@comcast.com'
        },
        allow_redirects=False
    )
    
    if response.status_code == 302 and '/verify-reset-code' in response.headers.get('Location', ''):
        print("✓ PASS: Valid request redirected to verification page")
        print("\n" + "="*70)
        print("CHECK CONSOLE/LOGS FOR 6-DIGIT VERIFICATION CODE")
        print("="*70)
        print("\nRun this command to see the code:")
        print("sudo journalctl -u device-testing.service --since '1 minute ago' | grep 'PASSWORD RESET CODE'")
    else:
        print("✗ FAIL: Valid request not handled correctly")
        print(f"Status: {response.status_code}")
    print()

def test_cable_comcast_email():
    """Test that @cable.comcast.com emails are accepted"""
    print("="*70)
    print("TEST 5: Cable.comcast.com Email Domain")
    print("="*70)
    
    session = requests.Session()
    
    # This will fail with "No account found" but should accept the email domain
    response = session.post(
        f"{BASE_URL}/forgot-password",
        data={
            'ntid': 'test_user',
            'email': 'test@cable.comcast.com'
        }
    )
    
    if 'valid Comcast email address' in response.text:
        print("✗ FAIL: @cable.comcast.com domain incorrectly rejected")
    elif 'No account found' in response.text:
        print("✓ PASS: @cable.comcast.com domain accepted (user doesn't exist)")
    else:
        print("✓ PARTIAL: Email domain accepted")
    print()

if __name__ == "__main__":
    try:
        print("\n" + "="*70)
        print("PASSWORD RESET VALIDATION TESTS")
        print("="*70)
        
        test_invalid_email_domain()
        test_nonexistent_user()
        test_mismatched_email()
        test_cable_comcast_email()
        test_valid_reset_request()
        
        print("="*70)
        print("TESTS COMPLETE")
        print("="*70)
        print()
        
    except requests.exceptions.ConnectionError:
        print("\nERROR: Could not connect to the application")
        print(f"Make sure the app is running at {BASE_URL}")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
