#!/usr/bin/env python3
"""
Reboot Performance Monitoring Implementation V2
Monitors reboot time to home screen with log line detection and timing calculation
Version 2: With optional post-reboot command checks (teetz, custom commands)
"""

import sys
import time
import re
import paramiko
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

def get_log_line_count(ssh, log_file="/opt/logs/sky-messages.log"):
    """
    Get the current line count of a log file
    Returns: int (line count) or None if error
    """
    try:
        stdin, stdout, stderr = ssh.exec_command(f"wc -l < {log_file}")
        line_count_str = stdout.read().decode('utf-8', errors='ignore').strip()
        if line_count_str.isdigit():
            return int(line_count_str)
    except Exception as e:
        pass
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
            # Use grep -n to get line numbers along with the matching lines
            # First try recent logs (last 500 lines)
            tail_and_grep_command = f"tail -n 500 /opt/logs/sky-messages.log | grep -n -E \"{log_line_HOME}\""
            stdin, stdout, stderr = ssh.exec_command(tail_and_grep_command)
            log_output = stdout.read().decode('utf-8', errors='ignore')
            
            # If recent logs didn't have HOME, try searching entire file (in case log is huge and HOME is outside last 500)
            if not log_output.strip():
                log_message_func(f"  ℹ HOME not in recent 500 lines, searching entire log file...")
                entire_file_grep = f"grep -n -E \"{log_line_HOME}\" /opt/logs/sky-messages.log"
                stdin, stdout, stderr = ssh.exec_command(entire_file_grep)
                log_output = stdout.read().decode('utf-8', errors='ignore')
            
            # Check if HOME log line is present in recent logs
            if log_output.strip():
                # Found matching lines - extract all of them
                # grep -n format: "LINE_NUM:log line content"
                lines = log_output.strip().split('\n')
                log_message_func(f"  📋 Found {len(lines)} HOME log line(s) in logs")
                
                # Filter lines to only those AFTER reboot start time AND after baseline line count
                valid_lines = []
                invalid_count = 0
                for line_entry in lines:
                    if not line_entry.strip():
                        continue
                    
                    # Parse grep -n output format: "LINE_NUM:content"
                    if ':' in line_entry:
                        try:
                            line_num_str, line_content = line_entry.split(':', 1)
                            line_num = int(line_num_str)
                        except (ValueError, IndexError):
                            log_message_func(f"  ⚠ Could not parse line number: {line_entry[:100]}")
                            continue
                    else:
                        # Fallback if format is different
                        line_num = None
                        line_content = line_entry
                    
                    if not line_content.strip():
                        continue
                    
                    # Parse timestamp from this line
                    line_timestamp = parse_log_timestamp(line_content)
                    if line_timestamp:
                        # Check if this is after reboot AND after baseline line count
                        is_after_baseline = (baseline_line_count is None) or (line_num is None) or (line_num > baseline_line_count)
                        is_after_reboot = (reboot_start_time is None) or (line_timestamp > reboot_start_time)
                        
                        if is_after_baseline and is_after_reboot:
                            valid_lines.append((line_timestamp, line_content))
                            baseline_note = f"(line {line_num} > baseline {baseline_line_count})" if (baseline_line_count and line_num) else ""
                            log_message_func(f"  ✓ Valid (after reboot & baseline) {baseline_note}: {line_timestamp.strftime('%H:%M:%S.%f')[:-3]} - {line_content[:120]}")
                        else:
                            invalid_count += 1
                            reason = []
                            if not is_after_baseline and line_num:
                                reason.append(f"line {line_num} ≤ baseline {baseline_line_count}")
                            if not is_after_reboot:
                                reason.append(f"before reboot")
                            log_message_func(f"  ✗ Old ({', '.join(reason)}): {line_timestamp.strftime('%H:%M:%S.%f')[:-3]}")
                    else:
                        # If can't parse timestamp, show warning
                        log_message_func(f"  ⚠ Could not parse timestamp: {line_content[:100]}")
                
                log_message_func(f"  Summary: {len(valid_lines)} valid, {invalid_count} old/filtered")
                
                # Get the LATEST valid line (most recent after reboot)
                if valid_lines:
                    # Sort by timestamp and get the latest
                    valid_lines.sort(key=lambda x: x[0])
                    latest_timestamp, home_line = valid_lines[-1]
                    time_found = datetime.now(timezone.utc)
                    
                    log_message_func(f"✓ HOME screen log line detected!")
                    log_message_func(f"   Found {len(valid_lines)} HOME log(s) after reboot, using the LATEST one")
                    log_message_func(f"   Timestamp from log: {latest_timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} UTC")
                    log_message_func(f"   Log line: {home_line[:200]}")
                    return True, home_line, time_found
                else:
                    # Found HOME lines but all are filtered out - keep monitoring
                    if reboot_start_time or baseline_line_count:
                        log_message_func(f"  ⏱ All {len(lines)} HOME logs found are from BEFORE reboot/baseline - continuing to monitor...")
            
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

def execute_optional_post_reboot_checks(ssh, optional_checks, log_message_func):
    """
    Execute optional post-reboot log checks and validation commands
    Args:
        ssh: SSH connection
            optional_checks: dict with check configurations - MANDATORY field
                            Can include 'skip_all': True to bypass all checks
        log_message_func: logging function
    Returns: dict with validation results
    """
    from config_log_patterns import get_all_optional_checks
    
    results = {
        'custom_checks': [],
        'overall_passed': True,
        'stop_iterations': False
    }
    
    # Check if user explicitly requested to skip all checks with -NA-
    if optional_checks and optional_checks.get('skip_all'):
        log_message_func(f"\n[POST-REBOOT CHECKS] User selected -NA- - skipping all validation checks")
        return results
    
    # Get all available log checks from config
    all_available_checks = get_all_optional_checks()
    
    # Determine which checks to run
    custom_commands_to_run = []
    
    # Run checks based on user selection (now mandatory)
    if optional_checks and optional_checks.get('custom_commands'):
        custom_commands_to_run = optional_checks.get('custom_commands', [])
        log_message_func(f"\n[POST-REBOOT VALIDATION] Running {len(custom_commands_to_run)} selected check(s)...")
    else:
        # Should not happen now that checks are mandatory, but handle gracefully
        log_message_func(f"\n⚠ Warning: No post-reboot checks configured (field should be mandatory)")
        return results
    
    if custom_commands_to_run:
        log_message_func(f"\n[POST-REBOOT VALIDATION] Executing {len(custom_commands_to_run)} check(s)...")
        for idx, cmd_config in enumerate(custom_commands_to_run, 1):
            cmd = cmd_config.get('command')
            description = cmd_config.get('description', cmd)
            check_key = cmd_config.get('check_key', '')
            terminate_on_match = cmd_config.get('terminate_on_match', False)
            
            log_message_func(f"\n  Check {idx}/{len(custom_commands_to_run)}: {description}")
            log_message_func(f"  Command: {cmd}")
            if terminate_on_match:
                log_message_func(f"  🛑 TERMINATION TRIGGER: Will stop iterations if pattern found")
            
            try:
                stdin, stdout, stderr = ssh.exec_command(cmd)
                cmd_output = stdout.read().decode('utf-8', errors='ignore').strip()
                cmd_error = stderr.read().decode('utf-8', errors='ignore').strip()
                
                # Special handling for teetz check to determine if we should stop iterations
                is_teetz_check = 'teetz' in check_key.lower() or 'teetz' in description.lower()
                check_passed = True
                pattern_found = bool(cmd_output)  # If grep finds something, it returns output
                
                if is_teetz_check:
                    # Validate teetz directory specifically
                    has_ta_files = cmd_output and ".ta" in cmd_output
                    has_content = cmd_output and len(cmd_output.split('\n')) > 1
                    
                    if cmd_error and ("No such file or directory" in cmd_error or "cannot access" in cmd_error):
                        log_message_func("  ❌ /lib/teetz/ directory NOT FOUND!")
                        log_message_func(f"     Error: {cmd_error}")
                        log_message_func("  ⚠️  CRITICAL: Cannot proceed with next iteration!")
                        check_passed = False
                        results['overall_passed'] = False
                        results['stop_iterations'] = True
                    elif has_ta_files:
                        ta_file_count = cmd_output.count('.ta')
                        log_message_func(f"  ✓ Validation PASSED ({ta_file_count} .ta files found)")
                        log_message_func(f"     Output preview:\n{cmd_output[:300]}")
                    elif has_content:
                        log_message_func("  ⚠ Directory exists but no .ta files found!")
                        log_message_func(f"     Output: {cmd_output}")
                        log_message_func("  ⚠️  WARNING: Unusual state - proceeding cautiously")
                    else:
                        log_message_func("  ❌ Directory appears EMPTY or inaccessible!")
                        log_message_func(f"     Output: {cmd_output or 'No output'}")
                        log_message_func("  ⚠️  CRITICAL: Cannot proceed with next iteration!")
                        check_passed = False
                        results['overall_passed'] = False
                        results['stop_iterations'] = True
                else:
                    # Regular check - show output and check for termination trigger
                    if cmd_output:
                        # Show first few lines for log checks
                        output_lines = cmd_output.split('\n')
                        if len(output_lines) > 10:
                            log_message_func(f"  ✓ Pattern FOUND (showing first 10 lines):")
                            for line in output_lines[:10]:
                                log_message_func(f"     {line}")
                            log_message_func(f"     ... ({len(output_lines) - 10} more lines)")
                        else:
                            log_message_func(f"  ✓ Pattern FOUND:")
                            for line in output_lines:
                                log_message_func(f"     {line}")
                        
                        # Check if this is a termination trigger
                        if terminate_on_match:
                            log_message_func(f"  🛑 TERMINATION TRIGGER ACTIVATED!")
                            log_message_func(f"     Pattern '{description}' was found in logs")
                            log_message_func(f"     Stopping further iterations as requested")
                            results['stop_iterations'] = True
                            results['overall_passed'] = False
                    else:
                        log_message_func(f"  ℹ Pattern NOT found (this may be normal)")
                    
                    if cmd_error:
                        # Grep returns exit code 1 when no match - this is normal
                        if "No such file" in cmd_error or "cannot access" in cmd_error:
                            log_message_func(f"  ⚠ Error: {cmd_error[:200]}")
                
                check_result = {
                    'command': cmd,
                    'description': description,
                    'output': cmd_output,
                    'error': cmd_error,
                    'success': check_passed,
                    'terminate_on_match': terminate_on_match,
                    'pattern_found': pattern_found
                }
                
                results['custom_checks'].append(check_result)
            except Exception as e:
                log_message_func(f"  ❌ Exception: {e}")
                results['custom_checks'].append({
                    'command': cmd,
                    'description': description,
                    'output': '',
                    'error': str(e),
                    'success': False
                })
    else:
        log_message_func("\nℹ No post-reboot checks configured")
    
    return results

def execute_reboot_performance_v2_process(device_ip, port, username, password, iteration=1, device_name="Device", combined_method_name=None, optional_checks=None, wait_after_reboot=80, home_screen_timeout=180):
    """
    Execute Reboot Performance Monitoring V2:
    Step 1: Pre-validation (connect, fetch build details, press HOME button to ensure device is on HOME screen)
    Step 2: Capture start time and send reboot command
    Step 3: Initial wait (85 seconds) to allow device to fully reboot
    Step 4: Wait for device to come back online (SSH connectivity)
    Step 5: Monitor logs for HOME screen detection - device should automatically reach HOME after reboot
    Step 6: Calculate reboot performance time if HOME screen found
    Step 7: Re-activate ScreenCapture service and capture AFTER screenshot (success or failure)
    Step 8: Execute post-reboot log checks (MANDATORY - unless user explicitly entered -NA-)
    
    Args:
            optional_checks: dict with check configurations - MANDATORY field
            {
                    'skip_all': True  # If user entered -NA- to bypass all checks
                    OR
                'custom_commands': [  # Specific checks to run
                    {'command': 'ls -ltr /opt/logs/', 'description': 'Check logs directory'},
                    ...
                ]
            }
                User must provide either skip_all=True or custom_commands list
        wait_after_reboot: int, DEPRECATED - kept for backward compatibility (not used)
        home_screen_timeout: int, total seconds from reboot to wait for HOME screen log line (default: 180)
    """
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    screenshots_list = []
    logs_list = []
    optional_checks = optional_checks or {}
    screenshot_result_before = None  # Store BEFORE screenshot for comparison
    screen_validation = None  # Initialize screen validation result
    
    # Clean device name for filename
    safe_device_name = device_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    
    # Set USB log file path for this execution
    try:
        from services.log_service import LogService
        log_service = LogService()
        usb_log_path = create_execution_log_path(device_ip, device_name, iteration, "REBOOT_PERFORMANCE_V2")
        log_service.current_usb_log_file = usb_log_path
        log_message(f"💾 USB execution log: {usb_log_path}")
    except Exception as e:
        log_message(f"⚠ Could not set USB log path: {e}")
    
    log_message("="*80)
    log_message("REBOOT PERFORMANCE MONITORING V2 - START")
    log_message("="*80)
    
    try:
        # STEP 1: DEVICE CONNECTION & PRE-REBOOT SETUP
        log_message("[STEP 1] Connecting to device and initial setup...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(device_ip, port=port, username=username, password=password, timeout=15)
        log_message("✓ Connected to device successfully")
        
        # Fetch build details from device
        fetch_build_details(ssh, log_message)
        
        # Activate ScreenCapture service before reboot
        activate_screencapture_service(ssh, log_message)
        
        # Ensure device is on HOME screen before reboot
        log_message("Ensuring device is on HOME screen before reboot...")
        try:
            home_key_command = "curl -d '{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"org.rdk.RDKShell.1.generateKey\",\"params\":{\"keys\":[{\"keyCode\":36,\"modifiers\":[],\"delay\":1.0}]}}' http://127.0.0.1:9998/jsonrpc"
            stdin, stdout, stderr = ssh.exec_command(home_key_command, timeout=10)
            response = stdout.read().decode('utf-8', errors='ignore')
            log_message("✓ HOME button pressed to navigate to HOME screen")
            log_message("   Waiting 10 seconds for UI to settle...")
            time.sleep(10)
        except Exception as e:
            log_message(f"⚠ Warning: Failed to press HOME button: {e}")
            log_message("   Continuing with reboot anyway...")
        
        log_message("✓ Pre-reboot setup complete")
        
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
        
        # STEP 3: INITIAL WAIT (85 SECONDS) BEFORE ATTEMPTING SSH RECONNECTION
        # This gives device time to complete shutdown and start boot process
        log_message(f"\n[STEP 3] Waiting 85 seconds for device to reboot...")
        initial_wait = 85
        for remaining in range(initial_wait, 0, -10):
            log_message(f"  ⏳ {remaining} seconds remaining...")
            time.sleep(10)
        log_message("✓ Initial wait complete")
        
        # STEP 4: WAIT FOR DEVICE TO COME BACK ONLINE
        log_message("\n[STEP 4] Waiting for device to come back online (SSH connectivity)...")
        log_message("  This step will continuously attempt SSH connection and monitor logs")
        ssh = wait_for_device(device_ip, port, username, password, log_callback=log_message)
        
        if not ssh:
            log_message("❌ Device did not come back online within timeout")
            return {"iteration": iteration, "screenshots": screenshots_list, "logs": logs_list, "success": False}
        
        log_message("✓ Device is back online - SSH connection established")
        
        # STEP 5: MONITOR LOGS FOR HOME SCREEN (PERFORMANCE METRIC)
        # Device should automatically navigate to HOME screen after reboot
        # Calculate remaining time for monitoring from when we reconnected
        elapsed_since_reboot = time.time() - reboot_start_time.timestamp()
        remaining_timeout = max(30, home_screen_timeout - elapsed_since_reboot)
        
        log_message(f"\n[STEP 5] Monitoring logs for HOME screen detection...")
        log_message(f"   Elapsed since reboot command: {elapsed_since_reboot:.0f}s")
        log_message(f"   Will monitor for up to: {remaining_timeout:.0f}s more (total timeout: {home_screen_timeout}s)")
        log_message(f"   Log source: /opt/logs/sky-messages.log")
        log_message(f"   Looking for HOME screen indicators in logs AFTER reboot time")
        home_found, home_log_line, home_time = check_for_home_log_continuously(
            ssh, timeout_seconds=int(remaining_timeout), log_message_func=log_message, 
            reboot_start_time=reboot_start_time, baseline_line_count=None
        )
        time.sleep(10)
        
        # STEP 6: CALCULATE PERFORMANCE IF HOME SCREEN FOUND
        reboot_duration = None
        performance_str = "N/A"
        
        if home_found:
            log_message("\n[STEP 6] Calculating reboot performance time...")
            
            # Try to parse timestamp from log line
            log_timestamp = parse_log_timestamp(home_log_line)
            
            if log_timestamp:
                # Calculate duration using log timestamp
                reboot_duration = (log_timestamp - reboot_start_time).total_seconds()
                log_message(f"✓ Reboot Start Time (UTC): {reboot_start_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
                log_message(f"✓ HOME Log Timestamp (UTC): {log_timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
                log_message(f"✓ Calculated Reboot Duration: {reboot_duration:.2f} seconds")
                performance_str = f"{reboot_duration:.2f}s"
            else:
                # Fallback to detection time
                reboot_duration = (home_time - reboot_start_time).total_seconds()
                log_message(f"⚠ Could not parse log timestamp, using detection time")
                log_message(f"✓ Calculated Reboot Duration (approximate): {reboot_duration:.2f} seconds")
                performance_str = f"~{reboot_duration:.2f}s"
            
            # STEP 7: CAPTURE SCREENSHOT FOR SUCCESS
            log_message("\n[STEP 7] Capturing success screenshot...")
            log_message("⚠ NOTE: Screenshot is informational - execution will continue even if it fails")
            
            # Re-activate screencapture service after reboot (service may have reset)
            log_message("Re-activating ScreenCapture service after reboot...")
            activate_screencapture_service(ssh, log_message)
            log_message("Waiting 3 seconds for service to fully initialize...")
            time.sleep(3)  # Reduced from 5s

            
            screenshot_folder = create_screenshot_folder(device_ip, device_name, iteration, "SUCCESS", method_name="reboot_performance_v2", execution_timestamp=timestamp)
            screenshot_name = f"{device_ip}_{safe_device_name}_Iteration-{iteration}_After-Reboot-Performance-V2-SUCCESS_{timestamp}"
            
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
                log_message(f"⚠ Screenshot exception: {e}")
                log_message("⚠ Continuing with test - screenshot is non-critical")
                screenshot_result = None
            
            if screenshot_result and screenshot_result.get('success'):
                screenshots_list.append(screenshot_result.get('local_path', ''))
                log_message(f"✓ Screenshot saved: {screenshot_result.get('local_path', 'N/A')}")
                
                # Check OCR text for errors even on success
                extracted_text = screenshot_result.get('extracted_text', '')
                screen_state = screenshot_result.get('screen_state', {})
                if screen_state and screen_state.get('has_network_error'):
                    log_message("⚠ WARNING: Network error detected in screenshot text even though HOME screen log found")
                    log_message(f"⚠ Error indicators in text: {extracted_text[:300]}")
            else:
                error_msg = screenshot_result.get('error', 'Unknown error') if screenshot_result else 'Screenshot failed'
                log_message(f"⚠ Screenshot not captured: {error_msg}")
                log_message("✓ Test continues - screenshot is informational only")
                screenshot_result = None  # Clear for validation check
                
            # VALIDATE SCREEN COMPARISON: BEFORE vs AFTER (Informational only)
            screen_validation = None
            if screenshot_result_before and screenshot_result:  # Only compare if both exist
                screen_validation = validate_screen_comparison(screenshot_result_before, screenshot_result, log_message)
            else:
                log_message("⚠ Screen validation skipped - BEFORE or AFTER screenshot unavailable")
            
            # Screen validation is informational only - don't fail test based on it
            # Some devices have 0-byte screenshot issues, log check is primary validation
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
            
            log_message("\n" + "="*80)
            log_message("✓ REBOOT PERFORMANCE TEST V2 PASSED")
            if reboot_duration:
                log_message(f"✓ Performance: {performance_str}")
            log_message("="*80)
            
            # STEP 8: EXECUTE POST-REBOOT LOG CHECKS (mandatory unless -NA-)
            check_results = None
            if optional_checks and (optional_checks.get('custom_commands') or optional_checks.get('skip_all')):
                log_message("\n[STEP 8] Post-reboot validation checks...")
                check_results = execute_optional_post_reboot_checks(ssh, optional_checks, log_message)
            else:
                log_message("\n[STEP 8] ⚠ No check configuration provided (field should be mandatory)")
                check_results = {
                    'custom_checks': [],
                    'overall_passed': True,
                    'stop_iterations': False
                }
            
            ssh.close()
            
            # Return with validation status
            return {
                "iteration": iteration, 
                "screenshots": screenshots_list, 
                "logs": logs_list, 
                "success": True, 
                "performance_seconds": reboot_duration,
                "optional_checks": check_results,
                "stop_iterations": check_results['stop_iterations'],
                "screen_validation": screen_validation
            }
        
        else:
            # HOME screen not found - capture screenshot for diagnostics
            log_message("\n[STEP 6-7] HOME screen NOT found - Capturing failure screenshot...")
            log_message("⚠ NOTE: Screenshot is informational - execution will continue even if it fails")
            
            # Re-activate screencapture service after reboot
            log_message("Re-activating ScreenCapture service after reboot...")
            activate_screencapture_service(ssh, log_message)
            log_message("Waiting 3 seconds for service to fully initialize...")
            time.sleep(3)  # Reduced from 5s
            
            screenshot_folder = create_screenshot_folder(device_ip, device_name, iteration, "FAILED", method_name="reboot_performance_v2", execution_timestamp=timestamp)
            screenshot_name = f"{device_ip}_{safe_device_name}_Iteration-{iteration}_After-Reboot-Performance-V2-FAILED_{timestamp}"
            
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
                    
                    # Check OCR text for errors
                    extracted_text = screenshot_result.get('extracted_text', '')
                    screen_state = screenshot_result.get('screen_state', {})
                    has_network_error = screen_state.get('has_network_error', False)
                    
                    if has_network_error:
                        log_message("⚠ NETWORK ERROR DETECTED in screenshot text:")
                        log_message(f"   Text preview: {extracted_text[:300]}")
                else:
                    log_message("⚠ Failure screenshot not captured - continuing anyway")
            except Exception as e:
                log_message(f"⚠ Screenshot capture exception: {e}")
                log_message("⚠ Continuing without screenshot")
            
            # Check for network/Realtek errors in device logs
            check_network_and_realtek_errors(ssh, log_message)
            
            # Capture device logs for analysis
            log_message("Capturing device logs from /opt/logs/* for error analysis...")
            log_filename = f"{device_ip}_{safe_device_name}_Iteration-{iteration}_Reboot-Performance-V2-FAILED-Logs_{timestamp}.tar.gz"
            log_path = capture_device_logs_sftp(ssh, log_filename, log_message, iteration, device_ip)
            if log_path:
                logs_list.append(log_path)
            else:
                # Fallback to minimal log capture
                fallback_logs = capture_minimal_logs_fallback(ssh, f"Iteration-{iteration}_Reboot-Performance-V2-FAILED", log_message, iteration, device_ip)
                logs_list.extend(fallback_logs)
            
            log_message("\n" + "="*80)
            log_message("❌ REBOOT PERFORMANCE TEST V2 FAILED")
            log_message(f"❌ Device did not reach HOME screen within {home_screen_timeout} seconds")
            log_message("="*80)
            
            ssh.close()
            return {"iteration": iteration, "screenshots": screenshots_list, "logs": logs_list, "success": False}
    
    except Exception as e:
        import traceback
        log_message(f"❌ Error during Reboot Performance V2 test: {e}")
        log_message(f"Full traceback:\n{traceback.format_exc()}")
        return {"iteration": iteration, "screenshots": screenshots_list, "logs": logs_list, "success": False}
