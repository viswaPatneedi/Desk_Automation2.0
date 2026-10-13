"""
Slack Notification Configuration - Desk Automation v2.0 (Global)
Mirrors the device-health-dashboard Slack pattern:
  - Bot token comes from the SLACK_BOT_TOKEN environment variable (never committed).
  - Channel / enable flags come from environment variables (with .env support).
"""

import os

# Try to load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed, just use os.getenv
    pass

# ===========================
# Slack Configuration
# ===========================

# Application identity shown in Slack messages (differentiates Standalone vs V2.0)
APP_DISPLAY_NAME = os.getenv('SLACK_APP_NAME', 'Desk Automation v2.0 (Global)')

# Bot token for chat.postMessage (REQUIRED - set in environment or .env)
SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN', '')

# Channel that receives job notifications (env override allowed)
SLACK_CHANNEL = os.getenv('SLACK_CHANNEL', 'desk_automation_v2')

# Optional debug/development channel
SLACK_DEBUG_CHANNEL = os.getenv('SLACK_DEBUG_CHANNEL', 'desk_automation_v2_dev')

# Feature toggles
SLACK_ENABLED = os.getenv('SLACK_ENABLED', 'true').lower() == 'true'
SLACK_NOTIFY_ON_START = os.getenv('SLACK_NOTIFY_ON_START', 'true').lower() == 'true'
SLACK_NOTIFY_ON_COMPLETE = os.getenv('SLACK_NOTIFY_ON_COMPLETE', 'true').lower() == 'true'
SLACK_NOTIFY_ON_FAILURE = os.getenv('SLACK_NOTIFY_ON_FAILURE', 'true').lower() == 'true'
SLACK_NOTIFY_ON_CANCEL = os.getenv('SLACK_NOTIFY_ON_CANCEL', 'true').lower() == 'true'

# Dashboard base URL used for the "Open Dashboard" link in messages
DASHBOARD_BASE_URL = os.getenv('DASHBOARD_BASE_URL', 'http://10.26.52.151:11079')

# Slack API settings
SLACK_API_URL = 'https://slack.com/api/chat.postMessage'
SLACK_TIMEOUT = 10  # seconds
SLACK_USERNAME = os.getenv('SLACK_USERNAME', APP_DISPLAY_NAME)
SLACK_ICON_EMOJI = os.getenv('SLACK_ICON_EMOJI', ':robot_face:')

print("[CONFIG] Slack Configuration Loaded:")
print(f"  - App: {APP_DISPLAY_NAME}")
print(f"  - Channel: {SLACK_CHANNEL}")
print(f"  - Enabled: {SLACK_ENABLED}")
print(f"  - Bot Token Configured: {bool(SLACK_BOT_TOKEN)}")
