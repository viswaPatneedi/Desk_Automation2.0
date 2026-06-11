"""
Email Configuration - Unified Gmail SMTP Configuration
Handles all email-related settings for the RDK-E Middleware QA Testing Tool
"""

import os

# Try to load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed, just use os.getenv
    pass

# Gmail SMTP Configuration
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SENDER_EMAIL = os.getenv('SENDER_EMAIL', 'cperdkemiddleware@gmail.com')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD', 'tbbwaifvmtzovqcs')  # Replace with new app password from Google

# Email Service Settings
EMAIL_ENABLED = os.getenv('EMAIL_ENABLED', 'true').lower() == 'true'
EMAIL_ON_COMPLETION = os.getenv('EMAIL_ON_COMPLETION', 'true').lower() == 'true'
EMAIL_ON_FAILURE = os.getenv('EMAIL_ON_FAILURE', 'true').lower() == 'true'

# Email subject and body templates
EMAIL_SUBJECT_COMPLETION = "🎉 Test Execution Completed: {job_id}"
EMAIL_SUBJECT_FAILURE = "❌ Test Execution Failed: {job_id}"

# Email recipients (can be overridden per user)
DEFAULT_RECIPIENTS = []

# SMTP Connection Settings
SMTP_USE_TLS = True
SMTP_TIMEOUT = 10

# Retry Settings
MAX_EMAIL_RETRIES = 3
EMAIL_RETRY_DELAY = 5  # seconds

print("[CONFIG] Email Configuration Loaded:")
print(f"  - SMTP Server: {SMTP_SERVER}:{SMTP_PORT}")
print(f"  - Sender Email: {SENDER_EMAIL}")
print(f"  - Email Enabled: {EMAIL_ENABLED}")
print(f"  - Email on Completion: {EMAIL_ON_COMPLETION}")
print(f"  - Email on Failure: {EMAIL_ON_FAILURE}")
