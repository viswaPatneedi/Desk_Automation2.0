#!/usr/bin/env python3
"""
Quick test script to verify email service is working
"""
import os
import sys

# Test environment variables are set
print("=" * 60)
print("EMAIL CONFIGURATION TEST")
print("=" * 60)

smtp_server = os.environ.get('SMTP_SERVER', 'NOT SET')
smtp_port = os.environ.get('SMTP_PORT', 'NOT SET')
sender_email = os.environ.get('SENDER_EMAIL', 'NOT SET')
sender_password = os.environ.get('SENDER_PASSWORD', 'NOT SET')

print(f"\n1. Environment Variables:")
print(f"   SMTP_SERVER: {smtp_server}")
print(f"   SMTP_PORT: {smtp_port}")
print(f"   SENDER_EMAIL: {sender_email}")
print(f"   SENDER_PASSWORD: {'SET (hidden)' if sender_password != 'NOT SET' else 'NOT SET'}")

if smtp_server == 'NOT SET' or sender_password == 'NOT SET':
    print("\n❌ Email configuration is missing!")
    print("\nTo fix, run:")
    print("  export SMTP_SERVER='smtp.gmail.com'")
    print("  export SMTP_PORT='587'")
    print("  export SENDER_EMAIL='cperdkemiddleware@gmail.com'")
    print("  export SENDER_PASSWORD='your-app-password'")
    sys.exit(1)

# Test EmailService initialization
print(f"\n2. Testing EmailService initialization...")
try:
    from services.email_service import EmailService
    email_service = EmailService()
    print(f"   ✓ EmailService initialized")
    print(f"   ✓ Enabled: {email_service.enabled}")
    print(f"   ✓ SMTP: {email_service.smtp_server}:{email_service.smtp_port}")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    sys.exit(1)

# Prompt for test email
print(f"\n3. Send test email?")
recipient = input("   Enter recipient email (or press Enter to skip): ").strip()

if recipient:
    print(f"\n   Sending test email to {recipient}...")
    try:
        # Send a simple test execution email
        job_data = {
            'job_id': 'test-123',
            'device_name': 'TestDevice',
            'device_ip': '10.0.0.1',
            'methods': ['reboot_performance'],
            'status': 'completed',
            'start_time': '2026-01-06 15:00:00',
            'end_time': '2026-01-06 15:02:00',
            'iterations': 1,
            'iterations_completed': 1,
            'sequence_name': 'Test Sequence',
            'iteration_results': {}
        }
        
        success, message = email_service.send_execution_results_email(
            recipient, 
            job_data,
            []  # No attachments for test
        )
        
        if success:
            print(f"   ✅ Test email sent successfully!")
        else:
            print(f"   ❌ Failed to send: {message}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
else:
    print("   ⏭️  Skipped test email")

print("\n" + "=" * 60)
print("EMAIL CONFIGURATION TEST COMPLETE")
print("=" * 60)
