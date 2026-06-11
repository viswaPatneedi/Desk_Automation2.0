import os
import sys
import hashlib
from datetime import datetime, timezone

def create_execution_session_folder(method, device_name, device_ip, iterations):
    """
    Create execution session folder with smart storage management.
    
    Uses USB storage if available (auto-detected), falls back to local storage.
    Storage path is determined by usb_storage_manager.
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
    
    # Create safe folder names
    safe_device_name = device_name.replace(' ', '-').replace('/', '_').replace('\\', '_').upper()
    safe_ip = device_ip.replace('.', '-')
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_UTC')
    
    # Handle long method names by truncating or using hash
    safe_method = method.upper()
    max_method_length = 100  # Leave room for device name, IP, iteration, timestamp
    
    if len(safe_method) > max_method_length:
        # For long sequences, use first 3 methods + hash
        methods_list = safe_method.split(',')[:3]
        method_hash = hashlib.md5(safe_method.encode()).hexdigest()[:8]
        safe_method = '_'.join(methods_list) + f'_+{len(safe_method.split(",")) - 3}MORE_{method_hash}'
    
    session_name = f"{safe_method}_{safe_device_name}_{safe_ip}_{iterations}_ITR_{timestamp}"
    
    # Final safety check - truncate if still too long (filesystem limit is typically 255)
    if len(session_name) > 200:
        session_name = f"{safe_method[:80]}_{safe_device_name[:30]}_{safe_ip}_{iterations}_ITR_{timestamp}"
    
    # Create session folder structure
    session_folder = os.path.join(base_output, 'sessions', session_name)
    screenshots_dir = os.path.join(session_folder, "SCREENSHOTS")
    execution_logs_dir = os.path.join(session_folder, "EXECUTION_LOGS")
    device_logs_dir = os.path.join(session_folder, "DEVICE_LOGS")

    for folder in [session_folder, screenshots_dir, execution_logs_dir, device_logs_dir]:
        if not os.path.exists(folder):
            os.makedirs(folder)

    return session_folder, screenshots_dir, execution_logs_dir, device_logs_dir
