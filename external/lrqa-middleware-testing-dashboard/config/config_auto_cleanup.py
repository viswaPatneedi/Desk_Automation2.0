"""
Auto Cleanup Configuration
==========================
Automatically deletes old logs, screenshots, and job folders to prevent disk space issues.

Features:
  - Clean old log files (>X days)
  - Clean old screenshots (>X days)
  - Clean old job execution folders (>X days)
  - Configurable retention period
  - Dry-run mode for testing
  - Exclusion patterns to prevent accidental deletion
"""

import os
from datetime import datetime, timedelta

# ============================================================
# CLEANUP SETTINGS
# ============================================================

# Enable/disable auto cleanup
AUTO_CLEANUP_ENABLED = os.getenv('AUTO_CLEANUP_ENABLED', 'true').lower() == 'true'

# Days to keep files (delete files older than this)
CLEANUP_RETENTION_DAYS = int(os.getenv('CLEANUP_RETENTION_DAYS', '10'))

# Run cleanup on startup
CLEANUP_ON_STARTUP = os.getenv('CLEANUP_ON_STARTUP', 'true').lower() == 'true'

# ============================================================
# CLEANUP TARGETS
# ============================================================

# Paths to clean (relative to project root or absolute)
CLEANUP_PATHS = {
    'logs': {
        'path': 'logs',
        'enabled': True,
        'pattern': '*.log',
        'description': 'Application log files'
    },
    'job_logs': {
        'path': 'logs/jobs',
        'enabled': True,
        'pattern': None,  # Entire directories
        'description': 'Job execution logs (folders with job ID)'
    },
    'screenshots': {
        'path': 'screenshots',
        'enabled': True,
        'pattern': '*.png',
        'description': 'Captured device screenshots'
    },
    'enhancement_output': {
        'path': 'Enhancement_output',
        'enabled': True,
        'pattern': None,  # Will delete old session folders
        'description': 'Old execution session folders'
    }
}

# ============================================================
# EXCLUSIONS (Prevent accidental deletion)
# ============================================================

# Folder/file patterns to NEVER delete
EXCLUDE_PATTERNS = [
    'README*',
    '*.md',
    '.git*',
    '*.py',
    'config*',
    'current_*',
    'active_*',
    'running_*',
]

# Specific folders to never delete
EXCLUDE_FOLDERS = [
    '.git',
    '__pycache__',
    'venv',
    '.venv',
    'node_modules',
]

# ============================================================
# CLEANUP SCHEDULE
# ============================================================

# Run cleanup at startup
RUN_ON_STARTUP = True

# Schedule cleanup via cron (if using scheduler)
# Format: "0 2 * * *" = every day at 2 AM
CRON_SCHEDULE = os.getenv('CLEANUP_CRON_SCHEDULE', '0 2 * * *')

# Or use time-based interval (seconds)
# 86400 = 24 hours, 3600 = 1 hour, 1800 = 30 minutes
CLEANUP_INTERVAL_SECONDS = int(os.getenv('CLEANUP_INTERVAL_SECONDS', '86400'))  # Daily

# ============================================================
# CLEANUP BEHAVIOR
# ============================================================

# Dry-run mode (show what would be deleted, don't actually delete)
DRY_RUN = os.getenv('CLEANUP_DRY_RUN', 'false').lower() == 'true'

# Verbose logging
VERBOSE = os.getenv('CLEANUP_VERBOSE', 'true').lower() == 'true'

# Calculate threshold date
THRESHOLD_DATE = datetime.now() - timedelta(days=CLEANUP_RETENTION_DAYS)
THRESHOLD_TIMESTAMP = THRESHOLD_DATE.timestamp()

# ============================================================
# CLEANUP STATISTICS
# ============================================================

# Log cleanup statistics
TRACK_STATISTICS = True

# Statistics file
CLEANUP_STATS_FILE = 'logs/cleanup_statistics.json'

# ============================================================
# SAFETY CHECKS
# ============================================================

# Minimum free space to maintain (in gigabytes)
# If below this, trigger cleanup
MINIMUM_FREE_SPACE_GB = float(os.getenv('CLEANUP_MIN_FREE_SPACE_GB', '2.0'))

# Maximum cleanup at once (to prevent system overload)
MAX_ITEMS_PER_RUN = int(os.getenv('CLEANUP_MAX_ITEMS_PER_RUN', '1000'))

# Stop cleanup if less than this free space after deletion
# (safety to prevent filling disk completely)
SAFETY_FREE_SPACE_GB = float(os.getenv('CLEANUP_SAFETY_FREE_SPACE_GB', '1.0'))

# ============================================================
# LOGGING
# ============================================================

CLEANUP_LOG_FILE = 'logs/cleanup.log'
CLEANUP_LOG_LEVEL = os.getenv('CLEANUP_LOG_LEVEL', 'INFO')  # DEBUG, INFO, WARNING, ERROR

# ============================================================
# SUMMARY MESSAGE
# ============================================================

CLEANUP_CONFIG_SUMMARY = f"""
AUTO CLEANUP CONFIGURATION
==========================
Status: {'ENABLED' if AUTO_CLEANUP_ENABLED else 'DISABLED'}
Retention Period: {CLEANUP_RETENTION_DAYS} days
Threshold Date: {THRESHOLD_DATE.strftime('%Y-%m-%d %H:%M:%S')}
Dry-Run Mode: {'YES (no actual deletion)' if DRY_RUN else 'NO (will delete files)'}
Cleanup Interval: {CLEANUP_INTERVAL_SECONDS} seconds ({CLEANUP_INTERVAL_SECONDS/3600:.1f} hours)
Min Free Space: {MINIMUM_FREE_SPACE_GB} GB

CLEANUP TARGETS:
"""

for name, config in CLEANUP_PATHS.items():
    if config['enabled']:
        CLEANUP_CONFIG_SUMMARY += f"  ✓ {config['description']}: {config['path']}\n"
    else:
        CLEANUP_CONFIG_SUMMARY += f"  ✗ {config['description']}: {config['path']} (disabled)\n"

CLEANUP_CONFIG_SUMMARY += f"""
SAFETY SETTINGS:
  Min Free Space: {MINIMUM_FREE_SPACE_GB} GB (trigger cleanup if below)
  Safety Free Space: {SAFETY_FREE_SPACE_GB} GB (stop cleanup if below)
  Max Items Per Run: {MAX_ITEMS_PER_RUN}
  Exclusions: {len(EXCLUDE_PATTERNS)} patterns + {len(EXCLUDE_FOLDERS)} folders
"""
