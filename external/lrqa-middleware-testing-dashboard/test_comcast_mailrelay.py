#!/usr/bin/env python3
"""
Test SMTP Connection for Comcast Mail Relay
Tests email sending via mailrelay.comcast.com (port 25, no auth)
"""
import smtplib
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# SMTP Configuration for Comcast Mail Relay
SMTP_HOST = "mailrelay.comcast.com"
SMTP_PORT = 25
SENDER_EMAIL = "viswachaithanya_patneedi@comcast.com"

print("="*70)
print("SMTP Connection Test - Comcast Mail Relay")
print("="*70)
print(f"\nSMTP Host: {SMTP_HOST}")
print(f"Port: {SMTP_PORT}")
print(f"Sender: {SENDER_EMAIL}")
print(f"Authentication: Not required (internal relay)")

# Get recipient email
recipient = input("\nEnter recipient email address to test: ").strip()
if not recipient:
    print("❌ Recipient email is required!")
    sys.exit(1)

print(f"\n{'='*70}")
print("Testing Email Delivery...")
print(f"{'='*70}\n")

try:
    # Step 1: Connect to SMTP server
    print("[1/4] Connecting to SMTP server...")
    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
    print("✅ Connection successful!")
    
    # Step 2: Test EHLO
    print("\n[2/4] Sending EHLO command...")
    server.ehlo()
    print("✅ EHLO successful!")
    
    # Note: No STARTTLS or authentication needed for mail relay
    print("\n[3/4] Authentication: Skipped (mail relay doesn't require auth)")
    print("✅ Mail relay access granted!")
    
    # Step 3: Send test email
    print("\n[4/4] Testing email send capability...")
    msg = MIMEMultipart()
    msg['Subject'] = 'SMTP Test - LRQA MW Testing Dashboard (Comcast Mail Relay)'
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient
    
    body = f"""
    SMTP Test Email - Comcast Mail Relay
    
    This is a test email sent from the LRQA MW Testing Dashboard.
    
    If you receive this email, your SMTP configuration is working correctly!
    
    Configuration Details:
    SMTP Host: {SMTP_HOST}
    Port: {SMTP_PORT}
    Sender: {SENDER_EMAIL}
    Authentication: Not required (internal mail relay)
    
    ---
    Sent: {smtplib.SMTP.__module__}
    Test Script: test_comcast_mailrelay.py
    """
    
    msg.attach(MIMEText(body, 'plain'))
    
    server.send_message(msg)
    print("✅ Email sent successfully!")
    
    server.quit()
    
    print(f"\n{'='*70}")
    print("🎉 ALL TESTS PASSED!")
    print(f"{'='*70}")
    print(f"\n✅ Email sent to: {recipient}")
    print(f"✅ From: {SENDER_EMAIL}")
    print(f"✅ Via: {SMTP_HOST}:{SMTP_PORT}")
    print("\n📧 Check your inbox (and spam folder) for the test email.")
    print("\nYour email configuration is ready to use!")
    print("\nTo configure your application, run:")
    print("  ./setup_email.sh")
    print("Or set environment variables:")
    print(f"  export SMTP_HOST='{SMTP_HOST}'")
    print(f"  export SMTP_PORT='{SMTP_PORT}'")
    print(f"  export SENDER_EMAIL='{SENDER_EMAIL}'")
    print(f"  export SENDER_PASSWORD=''  # Not required")
    
except ConnectionRefusedError:
    print(f"❌ Connection refused!")
    print(f"   The SMTP server {SMTP_HOST}:{SMTP_PORT} is not reachable.")
    print(f"   Check network connectivity and firewall settings.")
    sys.exit(1)
    
except smtplib.SMTPException as e:
    print(f"❌ SMTP Error: {e}")
    print(f"   Check server address and port.")
    sys.exit(1)
    
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
