#!/usr/bin/env python3
"""
Reboot Performance Monitoring Implementation
Monitors reboot time to home screen with log line detection and timing calculation
"""

import sys
import time
import re
import paramiko
from datetime import datetime, timezone

# Import configurations
from config.config_commands import *
from config.config_log_patterns import *
from config.config_timing import *

# Import shared utilities
from methods.method_utils import (
    log_message,
    fetch_build_details,
    activate_screencapture_service,
    create_screenshot_folder,
    create_execution_log_path,
    wait_for_device,
    check_network_and_realtek_errors,
    capture_device_logs_sftp,
    capture_minimal_logs_fallback,
    get_folder_method_name
)

# Import screenshot utilities
from utils.screenshot_utils import take_and_analyze_screenshot
from tools.screen.screenshot_utils_vnc import take_vnc_screenshot_with_fallback

def parse_log_timestamp(log_line):
    """
    Extract timestamp from log line
    Supports multiple formats:
    - ISO 8601: 2026-01-06T18:58:44.641Z
    - Custom format: 241210-15:06:48.123456 [mod=QMS, lvl=INFO]
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

def check_for_home_log_continuously(ssh, timeout_seconds, log_message_func):
    """
    Continuously check for HOME screen log line for specified timeout
    Returns: (found: bool, log_line: str or None, time_found: datetime or None)
    """
    start_time = time.time()
    last_log_time = start_time
    check_interval = 5  # Check every 5 seconds
    
    log_message_func(f"⏱ Monitoring logs for HOME screen (timeout: {timeout_seconds}s, checking every {check_interval}s)...")
    
    while (time.time() - start_time) < timeout_seconds:
        try:
            # Execute log check command
            stdin, stdout, stderr = ssh.exec_command(log_check_command_HOME)
            log_output = stdout.read().decode('utf-8', errors='ignore')
            
            # Check if HOME log line is present
            if log_line_HOME.split(".*")[0] in log_output:
                # Found the log line - extract the full line with timestamp
                lines = log_output.strip().split('\n')
                # Get the last matching line (most recent)
                home_line = lines[-1] if lines else log_output
                time_found = datetime.now(timezone.utc)
                
                log_message_func(f"✓ HOME screen log line detected!")
                log_message_func(f"   Log line: {home_line[:150]}...")
                return True, home_line, time_found
            
            # Log progress every 20 seconds
            elapsed = time.time() - start_time
            if (time.time() - last_log_time) >= 20:
                remaining = timeout_seconds - int(elapsed)
                log_message_func(f"  ⏱ Still monitoring... {int(elapsed)}s elapsed, {remaining}s remaining")
                last_log_time = time.time()
            
            # Wait before next check
            time.sleep(check_interval)
            
        except Exception as e:
            log_message_func(f"⚠ Error checking logs: {e}")
            time.sleep(check_interval)
    
    # Timeout reached without finding HOME log
    log_message_func(f"❌ HOME screen log line NOT found within {timeout_seconds}s timeout")
    return False, None, None

def execute_reboot_performance_process(device_ip, port, username, password, iteration=1, device_name="Device", combined_method_name=None):
    """
    Execute Reboot Performance Monitoring:
    Step 1: Pre-validation (connect and fetch build details)
    Step 2: Capture start time and send reboot command
    Step 3: Wait 80 seconds for device to reboot
    Step 4: Wait for device to come back online (SSH connectivity)
    Step 5: Monitor logs for HOME screen for up to 120 seconds
    Step 6: Calculate reboot performance time
    Step 7: Capture screenshot (success or failure)
    """
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    screenshots_list = []
    logs_list = []
    
    # Clean device name for filename
    safe_device_name = device_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    
    # Set USB log file path for this execution
    try:
        from services.log_service import LogService
        log_service = LogService()
        usb_log_path = create_execution_log_path(device_ip, device_name, iteration, "REBOOT_PERFORMANCE")
        log_service.current_usb_log_file = usb_log_path
        log_message(f"💾 USB execution log: {usb_log_path}")
    except Exception as e:
        log_message(f"⚠ Could not set USB log path: {e}")
    
    log_message("="*80)
    log_message("REBOOT PERFORMANCE MONITORING - START")
    log_message("="*80)
    
    try:
        # STEP 1: PRE-VALIDATION
        log_message("[STEP 1] Connecting to device and validating...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(device_ip, port=port, username=username, password=password, timeout=15)
        log_message("✓ Connected to device successfully")
        
        # Fetch build details from device
        fetch_build_details(ssh, log_message)
        
        # Activate ScreenCapture service before reboot
        activate_screencapture_service(ssh, log_message)
        
        log_message("✓ Pre-validation complete")
        
        # STEP 2: SEND REBOOT COMMAND AND CAPTURE START TIME
        log_message("\n[STEP 2] Sending reboot command and capturing start time...")
        # Capture UTC start time
        reboot_start_time = datetime.now(timezone.utc)
        log_message(f"⏱ Reboot command timestamp (UTC): {reboot_start_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        
        # Send reboot command
        stdin, stdout, stderr = ssh.exec_command(reboot_command)
        error_output = stderr.read().decode('utf-8', errors='ignore')
        if error_output:
            log_message(f"⚠ Reboot command stderr: {error_output}")
        
        ssh.close()
        log_message("✓ Reboot command sent successfully")
        
        # STEP 3: WAIT 80 SECONDS FOR DEVICE TO REBOOT
        log_message("\n[STEP 3] Waiting 80 seconds for device to reboot...")
        mandatory_wait = 80  # seconds
        
        # Chunked wait with progress logging every 20 seconds
        for i in range(8):  # 8 chunks of 10 seconds = 80 seconds
            time.sleep(10)
            elapsed = (i + 1) * 10
            if (i + 1) % 2 == 0:  # Log every 20 seconds (every 2 chunks)
                log_message(f"  ⏱ Reboot wait: {elapsed}/{mandatory_wait} seconds")
        
        log_message("✓ 80 second wait complete")
        
        # STEP 4: WAIT FOR DEVICE TO COME BACK ONLINE
        log_message("\n[STEP 4] Waiting for device to come back online (SSH connectivity)...")
        ssh = wait_for_device(device_ip, port, username, password, log_message)
        if not ssh:
            log_message("❌ Reboot performance test FAILED - device did not come back online")
            return {"iteration": iteration, "screenshots": screenshots_list, "logs": logs_list, "success": False, "device_name": device_name}
        
        log_message("✓ Device is back online (SSH connected)")
        
        # Fetch build details from device after reboot
        fetch_build_details(ssh, log_message)
        
        # Activate ScreenCapture service after reboot
        log_message("Activating ScreenCapture service after reboot...")
        activate_screencapture_service(ssh, log_message)
        
        # STEP 5: MONITOR LOGS FOR HOME SCREEN (150 seconds max)
        log_message("\n[STEP 5] Monitoring device logs for HOME screen...")
        monitoring_timeout = 150  # seconds
        
        home_found, home_log_line, home_found_time = check_for_home_log_continuously(
            ssh, monitoring_timeout, log_message
        )
        
        # STEP 6: CALCULATE REBOOT PERFORMANCE TIME
        log_message("\n[STEP 6] Calculating reboot performance...")
        
        if home_found and home_log_line:
            # Parse timestamp from log line
            home_log_time = parse_log_timestamp(home_log_line)
            
            if home_log_time:
                # Calculate time difference
                reboot_duration = (home_log_time - reboot_start_time).total_seconds()
                
                log_message(f"✓ Reboot Start Time: {reboot_start_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} UTC")
                log_message(f"✓ Home Screen Time:  {home_log_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} UTC")
                log_message(f"✓ Reboot Performance: {reboot_duration:.2f} seconds")
                
                # Format for display
                minutes = int(reboot_duration // 60)
                seconds = reboot_duration % 60
                if minutes > 0:
                    performance_str = f"{minutes}m {seconds:.2f}s"
                else:
                    performance_str = f"{seconds:.2f}s"
                
                log_message(f"✓ REBOOT TO HOME SCREEN TIME: {performance_str}")
            else:
                log_message("⚠ Could not parse timestamp from HOME log line")
                reboot_duration = None
        else:
            log_message("❌ HOME screen NOT reached within 150 seconds")
            reboot_duration = None
        
        # STEP 7: CAPTURE SCREENSHOT
        log_message("\n[STEP 7] Capturing screenshot...")
        method_for_folder = get_folder_method_name() or combined_method_name or "reboot_performance"
        screenshot_folder = create_screenshot_folder(device_ip, safe_device_name, iteration, "After", method_for_folder)
        
        if home_found:
            screenshot_name = f"{device_ip}_{safe_device_name}_Iteration-{iteration}_Reboot-Performance-SUCCESS_{timestamp}"
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
                log_message(f"✓ Screenshot saved: {screenshot_result.get('local_path')}")
                screenshots_list.append(screenshot_result.get('local_path', ''))
                
                # Check OCR text for network errors even on HOME screen
                extracted_text = screenshot_result.get('extracted_text', '')
                screen_state = screenshot_result.get('screen_state', {})
                if screen_state and screen_state.get('has_network_error'):
                    log_message("⚠ WARNING: Network error detected in screenshot text even though HOME screen log found")
                    log_message(f"⚠ Error indicators in text: {extracted_text[:300]}")
            
            log_message("\n" + "="*80)
            log_message("✓ REBOOT PERFORMANCE TEST PASSED")
            if reboot_duration:
                log_message(f"✓ Performance: {performance_str}")
            log_message("="*80)
            
            # STEP 8: VALIDATE /lib/teetz/ DIRECTORY BEFORE NEXT ITERATION
            log_message("\n[STEP 8] Validating /lib/teetz/ directory for next iteration...")
            stdin, stdout, stderr = ssh.exec_command("ls -ltr /lib/teetz/")
            teetz_output = stdout.read().decode('utf-8', errors='ignore').strip()
            teetz_error = stderr.read().decode('utf-8', errors='ignore').strip()
            
            # Check if directory has .ta files (the critical content we need)
            has_ta_files = teetz_output and ".ta" in teetz_output
            has_content = teetz_output and len(teetz_output.split('\n')) > 1  # More than just header
            
            if teetz_error and ("No such file or directory" in teetz_error or "cannot access" in teetz_error):
                # Directory doesn't exist
                log_message("❌ /lib/teetz/ directory NOT FOUND!")
                log_message(f"   Error: {teetz_error}")
                log_message("⚠️  CRITICAL: Cannot proceed with next reboot - Developer intervention required!")
                validation_passed = False
            elif has_ta_files:
                # Directory has .ta files - validation passed
                ta_file_count = teetz_output.count('.ta')
                log_message(f"✓ /lib/teetz/ directory validation PASSED ({ta_file_count} .ta files found)")
                log_message(f"   Directory contents:\n{teetz_output}")
                validation_passed = True
            elif has_content:
                # Directory exists and has some content, but no .ta files
                log_message("⚠ /lib/teetz/ directory exists but no .ta files found!")
                log_message(f"   Output: {teetz_output}")
                log_message("⚠️  WARNING: Unusual state - proceeding cautiously")
                validation_passed = True  # Allow to proceed but log warning
            else:
                # Directory might be empty or other issue
                log_message("⚠ /lib/teetz/ directory appears EMPTY or inaccessible!")
                log_message(f"   Output: {teetz_output or 'No output'}")
                log_message(f"   Error: {teetz_error or 'No error'}")
                log_message("⚠️  CRITICAL: Cannot proceed with next reboot - Developer intervention required!")
                validation_passed = False
            
            ssh.close()
            
            # Return with validation status
            return {
                "iteration": iteration, 
                "screenshots": screenshots_list, 
                "logs": logs_list, 
                "success": True, 
                "performance_seconds": reboot_duration,
                "teetz_validation": validation_passed,
                "stop_iterations": not validation_passed,  # Signal to stop further iterations if validation failed
                "device_name": device_name
            }
        
        else:
            # HOME screen not found - capture screenshot for diagnostics
            screenshot_name = f"{device_ip}_{safe_device_name}_Iteration-{iteration}_Reboot-Performance-FAILED_{timestamp}"
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
                
                # Check OCR text for errors
                extracted_text = screenshot_result.get('extracted_text', '')
                screen_state = screenshot_result.get('screen_state', {})
                has_network_error = screen_state.get('has_network_error', False)
                
                if has_network_error:
                    log_message("⚠ NETWORK ERROR DETECTED in screenshot text:")
                    log_message(f"   Text preview: {extracted_text[:300]}")
            
            # Check for network/Realtek errors in device logs
            check_network_and_realtek_errors(ssh, log_message)
            
            # Capture device logs for analysis
            log_message("Capturing device logs from /opt/logs/* for error analysis...")
            log_filename = f"{device_ip}_{safe_device_name}_Iteration-{iteration}_Reboot-Performance-FAILED-Logs_{timestamp}.tar.gz"
            log_path = capture_device_logs_sftp(ssh, log_filename, log_message, iteration, device_ip)
            if log_path:
                logs_list.append(log_path)
            else:
                # Fallback to minimal log capture
                fallback_logs = capture_minimal_logs_fallback(ssh, f"Iteration-{iteration}_Reboot-Performance-FAILED", log_message, iteration, device_ip)
                logs_list.extend(fallback_logs)
            
            log_message("\n" + "="*80)
            log_message("❌ REBOOT PERFORMANCE TEST FAILED")
            log_message("❌ Device did not reach HOME screen within 150 seconds")
            log_message("="*80)
            
            ssh.close()
            return {"iteration": iteration, "screenshots": screenshots_list, "logs": logs_list, "success": False, "device_name": device_name}
    
    except Exception as e:
        import traceback
        log_message(f"❌ Error during Reboot Performance test: {e}")
        log_message(f"Full traceback:\n{traceback.format_exc()}")
        return {"iteration": iteration, "screenshots": screenshots_list, "logs": logs_list, "success": False, "device_name": device_name}
