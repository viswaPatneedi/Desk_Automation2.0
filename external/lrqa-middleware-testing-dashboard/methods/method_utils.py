#!/usr/bin/env python3
"""
Shared utilities for device testing methods
Contains common helper functions used across reboot, deepsleep, and IR test methods
"""

import os
import sys
import time
import paramiko
import threading
from datetime import datetime, timezone

# Import configuration files
from config.config_commands import *
from config.config_log_patterns import *
from config.config_timing import *
from config.config_screenshot import rpc_url

def get_lexar_base_path():
    """Resolve Lexar USB base path dynamically.

    Returns: path to Enhancement_output folder if Lexar is mounted, else local fallback.
    """
    if sys.platform.startswith('linux'):
        # Preferred locations
        candidates = []
        user = os.environ.get('USER') or ''
        # Add common explicit paths (case-sensitive variants handled below)
        if user:
            candidates.append(os.path.join('/media', user, 'Lexar'))
            candidates.append(os.path.join('/media', user, 'lexar'))
        candidates.append('/media/pi/Lexar')
        candidates.append('/media/pi/lexar')

        # Scan /media/* for any directory named like 'lexar' (case-insensitive)
        try:
            if os.path.isdir('/media'):
                for entry in os.listdir('/media'):
                    entry_path = os.path.join('/media', entry)
                    # if there's a Lexar folder under the user-specific media dir
                    possible = os.path.join(entry_path, 'Lexar')
                    possible_lower = os.path.join(entry_path, 'lexar')
                    if os.path.exists(possible):
                        candidates.append(possible)
                    if os.path.exists(possible_lower):
                        candidates.append(possible_lower)
                    # also check any child dir whose name contains 'lexar' (case-insensitive)
                    try:
                        for child in os.listdir(entry_path):
                            if 'lexar' in child.lower():
                                candidates.append(os.path.join(entry_path, child))
                    except Exception:
                        pass
        except Exception:
            pass

        # Return the first existing candidate's Enhancement_output subfolder
        for base in candidates:
            try:
                if base and os.path.exists(base):
                    return os.path.join(base, 'Enhancement_output')
            except Exception:
                continue

    return 'Enhancement_output'

# Thread-local storage for execution session paths
thread_local = threading.local()

# Global variable to store current execution methods and sequence names (for combined method tracking)
_current_execution_methods = {}
_current_sequence_names = {}
_current_job_ids = {}  # Store job_id for each thread for cancellation checking

def set_current_job_id(thread_id, job_id):
    """Store the current job ID for this thread"""
    _current_job_ids[thread_id] = job_id

def get_current_job_id(thread_id):
    """Get the current job ID for this thread"""
    return _current_job_ids.get(thread_id, None)

def is_job_cancelled(job_id=None):
    """
    Check if the current job has been cancelled.
    If job_id is None, uses the job_id stored in thread-local storage.
    
    Returns: True if job is cancelled, False otherwise
    """
    if not job_id:
        import threading
        thread_id = threading.get_ident()
        job_id = get_current_job_id(thread_id)
    
    if not job_id:
        return False
    
    try:
        import json
        from models.job import Job
        job = Job.get_job(job_id)
        if job and job.get('status') == 'cancelled':
            return True
    except:
        pass
    
    return False

def set_execution_methods(thread_id, methods, sequence_name=None):
    """Set the methods and sequence name being executed in current thread"""
    _current_execution_methods[thread_id] = methods
    if sequence_name:
        _current_sequence_names[thread_id] = sequence_name

def get_execution_methods(thread_id):
    """Get the methods being executed in current thread"""
    return _current_execution_methods.get(thread_id, None)

def get_sequence_name(thread_id):
    """Get the sequence name for current thread"""
    return _current_sequence_names.get(thread_id, None)

def get_folder_method_name():
    """Get the method name to use for folder creation - prefers sequence name over combined methods"""
    import threading
    thread_id = threading.get_ident()
    
    # First try to get sequence name
    sequence_name = get_sequence_name(thread_id)
    if sequence_name:
        return sequence_name.replace(' ', '_').replace(',', '_')
    
    # Fall back to combined methods
    methods = get_execution_methods(thread_id)
    if methods and isinstance(methods, list):
        if len(methods) > 3:
            # Truncate for long sequences
            return ','.join(methods[:3]) + f'+{len(methods)-3}more'
        else:
            return ','.join(methods)
    
    return None

# Global variables (legacy - being phased out)
current_session_folder = None
current_screenshots_dir = None
current_execution_logs_dir = None
current_device_logs_dir = None
current_log_handle = None

def log_message(message, write_to_file=True, log_callback=None):
    """Add a log message with UTC timestamp
    
    Args:
        message: The message to log
        write_to_file: Whether to write to the execution log file
        log_callback: Optional callback function for logging
    """
    if log_callback:
        log_callback(message)
        return
    
    # Import here to avoid circular dependency
    from datetime import datetime, timezone
    
    # Try to use log service if available
    try:
        from services.log_service import LogService
        log_service = LogService()
        log_service.log(message, write_to_file)
    except:
        # Fallback to simple print if log service not available
        timestamp = datetime.now(timezone.utc).strftime('[%Y-%m-%d %H:%M:%S UTC]')
        formatted_message = f"{timestamp} {message}"
        print(formatted_message)

def fetch_build_details(ssh, log_callback=None):
    """Fetch build details from device using cat /version.txt"""
    def log(message):
        log_message(message, log_callback=log_callback)
    
    try:
        log("Fetching build details from device...")
        stdin, stdout, stderr = ssh.exec_command("cat /version.txt")
        build_info = stdout.read().decode('utf-8', errors='ignore').strip()
        
        if build_info:
            log("✓ Build Details:")
            for line in build_info.split('\n')[:5]:
                log(f"  {line}")
            return build_info
        else:
            log("⚠ No build details found in /version.txt")
            return None
    except Exception as e:
        log(f"⚠ Error fetching build details: {e}")
        return None

def activate_screencapture_service(ssh, log_callback=None, timeout=10):
    """Activate ScreenCapture service on device
    
    Args:
        ssh: SSH connection object
        log_callback: Logging callback function
        timeout: Timeout in seconds for the operation (default: 10s)
    """
    import socket
    def log(message):
        log_message(message, log_callback=log_callback)
    
    try:
        log("Activating ScreenCapture service...")
        activate_command = f"curl -d '{{\"jsonrpc\":\"2.0\",\"id\":\"1\",\"method\": \"Controller.1.activate\", \"params\":{{\"callsign\":\"org.rdk.ScreenCapture\"}}}}' {rpc_url}"
        stdin, stdout, stderr = ssh.exec_command(activate_command, timeout=timeout)
        
        # Set timeout on socket to prevent hanging on read
        stdout.channel.settimeout(timeout)
        
        try:
            activate_response = stdout.read().decode('utf-8', errors='ignore')
        except socket.timeout:
            log(f"⚠ ScreenCapture activation command timed out after {timeout}s - continuing anyway")
            activate_response = ""
        
        if activate_response:
            log(f"Service activation response: {activate_response}")
        
        time.sleep(3)
        log("✓ ScreenCapture service activation completed")
        return True
    except Exception as e:
        log(f"⚠ Warning: ScreenCapture activation failed: {e}")
        log(f"Continuing execution anyway (screenshot is non-critical)")
        return False

def create_execution_log_path(device_ip, device_name, iteration, method_name):
    """Create execution log path with date-based organization
    
    Structure: /media/pi/Lexar/Enhancement_output/EXECUTION_LOGS/YYYY-MM-DD/DEVICE/ITR-X/METHOD_NAME_ITR_X.log
    Example: /media/pi/Lexar/Enhancement_output/EXECUTION_LOGS/2025-12-04/10-0-0-126_WESTINGHOUSE-4K-DESK/ITR-1/REBOOT_ITR_1.log
    """
    from datetime import datetime, timezone
    current_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    # Base path with EXECUTION_LOGS folder and date folder
    usb_base = os.path.join(get_lexar_base_path(), "EXECUTION_LOGS")
    date_folder = os.path.join(usb_base, current_date)
    
    # Sanitize device name and IP for folder name
    safe_device_name = device_name.replace(' ', '-').replace('/', '_').replace('\\', '_').replace('__', '_').replace('--', '-').upper()
    safe_ip = device_ip.replace('.', '-')
    device_folder = f"{safe_ip}_{safe_device_name}"
    
    # Create folder path (ensure uniqueness to avoid overwriting existing runs)
    base_itr_dir = os.path.join(date_folder, device_folder)
    itr_dir_name = f"ITR-{iteration}"
    folder_path = os.path.join(base_itr_dir, itr_dir_name)

    # If folder exists, append a run suffix like _R2, _R3 to keep previous runs intact
    if os.path.exists(folder_path):
        suffix = 2
        while True:
            candidate = os.path.join(base_itr_dir, f"{itr_dir_name}_R{suffix}")
            if not os.path.exists(candidate):
                folder_path = candidate
                break
            suffix += 1

    # Create directory if it doesn't exist
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    
    # Generate log filename
    log_filename = f"{method_name.upper()}_ITR_{iteration}.log"
    log_file_path = os.path.join(folder_path, log_filename)
    
    return log_file_path

def create_screenshot_folder(device_ip, device_name, iteration, phase, method_name=None, execution_timestamp=None):
    """Create screenshot folder structure with date-based organization
    
    Structure: /media/pi/Lexar/Enhancement_output/YYYY-MM-DD/DEVICE/METHOD/ITR-X_TIMESTAMP/SCREENSHOTS
    Example: /media/pi/Lexar/Enhancement_output/2025-12-08/10-0-0-126_WESTINGHOUSE-4K-DESK/VOICECOMMAND/ITR-1_20251208_143025/SCREENSHOTS
    
    Args:
        execution_timestamp: Optional UTC timestamp string (format: YYYYMMDD_HHMMSS) to uniquely identify this execution.
                           If provided, all screenshots from the same execution will be in the same folder.
                           If not provided, falls back to old _R2 suffix behavior for backward compatibility.
    """
    # Generate current date folder
    from datetime import datetime, timezone
    current_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    # Base path
    usb_base = get_lexar_base_path()
    
    # Sanitize device name and IP for folder name
    safe_device_name = device_name.replace(' ', '-').replace('/', '_').replace('\\', '_').replace('__', '_').replace('--', '-').upper()
    safe_ip = device_ip.replace('.', '-')
    device_folder = f"{safe_ip}_{safe_device_name}"
    
    # Determine method folder name from phase or method_name
    if method_name:
        # Truncate long method names (especially for sequences)
        method_folder = method_name.upper().replace('_', '')
        # Limit to 80 characters to avoid filesystem limits
        if len(method_folder) > 80:
            # For long sequences, use first 3 methods + count
            methods_list = method_name.split(',')
            if len(methods_list) > 3:
                first_three = '-'.join([m.upper().replace('_', '') for m in methods_list[:3]])
                method_folder = f"{first_three}+{len(methods_list)-3}MORE"
            else:
                method_folder = method_folder[:80]
    else:
        # Map phase names to method names
        phase_to_method = {
            'VOICECOMMAND': 'VOICECOMMAND',
            'REBOOT': 'REBOOT',
            'DEEPSLEEP': 'DEEPSLEEP',
            'IRTEST': 'IRTEST',
            'BEFORE': 'REBOOT',  # Default for BEFORE
            'AFTER': 'REBOOT'    # Default for AFTER
        }
        method_folder = phase_to_method.get(phase.upper(), 'GENERAL')
    
    # Build base ITR directory with timestamp for uniqueness
    base_itr_dir = os.path.join(usb_base, current_date, device_folder, method_folder)
    
    if execution_timestamp:
        # Use timestamp to ensure all screenshots from same execution go to same folder
        itr_dir_name = f"ITR-{iteration}_{execution_timestamp}"
        itr_dir_path = os.path.join(base_itr_dir, itr_dir_name)
    else:
        # Backward compatibility: use old _R2 suffix logic if no timestamp provided
        itr_dir_name = f"ITR-{iteration}"
        itr_dir_path = os.path.join(base_itr_dir, itr_dir_name)
        
        # If the ITR dir already exists, append a run suffix like _R2, _R3
        if os.path.exists(itr_dir_path):
            suffix = 2
            while True:
                candidate = os.path.join(base_itr_dir, f"{itr_dir_name}_R{suffix}")
                if not os.path.exists(candidate):
                    itr_dir_path = candidate
                    break
                suffix += 1

    # Final screenshots folder path
    folder_path = os.path.join(itr_dir_path, "SCREENSHOTS")

    # Create directory if it doesn't exist
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    return folder_path

def send_home_key_based_on_power_state(ssh, log_callback=None):
    """Check device power state and send HOME key accordingly"""
    def log(message):
        log_message(message, log_callback=log_callback)
    
    try:
        # Check device power state
        stdin, stdout, stderr = ssh.exec_command(device_status_command)
        device_status = stdout.read().decode('utf-8', errors='ignore').strip()
        log(f"Device power state: {device_status}")
        
        # Send HOME key based on state
        if "STANDBY" in device_status:
            log("Device is in STANDBY state - sending HOME key to wake up...")
            stdin, stdout, stderr = ssh.exec_command(home_key_command)
            time.sleep(3)
            error_output = stderr.read().decode('utf-8', errors='ignore')
            if error_output:
                log(f"⚠ Error output: {error_output}")
            log("✓ HOME key sent to wake up device")
        elif "ON" in device_status:
            log("Device is ON - sending HOME key...")
            stdin, stdout, stderr = ssh.exec_command(home_key_command)
            time.sleep(3)
            error_output = stderr.read().decode('utf-8', errors='ignore')
            if error_output:
                log(f"⚠ Error output: {error_output}")
            log("✓ HOME key sent")
        else:
            log(f"Device state: {device_status} - sending HOME key anyway...")
            stdin, stdout, stderr = ssh.exec_command(home_key_command)
            time.sleep(3)
            log("✓ HOME key sent")
        
        return True, device_status
    except Exception as e:
        log(f"❌ Error checking power state and sending HOME key: {e}")
        return False, "UNKNOWN"

def reconnect_to_device_with_retry(device_ip, port, username, password, max_retries=10, retry_interval=5, log_callback=None):
    """Reconnect to device with retry logic"""
    def log(message):
        log_message(message, log_callback=log_callback)
    
    log("Reconnecting to device after wake up...")
    retry_count = 0
    ssh = None
    
    while retry_count < max_retries:
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(device_ip, port=port, username=username, password=password, timeout=10)
            log(f"✓ Reconnected to device after {retry_count + 1} attempt(s)")
            return ssh
        except Exception as e:
            retry_count += 1
            if retry_count < max_retries:
                log(f"Reconnection attempt {retry_count} failed, retrying in {retry_interval} seconds...")
                time.sleep(retry_interval)
            else:
                log(f"❌ Failed to reconnect after {max_retries} attempts: {e}")
    
    return None

def wait_for_device(device_ip, port, username, password, log_callback=None):
    """Actively poll for device to come back online after reboot.
    Eliminates the fixed countdown so we break as soon as SSH is reachable."""
    def log(message):
        log_message(message, log_callback=log_callback)
    
    max_wait = wait_for_bootime  # reuse existing timing config value
    start_time = time.time()
    log(f"Reboot initiated; attempting reconnection for up to {max_wait} seconds...")
    attempt = 0
    while time.time() - start_time < max_wait:
        remaining = max_wait - (time.time() - start_time)
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(device_ip, port=port, username=username, password=password, timeout=8)
            log(f"✓ Device back online after {int(time.time() - start_time)}s (attempt {attempt+1}).")
            return ssh
        except Exception:
            attempt += 1
            log(f"Attempt {attempt} failed; {int(remaining)}s remaining...")
            sleep_interval = min(wait_before_retry, max_wait - (time.time() - start_time))
            if sleep_interval > 0:
                time.sleep(sleep_interval)
    log("❌ Device did not come back online within the allotted wait window.")
    return None

def check_network_errors(ssh, log_callback=None):
    """Check for network errors in logs"""
    def log(message):
        log_message(message, log_callback=log_callback)
    
    try:
        stdin, stdout, stderr = ssh.exec_command(log_check_command_Network_Error)
        network_error_log_output = stdout.read().decode('utf-8', errors='ignore').strip()
        if network_error_log_output:
            log("⚠ Network Error detected in logs:")
            for line in network_error_log_output.split('\n')[:5]:
                log(f"  {line}")
            return True
        return False
    except Exception as e:
        log(f"Error checking network errors: {str(e)}")
        return False

def check_network_and_realtek_errors(ssh, log_callback=None):
    """Check for network/WiFi errors and Realtek module issues"""
    def log(message):
        log_message(message, log_callback=log_callback)
    
    has_errors = False
    
    try:
        # Check for network errors and WiFi issues
        log("Checking for network and WiFi errors...")
        stdin, stdout, stderr = ssh.exec_command(log_check_command_Network_Error)
        network_error_log = stdout.read().decode('utf-8', errors='ignore').strip()
        
        if network_error_log:
            log("⚠ Network/WiFi Error detected:")
            for line in network_error_log.split('\n')[:10]:
                log(f"  {line}")
            has_errors = True
        else:
            log("✓ No network/WiFi errors found")
        
        # Check for Realtek module issues
        log("Checking for Realtek module issues...")
        stdin, stdout, stderr = ssh.exec_command(log_check_command_Realtek)
        realtek_log = stdout.read().decode('utf-8', errors='ignore').strip()
        
        if realtek_log:
            log("⚠ Realtek module issue detected:")
            for line in realtek_log.split('\n')[:5]:
                log(f"  {line}")
            has_errors = True
        else:
            log("✓ No Realtek issues found")
        
        return has_errors
    except Exception as e:
        log(f"❌ Error checking for network/Realtek errors: {e}")
        return has_errors

def capture_device_logs_sftp(ssh, log_filename, log_callback=None, iteration=None, device_ip=None):
    """
    Capture device logs and download them via SFTP to device-specific folder structure
    
    Args:
        ssh: SSH connection object
        log_filename: Name of the log file to create
        log_callback: Optional callback for logging
        iteration: Current iteration number
        device_ip: Device IP address for folder organization
    
    Folder structure: device_logs/<device_ip>/ITR-<iteration>/
    """
    def log(message):
        log_message(message, log_callback=log_callback)
    
    try:
        from app import current_device_logs_dir

        # Always use .tgz extension
        if not log_filename.endswith('.tgz'):
            log_filename = log_filename.replace('.tar.gz', '.tgz').replace('.tar', '.tgz')
        remote_log_path = f"/media/apps/{log_filename}"

        # Verify SSH connection is active
        if not ssh.get_transport() or not ssh.get_transport().is_active():
            log("⚠ SSH connection is not active, skipping log capture")
            return None

        # Use thread-local device logs directory if available, with device-specific subfolder
        device_logs_dir = getattr(thread_local, 'device_logs_dir', current_device_logs_dir)
        if device_logs_dir and os.path.exists(device_logs_dir):
            # Create device-specific folder structure
            if device_ip:
                device_folder = os.path.join(device_logs_dir, device_ip)
                if not os.path.exists(device_folder):
                    os.makedirs(device_folder)
                if iteration:
                    local_dir = os.path.join(device_folder, f"ITR-{iteration}")
                    if not os.path.exists(local_dir):
                        os.makedirs(local_dir)
                else:
                    local_dir = device_folder
            elif iteration:
                local_dir = os.path.join(device_logs_dir, f"ITR-{iteration}")
                if not os.path.exists(local_dir):
                    os.makedirs(local_dir)
            else:
                local_dir = device_logs_dir
        else:
            # Fallback: create device_logs with device-specific subfolder
            logs_dir = 'device_logs'
            if not os.path.exists(logs_dir):
                os.makedirs(logs_dir)
            if device_ip:
                device_folder = os.path.join(logs_dir, device_ip)
                if not os.path.exists(device_folder):
                    os.makedirs(device_folder)
                if iteration:
                    local_dir = os.path.join(device_folder, f"ITR-{iteration}")
                    if not os.path.exists(local_dir):
                        os.makedirs(local_dir)
                else:
                    local_dir = device_folder
            else:
                local_dir = logs_dir

        log(f"Capturing device logs to {remote_log_path}...")

        # Create .tgz archive
        tar_command = f"tar -czf {remote_log_path} /opt/logs/*"
        stdin, stdout, stderr = ssh.exec_command(tar_command, timeout=60)
        stdout.channel.recv_exit_status()  # Wait for command to complete

        error_output = stderr.read().decode('utf-8', errors='ignore')
        if error_output and "tar:" not in error_output:
            log(f"⚠ Warning during log capture: {error_output}")

        log(f"✓ Device logs captured successfully")

        # Wait for remote .tgz file to exist and be nonzero size (up to 60 sec with progress)
        log(f"Waiting for remote .tgz file to be ready...")
        file_ready = False
        wait_time = 0
        check_interval = 5  # Check every 5 seconds
        max_wait = 60  # 1 minute max wait (reduced from 5 minutes)
        
        while wait_time < max_wait:
            try:
                sftp = ssh.open_sftp()
                try:
                    attrs = sftp.stat(remote_log_path)
                    if attrs.st_size > 0:
                        file_ready = True
                        log(f"✓ Remote file ready: {attrs.st_size} bytes")
                        sftp.close()
                        break
                except Exception:
                    pass
                sftp.close()
            except Exception:
                pass
            
            time.sleep(check_interval)
            wait_time += check_interval
            
            # Log progress every 15 seconds
            if wait_time % 15 == 0:
                log(f"  ⏱ Still waiting for file... ({wait_time}/{max_wait} seconds)")
        
        if not file_ready:
            log(f"❌ Remote .tgz file not found or empty after {max_wait} seconds, aborting download.")
            return None

        # Download via SFTP with retry logic
        log(f"Downloading logs from device via SFTP...")
        sftp = None
        max_retries = 3
        retry_count = 0
        local_log_path = os.path.join(local_dir, log_filename)

        while retry_count < max_retries:
            try:
                if not ssh.get_transport() or not ssh.get_transport().is_active():
                    log(f"⚠ SSH transport inactive on attempt {retry_count + 1}, aborting SFTP")
                    return None
                sftp = ssh.open_sftp()
                sftp.get_channel().settimeout(60.0)
                sftp.get(remote_log_path, local_log_path)
                sftp.close()
                log(f"✓ Logs downloaded successfully to {local_log_path}")
                break
            except Exception as sftp_error:
                retry_count += 1
                if sftp:
                    try:
                        sftp.close()
                    except:
                        pass
                if retry_count < max_retries:
                    log(f"⚠ SFTP download attempt {retry_count} failed: {str(sftp_error)}, retrying...")
                    time.sleep(10)
                else:
                    log(f"❌ SFTP download failed after {max_retries} attempts: {sftp_error}")
                    return None

        # Delete remote file
        log(f"Deleting remote log file...")
        stdin, stdout, stderr = ssh.exec_command(f"rm -f {remote_log_path}", timeout=10)
        stdout.channel.recv_exit_status()
        log(f"✓ Remote log file deleted")

        return local_log_path
    except Exception as e:
        log(f"✗ Error capturing device logs: {e}")
        return None

def capture_minimal_logs_fallback(ssh, local_basename, log_callback=None, iteration=None, device_ip=None):
    """
    Fallback: capture a small slice of key logs if full tar download fails.
    
    Args:
        ssh: SSH connection object
        local_basename: Base name for log files
        log_callback: Optional callback for logging
        iteration: Current iteration number
        device_ip: Device IP address for folder organization
    
    Folder structure: device_logs/<device_ip>/ITR-<iteration>/
    """
    def log(message):
        log_message(message, log_callback=log_callback)
    
    try:
        from app import current_device_logs_dir
        
        targets = ["/opt/logs/sky-messages.log", "/opt/logs/core_log.txt"]
        collected = []
        
        # Use thread-local device logs directory if available, with device-specific subfolder
        device_logs_dir = getattr(thread_local, 'device_logs_dir', current_device_logs_dir)
        if device_logs_dir and os.path.exists(device_logs_dir):
            # Create device-specific folder structure
            if device_ip:
                device_folder = os.path.join(device_logs_dir, device_ip)
                if not os.path.exists(device_folder):
                    os.makedirs(device_folder)
                if iteration:
                    local_dir = os.path.join(device_folder, f"ITR-{iteration}")
                    if not os.path.exists(local_dir):
                        os.makedirs(local_dir)
                else:
                    local_dir = device_folder
            elif iteration:
                local_dir = os.path.join(device_logs_dir, f"ITR-{iteration}")
                if not os.path.exists(local_dir):
                    os.makedirs(local_dir)
            else:
                local_dir = device_logs_dir
        else:
            # Fallback: create device_logs with device-specific subfolder
            local_dir = 'device_logs'
            if not os.path.exists(local_dir):
                os.makedirs(local_dir)
            if device_ip:
                device_folder = os.path.join(local_dir, device_ip)
                if not os.path.exists(device_folder):
                    os.makedirs(device_folder)
                if iteration:
                    local_dir = os.path.join(device_folder, f"ITR-{iteration}")
                    if not os.path.exists(local_dir):
                        os.makedirs(local_dir)
                else:
                    local_dir = device_folder
        
        for path in targets:
            try:
                cmd = f"tail -n 100 {path}"
                stdin, stdout, stderr = ssh.exec_command(cmd)
                content = stdout.read().decode('utf-8', errors='ignore')
                if content.strip():
                    fname = os.path.join(local_dir, f"{local_basename}_{os.path.basename(path)}")
                    with open(fname, 'w') as f:
                        f.write(content)
                    collected.append(fname)
            except:
                pass
        if not collected:
            log("⚠ No fallback logs captured")
        return collected
    except Exception as e:
        log(f"❌ Fallback logging error: {e}")
        return []
def validate_screen_comparison(before_screenshot_result, after_screenshot_result, log_callback=None):
    """
    Compare BEFORE and AFTER screenshots to validate HOME screen is reached after reboot
    
    Args:
        before_screenshot_result: dict from take_and_analyze_screenshot() for BEFORE screenshot
        after_screenshot_result: dict from take_and_analyze_screenshot() for AFTER screenshot
        log_callback: logging function
    
    Returns:
        dict: {
            'screen_validation_passed': bool,
            'before_screen': str,
            'after_screen': str,
            'confidence': float,
            'message': str
        }
    """
    def log(message):
        if log_callback:
            log_callback(message)
    
    # Initialize result
    result = {
        'screen_validation_passed': False,
        'before_screen': 'Unknown',
        'after_screen': 'Unknown',
        'confidence': 0.0,
        'message': ''
    }
    
    try:
        # Check if both screenshots were captured successfully
        if not before_screenshot_result or not before_screenshot_result.get('success'):
            result['message'] = "BEFORE screenshot not available - skipping screen comparison"
            log(f"⚠ {result['message']}")
            return result
        
        if not after_screenshot_result or not after_screenshot_result.get('success'):
            result['message'] = "AFTER screenshot not available - skipping screen comparison"
            log(f"⚠ {result['message']}")
            return result
        
        # Extract screen states
        before_state = before_screenshot_result.get('screen_state', {})
        after_state = after_screenshot_result.get('screen_state', {})
        
        before_screen = before_state.get('screen_detected', 'Unknown')
        after_screen = after_state.get('screen_detected', 'Unknown')
        before_confidence = before_state.get('confidence', 0.0)
        after_confidence = after_state.get('confidence', 0.0)
        
        result['before_screen'] = before_screen
        result['after_screen'] = after_screen
        result['confidence'] = after_confidence
        
        log(f"\n[SCREEN COMPARISON VALIDATION]")
        log(f"  BEFORE Screenshot: {before_screen} ({before_confidence:.1%} confidence)")
        log(f"  AFTER Screenshot: {after_screen} ({after_confidence:.1%} confidence)")
        
        # Validation logic: AFTER screen should be HomeScreen
        if after_screen == 'HomeScreen':
            if after_confidence >= 0.50:  # Minimum confidence threshold
                result['screen_validation_passed'] = True
                result['message'] = f"Screen validation PASSED: Device returned to HOME screen ({after_confidence:.1%} confidence)"
                log(f"✓ {result['message']}")
            else:
                result['message'] = f"Screen validation WARNING: HOME screen detected but low confidence ({after_confidence:.1%})"
                log(f"⚠ {result['message']}")
        else:
            # Enhanced message: show which screen was actually matched
            result['message'] = f"Screen validation MISMATCH: Expected HomeScreen, detected {after_screen} ({after_confidence:.1%} confidence)"
            log(f"⚠ {result['message']}")
            # Log additional info about what screen was detected
            log(f"   → Device is showing: {after_screen}")
            log(f"   → Confidence level: {after_confidence:.1%}")
            log(f"   → Test will continue (screen validation is informational only)")
        
        # Additional check: if BEFORE was not HOME screen, that's also a warning
        if before_screen != 'HomeScreen':
            log(f"⚠ WARNING: BEFORE screenshot was not HOME screen (was: {before_screen})")
        
        return result
        
    except Exception as e:
        result['message'] = f"Error during screen comparison: {str(e)}"
        log(f"❌ {result['message']}")
        return result