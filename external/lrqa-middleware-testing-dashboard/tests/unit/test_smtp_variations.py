#!/usr/bin/env python3
"""
Test SMTP Connection with Different Username Formats
"""
import smtplib
import getpass

SMTP_SERVER = "smtp.comcast.net"
SMTP_PORT = 587

# Different username formats to try
username_variants = [
    "vpatne290@cable.comcast.com",
    "vpatne290",
    "vpatne290@comcast.com"
]

print("=" * 60)
print("SMTP Connection Test - Multiple Username Formats")
print("=" * 60)
print(f"\nSMTP Server: {SMTP_SERVER}")
print(f"Port: {SMTP_PORT}\n")

password = getpass.getpass("Enter your Comcast email password: ")

for username in username_variants:
    print(f"\n{'='*60}")
    print(f"Testing with username: {username}")
    print('='*60)
    
    try:
        print("[1/3] Connecting to SMTP server...")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
        print("✓ Connected")
        
        print("[2/3] Starting TLS...")
        server.starttls()
        print("✓ TLS enabled")
        
        print(f"[3/3] Authenticating as '{username}'...")
        server.login(username, password)
        print(f"✓✓✓ SUCCESS! Authentication worked with: {username}")
        server.quit()
        
        print("\n" + "="*60)
        print("WORKING CONFIGURATION FOUND:")
        print("="*60)
        print(f"SMTP_SERVER={SMTP_SERVER}")
        print(f"SMTP_PORT={SMTP_PORT}")
        print(f"SENDER_EMAIL={username}")
        print("="*60)
        break
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"✗ Authentication failed: {e}")
        try:
            server.quit()
        except:
            pass
    except Exception as e:
        print(f"✗ Error: {e}")
        try:
            server.quit()
        except:
            pass
else:
    print("\n" + "="*60)
    print("All username formats failed authentication")
    print("="*60)
    print("\nNext steps:")
    print("1. Verify password is correct")
    print("2. Check if account has 2FA enabled")
    print("3. Contact IT for SMTP access requirements")
    print("4. Ask IT for correct username format")
