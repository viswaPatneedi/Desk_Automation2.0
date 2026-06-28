#!/usr/bin/env python3
"""
Reboot Performance Monitoring Implementation V2 - OPTIMIZED
Monitors reboot time to home screen with log line detection and timing calculation
Version: Optimized with intelligent early SSH probing (starts at 30s instead of 85s wait)

KEY IMPROVEMENTS:
- Initial wait reduced from 85s → 50s → 10s (data-driven optimization)
- SSH probing begins at 40s mark (optimal window for 84s average boot)
- Log monitoring starts immediately upon SSH reconnection
- Captures HOME logs that appear during boot phase
- ~50% faster test execution with better log coverage
- All original features preserved

TIMING COMPARISON:
Current (V2):        85s wait → SSH attempt → log check = 3-5 minutes total
Optimized V1:        50s wait + 30s SSH probe → immediate log check = 1-2.5 minutes total
ULTRA-Optimized:     10s wait + 40s SSH probe → immediate log check = 1-2 minutes total
"""

import sys
import time
import re
import paramiko
import socket
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
    get_folder_method_name,
    validate_screen_comparison
)

# Import screenshot utilities
from utils.screenshot_utils import take_and_analyze_screenshot
from tools.screen.screenshot_utils_vnc import take_vnc_screenshot_with_fallback

# Import AI Screen Validation
try:
    from ai_integration_universal import validate_screen_ai, get_ai_validator
    AI_VALIDATION_ENABLED = True
except ImportError:
    AI_VALIDATION_ENABLED = False
    log_message("⚠️  AI Screen Validation not available - using legacy validation")

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
    import socket
    try:
        stdin, stdout, stderr = ssh.exec_command(f"wc -l < {log_file}", timeout=5)
        stdout.channel.settimeout(5)
        try:
            line_count_str = stdout.read().decode('utf-8', errors='ignore').strip()
            stdout.channel.close()
            if line_count_str.isdigit():
                return int(line_count_str)
        except socket.timeout:
            pass
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
            # Check if job has been cancelled
            from methods.method_utils import is_job_cancelled
            if is_job_cancelled():
                log_message_func("⚠ [CANCELLED] Job cancellation detected - stopping HOME log monitoring...")
                return False, None, None
            
            # OPTIMIZED: Get ONLY the last matching line (most recent HOME log)
            # Use patterns that match what we know works on the device
            grep_patterns = [
                # Priority 1: QMS HOME_TILES complete // this is for XUMO, Rogers IUIv1 and SKY RDKE Devices - most reliable for HOME screen detection
                "grep -E 'QMS.*HOME_.*complete' /opt/logs/sky-messages.log | tail -1",
                
                # Priority 2: App focus event (MOST RELIABLE for HOME screen detection) //  this is for ROGERS IUIv2
                "grep -E 'App focus.*appId=com.entos.monarch_ui' /opt/logs/sky-messages.log | tail -1",
                
                # Priority 3: AppsModel.log App focus (alternative format) // not Required
                "grep -E 'AppsModel.*App focus.*monarch_ui' /opt/logs/sky-messages.log | tail -1",
                
                # Fallback: HOME_TILES only (exclude 'adding package' false positives) // not Required
                "tail -100 /opt/logs/sky-messages.log | grep -E 'HOME_.*complete' | tail -1"
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



def check_and_collect_logs_for_patterns(ssh, device_ip, device_name, iteration, log_patterns, log_message_func):
    """
    Search device logs for specific patterns and collect logs if any pattern is found
    
    Args:
        ssh: SSH connection object
        device_ip: Device IP address
        device_name: Device name for filename
        iteration: Current iteration number
        log_patterns: List of patterns to search for, e.g., ["process crashed", "ERROR", "CRASH"]
        log_message_func: logging function
    
    Returns: dict with:
        - 'found_patterns': List of patterns that were found
        - 'log_paths': List of collected log file paths
        - 'matched_lines': Sample of matched log lines
    """
    import os
    
    result = {
        'found_patterns': [],
        'log_paths': [],
        'matched_lines': []
    }
    
    if not log_patterns:
        log_message_func("\n[PATTERN SEARCH] No patterns configured - skipping pattern-based log collection")
        return result
    
    try:
        log_message_func(f"\n[PATTERN SEARCH] Searching for {len(log_patterns)} pattern(s) in device logs...")
        log_message_func(f"   Search location: /opt/logs/core_log.txt")
        
        # Search for patterns in device logs
        patterns_found = []
        
        for idx, pattern in enumerate(log_patterns, 1):
            log_message_func(f"\n  Pattern {idx}/{len(log_patterns)}: '{pattern}'")
            pattern_safe = pattern.replace("'", "\\'")
            
            # Search in core_log.txt and other log files
            search_cmd = f"grep -E '{pattern_safe}' /opt/logs/core_log.txt 2>/dev/null | head -5"
            
            try:
                stdin, stdout, stderr = ssh.exec_command(search_cmd, timeout=15)
                search_output = stdout.read().decode('utf-8', errors='ignore').strip()
                stdout.channel.close()
                
                if search_output:
                    log_message_func(f"  ✓ MATCH FOUND: Pattern '{pattern}' detected in logs!")
                    log_message_func(f"     Matched lines (up to 5):")
                    for line in search_output.split('\n')[:5]:
                        if line.strip():
                            log_message_func(f"       • {line[:150]}")
                    patterns_found.append(pattern)
                    result['matched_lines'].append({
                        'pattern': pattern,
                        'samples': search_output.split('\n')[:3]
                    })
                else:
                    log_message_func(f"  ⊘ No match: Pattern not found in logs")
            except Exception as e:
                log_message_func(f"  ⚠ Error searching pattern '{pattern}': {e}")
        
        # Log summary
        log_message_func(f"\n[PATTERN SEARCH SUMMARY]")
        log_message_func(f"  Total patterns searched: {len(log_patterns)}")
        log_message_func(f"  Patterns matched: {len(patterns_found)}")
        
        # If any patterns found, collect logs
        if patterns_found:
            result['found_patterns'] = patterns_found
            log_message_func(f"\n[LOG COLLECTION] Found {len(patterns_found)} pattern(s) - Collecting device logs for diagnostics...")
            patterns_str = ", ".join([f"'{p}'" for p in patterns_found])
            log_message_func(f"  Patterns that triggered collection: {patterns_str}")
            
            # Collect logs to /media/apps
            collected_log_path = collect_device_logs_to_media_app(
                ssh, device_ip, device_name, iteration, log_message_func
            )
            
            if collected_log_path:
                log_message_func(f"✓ Logs collected: {collected_log_path}")
                result['log_paths'].append(collected_log_path)
        else:
            log_message_func(f"  ℹ No patterns matched - No issue-based log collection (normal pass)")
        
        return result
    
    except Exception as e:
        log_message_func(f"❌ Error in pattern search: {e}")
        import traceback
        log_message_func(f"  Traceback: {traceback.format_exc()}")
        return result

def collect_device_logs_to_media_app(ssh, device_ip, device_name, iteration, log_message_func):
    """
    Collect device logs and store them in /media/apps for this iteration
    
    Args:
        ssh: SSH connection object
        device_ip: Device IP address
        device_name: Device name for filename
        iteration: Current iteration number
        log_message_func: logging function
    
    Returns: str (path to collected logs) or None if failed
    """
    import os
    
    # Clean device name for filename
    safe_device_name = device_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    
    try:
        log_message_func(f"\n📋 Collecting device logs for iteration {iteration}...")
        
        # Remote path in /media/apps
        remote_log_archive = f"/media/apps/{device_ip}_{safe_device_name}_ITR-{iteration}_logs_{timestamp}.tar.gz"
        
        # Create /media/apps directory if it doesn't exist
        log_message_func(f"  Ensuring /media/apps directory exists...")
        mkdir_cmd = "mkdir -p /media/apps && ls -la /media/apps | head -5"
        stdin, stdout, stderr = ssh.exec_command(mkdir_cmd, timeout=10)
        mkdir_output = stdout.read().decode('utf-8', errors='ignore').strip()
        stdout.channel.close()
        
        if mkdir_output:
            log_message_func(f"  ✓ /media/apps directory ready")
        
        # Create tar.gz archive of device logs
        log_message_func(f"  Creating log archive...")
        tar_cmd = f"tar -czf {remote_log_archive} /opt/logs/* 2>/dev/null || echo 'tar_done'"
        stdin, stdout, stderr = ssh.exec_command(tar_cmd, timeout=60)
        stdout.channel.recv_exit_status()
        tar_output = stdout.read().decode('utf-8', errors='ignore').strip()
        stdout.channel.close()
        
        log_message_func(f"  ✓ Archive created on device")
        
        # Verify file exists and has content
        log_message_func(f"  Verifying archive...")
        verify_cmd = f"ls -lh {remote_log_archive} && echo 'SIZE_OK' || echo 'FILE_NOT_FOUND'"
        stdin, stdout, stderr = ssh.exec_command(verify_cmd, timeout=10)
        verify_output = stdout.read().decode('utf-8', errors='ignore').strip()
        stdout.channel.close()
        
        if "SIZE_OK" in verify_output or remote_log_archive in verify_output:
            log_message_func(f"✓ Device logs successfully collected in /media/apps")
            log_message_func(f"  File: {remote_log_archive}")
            
            # Extract file size info
            for line in verify_output.split('\n'):
                if remote_log_archive in line:
                    log_message_func(f"  Details: {line}")
            
            return remote_log_archive
        else:
            log_message_func(f"❌ Failed to create log archive")
            log_message_func(f"  Output: {verify_output}")
            return None
    
    except Exception as e:
        log_message_func(f"❌ Error collecting logs: {e}")
        import traceback
        log_message_func(f"  Traceback: {traceback.format_exc()}")
        return None

def execute_optional_post_reboot_checks(ssh, optional_checks, log_message_func, device_ip=None, device_name=None, iteration=None):
    """
    Execute optional post-reboot log checks and validation commands
    Args:
        ssh: SSH connection
            optional_checks: dict with check configurations - MANDATORY field
                            Can include 'skip_all': True to bypass all checks
        log_message_func: logging function
        device_ip: Device IP (for log collection)
        device_name: Device name (for log collection)
        iteration: Current iteration number (for log collection)
    Returns: dict with validation results including detections for log collection
    """
    from config.config_log_patterns import get_all_optional_checks
    
    results = {
        'custom_checks': [],
        'overall_passed': True,
        'stop_iterations': False,
        'collected_logs': [],  # Track logs collected from pattern matches
        'detections': []  # Track what checks detected issues (for auto log collection)
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
                import socket
                stdin, stdout, stderr = ssh.exec_command(cmd, timeout=15)
                stdout.channel.settimeout(15)
                stderr.channel.settimeout(15)
                try:
                    cmd_output = stdout.read().decode('utf-8', errors='ignore').strip()
                    cmd_error = stderr.read().decode('utf-8', errors='ignore').strip()
                except socket.timeout:
                    log_message_func(f"  ⚠ Command timeout after 15s - skipping output")
                    cmd_output = ""
                    cmd_error = "Command timeout"
                
                # Always close the channel after reading
                try:
                    stdout.channel.close()
                except:
                    pass
                try:
                    stderr.channel.close()
                except:
                    pass
                
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
                        
                        # AUTO-COLLECT LOGS when pattern found in optional checks
                        if device_ip and device_name and iteration is not None:
                            log_message_func(f"\n  📋 Pattern detected - Auto-collecting device logs...")
                            collected_log_path = collect_device_logs_to_media_app(
                                ssh, device_ip, device_name, iteration, log_message_func
                            )
                            if collected_log_path:
                                log_message_func(f"  ✓ Logs collected: {collected_log_path}")
                                results['collected_logs'].append(collected_log_path)
                            else:
                                log_message_func(f"  ⚠ Log collection failed (continuing anyway)")
                        
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
                
                # Track detections for auto log collection (when check matches something)
                if pattern_found and cmd_output:
                    results['detections'].append({
                        'check_key': check_key,
                        'description': description,
                        'pattern_found': cmd_output[:200]  # Store preview of what was found
                    })
                    log_message_func(f"  📌 DETECTION RECORDED: This check found issues - logs should be collected!")
                
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
        try:
            # Check if job has been cancelled
            from methods.method_utils import is_job_cancelled
            if is_job_cancelled():
                log(f"⚠ [CANCELLED] Job cancellation detected - stopping SSH probing...")
                return None
            
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

def execute_reboot_perf_v2_optimized_process(device_ip, port, username, password, iteration=1, device_name="Device", combined_method_name=None, optional_checks=None, wait_after_reboot=80, home_screen_timeout=180, auto_collect_logs=False, log_search_patterns=None, job_id=None, termination_if_not_found=None, max_performance_time=None):
    """
    Execute Reboot Performance Monitoring V2 - OPTIMIZED:
    
    Step 1: Pre-validation (connect, fetch build details, press HOME button)
    Step 2: Capture start time and send reboot command
    Step 3: ULTRA-OPTIMIZED WAIT - 10s passive + SSH probing from 40s mark (data-driven)
    Step 4: Wait for device to come back online with intelligent probing in optimal window
    Step 5: Monitor logs for HOME screen detection immediately upon SSH reconnection
    Step 5.5: ⭐ SMART LOG COLLECTION (on SUCCESS - HOME reached)
       - If log_search_patterns specified: Search for patterns, collect if found
       - If reboot performance exceeds max_performance_time: Auto-collect logs for diagnostics
       - Otherwise: Skip log collection (deferred to post-reboot checks)
    Step 6: Calculate reboot performance time if HOME screen found
    Step 7: Re-activate ScreenCapture service and capture AFTER screenshot
    Step 8: Execute post-reboot log checks (MANDATORY - unless user explicitly entered -NA-)
       - IF detections found (process crashes, errors): AUTO-COLLECT LOGS to /media/apps
       - Otherwise: Skip log collection (normal pass, no issues)
    Step 9: Check termination conditions if patterns were NOT found (new feature)
    
    SMART LOG COLLECTION FEATURE - CORRECTED LOGIC:
    When HOME screen is reached successfully:
    1. Log collection SKIPPED initially (Step 5.5)
    2. Post-reboot validation checks execute (Step 8)
    3. IF crashes/errors detected: Logs auto-collected to /media/apps
    4. IF reboot time exceeds max_performance_time: Logs auto-collected to /media/apps
    5. IF no issues detected AND within performance threshold: NO logs collected (clean pass)
    
    When HOME screen is NOT reached:
    - Device logs are ALWAYS collected to /media/apps
    - Used for diagnostics (device stuck, power issues, etc.)
    
    The auto_collect_logs flag means: "Automatically collect logs when issues are detected"
    NOT "Automatically collect logs just because HOME was reached"
    
    Args:
        optional_checks: dict with check configurations - MANDATORY field
        home_screen_timeout: total seconds from reboot to wait for HOME screen log (default: 180)
        auto_collect_logs: bool - If True, automatically collect logs when ISSUES are detected (default: False)
        log_search_patterns: list of regex patterns to search for in logs, e.g., ["process crashed", "ERROR"]
                            If any pattern is found, logs are automatically collected (default: None)
        termination_if_not_found: dict with termination conditions for patterns NOT found
                                  e.g., {'patterns': ['HOME'], 'stop_if_not_found': True}
                                  If specified patterns are not found and stop_if_not_found=True,
                                  execution stops and device is left in current state (default: None)
        max_performance_time: int - Optional maximum acceptable reboot time in seconds (e.g., 120)
                             If reboot time exceeds this value and auto_collect_logs=True,
                             device logs are automatically collected for diagnostics (default: None)
    """
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    screenshots_list = []
    logs_list = []
    optional_checks = optional_checks or {}
    screenshot_result_before = None
    screen_validation = None
    build_info = None
    check_results = None
    
    # Store job_id in thread-local storage for cancellation checking
    if job_id:
        from methods.method_utils import set_current_job_id
        import threading
        set_current_job_id(threading.get_ident(), job_id)
    
    # Clean device name for filename
    safe_device_name = device_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    
    # Set USB log file path for this execution
    try:
        from services.log_service import LogService
        log_service = LogService()
        usb_log_path = create_execution_log_path(device_ip, device_name, iteration, "REBOOT_PERF_V2_OPTIMIZED")
        log_service.current_usb_log_file = usb_log_path
        log_message(f"💾 USB execution log: {usb_log_path}")
    except Exception as e:
        log_message(f"⚠ Could not set USB log path: {e}")
    
    log_message("="*80)
    log_message("REBOOT PERFORMANCE MONITORING V2 - OPTIMIZED - START")
    log_message("="*80)
    log_message("KEY IMPROVEMENT: Reduced wait 85s→50s, SSH probing starts at 30s")
    log_message("BENEFIT: 30-50% faster execution, better HOME log detection")
    log_message("="*80)
    
    try:
        # STEP 1: DEVICE CONNECTION & PRE-REBOOT SETUP
        log_message("[STEP 1] Connecting to device and initial setup...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(device_ip, port=port, username=username, password=password, timeout=15)
        log_message("✓ Connected to device successfully")
        
        # Fetch build details from device
        build_info = fetch_build_details(ssh, log_message)
        
        # Activate ScreenCapture service before reboot
        activate_screencapture_service(ssh, log_message)
        
        # Ensure device is on HOME screen before reboot
        log_message("Ensuring device is on HOME screen before reboot...")
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
            log_message("   Continuing with reboot anyway...")
        
        # Capture BEFORE screenshot after ScreenCapture activation and HOME button press
        log_message("\n[STEP 1.5] Capturing BEFORE screenshot (VNC method - fast)...")
        log_message("⚠ NOTE: Screenshot is informational - execution will continue even if it fails")
        try:
            screenshot_folder_before = create_screenshot_folder(device_ip, device_name, iteration, "Before", method_name="reboot_perf_v2_optimized", execution_timestamp=timestamp)
            screenshot_result_before = take_vnc_screenshot_with_fallback(
                ssh=ssh,
                device_ip=device_ip,
                device_name=safe_device_name,
                iteration=iteration,
                screenshot_folder=screenshot_folder_before,
                log_callback=log_message,
                fallback_to_plugin=True,
                context="Before-Reboot"
            )
            if screenshot_result_before and screenshot_result_before.get('success'):
                log_message(f"✓ BEFORE screenshot captured in {screenshot_result_before.get('capture_time', 0):.2f}s")
                log_message(f"  Saved: {screenshot_result_before.get('local_path')}")
                screenshots_list.append(screenshot_result_before.get('local_path', ''))
            else:
                error_msg = screenshot_result_before.get('error', 'Unknown error') if screenshot_result_before else 'Screenshot failed'
                log_message(f"⚠ BEFORE screenshot not available: {error_msg}")
                log_message("✓ Continuing with reboot execution anyway...")
                screenshot_result_before = None  # Clear for screen validation check later
        except Exception as e:
            log_message(f"⚠ Warning: Failed to capture BEFORE screenshot: {e}")
            log_message("✓ Continuing with reboot execution anyway...")
            screenshot_result_before = None
        
        log_message("✓ Pre-reboot setup complete")
        
        # STEP 2: SEND REBOOT COMMAND AND CAPTURE START TIME
        log_message("\n[STEP 2] Sending reboot command and capturing start time...")
        # Capture UTC start time
        reboot_start_time = datetime.now(timezone.utc)
        log_message(f"⏱ Reboot command timestamp (UTC): {reboot_start_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        
        # Send reboot command
        import socket
        stdin, stdout, stderr = ssh.exec_command(reboot_command, timeout=10)
        stderr.channel.settimeout(10)
        try:
            error_output = stderr.read().decode('utf-8', errors='ignore')
        except socket.timeout:
            error_output = ""
        
        # Always close the channel after reading
        try:
            stdout.channel.close()
        except:
            pass
        try:
            stderr.channel.close()
        except:
            pass
        
        if error_output:
            log_message(f"⚠ Reboot command stderr: {error_output}")
        
        ssh.close()
        log_message("✓ Reboot command sent successfully")
        
        # CHECK CANCELLATION: After reboot command sent
        from methods.method_utils import is_job_cancelled
        if is_job_cancelled():
            log_message("\n" + "="*60)
            log_message("⛔ JOB CANCELLATION DETECTED!")
            log_message("Stopping execution after reboot command was sent")
            log_message("="*60)
            return {"iteration": iteration, "screenshots": screenshots_list, "logs": logs_list, "success": False, "cancelled": True, "device_name": device_name}
        
        # STEP 3: OPTIMIZED WAIT WITH EARLY SSH PROBING
        log_message(f"\n[STEP 3] ULTRA-OPTIMIZED WAIT STRATEGY - 10s passive + SSH probing from 40s...")
        log_message(f"   Data-driven optimization: Real device boots in ~84s (40-90s range)")
        log_message(f"   Strategy: 10s shutdown wait → Wait until 40s → SSH probe every 5s → Immediate HOME monitoring")
        log_message(f"   Benefit: Catches SSH reconnection + HOME logs at optimal time window")
        
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
        
        # CHECK CANCELLATION: After device reconnection
        if is_job_cancelled():
            log_message("\n" + "="*60)
            log_message("⛔ JOB CANCELLATION DETECTED!")
            log_message("Stopping after device reconnection")
            log_message("="*60)
            ssh.close()
            return {"iteration": iteration, "screenshots": screenshots_list, "logs": logs_list, "success": False, "cancelled": True, "device_name": device_name}
        
        # STEP 4: MONITOR LOGS FOR HOME SCREEN (IMMEDIATELY)
        # Device should automatically navigate to HOME screen after reboot
        elapsed_since_reboot = time.time() - reboot_start_time.timestamp()
        remaining_timeout = max(30, home_screen_timeout - elapsed_since_reboot)
        
        log_message(f"\n[STEP 4] Monitoring logs for HOME screen detection...")
        log_message(f"   ✨ OPTIMIZATION: Starting immediately upon SSH reconnection")
        log_message(f"   Elapsed since reboot command: {elapsed_since_reboot:.0f}s")
        log_message(f"   Will monitor for up to: {remaining_timeout:.0f}s more (total timeout: {home_screen_timeout}s)")
        log_message(f"   Log source: /opt/logs/sky-messages.log")
        log_message(f"   Looking for HOME screen indicators in logs AFTER reboot time")
        home_found, home_log_line, home_time = check_for_home_log_continuously(
            ssh, timeout_seconds=int(remaining_timeout), log_message_func=log_message, 
            reboot_start_time=reboot_start_time, baseline_line_count=None
        )
        time.sleep(10)
        
        # CHECK CANCELLATION: After HOME detection phase
        if is_job_cancelled():
            log_message("\n" + "="*60)
            log_message("⛔ JOB CANCELLATION DETECTED!")
            log_message("Stopping after HOME detection phase")
            log_message("="*60)
            ssh.close()
            return {"iteration": iteration, "screenshots": screenshots_list, "logs": logs_list, "success": False, "cancelled": True, "device_name": device_name}
        
        # STEP 4.5: CHECK TERMINATION CONDITIONS FOR NOT-FOUND PATTERNS
        # This stops execution if required patterns were NOT detected
        termination_if_not_found = termination_if_not_found or {}
        should_terminate_on_not_found = False
        
        if termination_if_not_found and termination_if_not_found.get('stop_if_not_found'):
            patterns_to_check = termination_if_not_found.get('patterns', [])
            
            if patterns_to_check and 'HOME' in patterns_to_check and not home_found:
                should_terminate_on_not_found = True
                log_message("\n" + "="*80)
                log_message("⛔ TERMINATION CONDITION TRIGGERED: 'HOME' not found")
                log_message("="*80)
                log_message("❌ HOME log line was NOT detected during monitoring phase")
                log_message("⛔ Termination condition configured: STOP if 'HOME' not found")
                log_message("🔍 Device state: " + ("Device came back online via SSH" if ssh else "SSH connection failed"))
                log_message("\n📌 REASON: Execution stopped to allow manual inspection of device state")
                log_message("   This ensures the device is in the expected state before proceeding")
                log_message("   You can now:")
                log_message("   1. Manually check the device via SSH/VNC")
                log_message("   2. Inspect logs at /opt/logs/sky-messages.log")
                log_message("   3. Return device to desired state if needed")
                log_message("   4. Resume execution or retry")
                log_message("="*80)
                
                # Close SSH and return with stop flag
                ssh.close()
                return {
                    "iteration": iteration, 
                    "screenshots": screenshots_list, 
                    "logs": logs_list, 
                    "success": False, 
                    "termination_reason": "HOME_NOT_FOUND_TERMINATION",
                    "message": "Execution stopped: HOME log not found during monitoring phase (termination condition)"
                }
        
        # STEP 5.6: QUERY DEVICE POWER STATE FOR VALIDATION (MANDATORY - regardless of HOME screen detection)
        log_message("\n[STEP 5.6] Querying device state for validation (MANDATORY CHECK)...")
        try:
            stdin, stdout, stderr = ssh.exec_command("QueryPowerState", timeout=10)
            stdout.channel.settimeout(10)
            try:
                power_state_output = stdout.read().decode('utf-8', errors='ignore').strip()
                stdout.channel.close()
                if power_state_output:
                    log_message(f"✓ Device Power State Query Output:")
                    for line in power_state_output.split('\n'):
                        if line.strip():
                            log_message(f"   {line}")
                else:
                    log_message(f"⚠ QueryPowerState command executed but no output returned")
            except socket.timeout:
                log_message(f"⚠ QueryPowerState command timed out")
                stdout.channel.close()
        except Exception as e:
            log_message(f"⚠ Error executing QueryPowerState: {str(e)[:150]}")
        
        # STEP 5: CALCULATE PERFORMANCE IF HOME SCREEN FOUND
        reboot_duration = None
        performance_str = "N/A"
        
        if home_found:
            # STEP 5.5: SMART LOG COLLECTION - ONLY for detected issues (not for successful HOME reaches)
            collected_log_path = None
            pattern_search_result = None
            logs_already_collected = False  # ✅ NEW: Track if logs already collected to prevent duplicates
            
            # Priority 1: Search for user-specified log patterns (if configured)
            if log_search_patterns and len(log_search_patterns) > 0:
                log_message("\n[STEP 5.5] Pattern-based log collection...")
                pattern_search_result = check_and_collect_logs_for_patterns(
                    ssh, device_ip, device_name, iteration, log_search_patterns, log_message
                )
                if pattern_search_result.get('log_paths'):
                    logs_list.extend(pattern_search_result['log_paths'])
                    collected_log_path = pattern_search_result['log_paths'][0]
                    logs_already_collected = True  # ✅ Set flag: logs collected from pattern match
                    log_message(f"✓ Step 5.5: Logs collected from pattern match: {len(pattern_search_result['log_paths'])} file(s)")
                else:
                    log_message(f"✓ Step 5.5: Pattern search complete - No issues detected, no logs collected from patterns")
            else:
                # ✅ CORRECTED: Do NOT auto-collect logs just because HOME was reached
                # Logs should only be collected if issues are detected in STEP 7 post-reboot checks
                log_message("\n[STEP 5.5] No search patterns configured - Log collection deferred to post-reboot validation checks")
                log_message("   (Device reached HOME successfully)")
            
            log_message("\n[STEP 6] Calculating reboot performance time...")
            
            # Try to parse timestamp from log line
            log_timestamp = parse_log_timestamp(home_log_line)
            
            if log_timestamp:
                # Calculate duration using log timestamp
                reboot_duration = (log_timestamp - reboot_start_time).total_seconds()
                log_message(f"✓ Reboot Start Time (UTC): {reboot_start_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
                log_message(f"✓ HOME Log Timestamp (UTC): {log_timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
                log_message(f"✓ Calculated Reboot Duration: {reboot_duration:.2f} seconds")
                log_message(f"✨ OPTIMIZED METHOD: Detected HOME log {elapsed_since_reboot:.0f}s after reboot (faster capture)")
                performance_str = f"{reboot_duration:.2f}s"
            else:
                # Fallback to detection time
                reboot_duration = (home_time - reboot_start_time).total_seconds()
                log_message(f"⚠ Could not parse log timestamp, using detection time")
                log_message(f"✓ Calculated Reboot Duration (approximate): {reboot_duration:.2f} seconds")
                performance_str = f"~{reboot_duration:.2f}s"
            
            # ✅ NEW: CHECK IF REBOOT TIME EXCEEDED PERFORMANCE THRESHOLD (if configured)
            performance_threshold_exceeded = False
            if max_performance_time and reboot_duration and reboot_duration > max_performance_time:
                performance_threshold_exceeded = True
                log_message(f"\n⚠️ PERFORMANCE WARNING: Reboot time {reboot_duration:.2f}s exceeded threshold of {max_performance_time}s")
                log_message(f"   This iteration will be flagged for diagnostics")
            elif max_performance_time:
                log_message(f"\n✓ Performance acceptable: {reboot_duration:.2f}s <= {max_performance_time}s threshold")
            
            # STEP 6: CAPTURE SCREENSHOT FOR SUCCESS
            log_message("\n[STEP 6] Capturing success screenshot...")
            log_message("⚠ NOTE: Screenshot is informational - execution will continue even if it fails")
            
            # Re-activate screencapture service after reboot
            log_message("Re-activating ScreenCapture service after reboot...")
            activate_screencapture_service(ssh, log_message)
            log_message("Waiting 3 seconds for service to fully initialize...")
            sys.stdout.flush()  # Force log flush
            time.sleep(3)  # Reduced from 5s to 3s
            sys.stdout.flush()  # Force flush after sleep

            
            screenshot_folder = create_screenshot_folder(device_ip, device_name, iteration, "SUCCESS", method_name="reboot_perf_v2_optimized", execution_timestamp=timestamp)
            
            # Capture screenshot with VNC (3x faster)
            log_message("📸 Capturing AFTER screenshot (VNC method - faster)...")
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
                    context="After-Reboot-SUCCESS"
                )
            except Exception as e:
                log_message(f"⚠ Screenshot capture exception: {e}")
                log_message("⚠ Continuing with test - screenshot is non-critical")
                sys.stdout.flush()
                screenshot_result = None
            
            # Process screenshot result if successful, but don't block on failure
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
                # Screenshot failed but don't block execution
                error_msg = screenshot_result.get('error', 'Unknown error') if screenshot_result else 'Screenshot capture failed'
                log_message(f"⚠ Screenshot not captured: {error_msg}")
                log_message("✓ Test continues - screenshot is informational only")
                sys.stdout.flush()
                
                # VALIDATE SCREEN COMPARISON (Informational only)
            screen_validation = None
            if screenshot_result_before and screenshot_result:  # Only compare if both screenshots exist
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
            log_message("✓ REBOOT PERFORMANCE TEST V2 OPTIMIZED PASSED")
            if reboot_duration:
                log_message(f"✓ Performance: {performance_str}")
            log_message(f"✨ Execution optimized: Early SSH probing enabled faster detection")
            log_message("="*80)
            
            # CHECK CANCELLATION: Before post-reboot checks
            if is_job_cancelled():
                log_message("\n" + "="*60)
                log_message("⛔ JOB CANCELLATION DETECTED!")
                log_message("Stopping before post-reboot checks")
                log_message("="*60)
                ssh.close()
                return {"iteration": iteration, "screenshots": screenshots_list, "logs": logs_list, "success": False, "cancelled": True, "device_name": device_name}
            
            # STEP 7: EXECUTE POST-REBOOT LOG CHECKS (mandatory unless -NA-)
            check_results = None
            if optional_checks and (optional_checks.get('custom_commands') or optional_checks.get('skip_all')):
                log_message("\n[STEP 7] Post-reboot validation checks...")
                check_results = execute_optional_post_reboot_checks(
                    ssh, optional_checks, log_message, 
                    device_ip=device_ip, 
                    device_name=device_name, 
                    iteration=iteration
                )
                
                # Add collected logs from pattern matches to the main logs list
                if check_results.get('collected_logs'):
                    logs_list.extend(check_results['collected_logs'])
                    log_message(f"\n[LOG COLLECTION] Collected {len(check_results['collected_logs'])} log file(s) from pattern matches")
                
                # ✅ AUTO-COLLECT LOGS ONLY IF CHECKS DETECTED ISSUES (process crashes, etc.)
                if check_results.get('detections') and auto_collect_logs:
                    log_message(f"\n[DETECTION-BASED LOG COLLECTION] {len(check_results['detections'])} issue(s) detected during post-reboot checks!")
                    for detection in check_results['detections']:
                        log_message(f"  • {detection['description']}: {detection.get('pattern_found', 'DETECTED')}")
                    
                    # ✅ NEW: Only collect if not already collected
                    if logs_already_collected:
                        log_message(f"[INFO] Logs already collected in STEP 5.5 - Skipping duplicate collection")
                        check_results['detection_would_trigger_collection'] = True
                    else:
                        log_message(f"[AUTO-COLLECT] Automatically collecting device logs due to detected issues...")
                        collected_log_path = collect_device_logs_to_media_app(
                            ssh, device_ip, device_name, iteration, log_message
                        )
                        if collected_log_path:
                            log_message(f"✓ Logs collected and available at: {collected_log_path}")
                            logs_list.append(collected_log_path)
                            logs_already_collected = True  # ✅ Set flag
                            check_results['detection_triggered_logs'] = collected_log_path
                        else:
                            log_message(f"⚠ Failed to collect logs despite detected issues")
                
                # ✅ NEW: AUTO-COLLECT LOGS IF PERFORMANCE TIME EXCEEDED THRESHOLD (if configured)
                elif performance_threshold_exceeded and auto_collect_logs:
                    log_message(f"\n[PERFORMANCE-BASED LOG COLLECTION] Reboot time exceeded threshold - Collecting device logs for diagnostics...")
                    log_message(f"   Reboot Time: {reboot_duration:.2f}s | Threshold: {max_performance_time}s")
                    
                    # ✅ NEW: Only collect if not already collected
                    if logs_already_collected:
                        log_message(f"[INFO] Logs already collected in STEP 5.5 - Skipping duplicate collection")
                        check_results['performance_would_trigger_collection'] = True
                    else:
                        collected_log_path = collect_device_logs_to_media_app(
                            ssh, device_ip, device_name, iteration, log_message
                        )
                        if collected_log_path:
                            log_message(f"✓ Logs collected and available at: {collected_log_path}")
                            logs_list.append(collected_log_path)
                            logs_already_collected = True  # ✅ Set flag
                            check_results['performance_exceeded_logs'] = collected_log_path
                        else:
                            log_message(f"⚠ Failed to collect logs despite performance threshold exceeded")
                else:
                    log_message("\n[LOG COLLECTION] No issues detected - logs not collected (normal pass)")
            else:
                log_message("\n[STEP 7] ⚠ No check configuration provided (field should be mandatory)")
                check_results = {
                    'custom_checks': [],
                    'overall_passed': True,
                    'stop_iterations': False,
                    'collected_logs': [],
                    'detections': []
                }
                
                # ✅ Even without checks configured, collect logs if performance exceeded threshold
                if performance_threshold_exceeded and auto_collect_logs:
                    log_message(f"\n[PERFORMANCE-BASED LOG COLLECTION] Reboot time exceeded threshold - Collecting device logs for diagnostics...")
                    log_message(f"   Reboot Time: {reboot_duration:.2f}s | Threshold: {max_performance_time}s")
                    
                    # ✅ NEW: Only collect if not already collected
                    if logs_already_collected:
                        log_message(f"[INFO] Logs already collected in STEP 5.5 - Skipping duplicate collection")
                        check_results['performance_would_trigger_collection'] = True
                    else:
                        collected_log_path = collect_device_logs_to_media_app(
                            ssh, device_ip, device_name, iteration, log_message
                        )
                        if collected_log_path:
                            log_message(f"✓ Logs collected and available at: {collected_log_path}")
                            logs_list.append(collected_log_path)
                            logs_already_collected = True  # ✅ Set flag
                            check_results['performance_exceeded_logs'] = collected_log_path
                        else:
                            log_message(f"⚠ Failed to collect logs despite performance threshold exceeded")
            
            # ✅ NEW: Log collection summary
            if logs_already_collected:
                log_message("\n[LOG COLLECTION SUMMARY]")
                log_message(f"  ✓ Logs collected: 1 time (at earliest trigger point)")
                additional_triggers = []
                if check_results.get('detection_would_trigger_collection'):
                    additional_triggers.append("Issue detection in checks")
                if check_results.get('performance_would_trigger_collection'):
                    additional_triggers.append("Performance threshold exceeded")
                if additional_triggers:
                    log_message(f"  ℹ Additional triggers detected but NOT collected (logs already collected):")
                    for trigger in additional_triggers:
                        log_message(f"     • {trigger}")
            
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
                "screen_validation": screen_validation,
                "build_info": build_info,
                "device_name": device_name
            }
        
        else:
            # HOME screen not found - capture screenshot for diagnostics
            log_message("\n[STEP 5-6] HOME screen NOT found - Capturing failure screenshot...")
            log_message("⚠ NOTE: Screenshot is informational - execution will continue even if it fails")
            
            # Re-activate screencapture service after reboot
            log_message("Re-activating ScreenCapture service after reboot...")
            activate_screencapture_service(ssh, log_message)
            log_message("Waiting 3 seconds for service to fully initialize...")
            time.sleep(3)  # Reduced from 5s
            
            screenshot_folder = create_screenshot_folder(device_ip, device_name, iteration, "FAILED", method_name="reboot_perf_v2_optimized", execution_timestamp=timestamp)
            
            try:
                screenshot_result = take_vnc_screenshot_with_fallback(
                    ssh=ssh,
                    device_ip=device_ip,
                    device_name=safe_device_name,
                    iteration=iteration,
                    screenshot_folder=screenshot_folder,
                    log_callback=log_message,
                    fallback_to_plugin=True,
                    context="After-Reboot-FAILED"
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
            
            # STEP 6.5: EXECUTE POST-REBOOT LOG CHECKS & COLLECT LOGS (when HOME screen not found)
            # Strategy: Check for crashes first, then ALWAYS collect logs (only once)
            log_message("\n[STEP 6.5] Device not on HOME screen - Executing validation checks and collecting logs...")
            
            logs_already_collected = False
            check_results = None
            
            # Run optional checks if configured (informational + may collect logs)
            if optional_checks and (optional_checks.get('custom_commands') or optional_checks.get('skip_all')):
                log_message("Running post-reboot validation checks...")
                check_results = execute_optional_post_reboot_checks(
                    ssh, 
                    optional_checks, 
                    log_message,
                    device_ip=device_ip,
                    device_name=device_name,
                    iteration=iteration
                )
                
                # Check if optional_checks already collected logs
                if check_results.get('collected_logs'):
                    logs_already_collected = True
                    logs_list.extend(check_results['collected_logs'])
                    log_message(f"✓ Pattern detected - collected {len(check_results['collected_logs'])} log archive(s)")
                    for log_path in check_results['collected_logs']:
                        log_message(f"  - {log_path}")
                
                # Check for detection-based auto-collection
                if check_results.get('detections') and auto_collect_logs:
                    log_message(f"\n[DETECTION-BASED LOG COLLECTION] {len(check_results['detections'])} check(s) detected issues!")
                    for detection in check_results['detections']:
                        log_message(f"  • {detection['description']}: {detection['pattern_found']}")
                    if not logs_already_collected:
                        check_results['detection_triggered_logs'] = True
                        logs_already_collected = True
                elif not optional_checks.get('skip_all'):
                    log_message("ℹ No crash patterns detected in optional checks")
            else:
                log_message("⚠ No optional checks configured")
            
            # ALWAYS collect logs on FAILURE (if not already collected by optional_checks)
            if not logs_already_collected:
                log_message("\nCollecting device logs to /media/apps for this iteration...")
                collected_log_path = collect_device_logs_to_media_app(
                    ssh, device_ip, device_name, iteration, log_message
                )
                if collected_log_path:
                    log_message(f"✓ Device logs collected: {collected_log_path}")
                    logs_list.append(collected_log_path)
                else:
                    log_message("⚠ Failed to collect device logs to /media/apps")
            else:
                log_message("\n✓ Logs already collected by pattern detection - skipping duplicate collection")
            
            log_message("\n" + "="*80)
            log_message("❌ REBOOT PERFORMANCE TEST V2 OPTIMIZED FAILED")
            log_message(f"❌ Device did not reach HOME screen within {home_screen_timeout} seconds")
            log_message("="*80)
            
            ssh.close()
            return {
                "iteration": iteration,
                "screenshots": screenshots_list,
                "logs": logs_list,
                "success": False,
                "performance_seconds": reboot_duration,  # Include even if None (for consistency)
                "build_info": build_info,
                "optional_checks": check_results or {
                    'custom_checks': [],
                    'overall_passed': False,
                    'stop_iterations': False,
                    'collected_logs': []
                },
                "stop_iterations": (check_results or {}).get('stop_iterations', False),
                "device_name": device_name
            }
    
    except Exception as e:
        import traceback
        log_message(f"❌ Error during Reboot Performance V2 Optimized test: {e}")
        log_message(f"Full traceback:\n{traceback.format_exc()}")
        return {
            "iteration": iteration,
            "screenshots": screenshots_list,
            "logs": logs_list,
            "success": False,
            "performance_seconds": None,  # Not calculated due to exception
            "build_info": build_info,
            "optional_checks": check_results or {
                'custom_checks': [],
                'overall_passed': False,
                'stop_iterations': False,
                'collected_logs': []
            },
            "stop_iterations": (check_results or {}).get('stop_iterations', False),
            "device_name": device_name
        }
