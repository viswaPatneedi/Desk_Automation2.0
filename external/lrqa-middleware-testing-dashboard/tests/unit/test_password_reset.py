#!/usr/bin/env python3
"""
Test script for password reset functionality
This script demonstrates the password reset flow without using a web browser
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://10.0.0.32:8080"

def test_password_reset_flow():
    """Test the complete password reset flow"""
    
    print("=" * 70)
    print("Password Reset Feature Test")
    print("=" * 70)
    print()
    
    # Test user credentials
    test_ntid = "vpatne290"
    test_email = "viswachaithanya_patneedi@comcast.com"
    
    # Step 1: Request password reset
    print("[Step 1] Requesting password reset...")
    print(f"NTID: {test_ntid}")
    print(f"Email: {test_email}")
    print()
    
    session = requests.Session()
    
    response = session.post(
        f"{BASE_URL}/forgot-password",
        data={
            'ntid': test_ntid,
            'email': test_email
        },
        allow_redirects=False
    )
    
    if response.status_code == 302:  # Redirect to verify code page
        print("✓ Password reset request successful!")
        print("→ Redirected to verification code page")
        print()
        print("=" * 70)
        print("CHECK THE APPLICATION CONSOLE FOR THE 6-DIGIT CODE")
        print("=" * 70)
        print()
        print("The verification code will be displayed in the terminal where")
        print("the Flask application is running. Look for output like:")
        print()
        print("    ============================================================")
        print(f"    PASSWORD RESET CODE FOR {test_email}: 123456")
        print("    Code expires in 10 minutes")
        print("    ============================================================")
        print()
    else:
        print(f"✗ Password reset request failed")
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        return
    
    # Step 2: Instructions for manual verification
    print("[Step 2] Verification Code Entry")
    print("To complete the password reset:")
    print(f"1. Open browser to: {BASE_URL}/verify-reset-code")
    print("2. Enter the 6-digit code from the console")
    print("3. Click 'Verify Code'")
    print()
    
    # Step 3: Instructions for password reset
    print("[Step 3] New Password Entry")
    print("After verification:")
    print(f"1. You'll be redirected to: {BASE_URL}/reset-password")
    print("2. Enter your new password (minimum 8 characters)")
    print("3. Confirm the password")
    print("4. Click 'Reset Password'")
    print()
    
    # Step 4: Instructions for login
    print("[Step 4] Login with New Password")
    print("After password reset:")
    print(f"1. Navigate to: {BASE_URL}/login")
    print("2. Enter your NTID or Email")
    print("3. Enter your new password")
    print("4. Click 'Sign In'")
    print()
    
    print("=" * 70)
    print("Test Complete!")
    print("=" * 70)
    print()
    print("IMPORTANT NOTES:")
    print("- The verification code expires in 10 minutes")
    print("- Each code can only be used once")
    print("- In production, codes are sent via email")
    print("- In development, codes are printed to console")
    print()

def test_invalid_credentials():
    """Test with invalid NTID/email combination"""
    
    print("=" * 70)
    print("Testing Invalid Credentials")
    print("=" * 70)
    print()
    
    session = requests.Session()
    
    response = session.post(
        f"{BASE_URL}/forgot-password",
        data={
            'ntid': 'invalid_user',
            'email': 'wrong@comcast.com'
        }
    )
    
    if "If an account with this NTID and email exists" in response.text:
        print("✓ Security feature working: No user enumeration")
        print("  (Same message shown for valid and invalid users)")
    else:
        print("✗ Unexpected response")
    
    print()

if __name__ == "__main__":
    try:
        # Test valid flow
        test_password_reset_flow()
        
        # Test invalid credentials
        test_invalid_credentials()
        
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to the application")
        print(f"Make sure the app is running at {BASE_URL}")
    except Exception as e:
        print(f"ERROR: {e}")
