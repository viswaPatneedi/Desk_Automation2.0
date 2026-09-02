#!/usr/bin/env python3
"""
Maintenance > CURL DeepSleep > Wakeup Process Implementation
Optimized workflow using deepsleep_command (curl) to enter DeepSleep IMMEDIATELY after maintenance reboot
Significantly reduces test execution time (from ~13+ minutes to ~2-3 minutes for deepsleep entry)

DIFFERENCE from methods.method_maintenance_deepsleep_wakeup.py:
  - Original: Waits 13-15 minutes for device to naturally enter DeepSleep
  - New (CURL): Uses deepsleep_command (curl) to PUT device in DeepSleep immediately 
                after maintenance reboot when device is still in STANDBY
                Waits only 1-2 minutes before checking if device is inaccessible
                TIME SAVED: ~10+ minutes per iteration

Workflow:
  1-7: Maintenance cycle (same as original method - Steps 1-7)
  8: Device confirmed in STANDBY after maintenance reboot
  9: NEW STEP - Run deepsleep_command (curl) while device in STANDBY
  10: NEW STEP - Wait only 1-2 minutes (instead of 13+)
  11: NEW STEP - Check if device is SSH-accessible
       - If NOT accessible → Device in DeepSleep (SUCCESS) → Wake with IR POWER
       - If accessible → Try IR POWER to put in DeepSleep → Recheck
  12: Wake up with IR POWER key
  13: Calculate wake-up time from POWER key to HOME/SSH
  14: Validate device functionality post-wakeup
"""

import sys
import time
import json
import socket
import paramiko
from methods.method_utils import get_execution_ssh_client
import threading
from paramiko.ssh_exception import SSHException as ParamikException
from datetime import datetime, timezone

# Import configurations
from config.config_commands import (
    device_status_command,
    home_key_command,
    deepsleep_command,
    maintenance_get_status_command,
    maintenance_start_command,
    maintenance_stop_command,
    maintenance_reboot_command
)
from config.config_log_patterns import *
from config.config_timing import *

# Import utilities
from methods.method_utils import (
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
from utils.screenshot_utils import take_and_analyze_screenshot
from tools.screen.screenshot_utils_vnc import take_vnc_screenshot_with_fallback

# Import IR utilities
from config.config_ir_blaster import get_ir_config_for_device, generate_ir_code, send_ir_command

# Import device lock manager
from utils.device_lock_manager import DeviceLockManager


# ============================================================================
# HELPER FUNCTIONS FOR IMPROVED TIMEOUT HANDLING & DEEPSSLEEP VERIFICATION
# ============================================================================

def verify_ssh_connection_health(ssh_client, log_callback=None):
    """Quick health check of SSH connection without blocking."""
    try:
        transport = ssh_client.get_transport()
        if transport and transport.is_active():
            return True
    except:
        pass
    if log_callback:
        log_callback("  ⚠ SSH connection appears stale")
    return False


def execute_ssh_command_with_timeout(ssh_client, command, timeout_seconds=10, 
                                     log_callback=None, retry_count=0, max_retries=3):
    """
    Execute SSH command with robust timeout handling and automatic retry.
    
    Returns:
        tuple: (success: bool, output: str, error: str)
    """
    if log_callback:
        log_callback(f"  📡 Executing command (timeout={timeout_seconds}s)...")
    
    try:
        stdin, stdout, stderr = ssh_client.exec_command(command, timeout=timeout_seconds)
        time.sleep(1)
        
        output = stdout.read().decode('utf-8', errors='ignore').strip()
        error = stderr.read().decode('utf-8', errors='ignore').strip()
        
        return True, output, error
    
    except socket.timeout:
        if log_callback:
            log_callback(f"  ⚠ Command timeout after {timeout_seconds}s")
        if retry_count < max_retries:
            if log_callback:
                log_callback(f"  🔄 Retrying command (attempt {retry_count+1}/{max_retries})...")
            time.sleep(5)
            return execute_ssh_command_with_timeout(ssh_client, command, timeout_seconds, 
                                                   log_callback, retry_count+1, max_retries)
        return False, "", "Timeout"
    
    except (ConnectionRefusedError, ConnectionResetError, OSError) as e:
        if log_callback:
            log_callback(f"  ⚠ Connection error: {str(e)[:60]}")
        return False, "", str(e)
    
    except ParamikException as e:
        if log_callback:
            log_callback(f"  ⚠ SSH error: {str(e)[:80]}")
        return False, "", str(e)
    
    except Exception as e:
        if log_callback:
            log_callback(f"  ⚠ Unexpected error: {str(e)[:80]}")
        return False, "", str(e)


def create_ssh_connection_safe(device_ip, port, username, password, timeout_seconds=15, 
                               log_callback=None, retry_count=0, max_retries=5):
    """
    Create SSH connection with robust timeout and retry handling.
    
    Returns:
        tuple: (success: bool, ssh_client: paramiko.SSHClient or None, error_message: str)
    """
    try:
        if log_callback and retry_count == 0:
            log_callback(f"🔗 Connecting to {device_ip}:{port}...")
        
        ssh = get_execution_ssh_client()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(device_ip, port=port, username=username, password=password, 
                   timeout=timeout_seconds)
        
        if log_callback:
            log_callback(f"✓ SSH connection established to {device_ip}")
        
        return True, ssh, ""
    
    except socket.timeout:
        if log_callback:
            log_callback(f"  ⚠ SSH connection timeout ({timeout_seconds}s)")
        
        if retry_count < max_retries:
            if log_callback:
                log_callback(f"  🔄 Retrying SSH connection (attempt {retry_count+1}/{max_retries})...")
            time.sleep(5 * (retry_count + 1))  # Exponential backoff
            return create_ssh_connection_safe(device_ip, port, username, password, 
                                             timeout_seconds, log_callback, 
                                             retry_count+1, max_retries)
        
        error_msg = f"SSH connection timeout after {max_retries} retries"
        if log_callback:
            log_callback(f"  ❌ {error_msg}")
        return False, None, error_msg
    
    except (ConnectionRefusedError, ConnectionResetError):
        if log_callback:
            log_callback(f"  ⚠ Connection refused by device")
        
        if retry_count < max_retries:
            if log_callback:
                log_callback(f"  🔄 Retrying SSH connection (attempt {retry_count+1}/{max_retries})...")
            time.sleep(5 * (retry_count + 1))
            return create_ssh_connection_safe(device_ip, port, username, password,
                                             timeout_seconds, log_callback,
                                             retry_count+1, max_retries)
        
        error_msg = "Connection refused by device after retries"
        if log_callback:
            log_callback(f"  ❌ {error_msg}")
        return False, None, error_msg
    
    except ParamikException as e:
        if log_callback:
            log_callback(f"  ⚠ SSH exception: {str(e)[:100]}")
        
        if "Authentication failed" not in str(e) and retry_count < max_retries:
            if log_callback:
                log_callback(f"  🔄 Retrying SSH connection (attempt {retry_count+1}/{max_retries})...")
            time.sleep(5 * (retry_count + 1))
            return create_ssh_connection_safe(device_ip, port, username, password,
                                             timeout_seconds, log_callback,
                                             retry_count+1, max_retries)
        
        error_msg = f"SSH error: {str(e)}"
        if log_callback:
            log_callback(f"  ❌ {error_msg}")
        return False, None, error_msg
    
    except Exception as e:
        error_msg = f"Connection failed: {str(e)}"
        if log_callback:
            log_callback(f"  ❌ {error_msg}")
        return False, None, error_msg


def ensure_ssh_connected(ssh_client, device_ip, port, username, password, 
                         timeout_seconds=15, log_callback=None):
    """
    Ensure SSH client is connected and healthy. Reconnect if needed.
    
    Returns:
        tuple: (success: bool, ssh_client: paramiko.SSHClient or None)
    """
    if ssh_client:
        if verify_ssh_connection_health(ssh_client, log_callback):
            return True, ssh_client
        
        if log_callback:
            log_callback("  🔄 SSH connection stale - reconnecting...")
        
        try:
            ssh_client.close()
        except:
            pass
    
    success, new_ssh, error = create_ssh_connection_safe(device_ip, port, username, password,
                                                         timeout_seconds, log_callback)
    return success, new_ssh if success else None


def verify_deep_sleep_state(device_ip, port, username, password, log_callback=None):
    """
    Verify device is truly in deep sleep by checking if SSH is accessible.
    """
    try:
        test_ssh = get_execution_ssh_client()
        test_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        test_ssh.connect(device_ip, port=port, username=username, password=password, timeout=5)
        test_ssh.close()
        
        if log_callback:
            log_callback("⚠ Device is still accessible via SSH - NOT in DeepSleep")
        return False, "STILL_ACCESSIBLE"
    except (ParamikException, socket.timeout, ConnectionRefusedError, OSError):
        if log_callback:
            log_callback("✓ Device is inaccessible via SSH - DEEPSLEEP CONFIRMED")
        return True, "UNREACHABLE"
    except Exception as e:
        if log_callback:
            log_callback(f"✓ Device verification returned: {str(e)[:60]} (treating as deep sleep)")
        return True, "CONNECTION_ERROR_ASSUMED_DEEP_SLEEP"


def get_device_power_state(ssh_client, device_ip, port, username, password, log_callback=None):
    """
    Get current device power state by executing QueryPowerState command.
    
    Returns:
        tuple: (state: str, is_standby: bool, is_on: bool, is_deepsleep: bool)
    """
    try:
        success, power_state_output, error = execute_ssh_command_with_timeout(
            ssh_client, device_status_command, timeout_seconds=10,
            log_callback=log_callback, max_retries=1
        )
        
        if success and power_state_output:
            state = power_state_output.strip().upper()
            is_standby = 'STANDBY' in state
            is_on = 'ON' in state or 'ACTIVE' in state
            is_deepsleep = 'DEEP' in state or 'DEEPSLEEP' in state or 'SLEEP' in state
            
            if log_callback:
                log_callback(f"📊 Device power state: {state}")
                log_callback(f"   - STANDBY: {is_standby}, ON: {is_on}, DEEPSLEEP: {is_deepsleep}")
            
            return state, is_standby, is_on, is_deepsleep
        else:
            if log_callback:
                log_callback(f"⚠ Could not retrieve device power state: {error}")
            return "UNKNOWN", False, False, False
    
    except Exception as e:
        if log_callback:
            log_callback(f"⚠ Error getting device power state: {str(e)[:80]}")
        return "ERROR", False, False, False


def ensure_device_on_home_screen(ssh_client, device_ip, port, username, password, ir_config, 
                                 selected_remote_type, log_callback=None, screenshot_callback=None, 
                                 timeout_seconds=180):
    """
    Ensure device is ON and on HOME screen. If in STANDBY, wake it up.
    
    Returns:
        tuple: (success: bool, ssh_client_updated: paramiko.SSHClient or None, device_state: str)
    """
    if log_callback:
        log_callback("\n[PRE-VALIDATION] Checking if device needs to be brought to ON/HOME screen...")
    
    # Get current device state
    state, is_standby, is_on, is_deepsleep = get_device_power_state(
        ssh_client, device_ip, port, username, password, log_callback
    )
    
    if is_on:
        if log_callback:
            log_callback("✓ Device is already ON - checking for HOME screen...")
        
        # Check if on HOME screen
        home_detected, detection_method, home_log_line = detect_home_screen_with_fallback(
            ssh_client, timeout_seconds=60, log_callback=log_callback, 
            screenshot_callback=screenshot_callback
        )
        
        if home_detected:
            if log_callback:
                log_callback("✓ Device already on HOME SCREEN - ready to proceed")
            return True, ssh_client, state
        else:
            if log_callback:
                log_callback("⚠ Device ON but NOT on HOME SCREEN - sending HOME key...")
            
            # Send HOME key to navigate to HOME screen
            try:
                ir_code_home = generate_ir_code("HOME", ir_config['ir_port'], remote_type=selected_remote_type)
                send_ir_command(ir_code_home, ir_config['itach_ip'], ir_config['itach_port'], log_callback)
                time.sleep(10)
                
                # Wait for HOME screen
                home_detected, detection_method, _ = detect_home_screen_with_fallback(
                    ssh_client, timeout_seconds=60, log_callback=log_callback,
                    screenshot_callback=screenshot_callback
                )
                
                if home_detected:
                    if log_callback:
                        log_callback("✓ Device navigated to HOME SCREEN after HOME key")
                    return True, ssh_client, state
                else:
                    if log_callback:
                        log_callback("⚠ Device still not on HOME SCREEN after HOME key")
                    return True, ssh_client, state  # Continue anyway
            except Exception as e:
                if log_callback:
                    log_callback(f"⚠ Error sending HOME key: {str(e)[:80]}")
                return True, ssh_client, state
    
    elif is_standby:
        if log_callback:
            log_callback("⚠ Device is in STANDBY - bringing device to ON...")
        
        # Send IR POWER to wake up
        try:
            ir_code_power = generate_ir_code("POWER", ir_config['ir_port'], remote_type=selected_remote_type)
            send_ir_command(ir_code_power, ir_config['itach_ip'], ir_config['itach_port'], log_callback)
            
            if log_callback:
                log_callback("✓ IR POWER sent - waiting for device to boot...")
            
            time.sleep(30)
            
            # Reconnect SSH
            success, new_ssh, _ = create_ssh_connection_safe(
                device_ip, port, username, password, timeout_seconds=20, 
                log_callback=log_callback, max_retries=5
            )
            
            if not success:
                if log_callback:
                    log_callback("❌ Failed to reconnect after POWER wake-up")
                return False, None, "WAKEUP_FAILED"
            
            activate_screencapture_service(new_ssh, log_callback)
            time.sleep(10)
            
            # Wait for HOME screen
            if log_callback:
                log_callback("Waiting for HOME screen after wake-up...")
            
            home_detected, detection_method, _ = detect_home_screen_with_fallback(
                new_ssh, timeout_seconds=120, log_callback=log_callback,
                screenshot_callback=screenshot_callback
            )
            
            if home_detected:
                if log_callback:
                    log_callback("✓ Device woken from STANDBY and on HOME SCREEN")
                return True, new_ssh, "ON_HOME_SCREEN"
            else:
                if log_callback:
                    log_callback("⚠ Device woken but HOME SCREEN not detected - continuing anyway")
                return True, new_ssh, "ON_NO_HOME_SCREEN"
        
        except Exception as e:
            if log_callback:
                log_callback(f"❌ Error waking device from STANDBY: {str(e)[:80]}")
            return False, None, "WAKEUP_ERROR"
    
    else:
        if log_callback:
            log_callback(f"⚠ Device in unexpected state: {state}")
        return True, ssh_client, state


def detect_home_screen_with_fallback(ssh_client, timeout_seconds=120, log_callback=None, screenshot_callback=None):
    """Detect HOME screen on device with multiple fallback strategies."""
    home_patterns = [
        ("QMS HOME_TILES", "grep -E 'QMS.*HOME_TILES.*complete' /opt/logs/sky-messages.log | tail -1"),
        ("App focus", "grep -E 'App focus.*appId=com.entos.monarch_ui' /opt/logs/sky-messages.log | tail -1"),
        ("HOME_TILES fallback", "tail -100 /opt/logs/sky-messages.log | grep -E 'HOME_TILES' | tail -1"),
    ]
    
    check_start = time.time()
    check_interval = 5
    
    while (time.time() - check_start) < timeout_seconds:
        if not verify_ssh_connection_health(ssh_client, log_callback):
            if log_callback:
                log_callback("  ⚠ SSH connection lost - attempting screenshot fallback")
            break
        
        for pattern_name, grep_cmd in home_patterns:
            try:
                stdin, stdout, stderr = ssh_client.exec_command(grep_cmd, timeout=8)
                output = stdout.read().decode('utf-8', errors='ignore').strip()
                
                if output:
                    if log_callback:
                        log_callback(f"✓ HOME screen detected using pattern: {pattern_name}")
                        log_callback(f"  Log line: {output[:180]}")
                    return True, f"LOG_DETECTED_{pattern_name}", output
            except Exception as e:
                if log_callback:
                    log_callback(f"  ⚠ Pattern error ({pattern_name}): {str(e)[:60]}")
        
        elapsed = int(time.time() - check_start)
        if elapsed % 25 == 0 and elapsed > 0:
            remaining = timeout_seconds - int(elapsed)
            if log_callback:
                log_callback(f"  ⏱ Monitoring... {elapsed}s elapsed, {remaining}s remaining")
        
        time.sleep(check_interval)
    
    if log_callback:
        log_callback("⚠ HOME screen detection timeout - attempting screenshot fallback")
    
    if screenshot_callback:
        try:
            screenshot_success = screenshot_callback()
            if screenshot_success:
                return True, "SCREENSHOT_FALLBACK", "HOME screen detected via screenshot"
        except Exception as e:
            if log_callback:
                log_callback(f"  ⚠ Screenshot fallback failed: {str(e)[:80]}")
    
    if log_callback:
        log_callback("⚠ HOME screen detection failed - using SSH connection time as fallback")
    return False, "SSH_ACCESSIBLE_FALLBACK", ""


# ============================================================================
# MAIN EXECUTION FUNCTION - CURL DeepSleep Version
# ============================================================================

def execute_maintenance_CURL_deepsleep_wakeup_process(
    device_ip, port, username, password, iteration=1, device_name="Device", 
    combined_method_name=None, remote_type=None, sleep_duration_minutes=1, job_id=None,
    execute_deepsleep_wakeup=True
):
    """
    Execute Maintenance > CURL DeepSleep > Wakeup Process
    
    Key difference: Uses deepsleep_command (curl) to enter DeepSleep immediately
    
    Args:
        device_ip: Target device IP address
        port: SSH port (typically 10022)
        username: SSH username (typically 'root')
        password: SSH password
        iteration: Iteration number for logging
        device_name: Device name for IR config
        combined_method_name: Combined method name for folder naming
        remote_type: IR remote type ('XUMO' or 'SKY'). If None, auto-detect
        sleep_duration_minutes: Minutes to wait after deepsleep_command (default 1 - much less than original 13+)
        job_id: Job ID for lock management
        execute_deepsleep_wakeup: If True, execute Deep Sleep and Wake-up
    
    Returns:
        dict: {"iteration": int, "screenshots": list, "logs": list, "success": bool, 
               "wakeup_time_seconds": float, "time_saved_minutes": float, "details": str}
    """
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    screenshots_list = []
    logs_list = []
    wakeup_time_seconds = None
    power_key_send_time = None
    curl_deepsleep_send_time = None
    
    if job_id:
        from methods.method_utils import set_current_job_id
        import threading
        set_current_job_id(threading.get_ident(), job_id)
    
    safe_device_name = device_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    
    log_message("="*80)
    log_message("MAINTENANCE > CURL DEEPSLEEP > WAKEUP PROCESS - START")
    log_message("="*80)
    log_message(f"Device: {device_name} ({device_ip})")
    log_message(f"Iteration: {iteration}")
    log_message(f"[OPTIMIZED] DeepSleep Wait: {sleep_duration_minutes} minute (vs 13+ in standard method)")
    log_message(f"Remote Type: {remote_type or 'Auto-detect'}")
    log_message("="*80)
    
    try:
        from services.log_service import LogService
        log_service = LogService()
        usb_log_path = create_execution_log_path(device_ip, device_name, iteration, "MAINTENANCE_CURL_DEEPSLEEP_WAKEUP")
        log_service.current_usb_log_file = usb_log_path
        log_message(f"💾 USB execution log: {usb_log_path}")
    except Exception as e:
        log_message(f"⚠ Could not set USB log path: {e}")
    
    try:
        # ============================================================================
        # [STEP 0] PRE-EXECUTION VALIDATION - CHECK DEVICE STATE
        # ============================================================================
        log_message("\n" + "="*80)
        log_message("[STEP 0] PRE-EXECUTION VALIDATION - Device State Check...")
        log_message("="*80)
        
        # Establish initial SSH connection for pre-validation
        success, ssh, error_msg = create_ssh_connection_safe(
            device_ip, port, username, password, timeout_seconds=15, log_callback=log_message
        )
        
        if not success:
            log_message(f"❌ Failed to establish initial SSH connection: {error_msg}")
            return {
                "iteration": iteration,
                "screenshots": screenshots_list,
                "logs": logs_list,
                "success": False,
                "wakeup_time_seconds": None,
                "details": f"SSH connection failed: {error_msg}"
            }
        
        # Get IR config for potential device wake-up
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
        
        # Check device state and ensure it's ON and on HOME SCREEN
        def take_prevalidation_screenshot():
            try:
                method_for_folder = get_folder_method_name() or combined_method_name or "maintenance_CURL_deepsleep_wakeup"
                screenshot_folder = create_screenshot_folder(device_ip, safe_device_name, iteration, "PreValidation", method_for_folder)
                screenshot_name = f"{device_ip}_{safe_device_name}_Iteration-{iteration}_PreValidation_{timestamp}"
                screenshot_result = take_and_analyze_screenshot(ssh, screenshot_name, device_ip, log_message, screenshot_folder)
                return screenshot_result and screenshot_result.get('success', False)
            except Exception as e:
                log_message(f"  ⚠ Pre-validation screenshot error: {str(e)[:80]}")
                return False
        
        prevalidation_success, ssh, prevalidation_state = ensure_device_on_home_screen(
            ssh, device_ip, port, username, password, ir_config, selected_remote_type,
            log_callback=log_message, screenshot_callback=take_prevalidation_screenshot,
            timeout_seconds=180
        )
        
        if not prevalidation_success:
            log_message("⚠ Device pre-validation failed - but attempting to continue...")
        
        log_message(f"✓ STEP 0 COMPLETE - Device state: {prevalidation_state}")
        
        # ============================================================================
        # STEPS 1-7: MAINTENANCE CYCLE (Replicate from standard method)
        # ============================================================================
        log_message("\n" + "="*80)
        log_message("[STEPS 1-7] MAINTENANCE CYCLE - Executing...")
        log_message("="*80)
        
        # Ensure SSH is still healthy
        if not verify_ssh_connection_health(ssh, log_message):
            log_message("🔄 Reconnecting SSH for STEPS 1-7...")
            success, ssh, error_msg = create_ssh_connection_safe(
                device_ip, port, username, password, timeout_seconds=15, log_callback=log_message
            )
        
        if not success:
            log_message(f"❌ Failed to establish initial SSH connection: {error_msg}")
            return {
                "iteration": iteration,
                "screenshots": screenshots_list,
                "logs": logs_list,
                "success": False,
                "wakeup_time_seconds": None,
                "details": f"SSH connection failed: {error_msg}"
            }
        
        fetch_build_details(ssh, log_message)
        
        # Check maintenance activity status (STEPS 1-2) with timeout handling
        success, response, error = execute_ssh_command_with_timeout(
            ssh, maintenance_get_status_command, timeout_seconds=10, 
            log_callback=log_message, max_retries=2
        )
        
        if not success:
            log_message(f"⚠ Failed to get maintenance status: {error}")
            response = ""
        
        log_message(f"Maintenance activity status response: {response[:200]}")
        
        maintenance_status = None
        is_reboot_pending = False
        try:
            response_json = json.loads(response) if response.startswith('{') else {}
            maintenance_status = response_json.get('result', {}).get('maintenanceStatus', '').upper()
            is_reboot_pending = response_json.get('result', {}).get('isRebootPending', False)
            log_message(f"Current maintenance status: {maintenance_status}")
        except:
            if 'MAINTENANCE_ERROR' in response:
                maintenance_status = 'MAINTENANCE_ERROR'
            elif 'MAINTENANCE_COMPLETE' in response:
                maintenance_status = 'MAINTENANCE_COMPLETE'
        
        # Handle edge case if maintenance is in progress
        if maintenance_status not in ['MAINTENANCE_ERROR', 'MAINTENANCE_COMPLETE', '']:
            log_message(f"⚠ Maintenance in progress: {maintenance_status}")
            log_message("Stopping active maintenance...")
            
            success, _, error = execute_ssh_command_with_timeout(
                ssh, maintenance_stop_command, timeout_seconds=10,
                log_callback=log_message, max_retries=1
            )
            
            if not success:
                log_message(f"⚠ Failed to stop maintenance: {error}")
            
            ssh.close()
            
            # Wait 2 minutes
            log_message("⏱️  Waiting 2 minutes for maintenance to stop...")
            time.sleep(120)
            log_message("✓ 2-minute wait complete")
            
            # Reconnect with improved error handling
            success, ssh, error_msg = create_ssh_connection_safe(
                device_ip, port, username, password, timeout_seconds=15, log_callback=log_message
            )
            
            if not success:
                log_message(f"❌ Failed to reconnect after stopping maintenance: {error_msg}")
                return {
                    "iteration": iteration,
                    "screenshots": screenshots_list,
                    "logs": logs_list,
                    "success": False,
                    "wakeup_time_seconds": None,
                    "details": f"SSH reconnection failed: {error_msg}"
                }
        
        # STEP 3: Ensure device is in STANDBY (Simplified version)
        log_message("\n[STEP 3] Ensuring device is in STANDBY before starting maintenance...")
        
        success, power_state_output, error = execute_ssh_command_with_timeout(
            ssh, device_status_command, timeout_seconds=10, 
            log_callback=log_message, max_retries=2
        )
        
        if not success:
            log_message(f"⚠ Failed to get device power state: {error} - assuming STANDBY")
            power_state = "STANDBY"
        else:
            power_state = power_state_output
        
        initial_power_state = power_state[:100]
        log_message(f"Device power state: {initial_power_state}")
        
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
        
        # If not in STANDBY, send IR POWER
        if 'STANDBY' not in power_state.upper():
            log_message("✓ Sending IR POWER to ensure STANDBY...")
            ir_code_power = generate_ir_code("POWER", ir_config['ir_port'], remote_type=selected_remote_type)
            send_ir_command(ir_code_power, ir_config['itach_ip'], ir_config['itach_port'], log_message)
            time.sleep(30)
            
            success, power_state_output, error = execute_ssh_command_with_timeout(
                ssh, device_status_command, timeout_seconds=10,
                log_callback=log_message, max_retries=1
            )
            
            if success:
                power_state = power_state_output
            log_message(f"Device power state after IR: {power_state[:100]}")
        
        log_message("✓ STEP 3 PASSED - Device in STANDBY")
        
        # STEP 4: Start maintenance
        log_message("\n" + "="*80)
        log_message("[STEP 4] Starting maintenance cycle via MaintenanceManager...")
        log_message("="*80)
        log_message("Sending startMaintenance command via RDK MaintenanceManager API...")
        
        success, start_response, error = execute_ssh_command_with_timeout(
            ssh, maintenance_start_command, timeout_seconds=10,
            log_callback=log_message, max_retries=2
        )
        
        if success:
            log_message(f"Start maintenance response: {start_response[:200]}")
            log_message("✓ Maintenance start command accepted")
        else:
            log_message(f"⚠ Failed to start maintenance: {error}")
            log_message("Proceeding anyway...")
        
        ssh.close()
        log_message("\n⏳ Waiting 10 seconds for device to process startMaintenance command...")
        time.sleep(10)
        log_message("✓ Ready to check maintenance status")
        
        # STEP 5: Poll maintenance status
        log_message("\n" + "="*80)
        log_message("[STEP 5] Polling maintenance activity status every 10 seconds...")
        log_message("Goal: Wait for MAINTENANCE_ERROR status with isRebootPending=true")
        log_message("="*80)
        
        # Initial status check before polling starts
        log_message("\n📊 INITIAL STATUS CHECK (before polling starts):")
        log_message("-" * 80)
        
        try:
            success, ssh, error_msg = create_ssh_connection_safe(
                device_ip, port, username, password, timeout_seconds=10, 
                log_callback=None, max_retries=2
            )
            
            if success:
                success, response, error = execute_ssh_command_with_timeout(
                    ssh, maintenance_get_status_command, timeout_seconds=10,
                    log_callback=None, max_retries=1
                )
                
                if success:
                    try:
                        response_json = json.loads(response) if response.startswith('{') else {}
                        initial_status = response_json.get('result', {}).get('maintenanceStatus', 'UNKNOWN').upper()
                        initial_reboot_pending = response_json.get('result', {}).get('isRebootPending', False)
                        initial_critical = response_json.get('result', {}).get('isCriticalMaintenance', False)
                        last_successful_time = response_json.get('result', {}).get('LastSuccessfulCompletionTime', 'N/A')
                        
                        log_message(f"  📍 Maintenance Status: {initial_status}")
                        log_message(f"  🔄 Reboot Pending: {initial_reboot_pending}")
                        log_message(f"  ⚡ Critical Maintenance: {initial_critical}")
                        log_message(f"  ⏱️  Last Successful: {last_successful_time}")
                        log_message(f"  📝 Full Response: {response[:150]}")
                    except:
                        log_message(f"  ⚠ Could not parse response: {response[:100]}")
                
                try:
                    ssh.close()
                except:
                    pass
            else:
                log_message(f"  ⚠ Connection failed: {error_msg}")
        except Exception as e:
            log_message(f"  ⚠ Error during initial check: {str(e)[:80]}")
        
        log_message("-" * 80)
        
        maintenance_complete = False
        poll_count = 0
        max_polls = 360
        
        while not maintenance_complete and poll_count < max_polls:
            time.sleep(10)
            poll_count += 1
            
            log_message(f"\n⏳ Poll #{poll_count}: Waiting 10 seconds...")
            
            success, ssh, error_msg = create_ssh_connection_safe(
                device_ip, port, username, password, timeout_seconds=10, 
                log_callback=None, max_retries=2
            )
            
            if not success:
                if poll_count % 6 == 0:
                    log_message(f"  ⚠ Connection failed - {error_msg[:60]}")
                continue
            
            success, response, error = execute_ssh_command_with_timeout(
                ssh, maintenance_get_status_command, timeout_seconds=10,
                log_callback=None, max_retries=1
            )
            
            if not success:
                if poll_count % 6 == 0:
                    log_message(f"  ⚠ Command timeout/error - {error[:60]}")
                try:
                    ssh.close()
                except:
                    pass
                continue
            
            try:
                response_json = json.loads(response) if response.startswith('{') else {}
                maintenance_status = response_json.get('result', {}).get('maintenanceStatus', '').upper()
                is_reboot_pending = response_json.get('result', {}).get('isRebootPending', False)
                is_critical = response_json.get('result', {}).get('isCriticalMaintenance', False)
                last_successful = response_json.get('result', {}).get('LastSuccessfulCompletionTime', 'N/A')
            except:
                maintenance_status = 'IN_PROGRESS'
                is_reboot_pending = False
                is_critical = False
                last_successful = 'N/A'
            
            # Log detailed status every poll (not just every 60 seconds)
            log_message(f"📊 STATUS CHECK AFTER {poll_count * 10} SECONDS (Poll #{poll_count}):")
            log_message("-" * 80)
            log_message(f"  📍 Maintenance Status: {maintenance_status}")
            log_message(f"  🔄 Reboot Pending: {is_reboot_pending}")
            log_message(f"  ⚡ Critical Maintenance: {is_critical}")
            log_message(f"  ⏱️  Last Successful: {last_successful}")
            log_message(f"  📝 Full Response: {response[:150]}")
            log_message("-" * 80)
            
            if maintenance_status == 'MAINTENANCE_ERROR' and is_reboot_pending:
                log_message(f"\n✅ MAINTENANCE COMPLETE - Both conditions met:")
                log_message(f"   ✓ maintenanceStatus = MAINTENANCE_ERROR")
                log_message(f"   ✓ isRebootPending = true")
                log_message(f"   Exiting polling loop after {poll_count} polls ({poll_count * 10} seconds)")
                maintenance_complete = True
            
            try:
                ssh.close()
            except:
                pass
        
        log_message(f"\n✓ STEP 5 PASSED - Maintenance polling complete (polls: {poll_count}/{max_polls})")

        
        # STEP 6 & 7: Reboot device
        log_message("\n[STEPS 6-7] Rebooting device after maintenance...")
        
        success, ssh, error_msg = create_ssh_connection_safe(
            device_ip, port, username, password, timeout_seconds=10, 
            log_callback=log_message, max_retries=3
        )
        
        if success:
            success, _, error = execute_ssh_command_with_timeout(
                ssh, maintenance_reboot_command, timeout_seconds=10,
                log_callback=log_message, max_retries=1
            )
            
            if not success:
                log_message(f"⚠ Reboot command may have failed: {error}")
            
            try:
                ssh.close()
            except:
                pass
        else:
            log_message(f"⚠ Could not establish connection for reboot: {error_msg}")
        
        log_message("✓ Reboot command sent - Waiting 2 minutes for device to come back...")
        time.sleep(120)
        
        log_message("✓ STEPS 6-7 PASSED - Device rebooted and back online")
        
        # ============================================================================
        # STEP 8: VERIFY DEVICE IN STANDBY AFTER REBOOT
        # ============================================================================
        log_message("\n" + "="*80)
        log_message("[STEP 8] Verifying device is in STANDBY after maintenance reboot...")
        log_message("="*80)
        
        success, ssh, error_msg = create_ssh_connection_safe(
            device_ip, port, username, password, timeout_seconds=15, 
            log_callback=log_message, max_retries=5
        )
        
        if not success:
            log_message(f"❌ Failed to connect to device after reboot: {error_msg}")
            return {
                "iteration": iteration,
                "screenshots": screenshots_list,
                "logs": logs_list,
                "success": False,
                "wakeup_time_seconds": None,
                "details": f"Connection failed after reboot: {error_msg}"
            }
        
        success, power_state_output, error = execute_ssh_command_with_timeout(
            ssh, device_status_command, timeout_seconds=10,
            log_callback=log_message, max_retries=2
        )
        
        if success:
            power_state = power_state_output
        else:
            log_message(f"⚠ Failed to get power state: {error} - assuming STANDBY")
            power_state = "STANDBY"
        
        if 'STANDBY' in power_state.upper():
            log_message("✓ Device confirmed in STANDBY")
        else:
            log_message(f"⚠ Device power state: {power_state[:100]}")
        
        # ============================================================================
        # [NEW] STEP 9: RUN DEEPSLEEP COMMAND WHILE DEVICE IN STANDBY
        # ============================================================================
        log_message("\n" + "="*80)
        log_message("[STEP 9 - OPTIMIZATION] Running deepsleep_command via curl on device...")
        log_message("="*80)
        log_message("⏰ This is the KEY OPTIMIZATION - entering DeepSleep immediately!")
        log_message(f"  Command: {deepsleep_command[:100]}...")
        log_message("\nSending deepsleep curl command...")
        
        curl_deepsleep_send_time = time.time()
        log_message(f"📝 DeepSleep command sent at: {datetime.fromtimestamp(curl_deepsleep_send_time).isoformat()}")
        
        success, curl_response, error = execute_ssh_command_with_timeout(
            ssh, deepsleep_command, timeout_seconds=10,
            log_callback=log_message, max_retries=2
        )
        
        if success:
            if curl_response:
                log_message(f"✓ DeepSleep curl response: {curl_response[:100]}")
            else:
                log_message("✓ DeepSleep command sent (no response body)")
        else:
            log_message(f"⚠ DeepSleep command error: {error} - proceeding anyway")
        
        try:
            ssh.close()
        except:
            pass
        
        log_message("\n✓ STEP 9 PASSED - DeepSleep command issued to device")
        
        # ============================================================================
        # [NEW] STEP 10: WAIT SHORT DURATION (1-2 MINUTES) INSTEAD OF 13+
        # ============================================================================
        log_message("\n" + "="*80)
        log_message(f"[STEP 10 - OPTIMIZATION] Waiting {sleep_duration_minutes} minute(s) for DeepSleep entry...")
        log_message("="*80)
        log_message("⏰ TIME SAVED: Instead of waiting 13+ minutes, we wait only 1-2 minutes!")
        log_message("📊 This is where we save ~10+ minutes per test iteration!")
        
        log_message(f"✓ STEP 10 COMPLETE - {sleep_duration_minutes} minute(s) wait finished")
        
        # ============================================================================
        # [NEW] STEP 11: PERSISTENT CHECK - KEEP VERIFYING UNTIL DEVICE IN DEEPSLEEP
        # ============================================================================
        log_message("\n" + "="*80)
        log_message("[STEP 11 - PERSISTENT VERIFICATION] Checking if device entered DeepSleep...")
        log_message("="*80)
        log_message("Will keep checking until device is confirmed in DeepSleep (max 15 minutes)")
        log_message("Test: Attempting SSH connection to verify DeepSleep state")
        
        is_in_deep_sleep = False
        deep_sleep_entry_time = None
        max_retry_seconds = 900  # 15 minutes timeout
        retry_interval = 15  # Check every 15 seconds
        retry_count = 0
        max_retries = max_retry_seconds // retry_interval
        
        deepsleep_check_start = time.time()
        
        while not is_in_deep_sleep and retry_count < max_retries:
            retry_count += 1
            elapsed = time.time() - deepsleep_check_start
            elapsed_min = elapsed / 60
            
            log_message(f"\n[Retry {retry_count}] Checking DeepSleep status (elapsed: {elapsed_min:.1f}m)...")
            
            is_in_deep_sleep, verification_method = verify_deep_sleep_state(
                device_ip, port, username, password, log_callback=log_message
            )
            
            if is_in_deep_sleep:
                deep_sleep_entry_time = time.time()
                total_deepsleep_time = (deep_sleep_entry_time - curl_deepsleep_send_time) / 60
                log_message("\n" + "✓"*50)
                log_message(f"✓✓✓ SUCCESS - Device CONFIRMED in DeepSleep! ✓✓✓")
                log_message("✓"*50)
                log_message(f"\n📊 DEEPSLEEP ENTRY TIMING:")
                log_message(f"   • Curl command sent: {datetime.fromtimestamp(curl_deepsleep_send_time).isoformat()}")
                log_message(f"   • DeepSleep confirmed: {datetime.fromtimestamp(deep_sleep_entry_time).isoformat()}")
                log_message(f"   • Total time to DeepSleep: {total_deepsleep_time:.2f} minutes ({int(total_deepsleep_time*60)} seconds)")
                log_message(f"   • Verification method: {verification_method}")
                break
            else:
                if retry_count < max_retries:
                    remaining_secs = max_retry_seconds - int(elapsed)
                    remaining_min = remaining_secs // 60
                    log_message(f"   ⏳ Device still SSH-accessible (not in DeepSleep yet)...")
                    
                    # Every 4 checks (~60 seconds), check device power state and take corrective action if needed
                    if retry_count % 4 == 0:
                        log_message(f"\n   🔍 [State Check {retry_count // 4}] Checking device power state...")
                        try:
                            # Try to connect and check device power state
                            success, state_ssh, error_msg = create_ssh_connection_safe(
                                device_ip, port, username, password, timeout_seconds=10,
                                log_callback=None, max_retries=1
                            )
                            
                            if success:
                                success, power_state_output, error = execute_ssh_command_with_timeout(
                                    state_ssh, device_status_command, timeout_seconds=10,
                                    log_callback=None, max_retries=1
                                )
                                
                                try:
                                    state_ssh.close()
                                except:
                                    pass
                                
                                if success:
                                    power_state = power_state_output.upper()
                                    log_message(f"   📊 Device power state: {power_state[:80]}")
                                    
                                    # Only send IR POWER if device is in ON state, NOT if already in STANDBY
                                    if 'ON' in power_state or ('AWAKE' in power_state and 'STANDBY' not in power_state):
                                        log_message(f"   ⚠ Device is in ON state - needs to be in STANDBY before DeepSleep")
                                        log_message(f"   🔌 Sending IR POWER to put device in STANDBY...")
                                        
                                        ir_code_power = generate_ir_code("POWER", ir_config['ir_port'], remote_type=selected_remote_type)
                                        if send_ir_command(ir_code_power, ir_config['itach_ip'], ir_config['itach_port'], log_message):
                                            log_message("   ✓ IR POWER (1st attempt) sent")
                                            time.sleep(10)
                                            
                                            # Check power state again after IR POWER
                                            log_message("   🔍 Checking power state after IR POWER...")
                                            success, recheck_ssh, error_msg = create_ssh_connection_safe(
                                                device_ip, port, username, password, timeout_seconds=10,
                                                log_callback=None, max_retries=1
                                            )
                                            
                                            if success:
                                                success, power_state_after, error = execute_ssh_command_with_timeout(
                                                    recheck_ssh, device_status_command, timeout_seconds=10,
                                                    log_callback=None, max_retries=1
                                                )
                                                
                                                try:
                                                    recheck_ssh.close()
                                                except:
                                                    pass
                                                
                                                if success:
                                                    power_state_after = power_state_after.upper()
                                                    log_message(f"   📊 Power state after IR: {power_state_after[:80]}")
                                                    
                                                    # If still ON, resend IR POWER with 10 sec gap
                                                    if 'ON' in power_state_after or ('AWAKE' in power_state_after and 'STANDBY' not in power_state_after):
                                                        log_message(f"   ⚠ Device still in ON state - sending IR POWER again...")
                                                        time.sleep(10)
                                                        
                                                        if send_ir_command(ir_code_power, ir_config['itach_ip'], ir_config['itach_port'], log_message):
                                                            log_message("   ✓ IR POWER (2nd attempt) sent")
                                                            time.sleep(15)
                                                    else:
                                                        log_message(f"   ✓ Device transitioned to STANDBY state")
                                                        log_message(f"   ℹ️  Continuing to monitor for DeepSleep entry...")
                                                        time.sleep(10)
                                        else:
                                            log_message("   ⚠ Failed to send IR POWER")
                                    
                                    elif 'STANDBY' in power_state:
                                        log_message(f"   ✓ Device in STANDBY - deepsleep_command from STEP 9 is still active")
                                        log_message(f"   ⏳ Continuing to monitor for device inaccessibility (DeepSleep entry)...")
                                else:
                                    log_message(f"   ⚠ Could not get power state: {error}")
                            else:
                                log_message(f"   ⚠ Could not connect to check state: {error_msg}")
                        
                        except Exception as e:
                            log_message(f"   ⚠ Error during state check: {str(e)[:100]}")
                    
                    log_message(f"   ⏳ Waiting 15s before next check (timeout in {remaining_min}m)")
                    time.sleep(retry_interval)
                else:
                    log_message(f"\n⏰ TIMEOUT: Reached maximum retry time ({max_retry_seconds}s / {max_retry_seconds//60}m)")
                    log_message("⚠ Device did not enter DeepSleep within timeout period")
                    break
        
        # Final status
        if is_in_deep_sleep:
            log_message("\n✓ STEP 11 PASSED - Device confirmed in DeepSleep after retries")
        else:
            log_message("\n⚠ STEP 11 WARNING - Device never confirmed in DeepSleep (proceeding anyway)")
            deep_sleep_entry_time = time.time()
            total_deepsleep_time = (deep_sleep_entry_time - curl_deepsleep_send_time) / 60
            log_message(f"   ⚠ Elapsed wait time: {total_deepsleep_time:.2f} minutes")
        
        
        # ============================================================================
        # STEP 12: WAKE UP DEVICE WITH IR POWER
        # ============================================================================
        log_message("\n" + "="*80)
        log_message("[STEP 12] Waking up device with IR POWER command...")
        log_message("="*80)
        
        ir_code_power = generate_ir_code("POWER", ir_config['ir_port'], remote_type=selected_remote_type)
        log_message(f"🔌 Using IR port {ir_config['ir_port']} with iTach at {ir_config['itach_ip']}:{ir_config['itach_port']}")
        
        power_key_send_time = time.time()
        log_message(f"📝 IR POWER sent at: {datetime.fromtimestamp(power_key_send_time).isoformat()}")
        
        if not send_ir_command(ir_code_power, ir_config['itach_ip'], ir_config['itach_port'], log_message):
            log_message("⚠ Warning: IR POWER command may have failed")
        
        log_message("✓ IR POWER command sent")
        
        # ============================================================================
        # STEP 13: MEASURE WAKEUP TIME
        # ============================================================================
        log_message("\n" + "="*80)
        log_message("[STEP 13] Measuring device wakeup time...")
        log_message("="*80)
        
        log_message("Waiting 20 seconds for device startup...")
        time.sleep(20)
        
        log_message("Attempting SSH reconnection...")
        ssh_reconnect_start = time.time()
        ssh_wakeup = reconnect_to_device_with_retry(device_ip, port, username, password, max_retries=10, retry_interval=5, log_callback=log_message)
        ssh_reconnect_end = time.time()
        
        if ssh_wakeup:
            log_message(f"✓ SSH reconnected")
            
            activate_screencapture_service(ssh_wakeup, log_message)
            fetch_build_details(ssh_wakeup, log_message)
            
            # Monitor for HOME screen
            log_message("\n[SUB-STEP 13a] Monitoring for HOME screen...")
            
            def take_screenshot_for_detection():
                try:
                    method_for_folder = get_folder_method_name() or combined_method_name or "maintenance_CURL_deepsleep_wakeup"
                    screenshot_folder = create_screenshot_folder(device_ip, safe_device_name, iteration, "After", method_for_folder)
                    screenshot_name = f"{device_ip}_{safe_device_name}_Iteration-{iteration}_After-Wakeup_{timestamp}"
                    screenshot_result = take_and_analyze_screenshot(ssh_wakeup, screenshot_name, device_ip, log_message, screenshot_folder)
                    return screenshot_result and screenshot_result.get('success', False)
                except Exception as e:
                    log_message(f"  ⚠ Screenshot fallback error: {str(e)[:80]}")
                    return False
            
            home_screen_detected, detection_method, home_log_line = detect_home_screen_with_fallback(
                ssh_wakeup, 
                timeout_seconds=120,
                log_callback=log_message,
                screenshot_callback=take_screenshot_for_detection
            )
            
            home_screen_detection_time = time.time() if home_screen_detected else None
            device_state_at_wakeup = "ON_HOME_SCREEN" if home_screen_detected else "ON_NO_HOME_SCREEN"
            
            # ============================================================================
            # [SUB-STEP 13b] CHECK DEVICE STATE WHEN HOME SCREEN DETECTION FAILS
            # ============================================================================
            if not home_screen_detected:
                log_message("\n[SUB-STEP 13b] HOME screen detection FAILED - Checking device state...")
                
                # Get current device power state
                state, is_standby, is_on, is_deepsleep = get_device_power_state(
                    ssh_wakeup, device_ip, port, username, password, log_callback=log_message
                )
                
                device_state_at_wakeup = state
                
                if is_standby:
                    log_message(f"❌ Device state: STANDBY (NOT ON) - HOME screen detection impossible")
                    log_message(f"📊 Recording: Device NOT brought to ON state after wakeup")
                    device_state_at_wakeup = "STANDBY_NOT_ON"
                
                elif is_deepsleep:
                    log_message(f"❌ Device state: DEEPSLEEP (NOT ON) - HOME screen detection impossible")
                    log_message(f"📊 Recording: Device still in DEEPSLEEP after wakeup attempt")
                    device_state_at_wakeup = "DEEPSLEEP_NOT_ON"
                
                else:
                    log_message(f"⚠ Device state: {state} - ON but HOME screen NOT detected")
                    log_message(f"📊 Recording: Device ON but not on HOME SCREEN")
                    device_state_at_wakeup = "ON_NO_HOME_SCREEN"
                
                log_message(f"   Final device state marking: {device_state_at_wakeup}")
            
            # Calculate wakeup time
            if home_screen_detected and home_screen_detection_time:
                wakeup_time_seconds = home_screen_detection_time - power_key_send_time
                log_message(f"\n✓ HOME SCREEN WAKEUP TIME:")
                log_message(f"  ⏱ {int(wakeup_time_seconds)}s ({wakeup_time_seconds/60:.1f} minutes)")
            else:
                wakeup_time_seconds = ssh_reconnect_end - power_key_send_time
                log_message(f"\n⚠ Using SSH reconnection time (HOME screen not detected): {int(wakeup_time_seconds)}s")
                log_message(f"   Device state at wakeup: {device_state_at_wakeup}")
            
            # Take final screenshot
            time.sleep(10)
            method_for_folder = get_folder_method_name() or combined_method_name or "maintenance_CURL_deepsleep_wakeup"
            screenshot_folder = create_screenshot_folder(device_ip, safe_device_name, iteration, "After", method_for_folder)
            screenshot_name = f"{device_ip}_{safe_device_name}_Iteration-{iteration}_After-Wakeup-Final_{timestamp}"
            screenshot_result = take_and_analyze_screenshot(ssh_wakeup, screenshot_name, device_ip, log_message, screenshot_folder)
            
            if screenshot_result and screenshot_result.get('success'):
                log_message(f"✓ Screenshot saved: {screenshot_result.get('local_path')}")
                screenshots_list.append(screenshot_result.get('local_path', ''))
            
            ssh_wakeup.close()
            
            # ============================================================================
            # CALCULATE TIME SAVED
            # ============================================================================
            original_deepsleep_wait = 13  # 13+ minutes in standard method
            actual_deepsleep_wait = sleep_duration_minutes  # 1-2 minutes in this method
            time_saved_minutes = original_deepsleep_wait - actual_deepsleep_wait
            
            # Calculate actual measured deepsleep entry time if available
            if deep_sleep_entry_time:
                measured_deepsleep_minutes = (deep_sleep_entry_time - curl_deepsleep_send_time) / 60
            else:
                measured_deepsleep_minutes = None
            
            log_message("\n" + "="*80)
            log_message("✓ MAINTENANCE > CURL DEEPSLEEP > WAKEUP - COMPLETED SUCCESSFULLY")
            log_message("="*80)
            log_message(f"\n📊 TIME OPTIMIZATION RESULTS:")
            log_message(f"  • Original method wait: ~{original_deepsleep_wait} minutes")
            log_message(f"  • This method wait: {actual_deepsleep_wait} minute(s)")
            log_message(f"  • ⏰ TIME SAVED: ~{int(time_saved_minutes)} minutes per iteration!")
            log_message(f"\n📊 ACTUAL DEEPSLEEP ENTRY TIMING:")
            if measured_deepsleep_minutes is not None:
                log_message(f"  • DeepSleep command sent: {datetime.fromtimestamp(curl_deepsleep_send_time).isoformat()}")
                log_message(f"  • Device confirmed in DeepSleep: {datetime.fromtimestamp(deep_sleep_entry_time).isoformat()}")
                log_message(f"  • ⏱️  ACTUAL TIME TO DEEPSLEEP: {measured_deepsleep_minutes:.2f} minutes ({int(measured_deepsleep_minutes*60)} seconds)")
                log_message(f"  • Verification retries: {retry_count} checks")
            else:
                log_message(f"  • DeepSleep command sent: {datetime.fromtimestamp(curl_deepsleep_send_time).isoformat()}")
                log_message(f"  • ⚠ Device verification: Could not confirm DeepSleep entry")
            log_message(f"  • IR POWER wakeup sent: {datetime.fromtimestamp(power_key_send_time).isoformat()}")
            log_message(f"  • SSH re-connection time: {int(wakeup_time_seconds)}s")
            log_message(f"\n📊 WAKEUP VALIDATION STATUS:")
            log_message(f"  • HOME screen detected: {home_screen_detected}")
            log_message(f"  • Device state at wakeup: {device_state_at_wakeup}")
            log_message(f"  • Detection method: {detection_method if home_screen_detected else 'NONE - HOME screen not found'}")
            
            from app import add_html_result
            add_html_result(iteration, "DeepSleep-CURL", "PASSED", 
                          f"Optimized wakeup in {int(wakeup_time_seconds)}s - Actual DeepSleep: {measured_deepsleep_minutes:.2f}m - TIME SAVED: ~{int(time_saved_minutes)}min", 
                          ','.join(screenshots_list), '', device_ip=device_ip, method="maintenance_CURL_deepsleep_wakeup")
            
            return {
                "iteration": iteration,
                "screenshots": screenshots_list,
                "logs": logs_list,
                "success": True,
                "wakeup_time_seconds": wakeup_time_seconds,
                "time_saved_minutes": time_saved_minutes,
                "measured_deepsleep_minutes": measured_deepsleep_minutes,
                "deepsleep_verification_retries": retry_count,
                "deepsleep_method": "CURL_COMMAND",
                "home_screen_detected": home_screen_detected,
                "device_state_at_wakeup": device_state_at_wakeup,
                "details": f"Optimized DeepSleep: entry in {measured_deepsleep_minutes:.2f}m, wakeup in {int(wakeup_time_seconds)}s - SAVED ~{int(time_saved_minutes)} minutes - Device state: {device_state_at_wakeup}"
            }
        else:
            log_message("❌ Device did not wake up - SSH reconnection timeout")
            from app import add_html_result
            add_html_result(iteration, "Wakeup", "FAILED", "Device did not wake from DeepSleep", "", "", device_ip=device_ip, method="maintenance_CURL_deepsleep_wakeup")
            
            return {
                "iteration": iteration,
                "screenshots": screenshots_list,
                "logs": logs_list,
                "success": False,
                "wakeup_time_seconds": None,
                "time_saved_minutes": 0,
                "details": "Device did not wake up from DeepSleep"
            }
    
    except Exception as e:
        log_message(f"⚠ Error in STEP 8-13: {str(e)[:150]}")
        return {
            "iteration": iteration,
            "screenshots": screenshots_list,
            "logs": logs_list,
            "success": False,
            "wakeup_time_seconds": None,
            "details": f"Error: {str(e)}"
        }
    
    except Exception as e:
        log_message(f"\n❌ Unexpected error: {str(e)}")
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


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python method_maintenance_CURL_deepsleep_wakeup.py <device_ip> [port] [username] [password] [device_name] [remote_type]")
        print("\nExample: python method_maintenance_CURL_deepsleep_wakeup.py 10.0.0.126 10022 root skypass 'SKY-Device' SKY")
        sys.exit(1)
    
    device_ip = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 10022
    username = sys.argv[3] if len(sys.argv) > 3 else 'root'
    password = sys.argv[4] if len(sys.argv) > 4 else 'skypass'
    device_name = sys.argv[5] if len(sys.argv) > 5 else 'Device'
    remote_type = sys.argv[6] if len(sys.argv) > 6 else None
    
    print(f"\nExecuting Maintenance > CURL DeepSleep > Wakeup on {device_ip}")
    result = execute_maintenance_CURL_deepsleep_wakeup_process(
        device_ip, port, username, password, device_name=device_name, remote_type=remote_type
    )
    
    print(f"\nResult: {json.dumps(result, indent=2)}")
