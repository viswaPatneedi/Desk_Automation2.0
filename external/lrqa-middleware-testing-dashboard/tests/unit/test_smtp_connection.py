#!/usr/bin/env python3
"""
Test SMTP Connection for Comcast Email
"""
import smtplib
import getpass
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# SMTP Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "cperdkemiddleware@gmail.com"

print("=" * 60)
print("SMTP Connection Test - Gmail")
print("=" * 60)
print(f"\nSMTP Server: {SMTP_SERVER}")
print(f"Port: {SMTP_PORT}")
print(f"Username: {SENDER_EMAIL}")
print(f"Encryption: STARTTLS\n")

# Prompt for password securely
password = getpass.getpass("Enter your Comcast email password: ")

try:
    print("\n[1/4] Connecting to SMTP server...")
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
    print("✓ Connected successfully")
    
    print("\n[2/4] Starting TLS encryption...")
    server.starttls()
    print("✓ TLS encryption enabled")
    
    print("\n[3/4] Authenticating with credentials...")
    server.login(SENDER_EMAIL, password)
    print("✓ Authentication successful")
    
    print("\n[4/4] Testing email send capability...")
    # Create a test message
    msg = MIMEMultipart()
    msg['Subject'] = 'SMTP Test - LRQA MW Testing Dashboard'
    msg['From'] = SENDER_EMAIL
    msg['To'] = SENDER_EMAIL  # Send to yourself as a test
    
    body = """
    This is a test email from the LRQA MW Testing Dashboard.
    
    If you receive this email, your SMTP configuration is working correctly!
    
    SMTP Server: smtp.comcast.net
    Port: 587
    Encryption: STARTTLS
    """
    msg.attach(MIMEText(body, 'plain'))
    
    # Try to send
    server.send_message(msg)
    print("✓ Test email sent successfully")
    
    server.quit()
    
    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED")
    print("=" * 60)
    print(f"\nYour SMTP configuration is working correctly!")
    print(f"A test email has been sent to: {SENDER_EMAIL}")
    print(f"\nYou can now use these settings in your application:")
    print(f"  export SMTP_SERVER='{SMTP_SERVER}'")
    print(f"  export SMTP_PORT='{SMTP_PORT}'")
    print(f"  export SENDER_EMAIL='{SENDER_EMAIL}'")
    print(f"  export SENDER_PASSWORD='your_password'")
    print("\n")

except smtplib.SMTPAuthenticationError as e:
    print("\n✗ Authentication failed")
    print(f"Error: {e}")
    print("\nPossible issues:")
    print("  - Incorrect password")
    print("  - Account requires app-specific password")
    print("  - Two-factor authentication is enabled")
    print("  - Account is locked or disabled")

except smtplib.SMTPConnectError as e:
    print("\n✗ Connection failed")
    print(f"Error: {e}")
    print("\nPossible issues:")
    print("  - SMTP server is down or unreachable")
    print("  - Firewall blocking port 587")
    print("  - Network connectivity issue")

except smtplib.SMTPException as e:
    print("\n✗ SMTP error occurred")
    print(f"Error: {e}")

except Exception as e:
    print("\n✗ Unexpected error")
    print(f"Error: {type(e).__name__}: {e}")

finally:
    try:
        server.quit()
    except:
        pass

print("\n")
