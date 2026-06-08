#!/usr/bin/env python3
"""
Soft Boot / Hard Boot Performance Monitoring
Monitors reboot time to home screen with support for both SOFT BOOT (Settings GUI) and HARD BOOT (systemctl reboot)
Version: Intelligent boot type selection with log-based performance calculation

KEY FEATURES:
- HARD BOOT: Uses 'systemctl reboot' command (traditional full reboot)
- SOFT BOOT: Navigates through Settings GUI to trigger restart
- Performance calculated from command/key sent to HOME screen detection
- Captures rdk_milestones.log for diagnostic information
- Intelligent early SSH probing

BOOT TYPES:
HARD BOOT:  systemctl reboot → SSH probing → HOME screen detection
SOFT BOOT:  Settings GUI navigation → SSH probing → HOME screen detection
           Navigation: DOWN,DOWN,ENTER,DOWN,DOWN,ENTER,ENTER (5s wait per key)
"""

import sys
import time
import re
import paramiko
import socket
import subprocess
from datetime import datetime, timezone

# Import configurations
from config_commands import *
from config_log_patterns import *
from config_timing import *

# Import shared utilities
from method_utils import (
    log_message,
    fetch_build_details,
    activate_screencapture_service,
    create_screenshot_folder,
    create_execution_log_path,
    wait_for_device,
    check_network_and_realtek_errors,
    capture_device_logs_sftp,
    capture_minimal_logs_fallback,
    get_folder_method_name,
    validate_screen_comparison
)

# Import screenshot utilities
from screenshot_utils import take_and_analyze_screenshot
from screenshot_utils_vnc import take_vnc_screenshot_with_fallback

# Import AI Screen Validation
try:
    from ai_integration_universal import validate_screen_ai, get_ai_validator
    AI_VALIDATION_ENABLED = True
except ImportError:
    AI_VALIDATION_ENABLED = False

def parse_log_timestamp(log_line):
    """
    Extract timestamp from log line
    Supports multiple formats:
    - ISO 8601: 2026-01-06T18:58:44.641Z
    - Custom format: 241210-15:06:38.123456 [mod=QMS, lvl=INFO]
    Returns: datetime object in UTC or None if parsing fails
    """
    try:
        # First try ISO 8601 format: 2026-01-06T18:58:44.641Z
        iso_pattern = r'(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})\.(\d{3})Z'
        match = re.search(iso_pattern, log_line)
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
            hour = int(match.group(4))
            minute = int(match.group(5))
            second = int(match.group(6))
            millisecond = int(match.group(7))
            microsecond = millisecond * 1000  # Convert to microseconds
            
            # Create datetime object in UTC
            dt = datetime(year, month, day, hour, minute, second, microsecond, tzinfo=timezone.utc)
            log_message(f"   Parsed ISO timestamp: {dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} UTC")
            return dt
        
        # Fallback: Try custom format YYMMDD-HH:MM:SS.microseconds
        custom_pattern = r'(\d{6})-(\d{2}):(\d{2}):(\d{2})\.(\d{6})'
        match = re.search(custom_pattern, log_line)
        if match:
            date_str = match.group(1)  # YYMMDD
            hour = match.group(2)
            minute = match.group(3)
            second = match.group(4)
            microsecond = match.group(5)
            
            # Parse date
            year = 2000 + int(date_str[:2])
            month = int(date_str[2:4])
            day = int(date_str[4:6])
            
            # Create datetime object (assume UTC)
            dt = datetime(year, month, day, int(hour), int(minute), int(second), int(microsecond), tzinfo=timezone.utc)
            log_message(f"   Parsed custom timestamp: {dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} UTC")
            return dt
        
        log_message(f"⚠ No matching timestamp pattern found in log line")
    except Exception as e:
        log_message(f"⚠ Error parsing timestamp from log line: {e}")
    return None

def check_for_home_log_continuously(ssh, timeout_seconds, log_message_func, baseline_line_count=None, reboot_start_time=None):
    """
    Continuously check for HOME screen log line for specified timeout
    Only checks for NEW log lines added AFTER baseline_line_count
    
    Args:
        baseline_line_count: Number of lines before the action (HOME key press or reboot)
                            Only checks for logs AFTER this line
        reboot_start_time: datetime object of when reboot started (to filter old log entries)
    Returns: (found: bool, log_line: str or None, time_found: datetime or None)
    """
    start_time = time.time()
    last_log_time = start_time
    check_interval = 5  # Check every 5 seconds
    
    log_message_func(f"⏱ Monitoring logs for HOME screen (timeout: {timeout_seconds}s, checking every {check_interval}s)...")
    if reboot_start_time:
        log_message_func(f"   Reboot started at: {reboot_start_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} UTC")
        log_message_func(f"   Looking for log entries AFTER this time only")
    else:
        log_message_func(f"   ⚠ No reboot start time provided - will accept any HOME log match")
    log_message_func(f"   Searching /opt/logs/sky-messages.log")
    
    while (time.time() - start_time) < timeout_seconds:
        try:
            # OPTIMIZED: Get ONLY the last matching line (most recent HOME log)
            # Use patterns that match what we know works on the device
            grep_patterns = [
                # Priority 1: QMS HOME_TILES complete // this is for XUMO, Rogers IUIv1 and SKY RDKE Devices - most reliable for HOME screen detection
                "grep -E 'QMS.*HOME_TILES.*complete' /opt/logs/sky-messages.log | tail -1",
                
                # Priority 2: App focus event (MOST RELIABLE for HOME screen detection) //  this is for ROGERS IUIv2
                "grep -E 'App focus.*appId=com.entos.monarch_ui' /opt/logs/sky-messages.log | tail -1",
                
                # Priority 3: AppsModel.log App focus (alternative format) // not Required
                "grep -E 'AppsModel.*App focus.*monarch_ui' /opt/logs/sky-messages.log | tail -1",
                
                # Fallback: HOME_TILES only (exclude 'adding package' false positives) // not Required
                "tail -100 /opt/logs/sky-messages.log | grep -E 'HOME_TILES' | tail -1"
            ]
            
            log_output = ""
            error_occurred = False
            matched_pattern_index = -1
            
            # Try each pattern until we find a match
            for idx, grep_cmd in enumerate(grep_patterns, 1):
                try:
                    log_message_func(f"  [DEBUG] Trying pattern {idx}/{len(grep_patterns)}...")
                    stdin, stdout, stderr = ssh.exec_command(grep_cmd, timeout=20)
                    
                    # Read with longer timeout - grep on large files can take time
                    stdout.channel.settimeout(20.0)
                    try:
                        log_output = stdout.read(8192).decode('utf-8', errors='ignore').strip()
                    except socket.timeout:
                        log_message_func(f"  ⚠ Grep command timeout (20s) - log file may be very large")
                        log_output = ""
                    finally:
                        # Always close the channel after reading
                        stdout.channel.close()
                    
                    # If we found a match with this pattern, stop trying other patterns
                    if log_output:
                        matched_pattern_index = idx
                        log_message_func(f"  ✓ Pattern {idx} matched!")
                        break
                except Exception as pattern_error:
                    log_message_func(f"  ⚠ Pattern {idx} check error: {str(pattern_error)[:100]}")
                    error_occurred = True
                    continue
            
            # Check if HOME log line is present
            if log_output.strip():
                pattern_descriptions = [
                    "QMS HOME_TILES complete",
                    "App focus event (monarch_ui)",
                    "AppsModel App focus (alternative format)",
                    "HOME_TILES fallback"
                ]
                pattern_desc = pattern_descriptions[matched_pattern_index - 1] if 0 < matched_pattern_index <= len(pattern_descriptions) else "unknown"
                
                log_message_func(f"  📋 Found HOME log line using pattern {matched_pattern_index}: {pattern_desc}")
                home_line = log_output.strip()
                log_message_func(f"   Raw log line: {home_line[:250]}")
                
                # Parse timestamp from this line
                line_timestamp = parse_log_timestamp(home_line)
                
                if line_timestamp:
                    # Check if this is after reboot
                    is_after_reboot = (reboot_start_time is None) or (line_timestamp > reboot_start_time)
                    
                    if is_after_reboot:
                        time_found = datetime.now(timezone.utc)
                        log_message_func(f"✓ HOME screen log line detected!")
                        log_message_func(f"   Pattern used: {pattern_desc}")
                        log_message_func(f"   Timestamp from log: {line_timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} UTC")
                        log_message_func(f"   Log line: {home_line[:200]}")
                        return True, home_line, time_found
                    else:
                        log_message_func(f"  ⏱ HOME log found but it's from BEFORE reboot - continuing to monitor...")
                        log_message_func(f"     Reboot time: {reboot_start_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} UTC")
                        log_message_func(f"     Log time: {line_timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} UTC")
                else:
                    log_message_func(f"  ⚠ Could not parse timestamp from HOME log line: {home_line[:150]}")
            elif not error_occurred:
                elapsed = time.time() - start_time
                if (time.time() - last_log_time) >= 15:  # Log every 15 seconds instead of 20
                    remaining = timeout_seconds - int(elapsed)
                    log_message_func(f"  ⏱ Still monitoring... {int(elapsed)}s elapsed, {remaining}s remaining")
                    last_log_time = time.time()
            
            # Wait before next check
            time.sleep(check_interval)
            
        except Exception as e:
            log_message_func(f"⚠ Error checking logs: {str(e)[:150]}")
            time.sleep(check_interval)
    
    # Timeout reached without finding HOME log
    log_message_func(f"❌ HOME screen log line NOT found within {timeout_seconds}s timeout")
    return False, None, None

def collect_rdk_milestones_log(ssh, device_ip, device_name, iteration, log_message_func):
    """
    Collect rdk_milestones.log from device using 'cat' command
    
    Args:
        ssh: SSH connection object
        device_ip: Device IP address
        device_name: Device name for filename
        iteration: Current iteration number
        log_message_func: logging function
    
    Returns: str (path to collected log) or None if failed
    """
    try:
        log_message_func(f"\n[RDK MILESTONES LOG] Collecting rdk_milestones.log...")
        
        # Execute cat command to get rdk_milestones.log contents
        cmd = "cat /opt/logs/rdk_milestones.log 2>/dev/null"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=15)
        log_output = stdout.read().decode('utf-8', errors='ignore').strip()
        stdout.channel.close()
        
        if not log_output:
            log_message_func(f"⚠ rdk_milestones.log is empty or not accessible")
            log_message_func(f"   Full log content:\n{log_output}")
            return None
        
        # Parse and display rdk_milestones.log
        log_message_func(f"✓ rdk_milestones.log content retrieved ({len(log_output)} characters):")
        
        # Show first 20 lines
        log_lines = log_output.split('\n')
        for line in log_lines[:20]:
            if line.strip():
                log_message_func(f"   {line[:150]}")
        
        if len(log_lines) > 20:
            log_message_func(f"   ... ({len(log_lines) - 20} more lines)")
        
        return log_output
    
    except Exception as e:
        log_message_func(f"❌ Error collecting rdk_milestones.log: {e}")
        return None

def launch_settings_and_navigate_to_restart(ssh, log_message_func, boot_start_time=None):
    """
    Launch Settings app via Voice curl URL and navigate to System Management > Reset & updates > Restart device
    
    Navigation sequence:
    - DOWN (2x) to reach "System Management"
    - ENTER to select
    - DOWN (2x) to reach "Reset & updates"
    - ENTER to select
    - ENTER to confirm "Restart device"
    - Wait 5 seconds between each key press
    
    Args:
        ssh: SSH connection object
        log_message_func: logging function
        boot_start_time: datetime to track when boot sequence started (updated to last key press time)
    
    Returns: datetime of when the last key press was sent (for performance calculation)
    """
    try:
        log_message_func(f"\n[SOFT BOOT] Launching Settings app via Voice curl...")
        
        # Launch Settings using voice curl with retry logic
        launch_cmd = "curl --header \"Content-Type: application/json\" --request POST --silent -d '{\"jsonrpc\":\"2.0\",\"id\":\"3\",\"method\":\"org.rdk.VoiceControl.1.voiceSessionByText\",\"params\":{\"transcription\":\"SETTINGS\"}}' http://127.0.0.1:9998/jsonrpc"
        
        max_launch_attempts = 3
        launch_success = False
        
        for attempt in range(1, max_launch_attempts + 1):
            try:
                log_message_func(f"  [Attempt {attempt}/{max_launch_attempts}] Sending voice command to launch Settings...")
                stdin, stdout, stderr = ssh.exec_command(launch_cmd, timeout=10)
                output = stdout.read(2048).decode('utf-8', errors='ignore')
                error = stderr.read().decode('utf-8', errors='ignore')
                stdout.channel.close()
                stderr.channel.close()
                
                log_message_func(f"  ✓ Voice command sent")
                if output:
                    log_message_func(f"    Response: {output[:150]}")
                
                launch_success = True
                break
            except Exception as launch_err:
                log_message_func(f"  ⚠ Attempt {attempt} failed: {str(launch_err)[:100]}")
                if attempt < max_launch_attempts:
                    log_message_func(f"    Retrying in 2 seconds...")
                    time.sleep(2)
        
        if not launch_success:
            log_message_func(f"❌ Failed to launch Settings after {max_launch_attempts} attempts")
            log_message_func(f"  Voice command may not be available or network interface not responding")
            return None
        
        log_message_func(f"✓ Settings app launch command sent successfully")
        log_message_func(f"   Waiting 6 seconds for Settings app to fully load and take focus...")
        time.sleep(6)  # Wait longer for app to load and take focus
        
        # Try to verify Settings is active by checking running processes
        try:
            log_message_func(f"\n[SOFT BOOT] Verifying Settings app is active...")
            verify_cmd = "ps aux | grep -i 'settings\\|SettingsService' | grep -v grep | head -1"
            stdin, stdout, stderr = ssh.exec_command(verify_cmd, timeout=5)
            process_output = stdout.read().decode('utf-8', errors='ignore').strip()
            stdout.channel.close()
            stderr.channel.close()
            
            if process_output:
                log_message_func(f"  ✓ Settings process is active")
                log_message_func(f"    {process_output[:100]}")
            else:
                log_message_func(f"  ⚠ Settings process not found in running processes")
                log_message_func(f"    Continuing anyway - may still be initializing...")
        except Exception as verify_err:
            log_message_func(f"  ⚠ Could not verify Settings process: {verify_err}")
        
        # Define navigation sequence
        # Format: (key_name, number_of_times)
        navigation_sequence = [
            ("DOWN", 2),       # Navigate down 2x to System Management
            ("ENTER", 1),      # Select System Management
            ("DOWN", 2),       # Navigate down 2x to Reset & updates
            ("ENTER", 1),      # Select Reset & updates
            ("ENTER", 1),      # Confirm Restart device
        ]
        
        log_message_func(f"\n[SOFT BOOT] Sending navigation keys (10s wait per key press for device response)...")
        log_message_func(f"   Path: Settings > System Management > Reset & updates > Restart device")
        
        last_key_time = None
        total_keys = sum(repeat_count for _, repeat_count in navigation_sequence)
        key_count = 0
        keys_sent_successfully = 0
        
        for key_name, repeat_count in navigation_sequence:
            for i in range(repeat_count):
                key_count += 1
                # Send key press command - keySimulator has initialization overhead
                key_cmd = f"keySimulator -k{key_name.lower()}"
                log_message_func(f"\n  [{key_count}/{total_keys}] Sending key: {key_name} (press {i+1}/{repeat_count})")
                
                try:
                    stdin, stdout, stderr = ssh.exec_command(key_cmd, timeout=15)
                    
                    # CRITICAL: Read ALL output and wait for command to complete
                    # keySimulator has IARM initialization overhead that takes time
                    stdout.channel.settimeout(15)
                    stderr.channel.settimeout(15)
                    
                    output_lines = []
                    try:
                        while True:
                            line = stdout.readline()
                            if isinstance(line, bytes):
                                line = line.decode('utf-8', errors='ignore')
                            if not line:
                                break
                            output_lines.append(line.rstrip())
                            if len(output_lines) > 100:  # Safety limit
                                break
                    except socket.timeout:
                        log_message_func(f"  ⚠ Command read timeout (command may still be executing)")
                    
                    error_lines = []
                    try:
                        while True:
                            line = stderr.readline()
                            if isinstance(line, bytes):
                                line = line.decode('utf-8', errors='ignore')
                            if not line:
                                break
                            error_lines.append(line.rstrip())
                            if len(error_lines) > 100:  # Safety limit
                                break
                    except socket.timeout:
                        pass
                    
                    output = '\n'.join(output_lines)
                    error = '\n'.join(error_lines)
                    
                    # Get command return code
                    return_code = stdout.channel.recv_exit_status()
                    
                    stdout.channel.close()
                    stderr.channel.close()
                    
                    # Record this key press time for performance calculation
                    key_sent = False
                    
                    # Check if command succeeded
                    if 'not found' in output.lower() or 'not found' in error.lower() or 'command not found' in error.lower():
                        log_message_func(f"  ❌ keySimulator not found on device")
                        log_message_func(f"     Please install keySimulator tool: 'apt-get install keySimulator'")
                    elif return_code == 0 or 'Sending Key' in output:
                        # Success! The key was sent
                        key_sent = True
                        keys_sent_successfully += 1
                        last_key_time = datetime.now(timezone.utc)
                        log_message_func(f"  ✓ Key sent successfully at: {last_key_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} UTC")
                        
                        # Show key processing details from output
                        if 'IR=' in output:
                            # Extract IR key info
                            ir_match = output[output.find('IR='):output.find('IR=') + 50]
                            log_message_func(f"    {ir_match.split(chr(10))[0][:100]}")
                    else:
                        log_message_func(f"  ⚠ Command returned code {return_code}")
                        if output:
                            first_line = output.split('\n')[0][:100]
                            log_message_func(f"    Output: {first_line}")
                    
                    if key_sent:
                        # Wait for device to respond and update UI
                        # keySimulator command itself takes time, so reduce extra wait
                        if not (key_name == navigation_sequence[-1][0] and i == repeat_count - 1):
                            log_message_func(f"  ⏱ Waiting 6 seconds for device UI to respond...")
                            time.sleep(6)
                        else:
                            # For the last key, wait 3 seconds then start monitoring
                            log_message_func(f"  ⏱ Waiting 3 seconds for device to process restart command...")
                            time.sleep(3)
                    else:
                        log_message_func(f"  ⚠ Failed to send key, likely due to missing keySimulator tool")
                        
                except socket.timeout:
                    log_message_func(f"  ❌ SSH timeout waiting for keySimulator response after 15s")
                    last_key_time = datetime.now(timezone.utc)
                except Exception as key_err:
                    log_message_func(f"  ⚠ Error sending key '{key_name}': {str(key_err)[:150]}")
                    last_key_time = datetime.now(timezone.utc)
        
        if keys_sent_successfully == 0:
            log_message_func(f"\n❌ ERROR: No navigation keys were sent successfully!")
            log_message_func(f"  This is likely due to missing key input mechanisms on the device")
            log_message_func(f"  Available methods to try:")
            log_message_func(f"    - Install keySimulator tool on device")
            log_message_func(f"    - Enable netcat (nc) for alternative key input")
            log_message_func(f"    - Use RDK remote control interface instead")
            return None
        
        log_message_func(f"\n✓ Successfully sent {keys_sent_successfully}/{total_keys} navigation keys")
        log_message_func(f"  Last key press time: {last_key_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} UTC")
        log_message_func(f"  Device should begin restart sequence now...")
        
        return last_key_time
    
    except Exception as e:
        log_message_func(f"❌ Error during Settings navigation: {e}")
        import traceback
        log_message_func(f"  Traceback: {traceback.format_exc()}")
        return None

def wait_for_device_with_early_ssh_probing(device_ip, port, username, password, initial_wait=50, ssh_probe_start=30, probe_interval=5, total_ssh_timeout=120, log_callback=None):
    """
    OPTIMIZED: Wait for device with intelligent early SSH probing
    
    Instead of waiting 85s before attempting SSH, this function:
    1. Waits for initial_wait seconds (50s) 
    2. Starts SSH probing at ssh_probe_start seconds (30s) - within the wait period
    3. Continues probing for up to total_ssh_timeout seconds
    4. Returns SSH connection when device comes back online
    
    This ensures we catch logs that are written during the boot phase (40-70s typically)
    
    Args:
        initial_wait: Initial wait time before device expected to reboot fully (50s)
        ssh_probe_start: When to start SSH probing attempts within the wait period (30s)
        probe_interval: Time between SSH connection attempts (5s)
        total_ssh_timeout: Total time to keep trying SSH connections (120s)
        log_callback: Function to log messages
    
    Returns:
        paramiko.SSHClient if device comes back online, None if timeout
    """
    log = log_callback or print
    start_time = time.time()
    
    # Phase 1: Initial passive wait (device shutdown)
    log(f"\n[PROBING PHASE 1] Passive wait for {initial_wait}s (device shutting down)...")
    sys.stdout.flush()  # Force log output immediately
    time.sleep(initial_wait)
    
    # Phase 2: Wait until ssh_probe_start time from reboot
    elapsed = time.time() - start_time
    if elapsed < ssh_probe_start:
        wait_until_probe = ssh_probe_start - elapsed
        log(f"[PROBING PHASE 2] Waiting {wait_until_probe:.0f}s more until {ssh_probe_start}s mark...")
        sys.stdout.flush()
        time.sleep(wait_until_probe)
    
    # Phase 3: Active SSH probing
    log(f"[PROBING PHASE 3] Starting SSH probing at {ssh_probe_start}s mark...")
    log(f"   Will probe every {probe_interval}s for up to {total_ssh_timeout}s (max total: {ssh_probe_start + total_ssh_timeout}s)")
    sys.stdout.flush()  # Force log output immediately
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    elapsed_probe_time = 0
    while elapsed_probe_time < total_ssh_timeout:
        # Check if job has been cancelled
        from method_utils import is_job_cancelled
        if is_job_cancelled():
            log(f"❌ Job cancelled during SSH probing - stopping")
            return None
        
        try:
            log(f"  ⏱ SSH probe attempt at {elapsed_probe_time}s mark...")
            ssh.connect(device_ip, port=port, username=username, password=password, timeout=5)
            elapsed_total = time.time() - start_time
            log(f"✓ Device reconnected after {elapsed_total:.1f}s total")
            log(f"   (Initial wait: {ssh_probe_start}s, SSH probing: {elapsed_probe_time}s)")
            return ssh
        except Exception as e:
            # Connection failed, continue probing
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            time.sleep(probe_interval)
            elapsed_probe_time = time.time() - start_time - ssh_probe_start
    
    log(f"❌ Device did not come back online within {ssh_probe_start + total_ssh_timeout}s total")
    return None

def execute_soft_hard_boot_process(device_ip, port, username, password, iteration=1, device_name="Device", combined_method_name=None, boot_type="HARD", optional_checks=None, home_screen_timeout=180, job_id=None):
    """
    Execute Soft Boot or Hard Boot Performance Monitoring
    
    HARD BOOT: Uses 'systemctl reboot' command
    - Performance calculated from command sent time to HOME screen detection
    
    SOFT BOOT: Navigates through Settings GUI
    - Launches Settings app via Voice curl
    - Navigates: System Management > Reset & updates > Restart device
    - Performance calculated from last key press time to HOME screen detection
    - Navigation keys: DOWN(2x), ENTER, DOWN(2x), ENTER, ENTER with 5s wait per key
    
    Both boot types:
    - Capture rdk_milestones.log using 'cat /opt/logs/rdk_milestones.log'
    - Monitor logs for HOME screen detection
    - Support early SSH probing
    
    Args:
        device_ip: Device IP address
        port: SSH port
        username: SSH username
        password: SSH password
        iteration: Current iteration number
        device_name: Device name
        combined_method_name: Sequence name if part of sequence
        boot_type: "HARD" or "SOFT" (default: "HARD")
        optional_checks: Post-reboot validation checks
        home_screen_timeout: Timeout for HOME screen detection (default: 180s)
    """
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    screenshots_list = []
    logs_list = []
    optional_checks = optional_checks or {}
    screenshot_result_before = None
    screen_validation = None
    build_info = None
    check_results = None
    rdk_milestones_log = None
    
    # Store job_id in thread-local storage for cancellation checking
    if job_id:
        from method_utils import set_current_job_id
        import threading
        set_current_job_id(threading.get_ident(), job_id)
    
    # Clean device name for filename
    safe_device_name = device_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    
    # Validate boot type
    if boot_type not in ["HARD", "SOFT"]:
        boot_type = "HARD"
    
    # Set USB log file path for this execution
    try:
        from services.log_service import LogService
        log_service = LogService()
        usb_log_path = create_execution_log_path(device_ip, device_name, iteration, f"SOFT_HARD_BOOT_{boot_type}")
        log_service.current_usb_log_file = usb_log_path
        log_message(f"💾 USB execution log: {usb_log_path}")
    except Exception as e:
        log_message(f"⚠ Could not set USB log path: {e}")
    
    log_message("="*80)
    log_message(f"SOFT BOOT / HARD BOOT PERFORMANCE MONITORING - {boot_type} - START")
    log_message("="*80)
    log_message(f"Boot Type: {boot_type}")
    if boot_type == "HARD":
        log_message("Command: systemctl reboot")
        log_message("Performance calculated from: Command sent → HOME log detection")
    else:
        log_message("Method: Settings GUI navigation")
        log_message("Path: Settings > System Management > Reset & updates > Restart device")
        log_message("Performance calculated from: Last key press → HOME log detection")
    log_message("Additional data collection: rdk_milestones.log")
    log_message("="*80)
    
    try:
        # STEP 1: DEVICE CONNECTION & PRE-BOOT SETUP
        log_message("[STEP 1] Connecting to device and initial setup...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(device_ip, port=port, username=username, password=password, timeout=15)
        log_message("✓ Connected to device successfully")
        
        # Fetch build details from device
        build_info = fetch_build_details(ssh, log_message)
        
        # Activate ScreenCapture service before boot
        activate_screencapture_service(ssh, log_message)
        
        # Ensure device is on HOME screen before boot sequence
        log_message("Ensuring device is on HOME screen before boot sequence...")
        try:
            home_key_command = "timeout 5 keySimulator -khome || true"  # Timeout after 5s, continue even if fails
            stdin, stdout, stderr = ssh.exec_command(home_key_command, timeout=8)
            
            # Read output with built-in timeout (8 seconds)
            stdout.channel.settimeout(8)
            try:
                response = stdout.read(1024).decode('utf-8', errors='ignore')
            except:
                response = ""  # Timeout occurred, just use empty response
            finally:
                # Always close the channel after reading
                stdout.channel.close()
            
            log_message("✓ HOME button pressed to navigate to HOME screen")
            if response:
                log_message(f"   Response: {response[:100]}")
            log_message("   Waiting 10 seconds for UI to settle...")
            time.sleep(10)
        except Exception as e:
            log_message(f"⚠ Warning: Failed to press HOME button: {e}")
            log_message("   Continuing with boot sequence anyway...")
        
        # Capture BEFORE screenshot
        log_message("\n[STEP 1.5] Capturing BEFORE screenshot...")
        log_message("⚠ NOTE: Screenshot is informational - execution will continue even if it fails")
        try:
            screenshot_folder_before = create_screenshot_folder(device_ip, device_name, iteration, "Before", method_name=f"soft_hard_boot_{boot_type.lower()}", execution_timestamp=timestamp)
            screenshot_name_before = f"{device_ip}_{safe_device_name}_Iteration-{iteration}_Before-{boot_type}Boot_{timestamp}"
            screenshot_result_before = take_vnc_screenshot_with_fallback(
                    ssh=ssh,
                    device_ip=device_ip,
                    device_name=safe_device_name,
                    iteration=iteration,
                    screenshot_folder=screenshot_folder_before, after_reboot=False,
                    log_callback=log_message,
                    fallback_to_plugin=True,
                    context="Default"
                )
            if screenshot_result_before and screenshot_result_before.get('success'):
                log_message(f"✓ BEFORE screenshot saved: {screenshot_result_before.get('local_path')}")
                screenshots_list.append(screenshot_result_before.get('local_path', ''))
            else:
                error_msg = screenshot_result_before.get('error', 'Unknown error') if screenshot_result_before else 'Screenshot failed'
                log_message(f"⚠ BEFORE screenshot not available: {error_msg}")
                log_message("✓ Continuing with boot sequence anyway...")
                screenshot_result_before = None
        except Exception as e:
            log_message(f"⚠ Warning: Failed to capture BEFORE screenshot: {e}")
            log_message("✓ Continuing with boot sequence anyway...")
            screenshot_result_before = None
        
        log_message("✓ Pre-boot setup complete")
        
        # STEP 2: SEND REBOOT COMMAND OR NAVIGATE SETTINGS
        boot_start_time = datetime.now(timezone.utc)
        
        if boot_type == "HARD":
            # HARD BOOT: Send hard power off command
            log_message("\n[STEP 2] Sending HARD BOOT command...")
            log_message(f"⏱ Boot command timestamp (UTC): {boot_start_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
            
            stdin, stdout, stderr = ssh.exec_command(hard_power_off_command)
            error_output = stderr.read().decode('utf-8', errors='ignore')
            
            # Always close the channel after reading
            stdout.channel.close()
            stderr.channel.close()
            
            if error_output:
                log_message(f"⚠ Reboot command stderr: {error_output}")
            
            ssh.close()
            log_message("✓ HARD BOOT command sent successfully")
            
            # STEP 3: Wait for device with early SSH probing
            log_message(f"\n[STEP 3] ULTRA-OPTIMIZED WAIT STRATEGY - 10s passive + SSH probing from 40s...")
            ssh = wait_for_device_with_early_ssh_probing(
                device_ip, port, username, password,
                initial_wait=10,
                ssh_probe_start=40,
                probe_interval=5,
                total_ssh_timeout=100,
                log_callback=log_message
            )
        else:
            # SOFT BOOT: Navigate through Settings GUI
            log_message("\n[STEP 2] Initiating SOFT BOOT via Settings GUI...")
            
            # Launch Settings and navigate to restart option
            last_key_time = launch_settings_and_navigate_to_restart(ssh, log_message, boot_start_time)
            
            if not last_key_time:
                log_message("❌ Failed to navigate Settings for SOFT BOOT")
                ssh.close()
                return {"iteration": iteration, "screenshots": screenshots_list, "logs": logs_list, "success": False, "device_name": device_name}
            
            # Update boot_start_time to last key press time for performance calculation
            boot_start_time = last_key_time
            
            # Close current connection for device restart
            ssh.close()
            
            # STEP 3: Wait for device with early SSH probing
            log_message(f"\n[STEP 3] ULTRA-OPTIMIZED WAIT STRATEGY - 10s passive + SSH probing from 40s...")
            ssh = wait_for_device_with_early_ssh_probing(
                device_ip, port, username, password,
                initial_wait=10,
                ssh_probe_start=40,
                probe_interval=5,
                total_ssh_timeout=100,
                log_callback=log_message
            )
        
        if not ssh:
            log_message("❌ Device did not come back online within timeout")
            return {"iteration": iteration, "screenshots": screenshots_list, "logs": logs_list, "success": False, "device_name": device_name}
        
        log_message("✓ Device is back online - SSH connection established")
        
        # STEP 4: MONITOR LOGS FOR HOME SCREEN
        elapsed_since_boot = time.time() - boot_start_time.timestamp()
        remaining_timeout = max(30, home_screen_timeout - elapsed_since_boot)
        
        log_message(f"\n[STEP 4] Monitoring logs for HOME screen detection...")
        log_message(f"   Elapsed since boot: {elapsed_since_boot:.0f}s")
        log_message(f"   Will monitor for up to: {remaining_timeout:.0f}s more (total timeout: {home_screen_timeout}s)")
        
        home_found, home_log_line, home_time = check_for_home_log_continuously(
            ssh, timeout_seconds=int(remaining_timeout), log_message_func=log_message, 
            reboot_start_time=boot_start_time, baseline_line_count=None
        )
        time.sleep(5)
        
        # STEP 5: COLLECT RDK MILESTONES LOG
        log_message("\n[STEP 5] Collecting diagnostic logs...")
        rdk_milestones_log = collect_rdk_milestones_log(ssh, device_ip, device_name, iteration, log_message)
        
        # STEP 6: PROCESS RESULTS
        reboot_duration = None
        performance_str = "N/A"
        
        if home_found:
            log_message("\n[STEP 6] Calculating boot performance time...")
            
            # Try to parse timestamp from log line
            log_timestamp = parse_log_timestamp(home_log_line)
            
            if log_timestamp:
                # Calculate duration using log timestamp
                reboot_duration = (log_timestamp - boot_start_time).total_seconds()
                log_message(f"✓ Boot Start Time (UTC): {boot_start_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
                log_message(f"✓ HOME Log Timestamp (UTC): {log_timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
                log_message(f"✓ Calculated Boot Duration: {reboot_duration:.2f} seconds")
                performance_str = f"{reboot_duration:.2f}s"
            else:
                # Fallback to detection time
                reboot_duration = (home_time - boot_start_time).total_seconds()
                log_message(f"⚠ Could not parse log timestamp, using detection time")
                log_message(f"✓ Calculated Boot Duration (approximate): {reboot_duration:.2f} seconds")
                performance_str = f"~{reboot_duration:.2f}s"
            
            # STEP 7: Capture AFTER screenshot
            log_message("\n[STEP 7] Capturing success screenshot...")
            
            # Re-activate screencapture service after boot
            log_message("Re-activating ScreenCapture service after boot...")
            activate_screencapture_service(ssh, log_message)
            log_message("Waiting 3 seconds for service to fully initialize...")
            sys.stdout.flush()
            time.sleep(3)
            sys.stdout.flush()
            
            screenshot_folder = create_screenshot_folder(device_ip, device_name, iteration, "SUCCESS", method_name=f"soft_hard_boot_{boot_type.lower()}", execution_timestamp=timestamp)
            screenshot_name = f"{device_ip}_{safe_device_name}_Iteration-{iteration}_After-{boot_type}Boot-SUCCESS_{timestamp}"
            
            log_message("⏱ Screenshot capture will timeout after 60 seconds automatically")
            sys.stdout.flush()
            screenshot_result = None
            try:
                screenshot_result = take_vnc_screenshot_with_fallback(
                    ssh=ssh,
                    device_ip=device_ip,
                    device_name=safe_device_name,
                    iteration=iteration,
                    screenshot_folder=screenshot_folder,
                    log_callback=log_message,
                    fallback_to_plugin=True,
                    context="Default"
                )
            except Exception as e:
                log_message(f"⚠ Screenshot capture exception: {e}")
                log_message("⚠ Continuing with test - screenshot is non-critical")
                sys.stdout.flush()
                screenshot_result = None
            
            # Process screenshot result if successful
            if screenshot_result and screenshot_result.get('success'):
                screenshots_list.append(screenshot_result.get('local_path', ''))
                log_message(f"✓ Screenshot saved: {screenshot_result.get('local_path', 'N/A')}")
            else:
                error_msg = screenshot_result.get('error', 'Unknown error') if screenshot_result else 'Screenshot capture failed'
                log_message(f"⚠ Screenshot not captured: {error_msg}")
                log_message("✓ Test continues - screenshot is informational only")
                sys.stdout.flush()
            
            # Validate screen comparison (informational only)
            screen_validation = None
            if screenshot_result_before and screenshot_result:
                screen_validation = validate_screen_comparison(screenshot_result_before, screenshot_result, log_message)
                
                if screen_validation and not screen_validation.get('screen_validation_passed'):
                    log_message("\n" + "="*80)
                    log_message("⚠ Screen Validation INFO: Screen comparison did not pass")
                    log_message(f"⚠ {screen_validation.get('message', 'Unknown validation issue')}")
                    log_message("⚠ NOTE: Test continues - Log check is primary validation criterion")
                    if reboot_duration:
                        log_message(f"✓ Performance: {performance_str}")
                    log_message("="*80)
                elif screen_validation and screen_validation.get('screen_validation_passed'):
                    log_message("\n" + "="*80)
                    log_message("✓ Screen Validation PASSED (informational)")
                    log_message(f"✓ {screen_validation.get('message', 'Screen comparison successful')}")
                    log_message("="*80)
            else:
                log_message("⚠ Screen validation skipped - BEFORE or AFTER screenshot unavailable")
            
            log_message("\n" + "="*80)
            log_message(f"✓ SOFT/HARD BOOT TEST {boot_type} PASSED")
            if reboot_duration:
                log_message(f"✓ Performance: {performance_str}")
            log_message("="*80)
            
            # STEP 8: Execute post-boot checks (if configured)
            check_results = None
            if optional_checks and (optional_checks.get('custom_commands') or optional_checks.get('skip_all')):
                log_message("\n[STEP 8] Post-boot validation checks...")
                # For now, simplified - can be expanded later
                check_results = {
                    'custom_checks': [],
                    'overall_passed': True,
                    'stop_iterations': False,
                    'collected_logs': []
                }
            else:
                check_results = {
                    'custom_checks': [],
                    'overall_passed': True,
                    'stop_iterations': False,
                    'collected_logs': []
                }
            
            ssh.close()
            
            # Return success
            return {
                "iteration": iteration, 
                "screenshots": screenshots_list, 
                "logs": logs_list, 
                "success": True, 
                "performance_seconds": reboot_duration,
                "rdk_milestones_log": rdk_milestones_log,
                "boot_type": boot_type,
                "optional_checks": check_results,
                "stop_iterations": check_results.get('stop_iterations', False),
                "screen_validation": screen_validation,
                "build_info": build_info,
                "device_name": device_name
            }
        
        else:
            # HOME screen not found - capture failure screenshot
            log_message("\n[STEP 6] HOME screen NOT found - Capturing failure screenshot...")
            
            # Re-activate screencapture service
            log_message("Re-activating ScreenCapture service...")
            activate_screencapture_service(ssh, log_message)
            log_message("Waiting 3 seconds for service to fully initialize...")
            time.sleep(3)
            
            screenshot_folder = create_screenshot_folder(device_ip, device_name, iteration, "FAILED", method_name=f"soft_hard_boot_{boot_type.lower()}", execution_timestamp=timestamp)
            screenshot_name = f"{device_ip}_{safe_device_name}_Iteration-{iteration}_After-{boot_type}Boot-FAILED_{timestamp}"
            
            try:
                screenshot_result = take_vnc_screenshot_with_fallback(
                    ssh=ssh,
                    device_ip=device_ip,
                    device_name=safe_device_name,
                    iteration=iteration,
                    screenshot_folder=screenshot_folder,
                    log_callback=log_message,
                    fallback_to_plugin=True,
                    context="Default"
                )
                if screenshot_result and screenshot_result.get('success'):
                    screenshots_list.append(screenshot_result.get('local_path', ''))
                else:
                    log_message("⚠ Failure screenshot not captured - continuing anyway")
            except Exception as e:
                log_message(f"⚠ Screenshot capture exception: {e}")
            
            # Check for network/Realtek errors
            check_network_and_realtek_errors(ssh, log_message)
            
            log_message("\n" + "="*80)
            log_message(f"❌ SOFT/HARD BOOT TEST {boot_type} FAILED")
            log_message(f"❌ Device did not reach HOME screen within {home_screen_timeout} seconds")
            log_message("="*80)
            
            ssh.close()
            return {
                "iteration": iteration,
                "screenshots": screenshots_list,
                "logs": logs_list,
                "success": False,
                "performance_seconds": reboot_duration,
                "rdk_milestones_log": rdk_milestones_log,
                "boot_type": boot_type,
                "build_info": build_info,
                "optional_checks": check_results or {
                    'custom_checks': [],
                    'overall_passed': False,
                    'stop_iterations': False,
                    'collected_logs': []
                },
                "stop_iterations": False,
                "device_name": device_name
            }
    
    except Exception as e:
        import traceback
        log_message(f"❌ Error during Soft/Hard Boot test: {e}")
        log_message(f"Full traceback:\n{traceback.format_exc()}")
        return {
            "iteration": iteration,
            "screenshots": screenshots_list,
            "logs": logs_list,
            "success": False,
            "performance_seconds": None,
            "rdk_milestones_log": rdk_milestones_log,
            "boot_type": boot_type,
            "build_info": build_info,
            "optional_checks": check_results or {
                'custom_checks': [],
                'overall_passed': False,
                'stop_iterations': False,
                'collected_logs': []
            },
            "stop_iterations": False,
            "device_name": device_name
        }
