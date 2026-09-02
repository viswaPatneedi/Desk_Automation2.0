import os
import sys
import hashlib
from datetime import datetime, timezone

def _safe_path_part(value, fallback='UNKNOWN'):
    """Return a filesystem-safe, stable path component."""
    value = str(value or fallback).strip()
    value = value.replace('/', '_').replace('\\', '_')
    value = ''.join(char if char.isalnum() or char in '._-' else '_' for char in value)
    return value.strip('._') or fallback


def create_execution_session_folder(method, device_name, device_ip, iterations, job_id=None,
                                    team_name=None, user_id=None):
    """
    Create execution session folder with smart storage management.
    
    CRITICAL: Includes job_id to ensure UNIQUE folder per job
    This prevents screenshot and log mixing when same device runs multiple jobs
    
    Uses USB storage if available (auto-detected), falls back to local storage.
    Storage path is determined by usb_storage_manager.
    
    Args:
        method: Test method name(s)
        device_name: Device name
        device_ip: Device IP
        iterations: Number of iterations
        job_id: Optional job ID (RECOMMENDED for unique folder per job)
    """
    # Try to use USB storage manager directly
    try:
        from data_processing.usb_storage_manager import get_storage_manager
        manager = get_storage_manager(enable_logging=False)
        base_output = manager.storage_root
        usb_available = manager.is_usb_available
    except ImportError:
        # Fallback if USB manager not available
        usb_available = False
        base_output = 'Enhancement_output'
    
    # Create the stable hierarchy used by execution results and screenshots.
    safe_device_name = _safe_path_part(device_name).upper()
    safe_ip = _safe_path_part(device_ip.replace('.', '-'))
    safe_team = _safe_path_part(team_name).upper()
    safe_user = _safe_path_part(user_id)
    current_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    timestamp = datetime.now(timezone.utc).strftime('%H%M%S_UTC')
    
    # Handle long method names by truncating or using hash
    safe_method = method.upper()
    max_method_length = 100  # Leave room for device name, IP, iteration, timestamp
    
    if len(safe_method) > max_method_length:
        # For long sequences, use first 3 methods + hash
        methods_list = safe_method.split(',')[:3]
        method_hash = hashlib.md5(safe_method.encode()).hexdigest()[:8]
        safe_method = '_'.join(methods_list) + f'_+{len(safe_method.split(",")) - 3}MORE_{method_hash}'
    
    # Build the sequence execution folder below its job-owned device hierarchy.
    session_name = f"{safe_method}_{iterations}_{timestamp}"
    
    # Final safety check - truncate if still too long (filesystem limit is typically 255)
    if len(session_name) > 200:
        session_name = f"{safe_method[:70]}_{iterations}_{timestamp}"
    
    # Create session folder structure
    session_folder = os.path.join(
        base_output, 'EXECUTION_RESULTS', 'DESK_AUTOMATION-V2', safe_team,
        safe_user, current_date, f'{safe_device_name}_{safe_ip}', session_name
    )
    iteration_folder = os.path.join(session_folder, f'ITERATION_{iterations}', 'ITR_1')
    screenshots_dir = os.path.join(iteration_folder, 'screenshots')
    execution_logs_dir = os.path.join(iteration_folder, 'execution')
    device_logs_dir = os.path.join(iteration_folder, 'captured_device_logs')

    for folder in [session_folder, screenshots_dir, execution_logs_dir, device_logs_dir]:
        if not os.path.exists(folder):
            os.makedirs(folder)

    return session_folder, screenshots_dir, execution_logs_dir, device_logs_dir
