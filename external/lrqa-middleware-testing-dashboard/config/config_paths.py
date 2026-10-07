"""
Centralized Path Configuration
All data file paths are defined here for easy maintenance and consistency.
"""

import os

# Get the base directory (project root)
# Go up one level from config/ directory to reach project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'Json')
LOGS_DIR = os.path.join(BASE_DIR, 'iteration_logs')
SCREENSHOTS_DIR = os.path.join(BASE_DIR, 'screenshots')


def _inventory_path(env_name, default_path):
    """Resolve a per-deployment inventory file path from an env override.

    Returns ``default_path`` when the override is unset; otherwise validates
    that the override is an absolute, existing, readable+writable file.
    """
    configured_path = os.environ.get(env_name)
    if not configured_path:
        return default_path
    configured_path = os.path.expanduser(configured_path)
    if not os.path.isabs(configured_path):
        raise ValueError(f'{env_name} must be an absolute path: {configured_path}')
    configured_path = os.path.abspath(configured_path)
    if not os.path.isfile(configured_path):
        raise FileNotFoundError(f'{env_name} does not exist or is not a file: {configured_path}')
    if not os.access(configured_path, os.R_OK | os.W_OK):
        raise PermissionError(f'{env_name} must be readable and writable by the application: {configured_path}')
    return configured_path


_devices_override = os.environ.get('APP_DEVICES_FILE')
_users_override = os.environ.get('APP_USERS_FILE')
if bool(_devices_override) != bool(_users_override):
    raise ValueError('APP_DEVICES_FILE and APP_USERS_FILE must be configured together')

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

# JSON Data Files
DEVICES_FILE = _inventory_path('APP_DEVICES_FILE', os.path.join(DATA_DIR, 'devices.json'))
USERS_FILE = _inventory_path('APP_USERS_FILE', os.path.join(DATA_DIR, 'users.json'))
JOBS_FILE = os.path.join(DATA_DIR, 'jobs.json')
APP_STATE_FILE = os.path.join(DATA_DIR, 'app_state.json')
DEVICE_LOCKS_FILE = os.path.join(DATA_DIR, 'device_locks.json')
DEVICE_JOB_QUEUE_FILE = os.path.join(DATA_DIR, 'device_job_queue.json')
SAVED_SEQUENCES_FILE = os.path.join(DATA_DIR, 'saved_sequences.json')
TEST_RESULTS_FILE = os.path.join(DATA_DIR, 'test_results_history.json')
IR_KEYCODES_FILE = os.path.join(DATA_DIR, 'ir_keycodes.json')
IR_KEYCODES_BACKUP_FILE = os.path.join(DATA_DIR, 'ir_keycodes_backup.json')
RESET_CODES_FILE = os.path.join(DATA_DIR, 'reset_codes.json')
LOG_PATTERNS_FILE = os.path.join(DATA_DIR, 'log_patterns.json')
SYSTEM_COMMANDS_FILE = os.path.join(DATA_DIR, 'system_commands.json')
SYSTEM_COMMANDS_SUBMISSIONS_FILE = os.path.join(DATA_DIR, 'system_commands_submissions.json')
LOG_PATTERN_SUBMISSIONS_FILE = os.path.join(DATA_DIR, 'log_pattern_submissions.json')
TILES_RESULTS_DATA_FILE = os.path.join(DATA_DIR, 'tiles_results_data.json')
CHECKPOINT_FILE = os.path.join(DATA_DIR, 'checkpoint.pkl')

# Directory Paths
ITERATION_LOGS_DIRECTORY = LOGS_DIR
SCREENSHOTS_DIRECTORY = SCREENSHOTS_DIR

# Utility function to get relative path for backward compatibility
def get_data_file_path(filename):
    """Get the full path to a data file"""
    return os.path.join(DATA_DIR, filename)

__all__ = [
    'BASE_DIR',
    'DATA_DIR',
    'LOGS_DIR',
    'SCREENSHOTS_DIR',
    'DEVICES_FILE',
    'USERS_FILE',
    'JOBS_FILE',
    'APP_STATE_FILE',
    'DEVICE_LOCKS_FILE',
    'DEVICE_JOB_QUEUE_FILE',
    'SAVED_SEQUENCES_FILE',
    'TEST_RESULTS_FILE',
    'IR_KEYCODES_FILE',
    'IR_KEYCODES_BACKUP_FILE',
    'RESET_CODES_FILE',
    'LOG_PATTERNS_FILE',
    'SYSTEM_COMMANDS_FILE',
    'SYSTEM_COMMANDS_SUBMISSIONS_FILE',
    'LOG_PATTERN_SUBMISSIONS_FILE',
    'TILES_RESULTS_DATA_FILE',
    'CHECKPOINT_FILE',
    'ITERATION_LOGS_DIRECTORY',
    'SCREENSHOTS_DIRECTORY',
    'get_data_file_path',
]
