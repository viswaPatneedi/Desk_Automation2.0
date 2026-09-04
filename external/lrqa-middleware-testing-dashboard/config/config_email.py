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

# SMTP Configuration - Comcast (smtp.gmail.com is blocked on this network)
# mailrelay.comcast.com:25 rejects this host with "421 4.3.2 Service not available",
# so authenticated submission via smtp.comcast.net:587 (STARTTLS) is used instead.
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.comcast.net')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SENDER_EMAIL = os.getenv('SENDER_EMAIL', 'vpatne290@cable.comcast.com')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD', '')  # Set in .env - never commit

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
SMTP_USE_TLS = SMTP_PORT == 587
SMTP_TIMEOUT = 30

# Retry Settings
MAX_EMAIL_RETRIES = 3
EMAIL_RETRY_DELAY = 5  # seconds

print("[CONFIG] Email Configuration Loaded:")
print(f"  - SMTP Server: {SMTP_SERVER}:{SMTP_PORT}")
print(f"  - Sender Email: {SENDER_EMAIL}")
print(f"  - Email Enabled: {EMAIL_ENABLED}")
print(f"  - Email on Completion: {EMAIL_ON_COMPLETION}")
print(f"  - Email on Failure: {EMAIL_ON_FAILURE}")
