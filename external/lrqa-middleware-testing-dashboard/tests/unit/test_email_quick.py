#!/usr/bin/env python3
"""Quick test of email service with SMTP_HOST"""
import os
import sys

# Set environment variables
os.environ['SMTP_HOST'] = 'mailrelay.comcast.com'
os.environ['SMTP_PORT'] = '25'
os.environ['SENDER_EMAIL'] = 'viswachaithanya_patneedi@comcast.com'
os.environ['SENDER_PASSWORD'] = ''

print("="*70)
print("Email Service Test with SMTP_HOST")
print("="*70)

# Import email service
sys.path.insert(0, '/home/pi/Desktop/viswa/Latest_Enhancement/Enhancement')
from services.email_service import EmailService

# Initialize service
email_service = EmailService()

print(f"\n✓ Email Service Initialized")
print(f"  SMTP Host: {email_service.smtp_server}")
print(f"  SMTP Port: {email_service.smtp_port}")
print(f"  Sender Email: {email_service.sender_email}")
print(f"  Enabled: {email_service.enabled}")

if email_service.enabled:
    print("\n✅ Email service is ENABLED and ready to send emails!")
    
    # Ask for recipient
    recipient = input("\nEnter recipient email to send test (or press Enter to skip): ").strip()
    
    if recipient:
        print(f"\nSending test email to {recipient}...")
        success, message = email_service.send_password_reset_email(
            recipient_email=recipient,
            code="123456",
            name="Test User"
        )
        
        if success:
            print(f"✅ {message}")
            print(f"📧 Check inbox at {recipient}")
        else:
            print(f"❌ Failed: {message}")
    else:
        print("\nSkipped email send test")
else:
    print("\n⚠️ Email service is DISABLED")
    print("   SENDER_EMAIL needs to be configured")

print("\n" + "="*70)
