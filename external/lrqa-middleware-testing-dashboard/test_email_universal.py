#!/usr/bin/env python3
"""
Test Email Sending - Universal SMTP Tester
Tests both Comcast mail relay and Gmail SMTP
"""
import smtplib
import sys
import getpass
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

def test_comcast_relay(recipient):
    """Test Comcast Mail Relay"""
    SMTP_HOST = "mailrelay.comcast.com"
    SMTP_PORT = 25
    SENDER_EMAIL = "viswachaithanya_patneedi@comcast.com"
    
    print("\n" + "="*70)
    print("Testing Comcast Mail Relay")
    print("="*70)
    print(f"Host: {SMTP_HOST}:{SMTP_PORT}")
    print(f"Sender: {SENDER_EMAIL}")
    print("Auth: Not required (mail relay)")
    
    try:
        print("\n[1/3] Connecting to mail relay server...")
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
        print("✅ Connected!")
        
        print("\n[2/3] Sending EHLO...")
        server.ehlo()
        print("✅ EHLO successful!")
        
        print("\n[3/3] Sending test email...")
        msg = MIMEMultipart()
        msg['Subject'] = 'Test Email - Comcast Mail Relay'
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient
        
        body = f"""
Test Email from LRQA MW Testing Dashboard

Configuration: Comcast Mail Relay
Host: {SMTP_HOST}:{SMTP_PORT}
Sender: {SENDER_EMAIL}
Time: {datetime.now()}

If you receive this email, the mail relay configuration is working!
"""
        msg.attach(MIMEText(body, 'plain'))
        server.send_message(msg)
        print("✅ Email sent!")
        
        server.quit()
        return True, "Success"
        
    except Exception as e:
        return False, str(e)

def test_gmail_smtp(recipient):
    """Test Gmail SMTP"""
    SMTP_HOST = "smtp.gmail.com"
    SMTP_PORT = 587
    SENDER_EMAIL = "cperdkemiddleware@gmail.com"
    
    print("\n" + "="*70)
    print("Testing Gmail SMTP")
    print("="*70)
    print(f"Host: {SMTP_HOST}:{SMTP_PORT}")
    print(f"Sender: {SENDER_EMAIL}")
    print("Auth: Required (TLS + App Password)")
    
    password = getpass.getpass("\nEnter Gmail App Password (or press Enter to skip): ")
    if not password:
        print("⚠️ Skipped - No password provided")
        return False, "Skipped"
    
    try:
        print("\n[1/4] Connecting to Gmail SMTP server...")
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
        print("✅ Connected!")
        
        print("\n[2/4] Starting TLS encryption...")
        server.starttls()
        print("✅ TLS enabled!")
        
        print("\n[3/4] Authenticating...")
        server.login(SENDER_EMAIL, password)
        print("✅ Authentication successful!")
        
        print("\n[4/4] Sending test email...")
        msg = MIMEMultipart()
        msg['Subject'] = 'Test Email - Gmail SMTP'
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient
        
        body = f"""
Test Email from LRQA MW Testing Dashboard

Configuration: Gmail SMTP
Host: {SMTP_HOST}:{SMTP_PORT}
Sender: {SENDER_EMAIL}
Time: {datetime.now()}

If you receive this email, the Gmail SMTP configuration is working!
"""
        msg.attach(MIMEText(body, 'plain'))
        server.send_message(msg)
        print("✅ Email sent!")
        
        server.quit()
        return True, "Success"
        
    except smtplib.SMTPAuthenticationError as e:
        return False, f"Authentication failed: {e}"
    except Exception as e:
        return False, str(e)

def main():
    print("="*70)
    print("SMTP Email Configuration Tester")
    print("="*70)
    
    recipient = input("\nEnter recipient email address: ").strip()
    if not recipient:
        print("❌ Recipient email is required!")
        sys.exit(1)
    
    print(f"\nRecipient: {recipient}")
    print("\nWhich configuration would you like to test?")
    print("1) Comcast Mail Relay (mailrelay.comcast.com:25)")
    print("2) Gmail SMTP (smtp.gmail.com:587)")
    print("3) Both")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    results = []
    
    if choice in ['1', '3']:
        success, msg = test_comcast_relay(recipient)
        results.append(('Comcast Mail Relay', success, msg))
    
    if choice in ['2', '3']:
        success, msg = test_gmail_smtp(recipient)
        results.append(('Gmail SMTP', success, msg))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for name, success, msg in results:
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"\n{name}: {status}")
        if not success:
            print(f"  Error: {msg}")
    
    # Check inbox
    print("\n" + "="*70)
    print("📧 Check your inbox for test email(s)")
    print("="*70)
    print(f"Recipient: {recipient}")
    print("Note: Check spam/junk folder if not in inbox")
    
    # Configuration recommendations
    print("\n" + "="*70)
    print("CONFIGURATION RECOMMENDATIONS")
    print("="*70)
    
    comcast_success = any(r[0] == 'Comcast Mail Relay' and r[1] for r in results)
    gmail_success = any(r[0] == 'Gmail SMTP' and r[1] for r in results)
    
    if comcast_success:
        print("\n✅ Use Comcast Mail Relay (Recommended - simpler, no password needed)")
        print("   export SMTP_HOST='mailrelay.comcast.com'")
        print("   export SMTP_PORT='25'")
        print("   export SENDER_EMAIL='viswachaithanya_patneedi@comcast.com'")
        print("   export SENDER_PASSWORD=''")
    elif gmail_success:
        print("\n✅ Use Gmail SMTP (Requires app password)")
        print("   export SMTP_HOST='smtp.gmail.com'")
        print("   export SMTP_PORT='587'")
        print("   export SENDER_EMAIL='cperdkemiddleware@gmail.com'")
        print("   export SENDER_PASSWORD='your-app-password'")
    else:
        print("\n⚠️ Both configurations failed!")
        print("   Possible issues:")
        print("   - Network/firewall blocking SMTP ports")
        print("   - Not on Comcast internal network (for mail relay)")
        print("   - Incorrect Gmail app password")
        print("   - Check network connectivity and try again")

if __name__ == "__main__":
    main()
