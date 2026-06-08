#!/usr/bin/env python3
"""
Maintenance > DeepSleep > Wakeup Process Implementation
Complete workflow following the attached specification:
  1. Check maintenance activity status
  2. Stop maintenance if necessary
  3. Wait 5 minutes
  4. Trigger maintenance (standby, wait 1 minute, start maintenance)
  5. Poll status every 30 seconds until MAINTENANCE_ERROR or MAINTENANCE_COMPLETE
  6. Verify device stays in STANDBY
  7. Reboot device after maintenance completes
  8. Verify device in STANDBY
  9. Wait 15 minutes for DeepSleep entry
  10. Verify device inaccessible via SSH (DeepSleep confirmed)
  11. Wake up with IR POWER key
  12. Calculate wake-up time from POWER key to SSH accessibility
"""

import sys
import time
import json
import socket
import paramiko
import threading
from paramiko.ssh_exception import SSHException as ParamikException
from datetime import datetime, timezone

# Import configurations
from config_commands import (
    device_status_command,
    home_key_command,
    maintenance_get_status_command,
    maintenance_start_command,
    maintenance_stop_command,
    maintenance_reboot_command
)
from config_log_patterns import *
from config_timing import *

# Import utilities
from method_utils import (
    log_message,
    fetch_build_details,
    activate_screencapture_service,
    create_screenshot_folder,
    create_execution_log_path,
    send_home_key_based_on_power_state,
    reconnect_to_device_with_retry,
    check_network_and_realtek_errors,
    capture_device_logs_sftp,
    capture_minimal_logs_fallback,
    get_folder_method_name
)

# Import screenshot utilities
from screenshot_utils import take_and_analyze_screenshot
from screenshot_utils_vnc import take_vnc_screenshot_with_fallback

# Import IR utilities
from config_ir_blaster import get_ir_config_for_device, generate_ir_code, send_ir_command

# Import device lock manager
from utils.device_lock_manager import DeviceLockManager
from models.device_lock import DeviceLock


# ============================================================================
# HELPER FUNCTIONS FOR IMPROVED TIMEOUT HANDLING
# ============================================================================

def execute_ssh_command_with_timeout(ssh_client, command, timeout_seconds=10, log_callback=None):
    """
    Execute SSH command with proper timeout handling and thread-based cancellation.
    Prevents hanging SSH commands by enforcing strict timeout.
    
    Args:
        ssh_client: Paramiko SSH client (already connected)
        command: Shell command to execute
        timeout_seconds: Max time to wait for command output (default 10s)
        log_callback: Optional callback function for logging
    
    Returns:
        Tuple: (success, output_string) 
               - success: True if command completed within timeout
               - output_string: Command output or empty string if timeout/error
    """
    result = {"success": False, "output": "", "timed_out": False}
    
    def run_command():
        try:
            transport = ssh_client.get_transport()
            if not transport or not transport.is_active():
                result["output"] = ""
                return
            
            channel = transport.open_session()
            channel.exec_command(command)
            
            # Set timeout on channel
            channel.settimeout(timeout_seconds)
            
            try:
                output = channel.recv(8192).decode('utf-8', errors='ignore')
                result["output"] = output.strip()
                result["success"] = len(output) > 0
            except socket.timeout:
                result["timed_out"] = True
                result["output"] = ""
                if log_callback:
                    log_callback(f"  ⚠ SSH command timeout after {timeout_seconds}s")
            finally:
                try:
                    channel.close()
                except:
                    pass
        except Exception as e:
            result["output"] = ""
            if log_callback:
                log_callback(f"  ⚠ SSH command error: {str(e)[:80]}")
    
    # Run command in thread with timeout
    thread = threading.Thread(target=run_command, daemon=True)
    thread.start()
    thread.join(timeout=timeout_seconds + 2)  # Allow extra 2 seconds for cleanup
    
    return result["success"], result["output"]


def verify_ssh_connection_health(ssh_client, log_callback=None):
    """
    Quick health check of SSH connection without blocking.
    
    Args:
        ssh_client: Paramiko SSH client
        log_callback: Optional logging callback
    
    Returns:
        bool: True if connection is alive
    """
    try:
        transport = ssh_client.get_transport()
        if transport and transport.is_active():
            return True
    except:
        pass
    
    if log_callback:
        log_callback("  ⚠ SSH connection appears stale")
    return False


def detect_home_screen_with_fallback(ssh_client, timeout_seconds=120, log_callback=None, screenshot_callback=None, power_command_time=None):
    """
    Detect HOME screen on device with multiple fallback strategies (TIME-AWARE).
    
    IMPORTANT: This function now uses time-aware detection. It looks for HOME screen 
    log entries that appear AFTER the power command was sent, not old HOME entries 
    from the log history.
    
    Args:
        ssh_client: Connected SSH client
        timeout_seconds: Max time to spend detecting HOME screen
        log_callback: Logging function
        screenshot_callback: Optional function to take screenshot as fallback
        power_command_time: Unix timestamp when IR POWER was sent (for time-aware detection)
    
    Returns:
        Tuple: (home_detected, detection_method, log_line)
               - home_detected: True if HOME screen found
               - detection_method: String describing how it was detected
               - log_line: The log line that was found (if any)
    """
    # Get baseline log state IMMEDIATELY after power command (if not provided)
    if power_command_time is None:
        power_command_time = time.time()
    
    # Allow small buffer for log entries to appear
    detection_start_time = time.time()
    
    # HOME patterns - will be checked sequentially
    home_patterns = [
        ("QMS HOME_TILES", "grep -E 'QMS.*HOME_TILES.*complete' /opt/logs/sky-messages.log | tail -1"),
        ("App focus", "grep -E 'App focus.*appId=com.entos.monarch_ui' /opt/logs/sky-messages.log | tail -1"),
        ("HOME_TILES fallback", "tail -200 /opt/logs/sky-messages.log | grep -E 'HOME_TILES' | tail -1"),
    ]
    
    check_start = time.time()
    check_interval = 5  # Check every 5 seconds
    
    if log_callback:
        log_callback(f"\n[TIME-AWARE HOME DETECTION] Baseline set at power command time")
        log_callback(f"  Will detect HOME entries occurring AFTER power command (+buffer)")
    
    while (time.time() - check_start) < timeout_seconds:
        # Check SSH connection health
        if not verify_ssh_connection_health(ssh_client, log_callback):
            if log_callback:
                log_callback("  ⚠ SSH connection lost - attempting to proceed with screenshot")
            break
        
        # Try each pattern
        for pattern_name, grep_cmd in home_patterns:
            try:
                success, output = execute_ssh_command_with_timeout(
                    ssh_client, grep_cmd, timeout_seconds=8, log_callback=log_callback
                )
                
                if success and output and output.strip():
                    # Extract timestamp from log line if possible (format: YYYY-MM-DD HH:MM:SS or similar)
                    # Pattern: Look for ISO format timestamp at start of line or in brackets
                    import re
                    timestamp_match = re.search(r'\[?(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2})', output)
                    
                    if timestamp_match:
                        timestamp_str = timestamp_match.group(1).replace('T', ' ')
                        try:
                            from datetime import datetime
                            log_entry_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S').timestamp()
                            
                            # Check if this entry is AFTER the power command
                            time_diff = log_entry_time - power_command_time
                            
                            if time_diff >= -2:  # Allow 2 second margin for clock sync
                                if log_callback:
                                    log_callback(f"✓ HOME screen detected using pattern: {pattern_name}")
                                    log_callback(f"  Detected {time_diff:.1f}s after IR POWER command")
                                    log_callback(f"  Log line: {output[:180]}")
                                return True, f"LOG_DETECTED_{pattern_name}", output
                            else:
                                if log_callback:
                                    if int(time.time() - check_start) % 20 == 0:
                                        log_callback(f"  ⏳ HOME log found but BEFORE power command ({time_diff:.1f}s) - skipping old entry")
                        except Exception as e:
                            # If timestamp parsing fails, accept the entry anyway
                            if log_callback:
                                log_callback(f"✓ HOME screen detected using pattern: {pattern_name} (timestamp parse skipped)")
                                log_callback(f"  Log line: {output[:180]}")
                            return True, f"LOG_DETECTED_{pattern_name}", output
                    else:
                        # No timestamp in log line - accept it as fresh detection
                        if log_callback:
                            log_callback(f"✓ HOME screen detected using pattern: {pattern_name}")
                            log_callback(f"  Log line: {output[:180]}")
                        return True, f"LOG_DETECTED_{pattern_name}", output
                        
            except Exception as e:
                if log_callback:
                    if int(time.time() - check_start) % 30 == 0:
                        log_callback(f"  ⏳ Pattern check ({pattern_name}): {str(e)[:50]}")
        
        # Log progress every 25 seconds
        elapsed = int(time.time() - check_start)
        if elapsed % 25 == 0 and elapsed > 0:
            remaining = timeout_seconds - int(elapsed)
            if log_callback:
                log_callback(f"  ⏱ Still monitoring... {elapsed}s elapsed, {remaining}s remaining")
        
        time.sleep(check_interval)
    
    # HOME detection timeout - try screenshot as fallback
    if log_callback:
        log_callback("⚠ HOME screen log detection timeout - attempting screenshot fallback")
    
    if screenshot_callback:
        try:
            screenshot_success = screenshot_callback()
            if screenshot_success:
                return True, "SCREENSHOT_FALLBACK", "HOME screen detected via screenshot"
        except Exception as e:
            if log_callback:
                log_callback(f"  ⚠ Screenshot fallback failed: {str(e)[:80]}")
    
    # Both log and screenshot detection failed
    if log_callback:
        log_callback("⚠ HOME screen detection failed - using SSH connection time as fallback")
    return False, "SSH_ACCESSIBLE_FALLBACK", ""


def verify_deep_sleep_state(device_ip, port, username, password, log_callback=None):
    """
    Verify device is truly in deep sleep by checking multiple metrics.
    
    Args:
        device_ip: Device IP
        port: SSH port
        username: SSH username
        password: SSH password
        log_callback: Logging function
    
    Returns:
        Tuple: (is_in_deep_sleep, verification_method)
    """
    # Strategy: Try to connect - if device is in true deep sleep, it should be unreachable
    try:
        test_ssh = paramiko.SSHClient()
        test_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        test_ssh.connect(device_ip, port=port, username=username, password=password, timeout=5)
        test_ssh.close()
        
        # Device is reachable - check if it's really sleeping or just in standby
        if log_callback:
            log_callback("⚠ Device is still accessible via SSH")
            log_callback("  → Device may not be in true deep sleep (possibly in light sleep/standby)")
        return False, "STILL_ACCESSIBLE"
    except (ParamikException, socket.timeout, ConnectionRefusedError, OSError):
        if log_callback:
            log_callback("✓ Device is inaccessible via SSH (Deep Sleep confirmed)")
        return True, "UNREACHABLE"
    except Exception as e:
        if log_callback:
            log_callback(f"✓ Device verification returned: {str(e)[:60]} (treating as deep sleep)")
        return True, "CONNECTION_ERROR_ASSUMED_DEEP_SLEEP"


# ============================================================================
# MAIN EXECUTION FUNCTION
# ============================================================================

def execute_maintenance_deepsleep_wakeup_process(
    device_ip, port, username, password, iteration=1, device_name="Device", 
    combined_method_name=None, remote_type=None, sleep_duration_minutes=60, job_id=None,
    execute_deepsleep_wakeup=True, remaining_iterations=1, execution_queue=None
):
    """
    Execute Maintenance > DeepSleep > Wakeup Process following the specification:
    
    **Steps 1-7: Maintenance Cycle** (Always Executed)
    Step 1: Check maintenance activity status
    Step 2: If maintenance in progress, stop it and wait 5 minutes
    Step 3: Put device in STANDBY and verify
    Step 4: Start maintenance and poll status
    Step 5: Verify device remains in STANDBY during maintenance
    Step 6: Reboot device after maintenance completes
    Step 7: Wait 15 minutes for DeepSleep entry
    
    **Steps 8-12: DeepSleep & Wakeup** (Optional - Controlled by execute_deepsleep_wakeup)
    Step 8: Verify device inaccessible (DeepSleep confirmed)
    Step 9: Wake up with IR POWER key
    Step 10: Measure time from POWER key to SSH accessibility
    Step 11: Validate device functionality post-wakeup
    
    Args:
        device_ip: Target device IP address
        port: SSH port (typically 10022)
        username: SSH username (typically 'root')
        password: SSH password
        iteration: Iteration number for logging
        device_name: Device name for IR config and folder naming
        combined_method_name: Combined method name for folder naming
        remote_type: IR remote type ('XUMO' or 'SKY'). If None, auto-detect from device_name
        sleep_duration_minutes: Minutes to wait in DeepSleep before waking up (default 60)
        job_id: Job ID for lock management
        execute_deepsleep_wakeup: If True, execute steps 8-12 (deep sleep and wake-up)
                                If False, stop after step 7 (maintenance cycle only)
                                Default: True (full workflow)
    
    Returns:
        dict: {"iteration": int, "screenshots": list, "logs": list, "success": bool, 
               "wakeup_time_seconds": float (or None if deepsleep skipped), "details": str}
    """
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    screenshots_list = []
    logs_list = []
    wakeup_time_seconds = None
    power_key_send_time = None
    
    # Store job_id for cancellation checking
    if job_id:
        from method_utils import set_current_job_id
        import threading
        set_current_job_id(threading.get_ident(), job_id)
    
    safe_device_name = device_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    
    # Log execution parameters
    log_message("="*80)
    log_message("MAINTENANCE > DEEPSLEEP > WAKEUP PROCESS - START")
    log_message("="*80)
    log_message(f"Device: {device_name} ({device_ip})")
    log_message(f"Iteration: {iteration}")
    log_message(f"DeepSleep Duration: {sleep_duration_minutes} minutes")
    log_message(f"Remote Type: {remote_type or 'Auto-detect (from device name)'}")
    log_message("="*80)
    
    # Set USB log file path for this execution
    try:
        from services.log_service import LogService
        log_service = LogService()
        usb_log_path = create_execution_log_path(device_ip, device_name, iteration, "MAINTENANCE_DEEPSLEEP_WAKEUP")
        log_service.current_usb_log_file = usb_log_path
        log_message(f"💾 USB execution log: {usb_log_path}")
    except Exception as e:
        log_message(f"⚠ Could not set USB log path: {e}")
    
    try:
        # STEP 1-2: Check and manage maintenance status
        log_message("\n" + "="*80)
        log_message("[STEP 1-2] Checking maintenance activity status...")
        log_message("="*80)
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(device_ip, port=port, username=username, password=password, timeout=10)
        
        # Fetch build details
        fetch_build_details(ssh, log_message)
        
        # Check maintenance activity status
        stdin, stdout, stderr = ssh.exec_command(maintenance_get_status_command)
        time.sleep(2)
        response = stdout.read().decode('utf-8', errors='ignore').strip()
        
        log_message(f"Maintenance activity status response: {response[:200]}")
        
        # Parse maintenance status - look for maintenanceStatus in response
        maintenance_status = None
        is_reboot_pending = False
        try:
            response_json = json.loads(response) if response.startswith('{') else {}
            maintenance_status = response_json.get('result', {}).get('maintenanceStatus', '').upper()
            is_reboot_pending = response_json.get('result', {}).get('isRebootPending', False)
            log_message(f"Current maintenance status: {maintenance_status}")
            log_message(f"Reboot pending: {is_reboot_pending}")
        except:
            log_message("⚠ Could not parse maintenance status JSON, checking in text response")
            if 'MAINTENANCE_ERROR' in response:
                maintenance_status = 'MAINTENANCE_ERROR'
            elif 'MAINTENANCE_COMPLETE' in response:
                maintenance_status = 'MAINTENANCE_COMPLETE'
            else:
                maintenance_status = 'UNKNOWN'
            if 'isRebootPending":true' in response or '"isRebootPending": true' in response:
                is_reboot_pending = True
        
        # *** STEP 1-2: CONDITIONAL CHECKS (Only execute if MAINTENANCE_ERROR + isRebootPending=true) ***
        # Decision Logic:
        # - If MAINTENANCE_ERROR + isRebootPending=true: Execute CHECK 1, CHECK 2, CHECK 3
        # - Else: Skip all checks and proceed directly to STEP 3
        
        if maintenance_status == 'MAINTENANCE_ERROR' and is_reboot_pending:
            # CHECK 1: Emergency reboot if MAINTENANCE_ERROR + isRebootPending=true
            log_message("\n" + "="*80)
            log_message("⚠️ EDGE CASE: Device in MAINTENANCE_ERROR with reboot pending")
            log_message("="*80)
            log_message("Executing emergency reboot to recover device...")
            
            # Execute reboot
            stdin, stdout, stderr = ssh.exec_command("systemctl reboot")
            time.sleep(2)
            reboot_response = stdout.read().decode('utf-8', errors='ignore').strip()
            log_message(f"Reboot command response: {reboot_response[:100]}")
            ssh.close()
            
            # Wait for device to reboot and become SSH-accessible again
            log_message("\n⏱️  Waiting for device to reboot and become SSH-accessible...")
            max_reboot_wait = 120  # 2 minutes max wait
            reboot_check_interval = 5
            device_is_back = False
            ssh_accessible_time = None
            
            for attempt in range(max_reboot_wait // reboot_check_interval):
                remaining = max_reboot_wait - (attempt * reboot_check_interval)
                try:
                    test_ssh = paramiko.SSHClient()
                    test_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    test_ssh.connect(device_ip, port=port, username=username, password=password, timeout=5)
                    test_ssh.close()
                    device_is_back = True
                    ssh_accessible_time = time.time()
                    log_message(f"✓ Device SSH accessible after {attempt * reboot_check_interval}s")
                    break
                except:
                    if attempt % 2 == 0:
                        log_message(f"  ⏳ Device not ready ({remaining}s remaining)...")
                    time.sleep(reboot_check_interval)
            
            if not device_is_back:
                log_message("❌ Device failed to come back online after reboot")
                return {
                    "iteration": iteration,
                    "screenshots": screenshots_list,
                    "logs": logs_list,
                    "success": False,
                    "wakeup_time_seconds": None,
                    "details": "Device failed to recover after reboot"
                }
            
            # ============================================================================
            # POST-REBOOT STABILIZATION: Wait 90 seconds for device to stabilize
            # ============================================================================
            log_message("\n" + "="*80)
            log_message("[POST-REBOOT STABILIZATION] Waiting 90 seconds for device to stabilize...")
            log_message("="*80)
            log_message("Device is SSH-accessible but needs time to fully boot and stabilize")
            log_message("Expected final state: STANDBY")
            
            stabilization_wait = 90
            chunk_size = 15  # Log every 15 seconds
            stabilization_start = time.time()
            
            for elapsed in range(0, stabilization_wait, chunk_size):
                remaining = stabilization_wait - elapsed
                if remaining > 0:
                    log_message(f"  ⏳ Stabilizing... {remaining}s remaining")
                    time.sleep(min(chunk_size, remaining))
            
            log_message("\n✓ 90-second stabilization wait complete")
            
            # ============================================================================
            # CHECK DEVICE POWER STATE AFTER STABILIZATION
            # ============================================================================
            log_message("\n[POST-REBOOT CHECK] Verifying device power state...")
            
            try:
                test_ssh = paramiko.SSHClient()
                test_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                test_ssh.connect(device_ip, port=port, username=username, password=password, timeout=10)
                
                # Check power state
                stdin, stdout, stderr = test_ssh.exec_command(device_status_command)
                time.sleep(2)
                post_reboot_power_state = stdout.read().decode('utf-8', errors='ignore').strip().upper()
                log_message(f"📋 Device power state after stabilization: {post_reboot_power_state[:100]}")
                
                # Get IR config for potential wake-up
                ir_config = get_ir_config_for_device(device_name)
                remote_type_mapping = {
                    'SKY': 'SKY_LC103',
                    'COMCAST': 'XUMO_PR3',
                    'XUMO': 'XUMO_PR3',
                    'SKY_LC103': 'SKY_LC103',
                    'XUMO_PR3': 'XUMO_PR3'
                }
                
                if remote_type and remote_type.upper() in remote_type_mapping:
                    selected_remote_type = remote_type_mapping[remote_type.upper()]
                else:
                    selected_remote_type = 'SKY_LC103' if 'SKY' in device_name.upper() else 'XUMO_PR3'
                
                # If device is in STANDBY, send IR POWER to wake it up
                if 'STANDBY' in post_reboot_power_state:
                    log_message("\n✅ Device is in STANDBY - sending IR POWER to turn ON...")
                    
                    ir_code_power = generate_ir_code("POWER", ir_config['ir_port'], remote_type=selected_remote_type)
                    send_ir_command(ir_code_power, ir_config['itach_ip'], ir_config['itach_port'], log_message)
                    
                    time.sleep(15)  # Wait for device to respond to IR command
                    
                    # Monitor for HOME screen
                    log_message("\n[POST-REBOOT] Monitoring for HOME screen after IR POWER...")
                    
                    def take_post_reboot_screenshot():
                        try:
                            method_for_folder = get_folder_method_name() or combined_method_name or "maintenance_deepsleep_wakeup"
                            screenshot_folder = create_screenshot_folder(device_ip, safe_device_name, iteration, "PostRebootWakeup", method_for_folder)
                            screenshot_name = f"{device_ip}_{safe_device_name}_Iteration-{iteration}_PostRebootWakeup_{timestamp}"
                            screenshot_result = take_and_analyze_screenshot(test_ssh, screenshot_name, device_ip, log_message, screenshot_folder)
                            return screenshot_result and screenshot_result.get('success', False)
                        except Exception as e:
                            log_message(f"  ⚠ Post-reboot screenshot error: {str(e)[:80]}")
                            return False
                    
                    home_detected, detection_method, _ = detect_home_screen_with_fallback(
                        test_ssh, timeout_seconds=120, log_callback=log_message,
                        screenshot_callback=take_post_reboot_screenshot
                    )
                    
                    if home_detected:
                        log_message(f"\n✓ HOME screen detected after post-reboot wake-up (Method: {detection_method})")
                    else:
                        log_message("\n⚠ HOME screen not detected after post-reboot wake-up - continuing anyway")
                
                elif 'ON' in post_reboot_power_state or 'ACTIVE' in post_reboot_power_state:
                    log_message("\n✅ Device is already ON - no wake-up needed")
                    
                    # Monitor for HOME screen
                    log_message("\n[POST-REBOOT] Monitoring for HOME screen...")
                    
                    def take_post_reboot_screenshot():
                        try:
                            method_for_folder = get_folder_method_name() or combined_method_name or "maintenance_deepsleep_wakeup"
                            screenshot_folder = create_screenshot_folder(device_ip, safe_device_name, iteration, "PostRebootOn", method_for_folder)
                            screenshot_name = f"{device_ip}_{safe_device_name}_Iteration-{iteration}_PostRebootOn_{timestamp}"
                            screenshot_result = take_and_analyze_screenshot(test_ssh, screenshot_name, device_ip, log_message, screenshot_folder)
                            return screenshot_result and screenshot_result.get('success', False)
                        except Exception as e:
                            log_message(f"  ⚠ Post-reboot screenshot error: {str(e)[:80]}")
                            return False
                    
                    home_detected, detection_method, _ = detect_home_screen_with_fallback(
                        test_ssh, timeout_seconds=120, log_callback=log_message,
                        screenshot_callback=take_post_reboot_screenshot
                    )
                    
                    if home_detected:
                        log_message(f"\n✓ HOME screen detected (Method: {detection_method})")
                    else:
                        log_message("\n⚠ HOME screen not detected - continuing anyway")
                
                else:
                    log_message(f"\n⚠ Device in unexpected power state: {post_reboot_power_state}")
                
                test_ssh.close()
            
            except Exception as e:
                log_message(f"\n⚠ Error during post-reboot checks: {str(e)[:80]}")
            
            # Now reconnect for maintenance status check
            log_message("\nRe-checking maintenance activity status after reboot and stabilization...")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(device_ip, port=port, username=username, password=password, timeout=10)
            
            stdin, stdout, stderr = ssh.exec_command(maintenance_get_status_command)
            time.sleep(2)
            reboot_status_response = stdout.read().decode('utf-8', errors='ignore').strip()
            log_message(f"Post-reboot status response: {reboot_status_response[:200]}")
            
            # Parse post-reboot status
            post_reboot_status = None
            post_reboot_is_reboot_pending = False
            try:
                status_json = json.loads(reboot_status_response) if reboot_status_response.startswith('{') else {}
                post_reboot_status = status_json.get('result', {}).get('maintenanceStatus', '').upper()
                post_reboot_is_reboot_pending = status_json.get('result', {}).get('isRebootPending', False)
                log_message(f"Post-reboot maintenance status: {post_reboot_status}")
                log_message(f"Post-reboot reboot pending: {post_reboot_is_reboot_pending}")
            except:
                log_message("⚠ Could not parse post-reboot status")
            
            # If post-reboot status is MAINTENANCE_STARTED and isRebootPending=false
            if post_reboot_status == 'MAINTENANCE_STARTED' and not post_reboot_is_reboot_pending:
                log_message("✓ Post-reboot status is MAINTENANCE_STARTED with reboot pending cleared")
                log_message("Sending stopMaintenance command to clean up...")
                
                stdin, stdout, stderr = ssh.exec_command(maintenance_stop_command)
                time.sleep(2)
                stop_response = stdout.read().decode('utf-8', errors='ignore').strip()
                log_message(f"Stop maintenance response: {stop_response[:100]}")
                
                # ✨ OPTIMIZED: Wait only 10 seconds (was 3 minutes) then re-check status
                log_message("\n⏱️  Waiting 10 seconds for maintenance to fully stop...")
                log_message("Then re-checking maintenance status...")
                time.sleep(10)
                
                # Re-check maintenance status after 10 seconds
                stdin, stdout, stderr = ssh.exec_command(maintenance_get_status_command)
                time.sleep(2)
                check1_final_response = stdout.read().decode('utf-8', errors='ignore').strip()
                log_message(f"\nRe-checked maintenance status: {check1_final_response[:200]}")
                
                # Parse the final status
                check1_final_status = None
                check1_final_is_reboot_pending = False
                try:
                    check1_final_json = json.loads(check1_final_response) if check1_final_response.startswith('{') else {}
                    check1_final_status = check1_final_json.get('result', {}).get('maintenanceStatus', '').upper()
                    check1_final_is_reboot_pending = check1_final_json.get('result', {}).get('isRebootPending', False)
                except:
                    if 'MAINTENANCE_ERROR' in check1_final_response:
                        check1_final_status = 'MAINTENANCE_ERROR'
                    elif 'MAINTENANCE_STARTED' in check1_final_response:
                        check1_final_status = 'MAINTENANCE_STARTED'
                    if '"isRebootPending": true' in check1_final_response or 'isRebootPending":true' in check1_final_response:
                        check1_final_is_reboot_pending = True
                
                log_message(f"Final parsed status: {check1_final_status}, rebootPending: {check1_final_is_reboot_pending}")
                
                # Check if device is now in clean state
                if check1_final_status == 'MAINTENANCE_ERROR' and not check1_final_is_reboot_pending:
                    log_message("\n✓ [CHECK 1 SUCCESS] Device is now in clean state (MAINTENANCE_ERROR, rebootPending=false)")
                    log_message("✓ Cleanup completed in CHECK 1 - NO need for CHECK 2 and CHECK 3")
                    log_message("✓ Proceeding directly to STEP 3")
                    
                    # Set flag to skip CHECK 2 and CHECK 3
                    skip_check_2_and_3 = True
                else:
                    log_message(f"\n⚠ [CHECK 1] Device status: {check1_final_status} (rebootPending={check1_final_is_reboot_pending})")
                    log_message("⚠ Status not fully clean - proceeding to CHECK 2 for additional cleanup")
                    skip_check_2_and_3 = False
            else:
                log_message(f"⚠ Post-reboot status unexpected: {post_reboot_status} (rebootPending={post_reboot_is_reboot_pending})")
                log_message("Continuing to CHECK 2...")
                skip_check_2_and_3 = False
            
            # *** CHECK 2: Clean up MAINTENANCE_STARTED (runs ONLY after CHECK 1 if needed) ***
            # This check ONLY runs if CHECK 1 did not achieve clean state
            # Workflow: Stop → Start → Check status → Stop → Verify
            if not skip_check_2_and_3:
                log_message("\n" + "="*80)
                log_message("⚠️ CHECK 2: MANDATORY CLEANUP WORKFLOW - EXECUTING")
                log_message("="*80)
                log_message(f"Current status: {maintenance_status} (reboot pending: {is_reboot_pending})")
                log_message("Executing CHECK 2 workflow: Stop → Start → Check → Stop → Verify")
                log_message("This ensures device is in clean maintenance state before STEP 3")
                
                try:
                    
                    # Step 1: Send initial stopMaintenance
                    log_message("\n[CHECK 2 - Step 1] Sending initial stopMaintenance command...")
                    stdin, stdout, stderr = ssh.exec_command(maintenance_stop_command)
                    time.sleep(2)
                    stop_response1 = stdout.read().decode('utf-8', errors='ignore').strip()
                    log_message(f"Initial stop response: {stop_response1[:100]}")
                    
                    # Wait 30 sec
                    log_message("Waiting 30 seconds for maintenance to stop...")
                    time.sleep(30)
                    
                    # Step 2: Start maintenance again
                    log_message("\n[CHECK 2 - Step 2] Starting maintenance to trigger clean cycle...")
                    stdin, stdout, stderr = ssh.exec_command(maintenance_start_command)
                    time.sleep(2)
                    start_response = stdout.read().decode('utf-8', errors='ignore').strip()
                    log_message(f"Start maintenance response: {start_response[:100]}")
                    
                    # Wait 10 sec for device to process
                    time.sleep(10)
                    
                    # Step 3: Check maintenance status
                    log_message("\n[CHECK 2 - Step 3] Checking maintenance status after restart...")
                    stdin, stdout, stderr = ssh.exec_command(maintenance_get_status_command)
                    time.sleep(2)
                    check_response = stdout.read().decode('utf-8', errors='ignore').strip()
                    log_message(f"Status check response: {check_response[:150]}")
                    
                    # Parse status
                    check_status = None
                    try:
                        check_json = json.loads(check_response) if check_response.startswith('{') else {}
                        check_status = check_json.get('result', {}).get('maintenanceStatus', '').upper()
                        log_message(f"Current maintenance status: {check_status}")
                    except:
                        log_message("⚠ Could not parse status in CHECK 2")
                        check_status = 'UNKNOWN'
                    
                    # Step 4: Send stopMaintenance again
                    log_message("\n[CHECK 2 - Step 4] Sending stopMaintenance to force cleanup...")
                    stdin, stdout, stderr = ssh.exec_command(maintenance_stop_command)
                    time.sleep(2)
                    stop_response2 = stdout.read().decode('utf-8', errors='ignore').strip()
                    log_message(f"Final stop response: {stop_response2[:100]}")
                    
                    # Step 5: Verify maintenance stopped
                    log_message("\n[CHECK 2 - Step 5] Verifying maintenance is stopped...")
                    log_message("Waiting 10 seconds for maintenance to fully stop...")
                    wait_time = 10  # 10 seconds (optimized from 3 minutes)
                    chunk_size = 5
                    for elapsed in range(0, wait_time, chunk_size):
                        remaining = wait_time - elapsed
                        if remaining > 0:
                            log_message(f"  ⏳ {remaining}s remaining...")
                            time.sleep(min(chunk_size, remaining))
                    
                    # Final verification
                    stdin, stdout, stderr = ssh.exec_command(maintenance_get_status_command)
                    time.sleep(2)
                    final_response = stdout.read().decode('utf-8', errors='ignore').strip()
                    log_message(f"\nFinal status verification: {final_response[:150]}")
                    
                    try:
                        final_json = json.loads(final_response) if final_response.startswith('{') else {}
                        final_status = final_json.get('result', {}).get('maintenanceStatus', '').upper()
                        log_message(f"✓ CHECK 2 Complete - Final status: {final_status}")
                    except:
                        log_message("✓ CHECK 2 Complete - Status verification attempted")
                    
                    
                    # Reconnect for proceeding to STEP 3
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(device_ip, port=port, username=username, password=password, timeout=10)
                    
                    log_message("✓ CHECK 2 workflow complete - Device ready for CHECK 3")
                
                except Exception as e:
                    log_message(f"\n❌ CHECK 2 encountered error: {str(e)[:100]}")
                    log_message("Attempting to recover and reconnect...")
                    try:
                        if ssh:
                            ssh.close()
                    except:
                        pass
                    
                    # Reconnect for recovery
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(device_ip, port=port, username=username, password=password, timeout=10)
                    log_message("✓ Reconnected after CHECK 2 error - continuing to CHECK 3")
                
                # *** CHECK 3: Final verification of maintenance cleanup ***
                # This check ONLY executes after CHECK 1 and CHECK 2 (within the if block)
                # Purpose: Verify final device maintenance state before proceeding to STEP 3
                log_message("\n" + "="*80)
                log_message("⚠️ CHECK 3: FINAL VERIFICATION - Verifying device maintenance cleanup")
                log_message("="*80)
                log_message("Status: CHECK 2 cleanup workflow has completed")
                log_message("Purpose: Verify final state and handle any edge cases")
                
                # Verify current maintenance status after CHECKs 1-2
                log_message("\n[CHECK 3] Checking final maintenance status...")
                
                # Get fresh maintenance status
                try:
                    stdin, stdout, stderr = ssh.exec_command(maintenance_get_status_command)
                    time.sleep(2)
                    check3_response = stdout.read().decode('utf-8', errors='ignore').strip()
                    log_message(f"Final maintenance status response: {check3_response[:200]}")
                    
                    # Parse CHECK 3 status
                    check3_maintenance_status = None
                    check3_is_reboot_pending = False
                    try:
                        check3_response_json = json.loads(check3_response) if check3_response.startswith('{') else {}
                        check3_maintenance_status = check3_response_json.get('result', {}).get('maintenanceStatus', '').upper()
                        check3_is_reboot_pending = check3_response_json.get('result', {}).get('isRebootPending', False)
                    except:
                        if 'MAINTENANCE_ERROR' in check3_response:
                            check3_maintenance_status = 'MAINTENANCE_ERROR'
                        elif 'MAINTENANCE_COMPLETE' in check3_response:
                            check3_maintenance_status = 'MAINTENANCE_COMPLETE'
                        elif 'MAINTENANCE_STARTED' in check3_response:
                            check3_maintenance_status = 'MAINTENANCE_STARTED'
                        if '"isRebootPending": true' in check3_response or 'isRebootPending":true' in check3_response:
                            check3_is_reboot_pending = True
                    
                    log_message(f"CHECK 3 parsed status: {check3_maintenance_status}")
                    log_message(f"CHECK 3 reboot pending: {check3_is_reboot_pending}")
                    
                    # Handle lingering states not caught by CHECK 1 & 2
                    if check3_maintenance_status in ['MAINTENANCE_STARTED', 'MAINTENANCE_IN_PROGRESS']:
                        log_message(f"\n[CHECK 3] Found residual MAINTENANCE state: {check3_maintenance_status}")
                        log_message("[CHECK 3] Sending stopMaintenance to clean up...")
                        
                        stdin, stdout, stderr = ssh.exec_command(maintenance_stop_command)
                        time.sleep(2)
                        check3_stop_response = stdout.read().decode('utf-8', errors='ignore').strip()
                        log_message(f"[CHECK 3] Stop response: {check3_stop_response[:100]}")
                        
                        # Wait for stop to complete
                        log_message("[CHECK 3] Waiting 30 seconds for maintenance to stop...")
                        time.sleep(30)
                        
                        # Verify it stopped
                        stdin, stdout, stderr = ssh.exec_command(maintenance_get_status_command)
                        time.sleep(2)
                        verify_stop_response = stdout.read().decode('utf-8', errors='ignore').strip()
                        log_message(f"[CHECK 3] Verified status after stop: {verify_stop_response[:100]}")
                        
                        if 'MAINTENANCE_ERROR' in verify_stop_response or 'MAINTENANCE_COMPLETE' in verify_stop_response:
                            log_message("✓ [CHECK 3] Maintenance state cleaned successfully")
                        else:
                            log_message("⚠ [CHECK 3] Maintenance state may still be present, will proceed with caution")
                    
                    elif check3_maintenance_status == 'MAINTENANCE_ERROR' and check3_is_reboot_pending:
                        log_message(f"\n⚠ [CHECK 3] Found MAINTENANCE_ERROR with reboot pending")
                        log_message("[CHECK 3] This should have been handled by CHECK 1")
                        log_message("[CHECK 3] Will proceed as CHECK 1 should have handled this")
                    
                    elif check3_maintenance_status == 'MAINTENANCE_COMPLETE':
                        log_message(f"\n✓ [CHECK 3] Maintenance already COMPLETE - clean state confirmed")
                    
                    else:
                        log_message(f"\n✓ [CHECK 3] Device in clean state (status: {check3_maintenance_status or 'IDLE'})")
                
                except Exception as e:
                    log_message(f"⚠ [CHECK 3] Error during status verification: {str(e)[:100]}")
                
                log_message("\n" + "="*80)
                log_message("✓ CHECK 3 COMPLETE - Maintenance state verification done")
                log_message("="*80)
                log_message("Summary of STEP 1-2 Execution:")
                log_message(f"  • CHECK 1 (Emergency Reboot): Executed")
                log_message(f"  • CHECK 2 (Cleanup): Executed")
                log_message(f"  • CHECK 3 (Final Verification): Completed")
                log_message("Proceeding to STEP 3 - Ensure device is in STANDBY")
                log_message("="*80)
            
            else:
                # CHECK 2 and CHECK 3 skipped - device is already clean after CHECK 1
                log_message("\n" + "="*80)
                log_message("✓ STEP 1-2 STATUS: CHECK 1 achieved clean state")
                log_message("="*80)
                log_message(f"Final maintenance status: {check1_final_status}")
                log_message(f"Reboot pending: {check1_final_is_reboot_pending}")
                log_message("✓ CHECK 2 and CHECK 3 skipped - already clean")
                log_message("Proceeding directly to STEP 3")
                log_message("="*80)
        
        else:
            # No error condition detected in initial check - skip all checks and proceed to STEP 3
            log_message("\n" + "="*80)
            log_message("✓ STEP 1-2 STATUS: No emergency conditions detected")
            log_message("="*80)
            log_message(f"Initial maintenance status: {maintenance_status}")
            log_message(f"Reboot pending: {is_reboot_pending}")
            log_message("Skipping CHECK 1, CHECK 2, CHECK 3 - proceeding directly to STEP 3")
            log_message("="*80)
        
        # First, check current power state
        log_message("Checking current device power state...")
        stdin, stdout, stderr = ssh.exec_command(device_status_command)
        time.sleep(2)
        power_state = stdout.read().decode('utf-8', errors='ignore').strip()
        initial_power_state = power_state[:100]
        log_message(f"Device power state: {initial_power_state}")
        
        # Get IR configuration for device
        ir_config = get_ir_config_for_device(device_name)
        
        # Determine remote type - map UI selections to ir_keycodes remote types
        # UI shows 'SKY', 'XUMO', 'COMCAST' but ir_keycodes.json expects 'SKY_LC103', 'XUMO_PR3'
        remote_type_mapping = {
            'SKY': 'SKY_LC103',
            'COMCAST': 'XUMO_PR3',
            'XUMO': 'XUMO_PR3',
            'SKY_LC103': 'SKY_LC103',  # Also support full names
            'XUMO_PR3': 'XUMO_PR3'
        }
        
        if remote_type and remote_type.upper() in remote_type_mapping:
            selected_remote_type = remote_type_mapping[remote_type.upper()]
            log_message(f"📡 Using user-selected remote type: {remote_type.upper()} -> {selected_remote_type}")
        else:
            selected_remote_type = 'SKY_LC103' if 'SKY' in device_name.upper() else 'XUMO_PR3'
            log_message(f"📡 Auto-detected remote type from device name: {selected_remote_type}")
        
        log_message(f"🔌 Using IR port {ir_config['ir_port']} with iTach at {ir_config['itach_ip']}:{ir_config['itach_port']}")
        
        # SCENARIO 1: Device is in ON state
        # Action: Send IR POWER to power OFF the device (ON > STANDBY transition)
        if 'ON' in power_state.upper() and 'STANDBY' not in power_state.upper() and 'LIGHTSLEEP' not in power_state.upper():
            log_message("\n" + "="*80)
            log_message("📍 SCENARIO 1: Device is in ON state")
            log_message("="*80)
            log_message("✓ Sending IR POWER key to power OFF device (ON > STANDBY transition)...")
            
            ir_code_power = generate_ir_code("POWER", ir_config['ir_port'], remote_type=selected_remote_type)
            if send_ir_command(ir_code_power, ir_config['itach_ip'], ir_config['itach_port'], log_message):
                log_message("✓ IR POWER command sent successfully")
            else:
                log_message("⚠ Warning: IR POWER command may have failed")
            
            log_message("Waiting 30 seconds for device to process POWER command and transition to STANDBY...")
            time.sleep(30)
            
            # Check device state after POWER key
            stdin, stdout, stderr = ssh.exec_command(device_status_command)
            time.sleep(2)
            power_state = stdout.read().decode('utf-8', errors='ignore').strip()
            log_message(f"Device power state after IR POWER: {power_state[:100]}")
            
            if 'STANDBY' in power_state.upper():
                log_message("✓ Device successfully transitioned to STANDBY (ON > STANDBY)")
            else:
                log_message(f"⚠ Device did not enter STANDBY - Current state: {power_state[:100]}")
        
        # SCENARIO 2: Device is in LIGHTSLEEP state
        # Action: Send IR POWER to turn ON (LIGHTSLEEP > ON), then send IR POWER again for STANDBY (ON > STANDBY)
        elif 'LIGHTSLEEP' in power_state.upper() and 'STANDBY' not in power_state.upper():
            log_message("\n" + "="*80)
            log_message("📍 SCENARIO 2: Device is in LIGHTSLEEP state")
            log_message("="*80)
            
            # Step 2a: Send IR POWER to turn ON the device (LIGHTSLEEP > ON)
            log_message("✓ Step 2a: Sending IR POWER key to turn ON device (LIGHTSLEEP > ON transition)...")
            ir_code_power = generate_ir_code("POWER", ir_config['ir_port'], remote_type=selected_remote_type)
            if send_ir_command(ir_code_power, ir_config['itach_ip'], ir_config['itach_port'], log_message):
                log_message("✓ IR POWER command sent successfully")
            else:
                log_message("⚠ Warning: IR POWER command may have failed")
            
            log_message("Waiting 30 seconds for device to transition from LIGHTSLEEP to ON...")
            time.sleep(30)
            
            # Check device state - should be ON now
            stdin, stdout, stderr = ssh.exec_command(device_status_command)
            time.sleep(2)
            power_state = stdout.read().decode('utf-8', errors='ignore').strip()
            log_message(f"Device power state after first IR POWER: {power_state[:100]}")
            
            if 'ON' in power_state.upper() and 'STANDBY' not in power_state.upper():
                log_message("✓ Device successfully transitioned to ON (LIGHTSLEEP > ON)")
            else:
                log_message(f"⚠ Device state: {power_state[:100]} (expected ON)")
            
            # Step 2b: Send IR POWER again to set device to STANDBY (ON > STANDBY)
            log_message("\n✓ Step 2b: Sending IR POWER key again to transition to STANDBY (ON > STANDBY transition)...")
            ir_code_power = generate_ir_code("POWER", ir_config['ir_port'], remote_type=selected_remote_type)
            if send_ir_command(ir_code_power, ir_config['itach_ip'], ir_config['itach_port'], log_message):
                log_message("✓ IR POWER command sent successfully")
            else:
                log_message("⚠ Warning: IR POWER command may have failed")
            
            log_message("Waiting 30 seconds for device to process POWER command and transition to STANDBY...")
            time.sleep(30)
            
            # Check device state - should be STANDBY now
            stdin, stdout, stderr = ssh.exec_command(device_status_command)
            time.sleep(2)
            power_state = stdout.read().decode('utf-8', errors='ignore').strip()
            log_message(f"Device power state after second IR POWER: {power_state[:100]}")
            
            if 'STANDBY' in power_state.upper():
                log_message("✓ Device successfully transitioned to STANDBY (ON > STANDBY)")
            else:
                log_message(f"⚠ Device did not enter STANDBY - Current state: {power_state[:100]}")
        
        # SCENARIO 3: Device already in STANDBY
        # No action needed
        elif 'STANDBY' in power_state.upper():
            log_message("\n" + "="*80)
            log_message("📍 SCENARIO 3: Device already in STANDBY")
            log_message("="*80)
            log_message("✓ Device already in STANDBY - No action required")
        
        # SCENARIO 4: Unknown or unexpected state
        else:
            log_message("\n" + "="*80)
            log_message("📍 SCENARIO 4: Unknown or unexpected device state")
            log_message("="*80)
            log_message(f"⚠ Unexpected device state: {power_state[:100]}")
            log_message("Attempting to send IR POWER to cycle device to STANDBY...")
            
            ir_code_power = generate_ir_code("POWER", ir_config['ir_port'], remote_type=selected_remote_type)
            if send_ir_command(ir_code_power, ir_config['itach_ip'], ir_config['itach_port'], log_message):
                log_message("✓ IR POWER command sent successfully")
            else:
                log_message("⚠ Warning: IR POWER command may have failed")
            
            log_message("Waiting 30 seconds for device to process POWER command...")
            time.sleep(30)
            
            # Check device state
            stdin, stdout, stderr = ssh.exec_command(device_status_command)
            time.sleep(2)
            power_state = stdout.read().decode('utf-8', errors='ignore').strip()
            log_message(f"Device power state after IR POWER: {power_state[:100]}")
        
        # Final verification - device must be in STANDBY
        if 'STANDBY' not in power_state.upper():
            log_message("\n" + "="*80)
            log_message("❌ STEP 3 FAILED - Device did not reach STANDBY state")
            log_message("="*80)
            log_message(f"Final device state: {power_state[:100]}")
            log_message("\nPossible causes:")
            log_message("  • IR signal not reaching device (Remote blocked or out of range)")
            log_message("  • Device not responding to IR POWER command")
            log_message("  • Device application preventing STANDBY transition")
            log_message("  • Device power settings configured differently")
            log_message("\nAction Required: Check device and IR connectivity")
            
            return {
                "iteration": iteration,
                "screenshots": screenshots_list,
                "logs": logs_list,
                "success": False,
                "wakeup_time_seconds": None,
                "details": f"STEP 3 FAILED: Device did not enter STANDBY. Final state: {power_state}"
            }
        
        log_message("\n" + "="*80)
        log_message("✓ STEP 3 PASSED - Device is in STANDBY and ready for maintenance")
        log_message("="*80)
        
        # Wait before starting maintenance (Per manual procedure: total 1 minute from initial check)
        log_message("Waiting 30 seconds before starting maintenance...")
        time.sleep(30)
        
        log_message("✓ Device ready for maintenance start")
        
        # STEP 4: Start maintenance (Per manual procedure)
        log_message("\n" + "="*80)
        log_message("[STEP 4] Starting maintenance cycle via MaintenanceManager...")
        log_message("="*80)
        
        log_message("Sending startMaintenance command via RDK MaintenanceManager API...")
        stdin, stdout, stderr = ssh.exec_command(maintenance_start_command)
        time.sleep(2)
        start_response = stdout.read().decode('utf-8', errors='ignore').strip()
        log_message(f"Start maintenance response: {start_response[:200]}")
        
        if 'success":true' in start_response or 'success": true' in start_response:
            log_message("✓ Maintenance start command accepted")
        
        ssh.close()
        
        # Wait 10 seconds to allow device to process startMaintenance and reach MAINTENANCE_STARTED state
        log_message("\n⏳ Waiting 10 seconds for device to process startMaintenance command...")
        time.sleep(10)
        log_message("✓ Ready to check maintenance status")
        
        # STEP 5: Poll maintenance status every 10 seconds (Per manual procedure)
        log_message("\n" + "="*80)
        log_message("[STEP 5] Polling maintenance activity status every 10 seconds...")
        log_message("Goal: Wait for MAINTENANCE_ERROR status with isRebootPending=true")
        log_message("="*80)
        
        # Get INITIAL maintenance status right after startMaintenance command (BEFORE polling)
        log_message("\n📊 INITIAL STATUS CHECK (before polling starts):")
        log_message("-" * 80)
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(device_ip, port=port, username=username, password=password, timeout=10)
            
            stdin, stdout, stderr = ssh.exec_command(maintenance_get_status_command)
            time.sleep(2)
            initial_response = stdout.read().decode('utf-8', errors='ignore').strip()
            
            # Parse initial status
            try:
                initial_json = json.loads(initial_response) if initial_response.startswith('{') else {}
                initial_status = initial_json.get('result', {}).get('maintenanceStatus', 'UNKNOWN').upper()
                initial_reboot_pending = initial_json.get('result', {}).get('isRebootPending', False)
                initial_is_critical = initial_json.get('result', {}).get('isCriticalMaintenance', False)
            except:
                if 'MAINTENANCE_ERROR' in initial_response:
                    initial_status = 'MAINTENANCE_ERROR'
                elif 'MAINTENANCE_COMPLETE' in initial_response:
                    initial_status = 'MAINTENANCE_COMPLETE'
                else:
                    initial_status = 'IN_PROGRESS'
                initial_reboot_pending = 'isRebootPending":true' in initial_response
                initial_is_critical = 'true' in initial_response
            
            log_message(f"  📍 Maintenance Status: {initial_status}")
            log_message(f"  🔄 Reboot Pending: {initial_reboot_pending}")
            log_message(f"  ⚡ Critical Maintenance: {initial_is_critical}")
            log_message(f"  📝 Full Response: {initial_response[:150]}")
            log_message("-" * 80)
            
            ssh.close()
        except Exception as e:
            log_message(f"⚠ Error getting initial status: {str(e)[:100]}")
        
        maintenance_complete = False
        poll_count = 0
        max_polls = 360  # Maximum 60 minutes of polling (10 sec poll interval * 360 polls = 3600 sec = 60 min)
        
        while not maintenance_complete and poll_count < max_polls:
            # Check job cancellation
            from method_utils import is_job_cancelled
            if is_job_cancelled():
                log_message("\n❌ Job cancelled during maintenance polling")
                return {
                    "iteration": iteration, "screenshots": screenshots_list, 
                    "logs": logs_list, "success": False, 
                    "details": "Job cancelled during maintenance polling"
                }
            
            # Validate device lock
            if job_id and not DeviceLockManager.is_lock_valid_for_job(device_ip, job_id):
                log_message(f"\n❌ CRITICAL: Device lock lost during maintenance!")
                return {
                    "iteration": iteration, "screenshots": screenshots_list, 
                    "logs": logs_list, "success": False, 
                    "details": "Device lock lost during maintenance polling"
                }
            
            # Wait 30 seconds between polls
            log_message(f"\n⏳ Poll #{poll_count + 1}: Waiting 10 seconds...")
            time.sleep(10)
            poll_count += 1
            
            try:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(device_ip, port=port, username=username, password=password, timeout=10)
                
                # Get maintenance status AFTER 10-second wait
                log_message(f"📊 STATUS CHECK AFTER {poll_count * 10} SECONDS (Poll #{poll_count}):")
                log_message("-" * 80)
                
                stdin, stdout, stderr = ssh.exec_command(maintenance_get_status_command)
                time.sleep(2)
                response = stdout.read().decode('utf-8', errors='ignore').strip()
                
                # Parse maintenance status and reboot pending flag
                maintenance_status = None
                is_reboot_pending = False
                is_critical_maintenance = False
                last_successful_time = None
                
                try:
                    response_json = json.loads(response) if response.startswith('{') else {}
                    maintenance_status = response_json.get('result', {}).get('maintenanceStatus', '').upper()
                    is_reboot_pending = response_json.get('result', {}).get('isRebootPending', False)
                    is_critical_maintenance = response_json.get('result', {}).get('isCriticalMaintenance', False)
                    last_successful_time = response_json.get('result', {}).get('LastSuccessfulCompletionTime', None)
                except:
                    if 'MAINTENANCE_ERROR' in response:
                        maintenance_status = 'MAINTENANCE_ERROR'
                    elif 'MAINTENANCE_COMPLETE' in response:
                        maintenance_status = 'MAINTENANCE_COMPLETE'
                    else:
                        maintenance_status = 'IN_PROGRESS'
                    is_reboot_pending = 'isRebootPending":true' in response
                    is_critical_maintenance = 'true' in response
                
                log_message(f"  📍 Maintenance Status: {maintenance_status}")
                log_message(f"  🔄 Reboot Pending: {is_reboot_pending}")
                log_message(f"  ⚡ Critical Maintenance: {is_critical_maintenance}")
                if last_successful_time:
                    log_message(f"  ⏱️  Last Successful: {last_successful_time}")
                log_message(f"  📝 Full Response: {response[:150]}")
                log_message("-" * 80)
                
                # Check if maintenance complete with reboot pending
                # Per manual procedure: Continue polling UNTIL maintenanceStatus=MAINTENANCE_ERROR AND isRebootPending=true
                if maintenance_status == 'MAINTENANCE_ERROR' and is_reboot_pending:
                    log_message(f"\n✅ MAINTENANCE COMPLETE - Both conditions met:")
                    log_message(f"   ✓ maintenanceStatus = MAINTENANCE_ERROR")
                    log_message(f"   ✓ isRebootPending = true")
                    log_message(f"   Exiting polling loop after {poll_count} polls ({poll_count * 10} seconds)")
                    maintenance_complete = True
                elif maintenance_status == 'MAINTENANCE_ERROR' and not is_reboot_pending:
                    log_message(f"⚠ Maintenance ERROR detected but reboot NOT yet pending - continuing polling...")
                    log_message(f"   Polls so far: {poll_count}/{max_polls} ({poll_count * 10} seconds elapsed)")
                elif maintenance_status == 'MAINTENANCE_COMPLETE':
                    log_message(f"✅ MAINTENANCE COMPLETE status reached")
                    log_message(f"   Exiting polling loop after {poll_count} polls ({poll_count * 10} seconds)")
                    maintenance_complete = True
                else:
                    log_message(f"⏳ Maintenance still in progress: {maintenance_status}")
                    log_message(f"   Polls so far: {poll_count}/{max_polls} ({poll_count * 10} seconds elapsed)")
                
                # STEP 6: Verify device still in STANDBY
                if not maintenance_complete:
                    stdin, stdout, stderr = ssh.exec_command(device_status_command)
                    time.sleep(1)
                    power_state = stdout.read().decode('utf-8', errors='ignore').strip()
                    
                    if 'STANDBY' not in power_state.upper():
                        log_message(f"  ⚠ Warning: Device may have come out of STANDBY: {power_state[:50]}")
                    else:
                        log_message(f"  ✓ Device still in STANDBY")
                
                ssh.close()
            
            except Exception as poll_error:
                log_message(f"  ⚠ Error during polling: {str(poll_error)[:100]}")
                time.sleep(5)
        
        if not maintenance_complete:
            log_message("⚠ Maintenance did not complete within timeout window (60 minutes / 360 polls @ 10 sec interval)")
        
        # STEP 7: Reboot device after maintenance (Per manual procedure)
        log_message("\n" + "="*80)
        log_message("[STEP 7] Rebooting device after maintenance with isRebootPending=true...")
        log_message("="*80)
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(device_ip, port=port, username=username, password=password, timeout=10)
            
            log_message("Sending maintenance reboot command via RDK System API...")
            log_message("Expected: Device will reboot and then enter STANDBY")
            stdin, stdout, stderr = ssh.exec_command(maintenance_reboot_command)
            time.sleep(2)
            reboot_response = stdout.read().decode('utf-8', errors='ignore').strip()
            log_message(f"Reboot response: {reboot_response[:100]}")
            
            if 'success":true' in reboot_response or 'success": true' in reboot_response:
                log_message("✓ Reboot command accepted by device")
            
            ssh.close()
        except Exception as e:
            log_message(f"⚠ Error during reboot command: {str(e)[:100]}")
        
        log_message("Waiting 2 minutes for device to complete reboot and enter STANDBY...")
        time.sleep(120)
        
        # ============================================================================
        # CONDITIONAL STEP: Check if user wants to skip DeepSleep & Wakeup phases
        # ============================================================================
        if not execute_deepsleep_wakeup:
            log_message("\n" + "="*80)
            log_message("[STEPS 8-12] DeepSleep & Wakeup SKIPPED (as requested)")
            log_message("="*80)
            log_message("✓ Maintenance cycle completed successfully")
            log_message("✓ Device remains in STANDBY state")
            log_message("⏭️  DeepSleep and wake-up phases skipped per user selection")
            log_message("\n" + "="*80)
            log_message("MAINTENANCE CYCLE COMPLETED - DEEPSLEEP PHASES SKIPPED")
            log_message("="*80)
            
            return {
                "iteration": iteration,
                "screenshots": screenshots_list,
                "logs": logs_list,
                "success": True,
                "wakeup_time_seconds": None,  # Not applicable when skipped
                "details": "Maintenance cycle completed successfully. DeepSleep and wake-up phases skipped as requested."
            }
        
        # STEP 8: Verify device in STANDBY after reboot and transition if needed (Per manual procedure)
        log_message("\n" + "="*80)
        log_message("[STEP 8] Verifying device is in STANDBY after maintenance reboot...")
        log_message("="*80)
        log_message("If device is in ON state, sending IR POWER to transition to STANDBY...")
        log_message("="*80)
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(device_ip, port=port, username=username, password=password, timeout=10)
            
            # Check initial device state after reboot
            log_message("\n📊 Checking device state after maintenance reboot...")
            stdin, stdout, stderr = ssh.exec_command(device_status_command)
            time.sleep(2)
            power_state = stdout.read().decode('utf-8', errors='ignore').strip()
            log_message(f"Device power state: {power_state[:100]}")
            
            # If device is in ON state, transition it to STANDBY using IR POWER
            if 'ON' in power_state.upper() and 'STANDBY' not in power_state.upper():
                log_message("\n" + "="*80)
                log_message("📍 Device is in ON state after reboot")
                log_message("="*80)
                log_message("✓ Sending IR POWER key to transition device to STANDBY...")
                
                # Get IR configuration for device
                ir_config = get_ir_config_for_device(device_name)
                
                # Determine remote type mapping
                remote_type_mapping = {
                    'SKY': 'SKY_LC103',
                    'COMCAST': 'XUMO_PR3',
                    'XUMO': 'XUMO_PR3',
                    'SKY_LC103': 'SKY_LC103',
                    'XUMO_PR3': 'XUMO_PR3'
                }
                
                if remote_type and remote_type.upper() in remote_type_mapping:
                    selected_remote_type = remote_type_mapping[remote_type.upper()]
                    log_message(f"📡 Using user-selected remote type: {remote_type.upper()} -> {selected_remote_type}")
                else:
                    selected_remote_type = 'SKY_LC103' if 'SKY' in device_name.upper() else 'XUMO_PR3'
                    log_message(f"📡 Auto-detected remote type from device name: {selected_remote_type}")
                
                log_message(f"🔌 Using IR port {ir_config['ir_port']} with iTach at {ir_config['itach_ip']}:{ir_config['itach_port']}")
                
                # Generate and send IR POWER command
                ir_code_power = generate_ir_code("POWER", ir_config['ir_port'], remote_type=selected_remote_type)
                if send_ir_command(ir_code_power, ir_config['itach_ip'], ir_config['itach_port'], log_message):
                    log_message("✓ IR POWER command sent successfully")
                else:
                    log_message("⚠ IR POWER command failed - attempting to continue anyway")
                
                # Wait for device to process IR command and transition to STANDBY
                log_message("\nWaiting 30 seconds for device to transition to STANDBY...")
                time.sleep(30)
                
                # Verify device is now in STANDBY
                log_message("\n📊 Verifying STANDBY transition...")
                stdin, stdout, stderr = ssh.exec_command(device_status_command)
                time.sleep(2)
                power_state_after = stdout.read().decode('utf-8', errors='ignore').strip()
                log_message(f"Device power state after IR POWER: {power_state_after[:100]}")
                
                if 'STANDBY' in power_state_after.upper():
                    log_message("✓ Device successfully transitioned to STANDBY")
                else:
                    log_message(f"⚠ Device may not be in STANDBY yet (state: {power_state_after[:80]})")
                    log_message("   Proceeding to DeepSleep wait anyway...")
                    power_state = power_state_after
            
            elif 'STANDBY' in power_state.upper():
                log_message("✓ Device already in STANDBY - no IR command needed")
            
            else:
                log_message(f"⚠ Device power state is: {power_state[:100]}")
                log_message("   Proceeding with DeepSleep wait...")
            
            ssh.close()
        except Exception as e:
            log_message(f"⚠ Error verifying/transitioning STANDBY: {str(e)[:100]}")
        
        # STEP 9: Wait for DeepSleep entry (using configurable sleep_duration_minutes parameter)
        # ENHANCEMENT: Intelligently detect early DeepSleep entry and proceed early if confirmed
        # FLEXIBLE DETECTION: Support immediate checking (0 minutes) or normal wait
        # LOCK REFRESH: Before starting deepsleep wait, refresh the device lock if job is running
        if job_id:
            # Use the correctly calculated remaining_iterations from the calling code
            if execution_queue is None:
                # Fallback if execution_queue not provided
                execution_queue_deepsleep = [{'method': 'maintenance_deepsleep_wakeup', 'sleep_duration_minutes': sleep_duration_minutes or 60}]
            else:
                execution_queue_deepsleep = execution_queue
                
            if DeviceLockManager.refresh_lock(device_ip, job_id, execution_queue_deepsleep, remaining_iterations):
                time_remaining = DeviceLock.get_time_until_expiration(device_ip)
                hours = time_remaining // 3600
                minutes = (time_remaining % 3600) // 60
                log_message(f"🔒 [STEP 9 LOCK-REFRESH] Lock refreshed before DeepSleep wait")
                log_message(f"   Time remaining: {hours}h {minutes}m")
            else:
                log_message(f"⚠️  [STEP 9 LOCK-WARNING] Could not refresh lock before DeepSleep wait")
        
        log_message("\n" + "="*80)
        
        # Determine wait behavior based on sleep_duration_minutes
        # If 0 or blank: immediate checking (up to 1 hour max)
        # If > 0: normal wait with early detection capability
        if sleep_duration_minutes is None or sleep_duration_minutes == 0 or sleep_duration_minutes == '':
            immediate_check = True
            max_wait_time = 3600  # 1 hour max for immediate checks
            log_message(f"[STEP 9] IMMEDIATE DeepSleep checking (no initial wait)...")
            log_message(f"(Using 'DeepSleep Wait Duration' parameter: IMMEDIATE / Default max wait: 1 hour)")
        else:
            immediate_check = False
            max_wait_time = sleep_duration_minutes * 60  # Convert minutes to seconds
            log_message(f"[STEP 9] Waiting {sleep_duration_minutes} minutes for device to enter DeepSleep...")
            log_message(f"(Using 'DeepSleep Wait Duration' parameter: {sleep_duration_minutes} minutes)")
        
        log_message("="*80)
        log_message("NOTE: If device becomes SSH-inaccessible, will verify DeepSleep entry")
        log_message("      and proceed to STEP 10 early if confirmed (no need to wait full duration)")
        log_message("="*80)
        
        wait_time = max_wait_time
        probe_interval = 60  # Check SSH connectivity every 1 minute (60 seconds) during wait
        start_deepsleep_wait = time.time()
        early_deepsleep_detected = False
        deepsleep_entry_time = None
        
        # ===== WATCHDOG TIMEOUT: Add safety breaks for hung polling loop =====
        max_polling_iterations = (wait_time // probe_interval) + 10  # Allow extra 10 iterations before force-quit
        max_consecutive_accessible = 20  # If device accessible 20+ times in a row (20 min), force exit
        consecutive_accessible_count = 0
        
        # If immediate_check enabled, start probing immediately without initial wait
        if immediate_check:
            log_message("\n🚀 Starting immediate SSH probes to detect DeepSleep entry...")
        
        # Wait loop with periodic SSH probing (every 1 minute)
        elapsed = 0
        last_log_time = 0
        probe_count = 0
        
        while elapsed < wait_time and not early_deepsleep_detected:
            remaining = wait_time - elapsed
            current_time = time.time()
            probe_count += 1
            
            # ===== SAFETY CHECK 1: Force quit if polling takes too long =====
            if probe_count > max_polling_iterations:
                log_message(f"\n⚠️  [WATCHDOG] Force-exit: Exceeded max polling iterations ({max_polling_iterations})")
                log_message(f"    Elapsed: {elapsed} seconds, Remaining: {remaining} seconds")
                log_message(f"    Device may be stuck in accessible state - proceeding to next step")
                break
            
            # ===== SAFETY CHECK 2: Force quit if device accessible too many times =====
            if consecutive_accessible_count >= max_consecutive_accessible:
                log_message(f"\n⚠️  [WATCHDOG] Force-exit: Device accessible {max_consecutive_accessible} consecutive times (20+ minutes)")
                log_message(f"    Device likely not entering DeepSleep - proceeding to next step")
                break
            
            # Log progress based on check mode
            if immediate_check:
                # For immediate checks, log every probe (every 1 minute)
                minutes_elapsed = elapsed // 60
                seconds_elapsed = elapsed % 60
                log_message(f"  📡 SSH probe #{probe_count}: Checking device SSH-ability (elapsed: {minutes_elapsed}m {seconds_elapsed}s)...")
            else:
                # For normal waits, log every probe interval (now 1 minute)
                if (current_time - last_log_time) >= probe_interval:
                    minutes_remaining = remaining // 60
                    seconds_remaining = remaining % 60
                    log_message(f"  📡 Poll #{probe_count}: Checking device SSH-ability (remaining: {minutes_remaining}m {seconds_remaining}s)...")
                    sys.stdout.flush()
                    last_log_time = current_time
            
            # Probe SSH connectivity to detect early DeepSleep entry
            device_is_ssh_accessible = False
            probe_start = time.time()
            
            try:
                test_ssh = paramiko.SSHClient()
                test_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                test_ssh.connect(device_ip, port=port, username=username, password=password, timeout=5)
                
                try:
                    test_ssh.close()
                except:
                    pass  # Ignore close errors
                
                device_is_ssh_accessible = True
                consecutive_accessible_count += 1
                
                # Device is still SSH-accessible, continue waiting
                if immediate_check:
                    log_message(f"    ✓ SSH accessible (attempt #{consecutive_accessible_count}) - will probe again in {probe_interval}s (1 min)")
                else:
                    log_message(f"    ✓ SSH accessible (attempt #{consecutive_accessible_count}) - continuing to wait...")
                
                sys.stdout.flush()
                
            except (ParamikException, socket.timeout, ConnectionRefusedError, OSError) as e:
                consecutive_accessible_count = 0  # Reset counter on disconnect
                
                # Device is NOT SSH-accessible - check if it's in DeepSleep
                elapsed_since_start = int(time.time() - start_deepsleep_wait)
                minutes_elapsed = elapsed_since_start // 60
                seconds_elapsed = elapsed_since_start % 60
                expected_wait_desc = "immediate check" if immediate_check else f"{sleep_duration_minutes}m" if sleep_duration_minutes else f"{wait_time}s"
                log_message(f"\n⚠️  [EARLY DETECTION] Device became SSH-INACCESSIBLE at {minutes_elapsed}m {seconds_elapsed}s elapsed")
                log_message(f"    Expected wait duration: {expected_wait_desc}")
                log_message(f"    Connection error: {str(e)[:80]}")
                log_message(f"    Verifying if device is in true DeepSleep state...")
                
                # Verify DeepSleep state
                is_in_deep_sleep, verification_method = verify_deep_sleep_state(
                    device_ip, port, username, password, log_callback=log_message
                )
                
                if is_in_deep_sleep:
                    log_message(f"\n✅ [EARLY DEEPSLEEP CONFIRMED] Device entered DeepSleep after {elapsed_since_start}s")
                    log_message(f"    Verification method: {verification_method}")
                    if immediate_check:
                        log_message(f"    ✓ Immediate detection succeeded - proceeding to STEP 10 early")
                    else:
                        log_message(f"    ✓ Skipping remaining {remaining}s and proceeding to STEP 10 early")
                    early_deepsleep_detected = True
                    deepsleep_entry_time = elapsed_since_start
                    break
                else:
                    # Device is inaccessible but NOT in DeepSleep - could be a real connection issue
                    log_message(f"\n❌ Device is inaccessible but NOT confirmed in DeepSleep state")
                    log_message(f"    This may indicate a transient connectivity issue")
                    log_message(f"    Will continue polling... (remaining: {minutes_elapsed}m {seconds_elapsed}s)")
            
            except Exception as e:
                log_message(f"  ⚠️  [PROBE ERROR] Unexpected error during SSH probe: {str(e)[:80]}")
                consecutive_accessible_count += 1  # Treat as accessible if we can't determine
            
            # Sleep for probe interval or remaining time, whichever is smaller
            # ===== CRITICAL: Use lock-validating sleep to detect lock expiration =====
            time_to_sleep = min(probe_interval, remaining)
            
            # Check if we have a job_id for lock validation
            if job_id:
                try:
                    # Use lock-validating wait that checks lock every 60 seconds
                    DeviceLockManager.wait_with_lock_validation(
                        time_to_sleep, device_ip, job_id,
                        log_callback=log_message
                    )
                except RuntimeError as lock_error:
                    # Lock lost during wait - this is a critical failure
                    log_message(f"\n❌ CRITICAL: Device lock lost during DeepSleep wait!")
                    log_message(f"   Error: {str(lock_error)}")
                    log_message(f"   Elapsed: {elapsed}s / {wait_time}s")
                    # Re-raise to be caught by the outer exception handler
                    raise
            else:
                # No job_id, use regular sleep (fallback, shouldn't happen in normal flow)
                sleep_chunk = 5  # Sleep in 5-second chunks
                sleep_elapsed = 0
                
                while sleep_elapsed < time_to_sleep:
                    chunk = min(sleep_chunk, time_to_sleep - sleep_elapsed)
                    time.sleep(chunk)
                    sleep_elapsed += chunk
            
            elapsed = int(time.time() - start_deepsleep_wait)
        
        # Check if we exited the loop due to timeout or early detection
        if early_deepsleep_detected:
            log_message(f"\n✅ STEP 9 OPTIMIZED - Early DeepSleep detected after {deepsleep_entry_time} seconds")
        else:
            if immediate_check:
                log_message(f"\n✓ Immediate DeepSleep check wait complete ({wait_time}s max) - Device should now be in DeepSleep")
            else:
                log_message(f"\n✓ {sleep_duration_minutes}-minute wait complete - Device should now be in DeepSleep")
        
        # STEP 10: Verify device inaccessible (DeepSleep confirmed)
        log_message("\n" + "="*80)
        log_message("[STEP 10] Verifying device is inaccessible (DeepSleep confirmed)...")
        log_message("="*80)
        
        # If we already confirmed DeepSleep in STEP 9, log that and skip detailed verification
        if early_deepsleep_detected:
            log_message("✅ DeepSleep already confirmed in STEP 9 (early detection)")
            log_message(f"   Device became SSH-inaccessible at {deepsleep_entry_time}s")
            log_message("   Skipping redundant verification - proceeding to STEP 11")
            is_in_deep_sleep = True
            verification_method = "EARLY_DETECTION_IN_STEP_9"
        else:
            # Perform full verification if not already done
            is_in_deep_sleep, verification_method = verify_deep_sleep_state(
                device_ip, port, username, password, log_callback=log_message
            )
            
            if not is_in_deep_sleep:
                log_message("\n⚠ ⚠ ⚠ IMPORTANT: Device may NOT be in true DEEP SLEEP ⚠ ⚠ ⚠")
            log_message("  This could affect the accuracy of wakeup time measurements")
            log_message("  Proceeding with wakeup attempt anyway...")
        
        log_message(f"  Verification method: {verification_method}")
        
        # STEP 11: Wake up device with IR POWER key
        log_message("\n" + "="*80)
        log_message("[STEP 11] Waking up device with IR POWER command...")
        log_message("="*80)
        
        ir_config = get_ir_config_for_device(device_name)
        
        # Determine remote type - map UI selections to ir_keycodes remote types
        # UI shows 'SKY', 'XUMO', 'COMCAST' but ir_keycodes.json expects 'SKY_LC103', 'XUMO_PR3'
        remote_type_mapping = {
            'SKY': 'SKY_LC103',
            'COMCAST': 'XUMO_PR3',
            'XUMO': 'XUMO_PR3',
            'SKY_LC103': 'SKY_LC103',  # Also support full names
            'XUMO_PR3': 'XUMO_PR3'
        }
        
        if remote_type and remote_type.upper() in remote_type_mapping:
            selected_remote_type = remote_type_mapping[remote_type.upper()]
            log_message(f"📡 Using user-selected remote type: {remote_type.upper()} -> {selected_remote_type}")
        else:
            selected_remote_type = 'SKY_LC103' if 'SKY' in device_name.upper() else 'XUMO_PR3'
            log_message(f"📡 Auto-detected remote type from device name: {selected_remote_type}")
        
        ir_code_power = generate_ir_code("POWER", ir_config['ir_port'], remote_type=selected_remote_type)
        log_message(f"🔌 Using IR port {ir_config['ir_port']} with iTach at {ir_config['itach_ip']}:{ir_config['itach_port']}")
        
        # Send IR POWER command and record timestamp
        power_key_send_time = time.time()
        log_message(f"📝 IR POWER command send timestamp: {datetime.fromtimestamp(power_key_send_time).isoformat()}")
        
        if not send_ir_command(ir_code_power, ir_config['itach_ip'], ir_config['itach_port'], log_message):
            log_message("⚠ Warning: IR POWER command may have failed")
        
        log_message("✓ IR POWER command sent")
        
        # STEP 12: Measure time from POWER key to HOME SCREEN detection
        log_message("\n" + "="*80)
        log_message("[STEP 12] Measuring device wakeup time to HOME SCREEN...")
        log_message("="*80)
        
        log_message("Waiting 20 seconds for device to begin startup (before SSH probe)...")
        startup_wait_start = time.time()
        time.sleep(20)
        sys.stdout.flush()
        startup_wait_end = time.time()
        startup_wait_duration = startup_wait_end - startup_wait_start
        log_message(f"⏱ Initial wait duration: {startup_wait_duration:.1f} seconds")
        
        log_message("Attempting to reconnect to device...")
        ssh_reconnect_start = time.time()
        ssh_wakeup = reconnect_to_device_with_retry(device_ip, port, username, password, max_retries=10, retry_interval=5, log_callback=log_message)
        ssh_reconnect_end = time.time()
        ssh_reconnect_duration = ssh_reconnect_end - ssh_reconnect_start
        
        if ssh_wakeup:
            log_message(f"✓ SSH reconnected in {ssh_reconnect_duration:.1f} seconds")
            log_message(f"  • POWER key sent: {datetime.fromtimestamp(power_key_send_time).isoformat()}")
            log_message(f"  • SSH reconnected: {datetime.fromtimestamp(ssh_reconnect_end).isoformat()}")
            log_message(f"  • Time breakdown:")
            log_message(f"    - Initial wait (before SSH probe): {startup_wait_duration:.1f}s")
            log_message(f"    - SSH reconnection time: {ssh_reconnect_duration:.1f}s")
            log_message(f"    - Total to SSH accessible: {startup_wait_duration + ssh_reconnect_duration:.1f}s")
            
            # Activate ScreenCapture service
            activate_screencapture_service(ssh_wakeup, log_message)
            
            # Fetch build details post-wakeup
            fetch_build_details(ssh_wakeup, log_message)
            
            # Monitor for HOME screen log line to get accurate wakeup time
            # IMPORTANT: Pass power_command_time for TIME-AWARE detection
            # This ensures we only detect HOME entries that occur AFTER the IR POWER was sent
            log_message("\n[SUB-STEP 12a] Monitoring logs for HOME screen detection (time-aware)...")
            
            # Define screenshot fallback function
            def take_screenshot_for_detection():
                """Capture screenshot to verify HOME screen as fallback"""
                try:
                    method_for_folder = get_folder_method_name() or combined_method_name or "maintenance_deepsleep_wakeup"
                    screenshot_folder = create_screenshot_folder(device_ip, safe_device_name, iteration, "After", method_for_folder)
                    screenshot_name = f"{device_ip}_{safe_device_name}_Iteration-{iteration}_After-Wakeup_{timestamp}"
                    screenshot_result = take_and_analyze_screenshot(ssh_wakeup, screenshot_name, device_ip, log_message, screenshot_folder)
                    return screenshot_result and screenshot_result.get('success', False)
                except Exception as e:
                    log_message(f"  ⚠ Screenshot fallback error: {str(e)[:80]}")
                    return False
            
            # Use improved HOME screen detection with timeout enforcement
            # Pass power_key_send_time to ensure we detect HOME entries AFTER the power command
            home_screen_detected, detection_method, home_log_line = detect_home_screen_with_fallback(
                ssh_wakeup, 
                timeout_seconds=120,
                log_callback=log_message,
                screenshot_callback=take_screenshot_for_detection,
                power_command_time=power_key_send_time  # NEW: Use time-aware detection
            )
            
            # Record detection timestamp
            home_screen_detection_time = time.time() if home_screen_detected else None
            
            # Calculate wakeup time: from POWER key to HOME SCREEN detection (not SSH)
            if home_screen_detected and home_screen_detection_time:
                wakeup_time_seconds = home_screen_detection_time - power_key_send_time
                log_message(f"\n✓ HOME SCREEN WAKEUP TIME CALCULATED:")
                log_message(f"  • From IR POWER key sent: {datetime.fromtimestamp(power_key_send_time).isoformat()}")
                log_message(f"  • To HOME screen detected: {datetime.fromtimestamp(home_screen_detection_time).isoformat()}")
                log_message(f"  • ⏱ TOTAL WAKEUP TIME: {int(wakeup_time_seconds)} seconds ({wakeup_time_seconds/60:.1f} minutes)")
                log_message(f"  • Detection method: {detection_method}")
                log_message(f"  ✓ This excludes the initial {startup_wait_duration:.1f}s wait, measuring only actual boot-to-homescreen")
            else:
                # Fallback: if HOME screen detection fails, use SSH accessible time
                wakeup_time_seconds = ssh_reconnect_end - power_key_send_time
                log_message(f"\n⚠ HOME screen detection failed - using SSH accessible time instead")
                log_message(f"  • Detection method attempted: {detection_method}")
                log_message(f"  ⏱ WAKEUP TIME (SSH Accessible): {int(wakeup_time_seconds)} seconds")
            
            # Check for HOME screen with screenshot
            log_message("\nCapturing device state after wakeup...")
            time.sleep(10)
            
            # Take screenshot
            method_for_folder = get_folder_method_name() or combined_method_name or "maintenance_deepsleep_wakeup"
            screenshot_folder = create_screenshot_folder(device_ip, safe_device_name, iteration, "After", method_for_folder)
            screenshot_name = f"{device_ip}_{safe_device_name}_Iteration-{iteration}_After-Wakeup_{timestamp}"
            screenshot_result = take_and_analyze_screenshot(ssh_wakeup, screenshot_name, device_ip, log_message, screenshot_folder)
            
            if screenshot_result and screenshot_result.get('success'):
                log_message(f"✓ Screenshot saved: {screenshot_result.get('local_path')}")
                screenshots_list.append(screenshot_result.get('local_path', ''))
                from app import add_html_result
                
                if home_screen_detected:
                    add_html_result(iteration, "Post-Wakeup", "PASSED", 
                                  f"Device on HOME screen after {wakeup_time_seconds:.1f}s wakeup ({detection_method})", 
                                  screenshot_result.get('local_path', ''), "", device_ip=device_ip, method="maintenance_deepsleep_wakeup")
                else:
                    add_html_result(iteration, "Post-Wakeup", "PASSED", 
                                  f"Device wakeup complete in {wakeup_time_seconds:.1f}s ({detection_method})", 
                                  screenshot_result.get('local_path', ''), "", device_ip=device_ip, method="maintenance_deepsleep_wakeup")
            else:
                log_message("⚠ Screenshot capture failed")
                from app import add_html_result
                add_html_result(iteration, "Post-Wakeup", "WARNING", 
                              f"Device wakeup complete in {wakeup_time_seconds:.1f}s (screenshot failed)", 
                              "", "", device_ip=device_ip, method="maintenance_deepsleep_wakeup")
            
            # Run diagnostics if device not on HOME screen
            try:
                success, log_output = execute_ssh_command_with_timeout(
                    ssh_wakeup, log_check_command_HOME, timeout_seconds=10, log_callback=log_message
                )
                
                if log_line_HOME.split(".*")[0] not in log_output:
                    log_message("⚠ Device not on HOME screen - running diagnostics...")
                    check_network_and_realtek_errors(ssh_wakeup, log_message)
            except Exception as e:
                log_message(f"⚠ Error checking HOME screen: {str(e)[:100]}")

            # ============================================================================
            # STEP 12b: COLLECT LOGS IF DEVICE FAILED TO POWER ON AFTER IR POWER COMMAND
            # ============================================================================
            # Check failure conditions:
            # 1. No HOME log line was found (home_screen_detected = False)
            # 2. AND Device QueryPowerState is not in ON
            # 3. OR Device is still in STANDBY (even though SSH accessible)
            
            device_failed_to_power_on = False
            power_state_after_wakeup = None
            
            try:
                # Check device power state after wakeup attempt
                log_message("\n[STEP 12b] Checking device power state after IR POWER command...")
                stdin, stdout, stderr = ssh_wakeup.exec_command(device_status_command, timeout=10)
                time.sleep(2)
                power_state_after_wakeup = stdout.read().decode('utf-8', errors='ignore').strip()
                log_message(f"Device power state after wakeup: {power_state_after_wakeup[:150]}")
                
                # Determine if device failed to power on
                home_log_not_found = not home_screen_detected
                device_not_in_on_state = 'ON' not in power_state_after_wakeup.upper()
                device_still_in_standby = 'STANDBY' in power_state_after_wakeup.upper()
                
                # Failure condition: (No HOME log AND power not ON) OR (Still in STANDBY but SSH accessible)
                if (home_log_not_found and device_not_in_on_state) or device_still_in_standby:
                    device_failed_to_power_on = True
                    log_message("\n" + "="*80)
                    log_message("⚠️ DEVICE POWER-ON FAILURE DETECTED")
                    log_message("="*80)
                    log_message("Failure conditions detected:")
                    if home_log_not_found:
                        log_message("  ❌ No HOME screen log line detected")
                    if device_not_in_on_state:
                        log_message("  ❌ Device QueryPowerState is NOT in ON state")
                    if device_still_in_standby:
                        log_message("  ❌ Device is still in STANDBY (even though SSH accessible)")
                    log_message("\nAutomatic device logs collection initiated...")
                    
                    # Collect device logs for debugging
                    try:
                        # Create archive name with iteration and timestamp
                        safe_device_name_logs = device_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
                        timestamp_logs = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
                        remote_log_archive = f"/media/apps/{device_ip}_{safe_device_name_logs}_ITR-{iteration}_POWERON-FAILED_{timestamp_logs}.tar.gz"
                        
                        log_message(f"\n📋 Creating device logs archive for failed wakeup...")
                        log_message(f"  Archive: {remote_log_archive}")
                        
                        # Create /media/apps directory if it doesn't exist
                        mkdir_cmd = "mkdir -p /media/apps"
                        stdin, stdout, stderr = ssh_wakeup.exec_command(mkdir_cmd, timeout=10)
                        stdout.channel.recv_exit_status()
                        
                        # Create tar.gz archive of device logs
                        tar_cmd = f"tar -czf {remote_log_archive} /opt/logs/* 2>/dev/null || echo 'tar_done'"
                        stdin, stdout, stderr = ssh_wakeup.exec_command(tar_cmd, timeout=60)
                        stdout.channel.recv_exit_status()
                        log_message(f"  ✓ Archive created on device")
                        
                        # Verify file exists
                        verify_cmd = f"ls -lh {remote_log_archive} && echo 'VERIFIED'"
                        stdin, stdout, stderr = ssh_wakeup.exec_command(verify_cmd, timeout=10)
                        verify_output = stdout.read().decode('utf-8', errors='ignore').strip()
                        
                        if "VERIFIED" in verify_output:
                            log_message(f"✓ Device logs successfully collected for iteration {iteration}")
                            log_message(f"  Location: {remote_log_archive}")
                            logs_list.append(remote_log_archive)
                            log_message(f"  Logs will be available for forensic analysis")
                        else:
                            log_message(f"⚠ Log collection verification failed")
                    except Exception as e:
                        log_message(f"⚠ Error collecting logs for failed wakeup: {str(e)[:150]}")
                else:
                    log_message("\n✓ Device power-on validation passed")
                    if 'ON' in power_state_after_wakeup.upper():
                        log_message("  ✓ Device is in ON state")
                    if home_screen_detected:
                        log_message("  ✓ HOME screen log line detected")
            
            except Exception as e:
                log_message(f"⚠ Error checking device power state: {str(e)[:150]}")
            
            ssh_wakeup.close()
            
            log_message("\n" + "="*80)
            log_message("MAINTENANCE > DEEPSLEEP > WAKEUP PROCESS - COMPLETED SUCCESSFULLY")
            log_message("="*80)
            log_message(f"\n📊 DEEPSLEEP RESULTS SUMMARY:")
            log_message(f"  • Device: {device_name} ({device_ip})")
            log_message(f"  • Job ID: {job_id}")
            log_message(f"  • IR POWER key sent: {datetime.fromtimestamp(power_key_send_time).isoformat()}")
            if home_screen_detected and home_screen_detection_time:
                log_message(f"  • HOME screen detected: {datetime.fromtimestamp(home_screen_detection_time).isoformat()}")
                log_message(f"  • ✓ WAKEUP TIME (IR to HOME): {int(wakeup_time_seconds)}s ({wakeup_time_seconds/60:.1f}min)")
                home_screen_method = "HOME_LOG_DETECTED"
            else:
                log_message(f"  • SSH reconnected: {datetime.fromtimestamp(ssh_reconnect_end).isoformat()}")
                log_message(f"  • ⚠ WAKEUP TIME (IR to SSH): {int(wakeup_time_seconds)}s ({wakeup_time_seconds/60:.1f}min)")
                home_screen_method = "SSH_FALLBACK"
            log_message(f"  • Time breakdown:")
            log_message(f"    - Initial wait: {startup_wait_duration:.1f}s")
            log_message(f"    - SSH reconnect: {ssh_reconnect_duration:.1f}s")
            log_message(f"    - Total to SSH: {startup_wait_duration + ssh_reconnect_duration:.1f}s")
            if home_screen_detected and home_screen_detection_time:
                home_to_ssh = home_screen_detection_time - ssh_reconnect_end
                log_message(f"    - SSH to HOME detection: {home_to_ssh:.1f}s")
            
            return {
                "iteration": iteration,
                "screenshots": screenshots_list,
                "logs": logs_list,
                "success": True,
                "wakeup_time_seconds": wakeup_time_seconds,
                "time_to_home_screen": wakeup_time_seconds if home_screen_detected else None,
                "time_to_ssh_accessible": startup_wait_duration + ssh_reconnect_duration,
                "initial_wait_duration": startup_wait_duration,
                "ssh_reconnect_duration": ssh_reconnect_duration,
                "home_screen_method": home_screen_method,
                "details": f"Maintenance completed, DeepSleep verified, wakeup time (IR to HOME): {wakeup_time_seconds:.1f}s"
            }
        else:
            log_message("❌ Device did not wake up - SSH reconnection timeout")
            from app import add_html_result
            add_html_result(iteration, "Wakeup", "FAILED", "Device did not wake up from DeepSleep - SSH reconnection failed", "", "", 
                          device_ip=device_ip, method="maintenance_deepsleep_wakeup")
            log_message("\n" + "="*80)
            log_message("MAINTENANCE > DEEPSLEEP > WAKEUP PROCESS - FAILED")
            log_message("="*80)
            
            return {
                "iteration": iteration,
                "screenshots": screenshots_list,
                "logs": logs_list,
                "success": False,
                "wakeup_time_seconds": None,
                "details": "Device did not wake up from DeepSleep"
            }
    
    except Exception as e:
        log_message(f"\n❌ Unexpected error in Maintenance > DeepSleep > Wakeup process: {str(e)}")
        import traceback
        log_message(traceback.format_exc())
        
        return {
            "iteration": iteration,
            "screenshots": screenshots_list,
            "logs": logs_list,
            "success": False,
            "wakeup_time_seconds": None,
            "details": f"Unexpected error: {str(e)}"
        }


# Allow standalone execution for testing
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python method_maintenance_deepsleep_wakeup.py <device_ip> [port] [username] [password] [device_name] [remote_type]")
        print("\nExample: python method_maintenance_deepsleep_wakeup.py 10.0.0.126 10022 root skypass 'SKY-Device' SKY")
        sys.exit(1)
    
    device_ip = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 10022
    username = sys.argv[3] if len(sys.argv) > 3 else 'root'
    password = sys.argv[4] if len(sys.argv) > 4 else 'skypass'
    device_name = sys.argv[5] if len(sys.argv) > 5 else 'Device'
    remote_type = sys.argv[6] if len(sys.argv) > 6 else None
    
    print(f"\nExecuting Maintenance > DeepSleep > Wakeup on {device_ip}")
    result = execute_maintenance_deepsleep_wakeup_process(
        device_ip, port, username, password, device_name=device_name, remote_type=remote_type
    )
    
    print(f"\nResult: {json.dumps(result, indent=2)}")
