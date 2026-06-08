"""
Log Pattern Configuration for Device Status Checking
"""

import json
import os

LOG_PATTERNS_FILE = os.path.join('Json', 'log_patterns.json')


def _load_patterns_file():
    if not os.path.exists(LOG_PATTERNS_FILE):
        return {
            "LOG_PATTERNS": {},
            "SYSTEM_COMMAND_PATTERNS": {}
        }
    try:
        with open(LOG_PATTERNS_FILE, 'r') as f:
            data = json.load(f)
            return {
                "LOG_PATTERNS": data.get("LOG_PATTERNS", {}),
                "SYSTEM_COMMAND_PATTERNS": data.get("SYSTEM_COMMAND_PATTERNS", {})
            }
    except (json.JSONDecodeError, IOError):
        return {
            "LOG_PATTERNS": {},
            "SYSTEM_COMMAND_PATTERNS": {}
        }


_PATTERNS = _load_patterns_file()
_LOG_PATTERNS = _PATTERNS.get("LOG_PATTERNS", {})
_SYSTEM_COMMANDS = _PATTERNS.get("SYSTEM_COMMAND_PATTERNS", {})


def _get_log_pattern(name):
    return _LOG_PATTERNS.get(name, {})


def _get_system_command(name):
    return _SYSTEM_COMMANDS.get(name, {})


# Log patterns to check device status (loaded from log_patterns.json)
# HOME screen detection - supports both Sky and Rogers-Xfinity devices
_home = _get_log_pattern("HOME")
_net = _get_log_pattern("Network_Error")
_crash = _get_log_pattern("Process_Crash")
_realtek = _get_log_pattern("Realtek_Module")
_dsmgr = _get_system_command("Dsmgr_Status")

log_line_HOME = _home.get("log_pattern", "")
log_line_HOME_SKY = _home.get("log_pattern", "")
log_line_HOME_ROGERS_XFINITY = _home.get("log_pattern", "")
_net_pattern = _net.get("log_pattern", "")
_net_parts = _net_pattern.split('|') if _net_pattern else []
log_line_NO_WIFI = _net_parts[0] if len(_net_parts) > 0 else ""
log_line_Network_Error_1 = _net_parts[1] if len(_net_parts) > 1 else ""
log_line_Network_Error_2 = _net_parts[2] if len(_net_parts) > 2 else ""
log_line_Crash_WPEFramework = _get_log_pattern("WPEFramework_Crash").get("log_pattern", "")
log_line_Crash = _crash.get("log_pattern", "")
log_line_Realtek = _realtek.get("log_pattern", "")
log_line_DSMGR = _dsmgr.get("command", "")


# Log check commands - These check log files for specific patterns
# These commands are automatically available as optional post-reboot checks in Reboot Performance V2
# Add new log check commands to log_patterns.json and they'll automatically appear in the UI
log_check_command_HOME = f"grep -E \"{_home.get('log_pattern', '')}\" {_home.get('file_path', '')}" if _home.get('log_pattern') and _home.get('file_path') else ""
log_check_command_Network_Error = f"grep -E \"{_net.get('log_pattern', '')}\" {_net.get('file_path', '')}" if _net.get('log_pattern') and _net.get('file_path') else ""
log_check_command_Crash = f"grep -E \"{_crash.get('log_pattern', '')}\" {_crash.get('file_path', '')}" if _crash.get('log_pattern') and _crash.get('file_path') else ""
_wpe = _get_log_pattern("WPEFramework_Crash")
log_check_command_Crash_WPEFramework = f"grep -E \"{_wpe.get('log_pattern', '')}\" {_wpe.get('file_path', '')}" if _wpe.get('log_pattern') and _wpe.get('file_path') else ""
log_check_command_Realtek = f"grep -E \"{_realtek.get('log_pattern', '')}\" {_realtek.get('file_path', '')}" if _realtek.get('log_pattern') and _realtek.get('file_path') else ""

# System Commands - Direct Linux commands for system status monitoring
# These are pure system commands without log pattern checks
# Using separate variable names for clarity
_teetz = _get_system_command("Teetz")
_disk = _get_system_command("Disk_Usage")
_mem = _get_system_command("Memory_Usage")
_cpu = _get_system_command("CPU_Usage")
_dsmgr_cmd = _get_system_command("Dsmgr_Status")

system_command_teetz = _teetz.get("command", "")
system_command_disk_space = _disk.get("command", "")
system_command_memory_usage = _mem.get("command", "")
system_command_top = _cpu.get("command", "")
system_command_dsmgr_status = _dsmgr_cmd.get("command", "")

# Keep legacy names for backward compatibility
log_check_command_teetz = system_command_teetz
log_check_command_disk_space = system_command_disk_space
log_check_command_memory_usage = system_command_memory_usage
log_check_command_top = system_command_top
log_check_command_dsmgr_status = system_command_dsmgr_status


def get_system_commands():
    """
    Get only the system commands (direct Linux commands without log pattern checks).
    Returns a dictionary of system commands with their details.
    Any variable starting with 'system_command_' will be included.
    """
    commands = {}

    # Load from JSON-backed patterns
    for name, data in _SYSTEM_COMMANDS.items():
        commands[name.lower()] = {
            'command': data.get('command'),
            'description': data.get('description', f"Check {name.replace('_', ' ')}")
        }

    return commands


def get_log_check_commands():
    """
    Get only the log check commands (grep-based pattern checks).
    Returns a dictionary of log check commands with their details.
    Filters out system commands.
    """
    checks = {}

    for name, data in _LOG_PATTERNS.items():
        if not data.get('log_pattern') or not data.get('file_path'):
            continue
        checks[name.lower()] = {
            'command': f"grep -E \"{data.get('log_pattern', '')}\" {data.get('file_path', '')}",
            'description': data.get('description', f"Check {name.replace('_', ' ')}")
        }

    return checks


def get_all_optional_checks():
    """
    Get all optional checks (log checks, system commands, AND approved patterns).
    Returns a dictionary of all available checks with their commands and descriptions.
    Now includes approved patterns from log_pattern_submissions.json automatically.
    """
    # Combine log checks and system commands
    legacy_checks = {**get_log_check_commands(), **get_system_commands()}
    
    # Get approved pattern checks
    approved_checks = get_all_patterns_with_commands()
    
    # Merge them (approved checks take precedence if there's a name conflict)
    return {**legacy_checks, **approved_checks}


# Deprecated: Device-specific helper functions no longer needed
# log_line_HOME now includes both patterns with OR operator
# Keeping these functions for backward compatibility but they now return the universal pattern
def get_home_screen_pattern(device_name):
    """
    DEPRECATED: Returns universal HOME pattern that works for all devices.
    log_line_HOME now includes both Sky and Rogers-Xfinity patterns.
    """
    return log_line_HOME


def get_home_screen_command(device_name):
    """
    DEPRECATED: Returns universal HOME command that works for all devices.
    log_check_command_HOME now includes both Sky and Rogers-Xfinity patterns.
    """
    return log_check_command_HOME

def load_approved_patterns():
    """
    Load all approved log patterns from the log_patterns.json file.
    
    Returns:
        dict: Dictionary of approved patterns with their details
    """
    if not os.path.exists(LOG_PATTERNS_FILE):
        return {}

    try:
        with open(LOG_PATTERNS_FILE, 'r') as f:
            data = json.load(f)
            return data.get('LOG_PATTERNS', {})
    except (json.JSONDecodeError, IOError):
        return {}


def get_log_pattern(pattern_name):
    """
    Get a specific log pattern by name from approved patterns.
    
    Args:
        pattern_name: Name of the pattern to retrieve
        
    Returns:
        str: The regex pattern string, or None if not found
    """
    approved = load_approved_patterns()
    pattern_data = approved.get(pattern_name)

    if pattern_data:
        return pattern_data.get('log_pattern')

    json_pattern = _LOG_PATTERNS.get(pattern_name)
    if json_pattern:
        return json_pattern.get('log_pattern')

    return None


def get_log_file_path(pattern_name):
    """
    Get the file path for a specific log pattern.
    
    Args:
        pattern_name: Name of the pattern
        
    Returns:
        str: The file path, or None if not found
    """
    approved = load_approved_patterns()
    pattern_data = approved.get(pattern_name)

    if pattern_data:
        return pattern_data.get('file_path')

    json_pattern = _LOG_PATTERNS.get(pattern_name)
    if json_pattern:
        return json_pattern.get('file_path')

    return None


def build_log_check_command(pattern_name):
    """
    Build a log check command for a specific pattern.
    
    Args:
        pattern_name: Name of the pattern
        
    Returns:
        str: The grep command to check the log, or None if pattern not found
    """
    pattern = get_log_pattern(pattern_name)
    file_path = get_log_file_path(pattern_name)
    
    if not pattern or not file_path:
        return None
    
    return f"grep -E \"{pattern}\" {file_path}"


def get_all_approved_pattern_names():
    """
    Get a list of all approved pattern names.
    
    Returns:
        list: List of pattern names
    """
    approved = load_approved_patterns()
    return list(approved.keys())


def get_all_patterns_with_commands():
    """
    Get all approved patterns along with their generated check commands.
    Useful for dynamically displaying available checks.
    
    Returns:
        dict: Dictionary mapping pattern names to their commands and descriptions
    """
    approved = load_approved_patterns()
    result = {}

    for name, pattern_data in approved.items():
        result[name.lower()] = {
            'command': build_log_check_command(name),
            'description': pattern_data.get('description', f'Check {name}'),
            'pattern': pattern_data.get('log_pattern'),
            'file_path': pattern_data.get('file_path'),
            'submitted_by': pattern_data.get('submitted_by')
        }

    # Include JSON-backed log patterns
    for name, pattern_data in _LOG_PATTERNS.items():
        if not pattern_data.get('log_pattern') or not pattern_data.get('file_path'):
            continue
        result[name.lower()] = {
            'command': f"grep -E \"{pattern_data.get('log_pattern', '')}\" {pattern_data.get('file_path', '')}",
            'description': pattern_data.get('description', f'Check {name}'),
            'pattern': pattern_data.get('log_pattern'),
            'file_path': pattern_data.get('file_path'),
            'submitted_by': pattern_data.get('submitted_by')
        }

    # Include JSON-backed system commands
    for name, data in _SYSTEM_COMMANDS.items():
        result[name.lower()] = {
            'command': data.get('command'),
            'description': data.get('description', f'Check {name}'),
            'pattern': None,
            'file_path': None,
            'submitted_by': data.get('submitted_by')
        }

    return result


def merge_approved_with_legacy_checks():
    """
    DEPRECATED: Use get_all_optional_checks() instead.
    This function now just calls get_all_optional_checks() for backward compatibility.
    
    Returns:
        dict: Combined dictionary of all available checks
    """
    return get_all_optional_checks()


def get_approved_patterns_from_config():
    """
    Get existing patterns from the legacy hardcoded config.
    These are patterns defined directly in this config file.
    
    Returns:
        dict: Dictionary of existing patterns with their details
    """
    return {**_LOG_PATTERNS}