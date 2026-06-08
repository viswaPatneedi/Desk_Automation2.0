#!/usr/bin/env python3
"""
DeepSleep Process Implementation - REFACTORED
Complete deepsleep workflow with user-specified requirements
"""

import sys
import time
import socket
import json
import paramiko
from datetime import datetime, timezone

# Import configurations
from config_commands import *
from config_log_patterns import *
from config_timing import *
from config_commands import (
    maintenance_get_status_command,
    maintenance_stop_command
)

# Import utilities for lock management
from utils.device_lock_manager import DeviceLockManager

# Import shared utilities
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

# Import AI Screen Analyzer for intelligent screen validation
try:
    from services.ai_screen_validation_bridge import get_validation_bridge
    AI_VALIDATION_AVAILABLE = True
except ImportError:
    AI_VALIDATION_AVAILABLE = False
    log_message("⚠️  AI Screen Analyzer not available - will use legacy validation only")

# Global AI validation bridge instance
_ai_bridge = None

def get_ai_bridge():
    """Get or create the AI validation bridge singleton"""
    global _ai_bridge
    if _ai_bridge is None and AI_VALIDATION_AVAILABLE:
        try:
            _ai_bridge = get_validation_bridge(use_ai=True)
        except Exception as e:
            log_message(f"⚠️  Could not initialize AI bridge: {e}")
            return None
    return _ai_bridge

def get_device_power_state(ssh, log_callback=None):
    """
    Query device power state (ON or STANDBY)
    
    Args:
        ssh: SSH connection
        log_callback: Logging function
        
    Returns:
        str: 'ON' or 'STANDBY' or None if error
    """
    try:
        stdin, stdout, stderr = ssh.exec_command("QueryPowerState", timeout=10)
        stdout.channel.settimeout(10)
        
        try:
            output = stdout.read().decode('utf-8', errors='ignore').strip()
            stdout.channel.close()
            
            # Check for ON state
            if 'RenderingOn' in output or output.upper() == 'ON':
                if log_callback:
                    log_callback(f"✓ Device power state: ON (output: {output[:50]})")
                return 'ON'
            # Check for LIGHTSLEEP state
            elif 'LIGHTSLEEP' in output.upper() or 'LIGHT_SLEEP' in output.upper():
                if log_callback:
                    log_callback(f"✓ Device power state: LIGHTSLEEP (output: {output[:50]})")
                return 'LIGHTSLEEP'
            # Check for DEEPSLEEP state
            elif 'DEEPSLEEP' in output.upper() or 'DEEP_SLEEP' in output.upper():
                if log_callback:
                    log_callback(f"✓ Device power state: DEEPSLEEP (output: {output[:50]})")
                return 'DEEPSLEEP'
            # Check for STANDBY state
            elif 'RenderingOff' in output or output.upper() == 'STANDBY':
                if log_callback:
                    log_callback(f"✓ Device power state: STANDBY (output: {output[:50]})")
                return 'STANDBY'
            # Fallback: treat true/false as ON/STANDBY
            elif 'true' in output.lower():
                if log_callback:
                    log_callback(f"✓ Device power state: ON (output: {output[:50]})")
                return 'ON'
            elif 'false' in output.lower():
                if log_callback:
                    log_callback(f"✓ Device power state: STANDBY (output: {output[:50]})")
                return 'STANDBY'
            else:
                if log_callback:
                    log_callback(f"⚠ Unknown device power state: {output}")
                return None
        except socket.timeout:
            if log_callback:
                log_callback(f"⚠ QueryPowerState command timed out")
            return None
    except Exception as e:
        if log_callback:
            log_callback(f"⚠ Error querying power state: {str(e)[:100]}")
        return None

def check_home_screen_status(ssh, log_callback=None):
    """
    Check if device is on HOME screen
    
    Args:
        ssh: SSH connection
        log_callback: Logging function
        
    Returns:
        bool: True if on HOME screen, False otherwise
    """
    try:
        stdin, stdout, stderr = ssh.exec_command(log_check_command_HOME)
        log_output = stdout.read().decode('utf-8', errors='ignore')
        
        return log_line_HOME.split(".*")[0] in log_output
    except Exception as e:
        if log_callback:
            log_callback(f"⚠ Error checking HOME screen: {e}")
        return False

def phase_1_reboot(ssh, device_ip, port, username, password, log_callback=None):
    """
    PHASE 1: REBOOT (if perform_reboot=True)
    
    Steps:
    1. Verify device is on HOME screen
    2. Send systemctl reboot
    3. Wait 60 secs
    4. Verify SSH inaccessible
    5. Reconnect and monitor HOME log line for 80+ secs
    6. Check device state with QueryPowerState
    
    Returns:
        tuple: (success: bool, ssh: paramiko.SSHClient or None)
    """
    log_callback("\n" + "="*80)
    log_callback("PHASE 1: DEVICE REBOOT")
    log_callback("="*80)
    
    try:
        # Step 1: Verify device on HOME screen before reboot
        log_callback("\n[REBOOT-1] Verifying device is on HOME screen before reboot...")
        if not check_home_screen_status(ssh, log_callback):
            log_callback("❌ Device NOT on HOME screen - Cannot proceed with reboot")
            return False, ssh
        log_callback("✓ Device confirmed on HOME screen")
        
        # Step 2: Send reboot command
        log_callback("\n[REBOOT-2] Sending systemctl reboot command...")
        stdin, stdout, stderr = ssh.exec_command("systemctl reboot")
        time.sleep(3)
        ssh.close()
        log_callback("✓ Reboot command sent - SSH connection closed")
        
        # Step 3: Wait 60 seconds
        log_callback("\n[REBOOT-3] Waiting 60 seconds for device to reboot...")
        for remaining in range(60, 0, -10):
            if remaining % 20 == 0 or remaining == 60:
                log_callback(f"  ⏱ {remaining}s remaining...")
            time.sleep(10 if remaining > 10 else remaining)
        log_callback("✓ 60-second wait complete")
        
        # Step 4: Verify SSH inaccessible
        log_callback("\n[REBOOT-4] Verifying device is offline (SSH inaccessible)...")
        device_offline = False
        for check in range(3):
            try:
                test_ssh = paramiko.SSHClient()
                test_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                test_ssh.connect(device_ip, port=port, username=username, password=password, timeout=5)
                test_ssh.close()
                log_callback(f"  ⚠ Device still accessible (check {check + 1}/3), waiting 5s...")
                time.sleep(5)
            except Exception:
                log_callback(f"✓ Device is offline (check {check + 1}/3) - Confirmed")
                device_offline = True
                break
        
        if not device_offline:
            log_callback("⚠ WARNING: Device remained accessible - may not have rebooted properly")
        
        # Step 5: Reconnect and monitor HOME log line for 80+ seconds
        log_callback("\n[REBOOT-5] Reconnecting to device after reboot...")
        ssh = reconnect_to_device_with_retry(device_ip, port, username, password, 15, 5, log_callback)
        if not ssh:
            log_callback("❌ Failed to reconnect after reboot")
            return False, None
        
        log_callback("✓ SSH connection re-established")
        
        log_callback("\n[REBOOT-5a] Monitoring HOME log line (up to 80 seconds)...")
        home_found = False
        start_time = time.time()
        max_wait = 80
        
        while time.time() - start_time < max_wait:
            if check_home_screen_status(ssh, None):
                elapsed = time.time() - start_time
                log_callback(f"✓ HOME log line found after {elapsed:.1f} seconds")
                home_found = True
                break
            else:
                elapsed = time.time() - start_time
                if int(elapsed) % 20 < 1:
                    log_callback(f"  ⏳ HOME log not found yet ({elapsed:.1f}s / {max_wait}s)...")
                time.sleep(5)
        
        if not home_found:
            log_callback("⚠ WARNING: HOME log line not found within 80 seconds")
        else:
            log_callback("✓ Device confirmed on HOME screen after reboot")
        
        # Step 6: Check device power state
        log_callback("\n[REBOOT-6] Checking device power state...")
        power_state = get_device_power_state(ssh, log_callback)
        if power_state:
            log_callback(f"✓ Device power state: {power_state}")
        
        log_callback("\n" + "="*80)
        log_callback("PHASE 1: REBOOT - COMPLETED")
        log_callback("="*80)
        
        return True, ssh
    
    except Exception as e:
        log_callback(f"❌ Error during reboot phase: {e}")
        try:
            ssh.close()
        except:
            pass
        return False, None

def phase_2_deepsleep_transition(ssh, device_ip, device_name, ir_config, remote_type, port, username, password, log_callback=None):
    """
    PHASE 2: DEEPSLEEP TRANSITION
    
    Case 2a: IF device is ON and on HOME SCREEN:
        - Run deepsleep_command, wait 10s
        - Send IR POWER to transition to STANDBY
    
    Case 2b: IF device is STANDBY and NOT on HOME SCREEN:
        - Wake device with IR POWER, wait 10s
        - Verify HOME screen, then proceed to Case 2a
    
    Returns:
        tuple: (success: bool, ssh: paramiko.SSHClient or None)
    """
    log_callback("\n" + "="*80)
    log_callback("PHASE 2: DEEPSLEEP TRANSITION")
    log_callback("="*80)
    
    try:
        # Check current device state and HOME screen
        device_state = get_device_power_state(ssh, log_callback)
        on_home_screen = check_home_screen_status(ssh, log_callback)
        
        log_callback(f"\n[PHASE-2] Current status: State={device_state}, HomeScreen={on_home_screen}")
        
        # Case 2a: Device is ON and on HOME SCREEN
        if device_state == 'ON' and on_home_screen:
            log_callback("\n📍 [CASE 2a] Device is ON and on HOME SCREEN")
            
            # Send IR POWER to STANDBY
            log_callback("[CASE-2a-1] Sending IR POWER to transition device to STANDBY...")
            ir_code_power = generate_ir_code("POWER", ir_config['ir_port'], remote_type=remote_type)
            if send_ir_command(ir_code_power, ir_config['itach_ip'], ir_config['itach_port'], log_callback):
                log_callback("  ✓ IR POWER sent successfully")
            else:
                log_callback("  ⚠ IR POWER may have failed")
            
            # Verify device transitioned to STANDBY
            log_callback("[CASE-2a-1] Verifying device transitioned to STANDBY...")
            time.sleep(5)
            new_state = get_device_power_state(ssh, log_callback)
            if new_state in ('STANDBY', 'LIGHTSLEEP', 'DEEPSLEEP'):
                log_callback(f"  ✓ Device state confirmed: {new_state}")
            elif new_state == 'ON':
                log_callback("  ⚠ Device still ON - IR POWER transition may be in progress")
            else:
                log_callback(f"  ⚠ Device state: {new_state or 'Unknown'} - transition still in progress")
            
            # Run deepsleep_command
            log_callback("[CASE-2a-2] Running deepsleep_command on device...")
            stdin, stdout, stderr = ssh.exec_command(deepsleep_command)
            response = stdout.read().decode('utf-8', errors='ignore').strip()
            if response:
                log_callback(f"  ✓ DeepSleep curl response: {response[:80]}")
            else:
                log_callback("  ✓ DeepSleep command sent (no response body)")
            
            # Wait 60 seconds after deepsleep_command
            log_callback("[CASE-2a-2] Waiting 60 seconds after deepsleep_command...")
            time.sleep(60)
            
            return True, ssh
        
        # Case 2b: Device is STANDBY and NOT on HOME SCREEN
        elif device_state == 'STANDBY' and not on_home_screen:
            log_callback("\n📍 [CASE 2b] Device is STANDBY and NOT on HOME SCREEN - Recovery")
            
            # Wake device with IR POWER
            log_callback("[CASE-2b-1] Sending IR POWER to wake from STANDBY...")
            ir_code_power = generate_ir_code("POWER", ir_config['ir_port'], remote_type=remote_type)
            if send_ir_command(ir_code_power, ir_config['itach_ip'], ir_config['itach_port'], log_callback):
                log_callback("  ✓ IR POWER sent")
            
            # Wait 10 seconds
            log_callback("[CASE-2b-2] Waiting 10 seconds for device to wake...")
            time.sleep(10)
            
            # Reconnect SSH
            log_callback("[CASE-2b-3] Reconnecting via SSH...")
            ssh.close()
            ssh = reconnect_to_device_with_retry(device_ip, port, username, password, 5, 3, log_callback)
            if not ssh:
                log_callback("⚠ Failed to reconnect - proceeding anyway")
                return False, None
            
            # Verify HOME screen
            log_callback("[CASE-2b-4] Verifying device is now on HOME screen...")
            if check_home_screen_status(ssh, log_callback):
                log_callback("✓ Device now on HOME screen - Proceeding to Case 2a")
                # Recursively call Case 2a
                return phase_2_deepsleep_transition(ssh, device_ip, device_name, ir_config, remote_type, port, username, password, log_callback)
            else:
                log_callback("❌ Device still not on HOME screen after recovery")
                return False, ssh
        
        # Case 2a: Device is ON (regardless of HOME screen)
        elif device_state == 'ON':
            log_callback("\n📍 [CASE 2a-ALTERNATE] Device is ON - Proceeding to transition")
            
            log_callback("[CASE-2a-1] Sending IR POWER to transition device to STANDBY...")
            ir_code_power = generate_ir_code("POWER", ir_config['ir_port'], remote_type=remote_type)
            if send_ir_command(ir_code_power, ir_config['itach_ip'], ir_config['itach_port'], log_callback):
                log_callback("  ✓ IR POWER sent")
            
            # Verify device transitioned to STANDBY
            log_callback("[CASE-2a-1] Verifying device transitioned to STANDBY...")
            time.sleep(5)
            new_state = get_device_power_state(ssh, log_callback)
            if new_state in ('STANDBY', 'LIGHTSLEEP', 'DEEPSLEEP'):
                log_callback(f"  ✓ Device state confirmed: {new_state}")
            elif new_state == 'ON':
                log_callback("  ⚠ Device still ON - IR POWER transition may be in progress")
            else:
                log_callback(f"  ⚠ Device state: {new_state or 'Unknown'} - transition still in progress")
            
            # Run deepsleep_command
            log_callback("[CASE-2a-2] Running deepsleep_command on device...")
            stdin, stdout, stderr = ssh.exec_command(deepsleep_command)
            response = stdout.read().decode('utf-8', errors='ignore').strip()
            if response:
                log_callback(f"  ✓ DeepSleep curl response: {response[:80]}")
            else:
                log_callback("  ✓ DeepSleep command sent (no response body)")
            
            # Wait 60 seconds after deepsleep_command
            log_callback("[CASE-2a-2] Waiting 60 seconds after deepsleep_command...")
            time.sleep(60)
            
            return True, ssh
        
        else:
            log_callback(f"⚠ Unexpected state: {device_state} - proceeding anyway")
            return False, ssh
    
    except Exception as e:
        log_callback(f"❌ Error during DEEPSLEEP transition Phase 2: {e}")
        return False, ssh

def phase_2c_verify_deepsleep(ssh, device_ip, port, username, password, log_callback=None):
    """
    PHASE 2c: VERIFY DEVICE IS IN DEEPSLEEP
    
    Polls SSH every 15 seconds continuously until SSH is inaccessible (device in DEEPSLEEP).
    No hard maximum — keeps checking until confirmed offline.
    
    Returns:
        bool: True if confirmed in DEEPSLEEP (SSH inaccessible), False on error
    """
    
    log_callback("\n[PHASE-2c] Verifying device is in DEEPSLEEP state (polling until SSH inaccessible)...")
    
    try:
        poll_interval = 15  # seconds between SSH probes
        elapsed = 0
        
        while True:
            try:
                test_ssh = paramiko.SSHClient()
                test_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                test_ssh.connect(device_ip, port=port, username=username, password=password, timeout=5)
                test_ssh.close()
                log_callback(f"  ⏳ Device still SSH-accessible ({elapsed}s elapsed) - waiting {poll_interval}s...")
                time.sleep(poll_interval)
                elapsed += poll_interval
            except Exception:
                log_callback(f"✓ Device NOT SSH-accessible at {elapsed}s - CONFIRMED IN DEEPSLEEP")
                return True
    
    except Exception as e:
        log_callback(f"❌ Error verifying DEEPSLEEP state: {e}")
        return False

def phase_3_wakeup_and_verify(ssh_initial, device_ip, port, username, password, device_name, ir_config, remote_type, sleep_duration_minutes, log_callback=None, execution_timestamp=None):
    """
    PHASE 3: WAKEUP FROM DEEPSLEEP AND VERIFY
    
    Steps:
    1. If sleep_duration_minutes > 0: Wait specified duration
    2. Send IR POWER to wake device
    3. Wait 15-20 seconds
    4. Check for latest HOME log line
    5. Verify device power state is ON
    6. Capture device state screenshot
    7. Calculate time from IR POWER to HOME screen
    
    Returns:
        tuple: (success: bool, ssh: paramiko.SSHClient or None, timing_info: dict with screenshot_path)
    """
    
    screenshot_path = None
    log_callback("\n" + "="*80)
    log_callback("PHASE 3: WAKEUP FROM DEEPSLEEP")
    log_callback("="*80)
    
    try:
        # If specified, wait in DEEPSLEEP
        if sleep_duration_minutes > 0:
            sleep_duration = sleep_duration_minutes * 60
            log_callback(f"\n[PHASE-3-SLEEP] Waiting in DEEPSLEEP: {sleep_duration_minutes} minutes...")
            for remaining in range(sleep_duration, 0, -60):
                if remaining % 120 < 1 or remaining <= 60:
                    minutes_remaining = remaining // 60
                    secs_remaining = remaining % 60
                    log_callback(f"  ⏱ {minutes_remaining}m {secs_remaining}s remaining...")
                time.sleep(60 if remaining > 60 else remaining)
            log_callback("✓ Sleep duration complete")
        else:
            log_callback("\n[PHASE-3-SLEEP] No sleep duration specified - proceeding to wakeup")
        
        # PHASE-3-1: Send IR POWER to wake
        log_callback("\n[PHASE-3-1] Sending IR POWER to wake device from DEEPSLEEP...")
        ir_wakeup_time = datetime.now(timezone.utc)
        log_callback(f"  ⏰ IR POWER sent at: {ir_wakeup_time.isoformat()}")
        
        ir_code_power = generate_ir_code("POWER", ir_config['ir_port'], remote_type=remote_type)
        if send_ir_command(ir_code_power, ir_config['itach_ip'], ir_config['itach_port'], log_callback):
            log_callback("  ✓ IR POWER sent successfully")
        else:
            log_callback("  ⚠ IR POWER may have failed")
        
        # Wait 3 seconds for device to process wakeup signal
        log_callback("\n[PHASE-3-2] Waiting 3 seconds for device to process IR POWER...")
        time.sleep(3)
        
        # PHASE-3-2B: Reconnect SSH immediately after IR POWER delay
        log_callback("\n[PHASE-3-2B] Reconnecting to device after IR POWER delay...")
        ssh = reconnect_to_device_with_retry(device_ip, port, username, password, 10, 5, log_callback)
        if not ssh:
            log_callback("❌ Failed to reconnect after wakeup")
            return False, None, {'screenshot_path': ''}
        
        log_callback("✓ SSH connection established")
        
        # Extract log file path from log_check_command_HOME for post-IR filtering
        # log_check_command_HOME format: grep -E "pattern" /path/to/file.log
        log_file_path = log_check_command_HOME.split()[-1] if log_check_command_HOME else "/opt/logs/sky-messages.log"
        
        # PHASE-3-3: Fetch latest HOME log entry to establish baseline
        log_callback("\n[PHASE-3-3] Fetching latest HOME log entry as baseline...")
        latest_home_entry_before_power = None
        home_found_time = None
        home_output = None
        try:
            # Get the most recent HOME log entry currently in the file
            home_cmd = f"grep -E \"{log_line_HOME}\" {log_file_path} | tail -1"
            stdin, stdout, stderr = ssh.exec_command(home_cmd, timeout=10)
            latest_home_entry_before_power = stdout.read().decode('utf-8', errors='ignore').strip()
            if latest_home_entry_before_power:
                log_callback(f"  ✓ Latest HOME entry found")
                log_callback(f"    Entry: {latest_home_entry_before_power[:100]}")
                
                # CHECK if baseline entry's timestamp is AFTER IR POWER time
                # This handles cases where HOME appears before PHASE-3-3 completes
                import re
                timestamp_match = re.search(r'\[?(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2})', latest_home_entry_before_power)
                if timestamp_match:
                    timestamp_str = timestamp_match.group(1).replace('T', ' ')
                    try:
                        from datetime import datetime as dt
                        baseline_entry_time = dt.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S').timestamp()
                        ir_power_unix = ir_wakeup_time.timestamp()
                        time_after_power = baseline_entry_time - ir_power_unix
                        
                        # Accept baseline entry as HOME if it appears after IR POWER (with 2-second tolerance)
                        if time_after_power >= -2:
                            home_found_time = datetime.now(timezone.utc)
                            home_output = latest_home_entry_before_power
                            log_callback(f"  ✓ Baseline entry IS the HOME we're looking for! (appears {time_after_power:.1f}s after IR POWER)")
                            log_callback(f"    Entry timestamp: {timestamp_str}")
                            log_callback(f"  ➜ Skipping PHASE-3-4 monitoring loop (HOME already detected)")
                        else:
                            log_callback(f"  ℹ Baseline entry is older than IR POWER ({abs(time_after_power):.1f}s old) - will monitor for NEW entry")
                    except Exception as e:
                        log_callback(f"  ⚠ Could not parse baseline entry timestamp: {e}")
                else:
                    log_callback(f"  ⚠ Could not extract timestamp from baseline entry")
            else:
                log_callback(f"  ℹ No previous HOME entries in log file")
        except Exception as e:
            log_callback(f"  ⚠ Could not fetch baseline HOME entry: {e}")
        
        # PHASE-3-4: Monitor for NEW HOME log entries (only if not already detected in PHASE-3-3)
        if home_found_time is None:  # Only run if HOME not already detected
            log_callback(f"\n[PHASE-3-4] Monitoring for NEW HOME screen log line (checking after IR POWER sent)...")
        else:
            log_callback(f"\n[PHASE-3-4] Skipped (HOME already detected in PHASE-3-3)")
        max_home_wait = 60  # seconds to poll for HOME
        home_elapsed = 0
        initial_aggressive_monitor = 10  # First 10 seconds: check every 1 second
        regular_poll_interval = 5  # After 10 seconds: check every 5 seconds
        
        while home_elapsed <= max_home_wait and home_found_time is None:  # Only loop if HOME not already detected
            try:
                # Fetch the LATEST HOME log entry from the file
                home_cmd = f"grep -E \"{log_line_HOME}\" {log_file_path} | tail -1"
                stdin, stdout, stderr = ssh.exec_command(home_cmd, timeout=10)
                latest_home_entry = stdout.read().decode('utf-8', errors='ignore').strip()
                
                if latest_home_entry and latest_home_entry != latest_home_entry_before_power:
                    # New entry found! Extract timestamp
                    import re
                    timestamp_match = re.search(r'\[?(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2})', latest_home_entry)
                    if timestamp_match:
                        timestamp_str = timestamp_match.group(1).replace('T', ' ')
                        try:
                            from datetime import datetime as dt
                            log_entry_time = dt.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S').timestamp()
                            ir_power_unix = ir_wakeup_time.timestamp()
                            time_after_power = log_entry_time - ir_power_unix
                            
                            # Accept if entry is from AFTER IR POWER (with 2-second tolerance for clock skew)
                            if time_after_power >= -2:
                                home_found_time = datetime.now(timezone.utc)
                                home_output = latest_home_entry
                                log_callback(f"✓ NEW HOME entry detected! (appears {time_after_power:.1f}s after IR POWER)")
                                log_callback(f"  Entry timestamp: {timestamp_str}")
                                break
                            else:
                                log_callback(f"  ⏳ HOME entry found but is BEFORE IR POWER ({abs(time_after_power):.1f}s old) - skipping")
                        except Exception as e:
                            log_callback(f"  ⚠ Timestamp parsing error: {e}")
                    else:
                        # No timestamp but new entry found - accept it
                        home_found_time = datetime.now(timezone.utc)
                        home_output = latest_home_entry
                        log_callback(f"✓ NEW HOME entry detected! (no timestamp to verify)")
                        break
                else:
                    # No new entry yet
                    next_poll_interval = 1 if home_elapsed < initial_aggressive_monitor else regular_poll_interval
                    if home_elapsed < max_home_wait:
                        log_callback(f"  ⏳ No new HOME entry ({home_elapsed}s elapsed)... checking again in {next_poll_interval}s")
                        time.sleep(next_poll_interval)
                        home_elapsed += next_poll_interval
                    else:
                        break
            except Exception as e:
                log_callback(f"  ⚠ Error fetching HOME log: {e}")
                time.sleep(regular_poll_interval)
                home_elapsed += regular_poll_interval
        
        # PHASE-3-5: SCREENSHOT CAPTURE - Capture device state REGARDLESS of HOME detection
        log_callback("\n[PHASE-3-5] SCREENSHOT CAPTURE: Capturing device state after wakeup attempt...")
        time.sleep(2)  # Brief wait to ensure screen is stable
        
        home_screenshot_path = ""
        try:
            # Try to capture screenshot using VNC
            screenshot_url = f"http://{device_ip}:5800/screenshot.png"
            try:
                import requests
                from datetime import date
                response = requests.get(screenshot_url, timeout=10)
                if response.status_code == 200:
                    # Save screenshot with improved naming
                    timestamp_unix = int(time.time())
                    date_str = date.today().isoformat()  # YYYY-MM-DD format
                    screenshot_filename = f"{device_ip}_After_DEEPSLEEP_WakeupState_screen_{date_str}-{timestamp_unix}.png"
                    screenshot_path_local = f"/media/viswa-pi4/Lexar/Enhancement_output/SCREENSHOTS/{screenshot_filename}"
                    os.makedirs(os.path.dirname(screenshot_path_local), exist_ok=True)
                    with open(screenshot_path_local, 'wb') as f:
                        f.write(response.content)
                    home_screenshot_path = screenshot_path_local
                    log_callback(f"✅ Wakeup state screenshot captured: {home_screenshot_path}")
            except Exception as e:
                log_callback(f"  ⚠ VNC screenshot error: {str(e)[:60]}")
        except Exception as e:
            log_callback(f"  ⚠ Screenshot capture error: {str(e)[:60]}")
        
        # CHECK: Was HOME detected in log?
        if not home_found_time:
            log_callback("❌ HOME log line NOT found after wakeup (post-IR POWER entries only)")
            log_callback(f"ℹ Screenshot captured anyway for device state verification: {home_screenshot_path}")
            return False, ssh, {'screenshot_path': home_screenshot_path}
        
        
        # PHASE-3-VERIFY: VERIFICATION CHECK - Explicitly confirm HOME screen log entry exists AFTER IR POWER
        log_callback("\n[PHASE-3-VERIFY] VERIFICATION: Confirming HOME screen log entry post-IR POWER...")
        home_log_verification_passed = False
        home_log_line_verified = ""
        
        if home_found_time and home_output:
            log_callback(f"✓ HOME screen log line found")
            log_callback(f"  Log entry: {home_output[:150] if home_output else 'N/A'}")
            
            # Extract and validate timestamp from the log line
            import re
            timestamp_match = re.search(r'\[?(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2})', home_output)
            if timestamp_match:
                timestamp_str = timestamp_match.group(1).replace('T', ' ')
                try:
                    from datetime import datetime as dt
                    log_entry_time = dt.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S').timestamp()
                    ir_power_unix = ir_wakeup_time.timestamp()
                    time_after_power = log_entry_time - ir_power_unix
                    log_callback(f"  ✓ Log entry timestamp: {timestamp_str}")
                    log_callback(f"  ✓ Time after IR POWER sent: {time_after_power:.1f} seconds")
                    
                    if time_after_power >= -2:  # 2 second tolerance
                        home_log_verification_passed = True
                        home_log_line_verified = home_output
                        log_callback(f"  ✅ VERIFICATION PASSED: HOME log entry confirmed AFTER IR POWER command")
                    else:
                        log_callback(f"  ⚠ Log entry is {abs(time_after_power):.1f}s BEFORE IR POWER (old entry skipped)")
                except Exception as e:
                    log_callback(f"  ⚠ Timestamp parsing error: {str(e)[:60]}")
                    home_log_verification_passed = True  # Accept detection even if timestamp parsing fails
            else:
                # No timestamp but HOME detected - accept it
                home_log_verification_passed = True
                home_log_line_verified = home_output
                log_callback(f"  ✓ VERIFICATION PASSED: HOME log entry detected (no timestamp to verify order)")
        else:
            log_callback("ℹ HOME log line not found - screenshot captured for device state verification")
        
        # NOTE: Screenshot already captured in PHASE-3-5 (happens regardless of HOME detection)
        
        # Link screenshot to result card
        log_callback("\n[PHASE-3-RESULT] LINKING RESULTS: Attaching verification data to result card...")
        try:
            from app import add_html_result
            
            # Build detailed result message
            if home_log_verification_passed and home_screenshot_path:
                result_status = "PASSED"
                result_message = f"✅ HOME verified after {timing_info['time_to_home_seconds']:.1f}s wakeup | LOG VERIFIED | Screenshot Linked"
                log_callback(f"  ✓ Result: PASSED with verification and screenshot")
            elif home_log_verification_passed:
                result_status = "PASSED"
                result_message = f"✅ HOME verified after {timing_info['time_to_home_seconds']:.1f}s wakeup | LOG VERIFIED (no screenshot)"
                log_callback(f"  ✓ Result: PASSED with log verification")
            elif home_screenshot_path:
                result_status = "PASSED"
                result_message = f"Device on HOME after {timing_info['time_to_home_seconds']:.1f}s wakeup | Screenshot Linked"
                log_callback(f"  ✓ Result: PASSED with screenshot")
            else:
                result_status = "WARNING"
                result_message = f"Device wakeup completed in {timing_info['time_to_home_seconds']:.1f}s"
                log_callback(f"  ⚠ Result: WARNING (no verification or screenshot)")
            
            # NOTE: do NOT add result to HTML report here - let main execution level handle it with proper job_id
            # This avoids duplicate results with unknown job IDs
            
        except Exception as e:
            log_callback(f"  ⚠ Error linking result card: {str(e)[:60]}")
        
        # Verify device power state is ON
        log_callback("\n[PHASE-3-6] Verifying device power state...")
        power_state = get_device_power_state(ssh, log_callback)
        if power_state != 'ON':
            log_callback(f"❌ Device power state is {power_state}, not ON")
            return False, ssh, {'screenshot_path': home_screenshot_path}
        else:
            log_callback("✓ Device power state is ON")
        
        # Calculate timing
        if home_found_time:
            # HOME was successfully detected
            timing_info = {
                'ir_sent_time': ir_wakeup_time.isoformat(),
                'home_verified_time': home_found_time.isoformat(),
                'time_to_home_seconds': (home_found_time - ir_wakeup_time).total_seconds(),
                'screenshot_path': home_screenshot_path  # Use wakeup state screenshot
            }
            log_callback("\n[PHASE-3-TIMING] Time calculated:")
            log_callback(f"  IR POWER sent: {ir_wakeup_time.isoformat()}")
            log_callback(f"  HOME verified: {home_found_time.isoformat()}")
            log_callback(f"  Time elapsed: {timing_info['time_to_home_seconds']:.1f} seconds")
            log_callback(f"  Screenshot: {home_screenshot_path if home_screenshot_path else 'Not captured'}")
            return True, ssh, timing_info
        else:
            # HOME was NOT detected, but screenshot was captured for verification
            log_callback("\n[PHASE-3-TIMING] HOME not detected, returning device state screenshot for analysis")
            timing_info = {
                'ir_sent_time': ir_wakeup_time.isoformat(),
                'home_verified_time': None,
                'time_to_home_seconds': None,
                'screenshot_path': home_screenshot_path  # Return wakeup state screenshot anyway
            }
            return False, ssh, timing_info
    
    except Exception as e:
        log_callback(f"❌ Error during wakeup phase: {e}")
        return False, None, {'screenshot_path': home_screenshot_path if 'home_screenshot_path' in locals() else screenshot_path}

def execute_deepsleep_process(device_ip, port, username, password, iteration=1, skip_pre_validation=False, device_name="Device", combined_method_name=None, remote_type=None, sleep_duration_minutes=60, job_id=None, perform_reboot=False):
    """
    Execute Deep Sleep Process - Main Entry Point
    
    WORKFLOW:
    - Phase 1 (OPTIONAL): Device Reboot (if perform_reboot=True)
    - Phase 2: DeepSleep Transition (Cases 2a & 2b)
    - Phase 2c: Verify DEEPSLEEP state
    - Phase 3: Wakeup and Verify
    
    Args:
        device_ip: Device IP address
        port: SSH port
        username: SSH username
        password: SSH password
        iteration: Iteration number
        skip_pre_validation: Skip pre-validation (not used currently)
        device_name: Device name
        combined_method_name: Combined method name
        remote_type: IR remote type
        sleep_duration_minutes: Duration to sleep in DEEPSLEEP
        job_id: Job identifier
        perform_reboot: If True, execute reboot phase first
    
    Returns:
        dict: {"iteration": int, "screenshots": list, "logs": list, "success": bool, "details": str}
    """
    
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    screenshots_list = []
    logs_list = []
    
    # Store job_id
    if job_id:
        from method_utils import set_current_job_id
        import threading
        set_current_job_id(threading.get_ident(), job_id)
    
    safe_device_name = device_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    
    log_message("="*80)
    log_message("DEEPSLEEP PROCESS - START")
    log_message("="*80)
    log_message(f"Device: {device_name} ({device_ip})")
    log_message(f"Iteration: {iteration}")
    log_message(f"DeepSleep Duration: {sleep_duration_minutes} minutes")
    log_message(f"Perform Reboot: {perform_reboot}")
    log_message(f"Remote Type Requested: {remote_type or 'Auto-detect'}")
    log_message("="*80)
    
    # Set USB log path
    try:
        from services.log_service import LogService
        log_service = LogService()
        usb_log_path = create_execution_log_path(device_ip, device_name, iteration, "DEEPSLEEP")
        log_service.current_usb_log_file = usb_log_path
        log_message(f"💾 USB execution log: {usb_log_path}")
    except Exception as e:
        log_message(f"⚠ Could not set USB log path: {e}")
    
    try:
        # Initial SSH connection
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(device_ip, port=port, username=username, password=password)
        
        # Fetch build details
        fetch_build_details(ssh, log_message)
        
        # Get IR config
        ir_config = get_ir_config_for_device(device_name)
        
        # Use remote type from UI (comes from ir_keycodes.json remotes dropdown)
        # User selects exact model like SKY_LC103, XUMO_PR3, etc.
        if remote_type:
            selected_remote_type = remote_type.strip()
        else:
            # Auto-detect based on device name
            selected_remote_type = 'SKY_LC103' if 'SKY' in device_name.upper() else 'XUMO_PR3'
        
        log_message(f"📡 Remote Type Selected: {remote_type or 'Auto-detect'}")
        log_message(f"✓ Using remote model: {selected_remote_type}")
        
        # PHASE 1: REBOOT (if enabled)
        if perform_reboot:
            success, ssh = phase_1_reboot(ssh, device_ip, port, username, password, log_message)
            if not success:
                log_message("❌ Reboot phase failed")
                from app import add_html_result
                add_html_result(iteration, "Reboot", "FAILED", "Reboot phase failed", "", "", device_ip=device_ip, method="deepsleep", job_id=job_id)
                return {"iteration": iteration, "screenshots": screenshots_list, "logs": logs_list, "success": False, "details": "Reboot phase failed", "device_name": device_name}
            
            # Reactivate services after reboot
            activate_screencapture_service(ssh, log_message)
            # Reestablish connection if needed
            if ssh:
                try:
                    ssh.close()
                except:
                    pass
                ssh = reconnect_to_device_with_retry(device_ip, port, username, password, 5, 3, log_message)
            
            # Check maintenance status after reboot (before proceeding to Phase 2)
            log_message("\n" + "="*80)
            log_message("[POST-REBOOT] Checking maintenance activity status...")
            log_message("="*80)
            
            try:
                stdin, stdout, stderr = ssh.exec_command(maintenance_get_status_command)
                time.sleep(2)
                response = stdout.read().decode('utf-8', errors='ignore').strip()
                
                log_message(f"Maintenance activity status response: {response[:200]}")
                
                # Parse maintenance status
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
                
                # If maintenance in progress (not ERROR or COMPLETE), stop it
                if maintenance_status not in ['MAINTENANCE_ERROR', 'MAINTENANCE_COMPLETE', '']:
                    log_message(f"\n⚠️  Maintenance activity in progress (status: {maintenance_status})")
                    log_message("Stopping active maintenance before proceeding to Phase 2...")
                    
                    stdin, stdout, stderr = ssh.exec_command(maintenance_stop_command)
                    time.sleep(2)
                    stop_response = stdout.read().decode('utf-8', errors='ignore').strip()
                    log_message(f"Stop maintenance response: {stop_response[:100]}")
                    
                    # Wait for maintenance to fully stop
                    log_message("\n⏱️  Waiting 2 minutes for maintenance to fully stop and stabilize...")
                    wait_time = 120  # 2 minutes
                    chunk_size = 30  # Log every 30 seconds
                    for elapsed in range(0, wait_time, chunk_size):
                        remaining = wait_time - elapsed
                        if remaining > 0:
                            log_message(f"  ⏳ {remaining}s remaining...")
                            time.sleep(min(chunk_size, remaining))
                    
                    log_message("✓ 2-minute wait complete")
                    
                    # Verify maintenance is stopped by rechecking status
                    log_message("\nVerifying maintenance was stopped...")
                    stdin, stdout, stderr = ssh.exec_command(maintenance_get_status_command)
                    time.sleep(2)
                    verify_response = stdout.read().decode('utf-8', errors='ignore').strip()
                    log_message(f"Post-stop maintenance status: {verify_response[:200]}")
                    
                    try:
                        verify_json = json.loads(verify_response) if verify_response.startswith('{') else {}
                        verify_status = verify_json.get('result', {}).get('maintenanceStatus', '').upper()
                        log_message(f"Verified maintenance status: {verify_status}")
                        
                        if verify_status in ['MAINTENANCE_ERROR', 'MAINTENANCE_COMPLETE', '']:
                            log_message("✓ Maintenance successfully stopped")
                        else:
                            log_message(f"⚠ Maintenance status still shows: {verify_status} - proceeding anyway")
                    except:
                        log_message("⚠ Could not parse post-stop status - proceeding with Phase 2")
                else:
                    log_message(f"✓ No active maintenance to stop (status: {maintenance_status or 'IDLE'})")
            
            except Exception as e:
                log_message(f"⚠ Error checking maintenance status after reboot: {e}")
                log_message("⚠ Continuing to Phase 2 anyway...")
        else:
            log_message("[REBOOT SKIPPED] perform_reboot=False - Proceeding to Phase 2")
        
        # PHASE 2: DEEPSLEEP TRANSITION
        success, ssh = phase_2_deepsleep_transition(ssh, device_ip, device_name, ir_config, selected_remote_type, port, username, password, log_message)
        if not success:
            log_message("❌ DEEPSLEEP transition phase failed")
            from app import add_html_result
            add_html_result(iteration, "DeepSleep-Transition", "FAILED", "Phase 2 transition failed", "", "", device_ip=device_ip, method="deepsleep", job_id=job_id)
            return {"iteration": iteration, "screenshots": screenshots_list, "logs": logs_list, "success": False, "details": "Phase 2 transition failed", "device_name": device_name}
        
        # PHASE 2c: VERIFY DEEPSLEEP STATE
        if not phase_2c_verify_deepsleep(ssh, device_ip, port, username, password, log_message):
            log_message("⚠ Device may not be in true DEEPSLEEP - proceeding anyway")
        
        # PHASE 3: WAKEUP AND VERIFY
        success, ssh, timing_info = phase_3_wakeup_and_verify(
            ssh, device_ip, port, username, password, device_name, 
            ir_config, selected_remote_type, sleep_duration_minutes, log_message, execution_timestamp=timestamp
        )
        
        if not success:
            log_message("❌ DEEPSLEEP wakeup phase failed")
            if ssh:
                ssh.close()
            from app import add_html_result
            add_html_result(iteration, "DeepSleep-Wakeup", "FAILED", "Phase 3 wakeup failed", "", "", device_ip=device_ip, method="deepsleep", job_id=job_id)
            return {"iteration": iteration, "screenshots": screenshots_list, "logs": logs_list, "success": False, "details": "Phase 3 wakeup failed", "device_name": device_name}
        
        # Add IR POWER screenshot to results if available
        if timing_info.get('screenshot_path'):
            screenshot_path = timing_info.get('screenshot_path')
            if screenshot_path:
                screenshots_list.append(screenshot_path)
                log_message(f"✓ Added IR POWER state screenshot to results")
        
        # SUCCESS
        log_message("\n" + "="*80)
        log_message("✓ DEEPSLEEP PROCESS COMPLETED SUCCESSFULLY")
        log_message("="*80)
        log_message(f"Time to HOME: {timing_info.get('time_to_home_seconds', 0):.1f} seconds")
        
        if ssh:
            ssh.close()
        
        from app import add_html_result
        add_html_result(iteration, "DeepSleep", "PASSED", f"Device on HOME after {timing_info.get('time_to_home_seconds', 0):.1f}s", 
                       ','.join(screenshots_list), ','.join(logs_list), device_ip=device_ip, method="deepsleep", job_id=job_id)
        
        return {
            "iteration": iteration,
            "screenshots": screenshots_list,
            "logs": logs_list,
            "success": True,
            "details": "Device on HOME screen after DeepSleep",
            "device_name": device_name,
            "timing": timing_info
        }
    
    except Exception as e:
        log_message(f"❌ Error during DeepSleep process: {e}")
        from app import add_html_result
        add_html_result(iteration, "DeepSleep", "FAILED", f"Exception: {str(e)}", "", "", device_ip=device_ip, method="deepsleep", job_id=job_id)
        return {"iteration": iteration, "screenshots": screenshots_list, "logs": logs_list, "success": False, "details": f"Error: {str(e)}", "device_name": device_name}
