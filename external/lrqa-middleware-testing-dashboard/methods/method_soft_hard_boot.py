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

import os
import sys
import time
import json
import re
import glob
import shlex
import paramiko
from methods.method_utils import get_execution_ssh_client
import socket
import subprocess
from datetime import datetime, timezone
from PIL import Image, ImageStat
from tools.screen.screen_validator_lightweight import LightweightScreenValidator

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
from methods.method_capture_current_screen import extract_text_from_local_image

# Reuse the /media/apps log archiving used by Reboot Performance V2 Optimized.
# Imported lazily at call sites to avoid a circular import with services/test_execution_service.

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
                        if reboot_start_time:
                            candidate_timestamp = parse_log_timestamp(log_output)
                            if not candidate_timestamp or candidate_timestamp <= reboot_start_time:
                                log_message_func(f"  ⏱ Pattern {idx} only matched a stale or unparseable HOME entry")
                                log_output = ""
                                continue
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

def check_process_crash(ssh, log_message_func, baseline_line_count=0):
    """
    Check /opt/logs/core_log.txt for process crash entries

    Returns: dict with 'crash_found' (bool) and 'matched_lines' (list)
    """
    result = {'crash_found': False, 'matched_lines': []}

    crash_pattern = '.*process crash.*'

    try:
        log_message_func("\n[CRASH CHECK] Searching /opt/logs/core_log.txt for process crashes...")
        start_line = max(1, int(baseline_line_count or 0) + 1)
        crash_cmd = (
            "current=$(wc -l < /opt/logs/core_log.txt 2>/dev/null || echo 0); "
            f"if [ \"$current\" -ge {start_line - 1} ]; then tail -n +{start_line} /opt/logs/core_log.txt; "
            "else cat /opt/logs/core_log.txt; fi | "
            f'grep -i "{crash_pattern}" | tail -10'
        )
        stdin, stdout, stderr = ssh.exec_command(crash_cmd, timeout=20)
        crash_output = stdout.read().decode('utf-8', errors='ignore').strip()
        stdout.channel.close()

        if crash_output:
            result['crash_found'] = True
            result['matched_lines'] = [line for line in crash_output.split('\n') if line.strip()]
            log_message_func(f"❌ Process crash detected ({len(result['matched_lines'])} matching line(s)):")
            for line in result['matched_lines'][:5]:
                log_message_func(f"   {line[:200]}")
        else:
            log_message_func("✓ No process crash entries found in core_log.txt")
    except Exception as e:
        log_message_func(f"⚠ Error checking core_log.txt for crashes: {str(e)[:150]}")

    return result

def check_custom_log_commands(ssh, commands, log_message_func):
    """Execute user-provided log search commands and treat non-empty output as a match."""
    results = []
    commands = [str(command).strip() for command in (commands or []) if str(command).strip()]

    if not commands:
        return {'overall_passed': True, 'any_matched': False, 'checks': results}

    log_message_func(f"\n[CUSTOM LOG VALIDATION] Executing {len(commands)} log search command(s)...")
    for index, command in enumerate(commands, 1):
        matched_line = ''
        error = ''
        try:
            stdin, stdout, stderr = ssh.exec_command(command, timeout=20)
            stdout.channel.settimeout(20)
            stderr.channel.settimeout(20)
            matched_line = stdout.read().decode('utf-8', errors='ignore').strip()
            error = stderr.read().decode('utf-8', errors='ignore').strip()
            stdout.channel.close()
            stderr.channel.close()
        except Exception as exc:
            error = str(exc)

        matched = bool(matched_line)
        results.append({
            'command': command,
            'matched': matched,
            'matched_line': matched_line[:500],
            'error': error[:500]
        })
        if matched:
            log_message_func(f"  ✓ [{index}/{len(commands)}] Command matched: {command}")
            log_message_func(f"    {matched_line[:200]}")
        else:
            log_message_func(f"  ℹ [{index}/{len(commands)}] No match; device log collection not required: {command}")
            if error:
                log_message_func(f"    Error: {error[:200]}")

    return {
        'overall_passed': True,
        'any_matched': any(item['matched'] for item in results),
        'checks': results
    }

def execute_device_command(ssh, command, log_message_func, timeout=15):
    """Execute a device command and return its output, error, and exit code."""
    try:
        stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
        stdout.channel.settimeout(timeout)
        stderr.channel.settimeout(timeout)
        output = stdout.read().decode('utf-8', errors='ignore').strip()
        error = stderr.read().decode('utf-8', errors='ignore').strip()
        exit_code = stdout.channel.recv_exit_status()
        stdout.channel.close()
        stderr.channel.close()
        return output, error, exit_code
    except Exception as exc:
        log_message_func(f"⚠ Command failed ({command}): {str(exc)[:150]}")
        return '', str(exc), -1

def query_device_power_state(ssh, log_message_func):
    """Return ON/STANDBY when QueryPowerState provides a recognized state."""
    output, error, exit_code = execute_device_command(
        ssh, "QueryPowerState", log_message_func, timeout=10
    )
    if output:
        log_message_func(f"   QueryPowerState: {output.replace(chr(10), ' | ')}")
    elif error:
        log_message_func(f"   QueryPowerState error: {error[:150]}")
    state_match = re.search(r'\b(ON|STANDBY)\b', output, re.IGNORECASE)
    return state_match.group(1).upper() if state_match else None

def collect_iteration_failure_diagnostics(
    ssh, device_ip, device_name, iteration, optional_checks, core_log_baseline,
    log_message_func, logs_list, failure_reasons, boot_type
):
    """Run all failure checks and collect device logs at most once for an iteration."""
    crash_check = check_process_crash(ssh, log_message_func, core_log_baseline)
    if crash_check.get('crash_found'):
        failure_reasons.append('Process Crash Detected')

    custom_log_commands = optional_checks.get('custom_log_commands')
    if custom_log_commands is None:
        custom_log_commands = [
            f"grep -R -F -m 1 -- {shlex.quote(pattern)} /opt/logs 2>/dev/null | head -1"
            for pattern in optional_checks.get('custom_log_patterns', [])
            if str(pattern).strip()
        ]
    custom_log_results = check_custom_log_commands(ssh, custom_log_commands, log_message_func)
    matched_custom_logs = [
        check for check in custom_log_results.get('checks', []) if check.get('matched')
    ]
    if matched_custom_logs:
        failure_reasons.append(f"Custom Log Pattern Matched ({len(matched_custom_logs)})")

    if failure_reasons:
        reasons = '; '.join(dict.fromkeys(failure_reasons))
        log_message_func(f"\n[LOG COLLECTION] {reasons} ({boot_type} boot)")
        from methods.method_reboot_perf_v2_optimized import collect_device_logs_to_media_app
        collected_log_path = collect_device_logs_to_media_app(
            ssh, device_ip, device_name, iteration, log_message_func
        )
        if collected_log_path:
            log_message_func(f"✓ Device logs collected: {collected_log_path}")
            logs_list.append(collected_log_path)
        else:
            log_message_func("⚠ Failed to collect device logs to /media/apps")

    return crash_check, custom_log_results

# Static ROIs shared by HOME layouts (logo + apps row); avoids the rotating hero
# carousel and clock so matching survives promo content and time changes.
HOME_SCREEN_KEY_REGIONS = [
    {'name': 'top_left_logo', 'roi': (0, 0, 400, 140)},
    {'name': 'bottom_apps_row', 'roi': (0, 860, 1920, 1080)},
]

def validate_soft_boot_home_screen(screenshot_path, log_message_func):
    """Validate a pre-SOFT-boot screenshot against available HomeScreen references."""
    reference_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reference_screens')
    references = sorted(glob.glob(os.path.join(reference_dir, '*_HomeScreen.png')))
    if not references:
        message = f"No *_HomeScreen.png reference found in {reference_dir}"
        log_message_func(f"❌ {message}")
        return {'is_match': False, 'error': message}

    validator = LightweightScreenValidator(reference_dir=reference_dir)
    best_result = None
    for reference_path in references:
        result = validator.validate_against_reference_layout(
            screenshot_path, reference_path, key_regions=HOME_SCREEN_KEY_REGIONS, threshold=0.55
        )
        result['reference'] = reference_path
        if best_result is None or result.get('confidence', 0) > best_result.get('confidence', 0):
            best_result = result
        if result.get('is_match'):
            log_message_func(f"✓ HOME screen image matched: {os.path.basename(reference_path)}")
            return result

    log_message_func("❌ Current screen did not match any *_HomeScreen.png reference")
    return best_result or {'is_match': False, 'error': 'HOME screen comparison failed'}


def is_black_screen(screenshot_path, max_mean_intensity=8, max_stddev=12):
    """Detect a black/near-black frame even when reference matching picks an unrelated screen."""
    if not screenshot_path or not os.path.isfile(screenshot_path):
        return False
    try:
        with Image.open(screenshot_path) as image:
            stats = ImageStat.Stat(image.convert('RGB'))
        return max(stats.mean) <= max_mean_intensity and max(stats.stddev) <= max_stddev
    except Exception:
        return False

def validate_settings_screen(screenshot_path, log_message_func, language='en'):
    """Validate the Settings screenshot against references for the detected UI language."""
    reference_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reference_screens')
    if language == 'de':
        references = sorted(set(
            glob.glob(os.path.join(reference_dir, '*DE*SettingScreen.png')) +
            glob.glob(os.path.join(reference_dir, '*DE*SettingsScreen.png')) +
            glob.glob(os.path.join(reference_dir, '*German*SettingScreen.png')) +
            glob.glob(os.path.join(reference_dir, '*German*SettingsScreen.png')) +
            glob.glob(os.path.join(reference_dir, '*Einstellung*Screen.png'))
        ))
        if not references:
            log_message_func("✓ German Settings screen confirmed by OCR; no German visual reference is configured")
            return {'is_match': True, 'validation_method': 'german_settings_ocr'}
    else:
        references = sorted(set(
            glob.glob(os.path.join(reference_dir, '*SettingScreen.png')) +
            glob.glob(os.path.join(reference_dir, '*SettingsScreen.png'))
        ))
        references = [
            path for path in references
            if not re.search(r'(^|[_-])(DE|German)([_-]|$)', os.path.basename(path), re.IGNORECASE)
        ]
    if not references:
        message = f"No *SettingScreen.png/*SettingsScreen.png reference found in {reference_dir}"
        log_message_func(f"❌ {message}")
        return {'is_match': False, 'error': message}

    validator = LightweightScreenValidator(reference_dir=reference_dir)
    best_result = None
    for reference_path in references:
        result = validator.validate_against_reference_layout(
            screenshot_path,
            reference_path,
            key_regions=[{'name': 'settings_screen', 'roi': (0, 0, 1920, 1080)}],
            threshold=0.55
        )
        result['reference'] = reference_path
        if best_result is None or result.get('confidence', 0) > best_result.get('confidence', 0):
            best_result = result
        if result.get('is_match'):
            log_message_func(f"✓ Settings screen validation passed (matched {os.path.basename(reference_path)})")
            return result

    log_message_func(
        "❌ Settings screen validation failed against all references: "
        f"best confidence={best_result.get('confidence', 0):.2%} "
        f"({os.path.basename(best_result.get('reference', ''))})"
    )
    return best_result or {'is_match': False, 'error': 'Settings screen comparison failed'}


def validate_restart_screen(screenshot_path, log_message_func, language='en'):
    """Validate the selected Restart screen when a reference exists for its language."""
    reference_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reference_screens')
    if language == 'de':
        references = sorted(set(
            glob.glob(os.path.join(reference_dir, '*DE*RestartScreen.png')) +
            glob.glob(os.path.join(reference_dir, '*German*RestartScreen.png'))
        ))
    else:
        references = sorted(
            path for path in glob.glob(os.path.join(reference_dir, '*RestartScreen.png'))
            if not re.search(r'(^|[_-])(DE|German)([_-]|$)', os.path.basename(path), re.IGNORECASE)
        )

    if not references:
        log_message_func(f"✓ Restart screen confirmed by OCR ({language}); no matching visual reference is configured")
        return {'is_match': True, 'validation_method': 'restart_ocr'}

    validator = LightweightScreenValidator(reference_dir=reference_dir)
    best_result = None
    for reference_path in references:
        result = validator.validate_against_reference_layout(
            screenshot_path,
            reference_path,
            key_regions=[{'name': 'restart_screen', 'roi': (0, 0, 1920, 1080)}],
            threshold=0.55
        )
        result['reference'] = reference_path
        if best_result is None or result.get('confidence', 0) > best_result.get('confidence', 0):
            best_result = result
        if result.get('is_match'):
            log_message_func(f"✓ Restart screen visually matched: {os.path.basename(reference_path)}")
            return result

    log_message_func(
        "❌ Restart screen visual validation failed against all matching references: "
        f"best confidence={best_result.get('confidence', 0):.2%} "
        f"({os.path.basename(best_result.get('reference', ''))})"
    )
    return best_result or {'is_match': False, 'error': 'Restart screen comparison failed'}

DEFAULT_SOFT_BOOT_NAVIGATION_KEYS = [
    "DOWN", "DOWN", "ENTER", "DOWN", "DOWN", "ENTER", "ENTER"
]

def _recover_to_home_before_retry(ssh, log_message_func):
    """Press HOME, confirm a fresh HOME log line, and log power state before retrying Settings navigation."""
    try:
        log_message_func("\n[SOFT BOOT RETRY] Pressing HOME to reset device before retrying Settings navigation...")
        home_key_time = datetime.now(timezone.utc)
        stdin, stdout, stderr = ssh.exec_command("timeout 5 keySimulator -khome || true", timeout=8)
        stdout.channel.settimeout(8)
        try:
            stdout.read(1024)
        except socket.timeout:
            pass
        finally:
            stdout.channel.close()
            stderr.channel.close()
        log_message_func("  ✓ HOME key sent")
        log_message_func("  ⏱ Waiting 3 seconds for HOME to settle...")
        time.sleep(3)

        log_message_func("  Validating HOME log line before retry...")
        home_found, _, _ = check_for_home_log_continuously(
            ssh, timeout_seconds=15, log_message_func=log_message_func,
            reboot_start_time=home_key_time
        )
        if home_found:
            log_message_func("  ✓ HOME screen log confirmed before retry")
        else:
            log_message_func("  ⚠ HOME screen log not confirmed within 15s before retry")

        power_state = query_device_power_state(ssh, log_message_func)
        log_message_func(f"  Power state before retry: {power_state or 'UNKNOWN'}")

        return home_found
    except Exception as exc:
        log_message_func(f"  ⚠ Error while recovering to HOME before retry: {str(exc)[:150]}")
        return False


# Retry the selected language's navigation once if either localized OCR check fails.
RETRYABLE_SETTINGS_NAV_FAILURES = {'settings_ocr', 'restart_ocr'}

def launch_settings_and_navigate_to_restart(
    ssh, log_message_func, boot_start_time=None, navigation_keys=None,
    device_ip=None, device_name="Device", iteration=1, screenshots_dir=None,
    captured_screenshots=None, max_attempts=2, language='en'
):
    """
    Launch Settings with the selected device language and navigate to the restart option.
    On retry, reuses the same language-specific voice command and navigation keys.

    Navigation keys are user-provided (in order) to reach "Restart device" under
    Settings > System Management > Reset & updates. Falls back to the default
    sequence (DOWN, DOWN, ENTER, DOWN, DOWN, ENTER, ENTER) when not supplied.

    Args:
        ssh: SSH connection object
        log_message_func: logging function
        boot_start_time: datetime to track when boot sequence started (updated to last key press time)
        navigation_keys: list of key names (e.g. ['DOWN', 'DOWN', 'ENTER', ...]) to send in order
        device_ip: Device IP used for the post-voice-command screenshot.
        device_name: Device name used for the post-voice-command screenshot.
        iteration: Current iteration number.
        screenshots_dir: Optional per-iteration screenshot folder.
        language: 'en' for English or 'de' for German device UI.
        captured_screenshots: list the caller wants populated with any Settings/Restart
            screenshots taken here, so they end up in the job's saved screenshots
            even when this function later returns None (validation failure).
        max_attempts: Total navigation attempts before giving up (default 2, i.e. one retry).

    Returns: datetime of when the last key press was sent (for performance calculation)
    """
    if captured_screenshots is None:
        captured_screenshots = []

    language = 'de' if str(language).strip().lower() in ('de', 'german') else 'en'
    settings_voice_command = 'Einstellungen' if language == 'de' else 'SETTINGS'

    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            log_message_func(
                f"\n[SOFT BOOT RETRY] Attempt {attempt}/{max_attempts}: retrying Settings navigation "
                f"with voice command '{settings_voice_command}' "
                f"after previous OCR validation failure..."
            )
            _recover_to_home_before_retry(ssh, log_message_func)

        last_key_time, failure_reason = _navigate_settings_to_restart_once(
            ssh, log_message_func, navigation_keys=navigation_keys,
            device_ip=device_ip, device_name=device_name, iteration=iteration,
            screenshots_dir=screenshots_dir, captured_screenshots=captured_screenshots,
            settings_voice_command=settings_voice_command, settings_language=language
        )
        if last_key_time:
            return last_key_time

        if failure_reason not in RETRYABLE_SETTINGS_NAV_FAILURES:
            log_message_func(
                f"❌ SOFT BOOT navigation failed with non-retryable reason ({failure_reason}) - stopping"
            )
            return None

        if attempt == max_attempts:
            log_message_func(
                f"❌ SOFT BOOT navigation failed after {max_attempts} attempt(s) - giving up"
            )
            return None

    return None

def _navigate_settings_to_restart_once(
    ssh, log_message_func, navigation_keys=None,
    device_ip=None, device_name="Device", iteration=1, screenshots_dir=None,
    captured_screenshots=None, settings_voice_command="SETTINGS", settings_language='en'
):
    """Single Settings-navigation attempt. Returns (last_key_time_or_None, failure_reason_or_None)."""
    if captured_screenshots is None:
        captured_screenshots = []
    try:
        # Reset focus to HOME before launching Settings so voice navigation starts clean
        log_message_func(f"\n[SOFT BOOT] Pressing HOME before launching Settings...")
        try:
            home_cmd = "timeout 5 keySimulator -khome || true"
            stdin, stdout, stderr = ssh.exec_command(home_cmd, timeout=8)
            stdout.channel.settimeout(8)
            try:
                home_response = stdout.read(1024).decode('utf-8', errors='ignore')
            except socket.timeout:
                home_response = ""
            finally:
                stdout.channel.close()
                stderr.channel.close()
            log_message_func(f"  ✓ HOME key sent")
            if home_response:
                log_message_func(f"    Response: {home_response[:100]}")
            log_message_func(f"  ⏱ Waiting 3 seconds for HOME to settle...")
            time.sleep(3)
        except Exception as home_err:
            log_message_func(f"  ⚠ Could not send HOME key before Settings launch: {str(home_err)[:150]}")

        log_message_func(f"\n[SOFT BOOT] Launching Settings app via Voice curl...")
        
        # Launch Settings using voice curl with retry logic
        launch_payload = json.dumps({
            "jsonrpc": "2.0",
            "id": "3",
            "method": "org.rdk.VoiceControl.1.voiceSessionByText",
            "params": {"transcription": settings_voice_command}
        })
        launch_cmd = (
            "curl --header 'Content-Type: application/json' --request POST --silent "
            f"-d {shlex.quote(launch_payload)} http://127.0.0.1:9998/jsonrpc"
        )
        
        max_launch_attempts = 3
        launch_success = False
        
        for attempt in range(1, max_launch_attempts + 1):
            try:
                log_message_func(
                    f"  [Attempt {attempt}/{max_launch_attempts}] Sending voice command "
                    f"'{settings_voice_command}' to launch Settings..."
                )
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
            return None, 'voice_launch_failed'
        
        log_message_func("✓ Settings app launch command sent successfully")
        log_message_func("   Waiting 10 seconds before validating the Settings screen...")
        time.sleep(10)

        settings_screenshot = None
        if device_ip:
            screenshot_folder = screenshots_dir or create_screenshot_folder(
                device_ip, device_name, iteration, "Settings",
                method_name="soft_hard_boot_soft"
            )
            try:
                settings_screenshot = take_vnc_screenshot_with_fallback(
                    ssh=ssh,
                    device_ip=device_ip,
                    device_name=device_name,
                    iteration=iteration,
                    screenshot_folder=screenshot_folder,
                    log_callback=log_message_func,
                    fallback_to_plugin=True,
                    context="SOFT_SETTINGS_AFTER_VOICE"
                )
            except Exception as screenshot_error:
                log_message_func(f"❌ Settings screen capture failed: {screenshot_error}")

        if not settings_screenshot or not settings_screenshot.get('success'):
            log_message_func("❌ SOFT BOOT stopped: Settings screen screenshot is unavailable")
            return None, 'settings_screenshot_unavailable'

        if settings_screenshot.get('local_path'):
            captured_screenshots.append(settings_screenshot['local_path'])
        log_message_func(
            f"✓ Settings screen screenshot saved: {settings_screenshot.get('local_path', 'N/A')}"
        )
        extracted_settings_text = extract_text_from_local_image(
            settings_screenshot.get('local_path'), log_callback=log_message_func
        )
        expected_settings_text = r'\bBild\s+und\s+Ton\b' if settings_language == 'de' else r'\bPicture\s+and\s+Sound\b'
        settings_label = 'Bild und Ton' if settings_language == 'de' else 'Picture and Sound'
        if not re.search(expected_settings_text, extracted_settings_text, re.IGNORECASE):
            log_message_func(
                "❌ SOFT BOOT stopped: OCR text from the Settings screenshot "
                f"does not contain the expected '{settings_label}' label for language '{settings_language}'"
            )
            return None, 'settings_ocr'
        log_message_func(f"✓ OCR validation passed: extracted text contains '{settings_label}' ({settings_language})")
        settings_validation = validate_settings_screen(
            settings_screenshot.get('local_path'), log_message_func, language=settings_language
        )
        if not settings_validation.get('is_match'):
            log_message_func("❌ SOFT BOOT stopped: visible screen is not Settings")
            return None, 'settings_visual'
        
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
        
        # Use user-provided navigation keys, falling back to the default sequence
        key_sequence = [str(key).strip().upper() for key in (navigation_keys or []) if str(key).strip()]
        if not key_sequence:
            key_sequence = list(DEFAULT_SOFT_BOOT_NAVIGATION_KEYS)

        log_message_func(f"\n[SOFT BOOT] Sending navigation keys (10s wait per key press for device response)...")
        log_message_func(f"   Path: Settings > System Management > Reset & updates > Restart device")
        log_message_func(f"   Keys: {', '.join(key_sequence)}")
        
        last_key_time = None
        total_keys = len(key_sequence)
        keys_sent_successfully = 0
        
        for key_count, key_name in enumerate(key_sequence, 1):
            is_last_key = key_count == total_keys

            if is_last_key:
                if key_name != "ENTER":
                    log_message_func(
                        f"❌ SOFT BOOT stopped: final navigation key must be ENTER, got {key_name}"
                    )
                    return None, 'invalid_key_sequence'

                log_message_func(
                    "\n[SOFT BOOT] Capturing screen before final ENTER to validate Restart device..."
                )
                restart_screenshot = None
                try:
                    restart_screenshot = take_vnc_screenshot_with_fallback(
                        ssh=ssh,
                        device_ip=device_ip,
                        device_name=device_name,
                        iteration=iteration,
                        screenshot_folder=screenshot_folder,
                        log_callback=log_message_func,
                        fallback_to_plugin=True,
                        context="SOFT_RESTART_DEVICE_BEFORE_ENTER"
                    )
                except Exception as screenshot_error:
                    log_message_func(
                        f"❌ Restart device screen capture failed: {screenshot_error}"
                    )

                if not restart_screenshot or not restart_screenshot.get('success'):
                    log_message_func(
                        "❌ SOFT BOOT stopped: Restart device screenshot is unavailable"
                    )
                    return None, 'restart_screenshot_unavailable'

                if restart_screenshot.get('local_path'):
                    captured_screenshots.append(restart_screenshot['local_path'])

                restart_text = extract_text_from_local_image(
                    restart_screenshot.get('local_path'), log_callback=log_message_func
                )
                expected_restart_text = r'\bNeustart\b' if settings_language == 'de' else r'\bRestart\s+device\b'
                expected_restart_label = 'Neustart' if settings_language == 'de' else 'Restart device'
                if not re.search(expected_restart_text, restart_text, re.IGNORECASE):
                    log_message_func(
                        f"❌ SOFT BOOT stopped: OCR text does not contain '{expected_restart_label}'"
                    )
                    return None, 'restart_ocr'
                log_message_func(
                    f"✓ OCR validation passed: extracted text contains '{expected_restart_label}'"
                )
                restart_validation = validate_restart_screen(
                    restart_screenshot.get('local_path'), log_message_func,
                    language=settings_language
                )
                if not restart_validation.get('is_match'):
                    log_message_func("❌ SOFT BOOT stopped: selected Restart screen failed visual validation")
                    return None, 'restart_visual'

            # Send key press command - keySimulator has initialization overhead
            key_cmd = f"keySimulator -k{key_name.lower()}"
            log_message_func(f"\n  [{key_count}/{total_keys}] Sending key: {key_name}")

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
                    if not is_last_key:
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
            return None, 'no_keys_sent'
        
        log_message_func(f"\n✓ Successfully sent {keys_sent_successfully}/{total_keys} navigation keys")
        log_message_func(f"  Last key press time: {last_key_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} UTC")
        log_message_func(f"  Device should begin restart sequence now...")
        
        return last_key_time, None
    
    except Exception as e:
        log_message_func(f"❌ Error during Settings navigation: {e}")
        import traceback
        log_message_func(f"  Traceback: {traceback.format_exc()}")
        return None, 'exception'

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
    
    ssh = get_execution_ssh_client()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    elapsed_probe_time = 0
    while elapsed_probe_time < total_ssh_timeout:
        # Check if job has been cancelled
        from methods.method_utils import is_job_cancelled
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
            ssh = get_execution_ssh_client()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            time.sleep(probe_interval)
            elapsed_probe_time = time.time() - start_time - ssh_probe_start
    
    log(f"❌ Device did not come back online within {ssh_probe_start + total_ssh_timeout}s total")
    return None

def reconnect_after_boot_timeout(device_ip, port, username, password, timeout_seconds=30, probe_interval=5, log_callback=None):
    """Make a short reconnect attempt so post-boot diagnostics can still run."""
    log = log_callback or print
    deadline = time.time() + timeout_seconds
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            log(f"  ⏱ Post-timeout SSH reconnect attempt {attempt}...")
            ssh.connect(device_ip, port=port, username=username, password=password, timeout=5)
            log("✓ SSH reconnected for post-boot diagnostics")
            return ssh
        except Exception:
            try:
                ssh.close()
            except Exception:
                pass
            time.sleep(min(probe_interval, max(0, deadline - time.time())))
    log(f"❌ SSH remained unavailable after the additional {timeout_seconds}s diagnostic reconnect window")
    return None

def execute_soft_hard_boot_process(device_ip, port, username, password, iteration=1, device_name="Device", combined_method_name=None, boot_type="HARD", optional_checks=None, home_screen_timeout=180, job_id=None, screenshots_dir=None, navigation_keys=None, language='en'):
    """
    Execute Soft Boot or Hard Boot Performance Monitoring
    
    HARD BOOT: Uses 'systemctl reboot' command
    - Performance calculated from command sent time to HOME screen detection
    
    SOFT BOOT: Navigates through Settings GUI
    - Launches Settings app via Voice curl
    - Navigates: System Management > Reset & updates > Restart device
    - Performance calculated from last key press time to HOME screen detection
    - Navigation keys: user-provided (via navigation_keys or optional_checks['navigation_keys']),
      falling back to DOWN(2x), ENTER, DOWN(2x), ENTER, ENTER when not supplied
    
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
        screenshots_dir: str - Optional job iteration screenshots folder (e.g. .../ITR_<n>/screenshots).
                              When provided, BEFORE/AFTER screenshots are saved here instead of the
                              standalone Enhancement_output/<DATE>/.../SCREENSHOTS location.
        navigation_keys: list of key names (e.g. ['DOWN', 'DOWN', 'ENTER', ...]) to send in order to
                              reach "Restart device" under Settings > System Management > Reset & updates
    """
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    screenshots_list = []
    logs_list = []
    optional_checks = optional_checks or {}
    language = 'de' if str(language).strip().lower() in ('de', 'german') else 'en'
    screenshot_result_before = None
    screen_validation = None
    build_info = None
    check_results = None
    rdk_milestones_log = None
    crash_check = None
    custom_log_results = None
    pre_boot_home_validation = None
    pre_boot_failure_reasons = []
    recovery_reboot_performed = False
    recovery_reboot_start_time = None
    core_log_baseline = 0
    power_state_after_boot = None
    
    # Store job_id in thread-local storage for cancellation checking
    if job_id:
        from methods.method_utils import set_current_job_id
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
        ssh = get_execution_ssh_client()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(device_ip, port=port, username=username, password=password, timeout=15)
        log_message("✓ Connected to device successfully")

        try:
            stdin, stdout, stderr = ssh.exec_command("wc -l < /opt/logs/core_log.txt 2>/dev/null || echo 0", timeout=10)
            core_log_baseline = int(stdout.read().decode('utf-8', errors='ignore').strip() or 0)
            stdout.channel.close()
            stderr.channel.close()
            log_message(f"Core crash log baseline: {core_log_baseline} line(s)")
        except Exception as baseline_error:
            log_message(f"⚠ Could not capture core crash log baseline: {baseline_error}")
        
        # Fetch build details from device
        build_info = fetch_build_details(ssh, log_message)
        
        # Activate ScreenCapture service before boot
        activate_screencapture_service(ssh, log_message)
        
        # Ensure device is on HOME screen before boot sequence
        log_message("Ensuring device is on HOME screen before boot sequence...")
        try:
            home_key_time = datetime.now(timezone.utc)
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

            # Capture the BEFORE screenshot NOW, while the device is still in its
            # pre-reboot state. This must happen before any SOFT BOOT recovery
            # `systemctl reboot` below - otherwise the "BEFORE" screenshot would
            # actually be taken AFTER that reboot completes and mislabeled.
            log_message("\n[STEP 1.5] Capturing BEFORE screenshot...")
            log_message("⚠ NOTE: Screenshot is informational - execution will continue even if it fails")
            try:
                if screenshots_dir:
                    os.makedirs(screenshots_dir, exist_ok=True)
                    screenshot_folder_before = screenshots_dir
                else:
                    screenshot_folder_before = create_screenshot_folder(device_ip, device_name, iteration, "Before", method_name=f"soft_hard_boot_{boot_type.lower()}", execution_timestamp=timestamp)
                screenshot_name_before = f"{device_ip}_{safe_device_name}_Iteration-{iteration}_Before-{boot_type}Boot_{timestamp}"
                screenshot_result_before = take_vnc_screenshot_with_fallback(
                        ssh=ssh,
                        device_ip=device_ip,
                        device_name=safe_device_name,
                        iteration=iteration,
                        screenshot_folder=screenshot_folder_before,
                        log_callback=log_message,
                        fallback_to_plugin=True,
                        context=f"{boot_type}_BEFOREBOOT"
                    )
                if screenshot_result_before and screenshot_result_before.get('success'):
                    log_message(f"✓ BEFORE screenshot saved: {screenshot_result_before.get('local_path')}")
                    screenshots_list.append(screenshot_result_before.get('local_path', ''))
                else:
                    error_msg = screenshot_result_before.get('error', 'Unknown error') if screenshot_result_before else 'Screenshot failed'
                    log_message(f"⚠ BEFORE screenshot not available: {error_msg}")
                    log_message("✓ Continuing with boot sequence anyway...")
                    screenshot_result_before = None
            except Exception as screenshot_error:
                log_message(f"⚠ Warning: Failed to capture BEFORE screenshot: {screenshot_error}")
                screenshot_result_before = None

            if boot_type == "SOFT":
                log_message("\n[SOFT BOOT PRECHECK] Validating the HOME log generated by the HOME key...")
                home_ready, home_log_line, home_time = check_for_home_log_continuously(
                    ssh,
                    timeout_seconds=10,
                    log_message_func=log_message,
                    reboot_start_time=home_key_time
                )
                if not home_ready:
                    pre_boot_failure_reasons.append('Device Not on Home Screen Before Boot')
                    log_message("⚠ HOME log not found - starting SOFT BOOT recovery")
                    power_state = query_device_power_state(ssh, log_message)

                    if power_state == 'ON':
                        log_message("[SOFT BOOT RECOVERY] Device is ON - sending systemctl reboot")
                        recovery_reboot_performed = True
                        recovery_reboot_start_time = datetime.now(timezone.utc)
                        _, reboot_error, reboot_exit_code = execute_device_command(
                            ssh, "systemctl reboot", log_message, timeout=10
                        )
                        log_message(
                            f"   Reboot command issued at: {recovery_reboot_start_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} UTC"
                        )
                        if reboot_error:
                            log_message(f"   Reboot command response: {reboot_error[:150]}")
                        ssh.close()
                        ssh = wait_for_device_with_early_ssh_probing(
                            device_ip, port, username, password,
                            initial_wait=10, ssh_probe_start=40,
                            probe_interval=5, total_ssh_timeout=100,
                            log_callback=log_message
                        )
                        if ssh:
                            home_ready, home_log_line, home_time = check_for_home_log_continuously(
                                ssh, timeout_seconds=home_screen_timeout,
                                log_message_func=log_message,
                                reboot_start_time=recovery_reboot_start_time
                            )
                    elif power_state == 'STANDBY':
                        log_message("[SOFT BOOT RECOVERY] Device is STANDBY - sending HOME to wake it")
                        wake_time = datetime.now(timezone.utc)
                        execute_device_command(
                            ssh, "timeout 5 keySimulator -khome || true", log_message, timeout=8
                        )
                        home_ready, home_log_line, home_time = check_for_home_log_continuously(
                            ssh, timeout_seconds=10,
                            log_message_func=log_message,
                            reboot_start_time=wake_time
                        )
                        if not home_ready:
                            power_state = query_device_power_state(ssh, log_message)

                    if not home_ready and power_state == 'ON' and ssh:
                        log_message("[SOFT BOOT RECOVERY] Device is ON but HOME is still not detected")
                        set_on_time = datetime.now(timezone.utc)
                        set_on_output, set_on_error, set_on_exit_code = execute_device_command(
                            ssh, "SetPowerState ON", log_message, timeout=15
                        )
                        if 'SetPowerState :: Success' in set_on_output:
                            confirmed_state = query_device_power_state(ssh, log_message)
                            if confirmed_state == 'ON':
                                home_ready, home_log_line, home_time = check_for_home_log_continuously(
                                    ssh, timeout_seconds=10,
                                    log_message_func=log_message,
                                    reboot_start_time=set_on_time
                                )
                        else:
                            log_message(
                                f"❌ SetPowerState ON failed (exit={set_on_exit_code}): "
                                f"{(set_on_error or set_on_output)[:150]}"
                            )

                    if not home_ready:
                        log_message("❌ SOFT BOOT recovery failed: device did not reach HOME")
                        pre_boot_failure_reasons.append('Home Screen Recovery Failed')
                        if ssh:
                            crash_check, custom_log_results = collect_iteration_failure_diagnostics(
                                ssh, device_ip, device_name, iteration, optional_checks,
                                core_log_baseline, log_message, logs_list,
                                pre_boot_failure_reasons, boot_type
                            )
                            ssh.close()
                        return {
                            "iteration": iteration, "screenshots": screenshots_list, "logs": logs_list,
                            "success": False, "boot_type": boot_type, "device_name": device_name,
                            "pre_boot_home_validation": {
                                'log_found': False, 'screen_matched': False,
                                'recovery_reasons': pre_boot_failure_reasons
                            },
                            "crash_check": crash_check,
                            "custom_log_results": custom_log_results
                        }
                    log_message("✓ SOFT BOOT recovery reached HOME - continuing normally")
                    log_message("   (Screen-match validation skipped: BEFORE screenshot predates the recovery reboot)")
                    pre_boot_home_validation = {'log_found': True, 'screen_matched': True, 'recovery_reboot_performed': True}
                    pre_boot_failure_reasons = []
                else:
                    if screenshot_result_before and screenshot_result_before.get('success'):
                        before_screenshot_path = screenshot_result_before.get('local_path')
                        if is_black_screen(before_screenshot_path):
                            log_message("⚠ BEFORE screenshot is black/near-black despite a fresh HOME log")
                            log_message("   Querying device power state before deciding whether to recover...")
                            power_state = query_device_power_state(ssh, log_message)
                            pre_boot_home_validation = {
                                'log_found': True,
                                'screen_matched': False,
                                'black_screen': True,
                                'power_state': power_state
                            }

                            if power_state == 'ON':
                                log_message("[SOFT BOOT RECOVERY] Black screen while device is ON - sending systemctl reboot")
                                pre_boot_failure_reasons.append('Black Screen Before Boot')
                                home_ready = False
                                home_log_line = None
                                home_time = None
                                recovery_reboot_performed = True
                                recovery_reboot_start_time = datetime.now(timezone.utc)
                                _, reboot_error, reboot_exit_code = execute_device_command(
                                    ssh, "systemctl reboot", log_message, timeout=10
                                )
                                log_message(
                                    f"   Reboot command issued at: "
                                    f"{recovery_reboot_start_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} UTC "
                                    f"(exit={reboot_exit_code})"
                                )
                                if reboot_error:
                                    log_message(f"   Reboot command response: {reboot_error[:150]}")
                                ssh.close()
                                ssh = wait_for_device_with_early_ssh_probing(
                                    device_ip, port, username, password,
                                    initial_wait=10, ssh_probe_start=40,
                                    probe_interval=5, total_ssh_timeout=100,
                                    log_callback=log_message
                                )
                                if ssh:
                                    home_ready, home_log_line, home_time = check_for_home_log_continuously(
                                        ssh, timeout_seconds=home_screen_timeout,
                                        log_message_func=log_message,
                                        reboot_start_time=recovery_reboot_start_time
                                    )

                                if not home_ready:
                                    log_message("❌ Black-screen recovery reboot did not produce a fresh HOME log")
                                    pre_boot_failure_reasons.append('Home Screen Recovery Failed')
                                    if ssh:
                                        crash_check, custom_log_results = collect_iteration_failure_diagnostics(
                                            ssh, device_ip, device_name, iteration, optional_checks,
                                            core_log_baseline, log_message, logs_list,
                                            pre_boot_failure_reasons, boot_type
                                        )
                                        ssh.close()
                                    return {
                                        "iteration": iteration, "screenshots": screenshots_list, "logs": logs_list,
                                        "success": False, "boot_type": boot_type, "device_name": device_name,
                                        "pre_boot_home_validation": pre_boot_home_validation,
                                        "crash_check": crash_check,
                                        "custom_log_results": custom_log_results,
                                        "recovery_reboot_performed": recovery_reboot_performed,
                                        "recovery_reboot_start_time": recovery_reboot_start_time.isoformat()
                                    }

                                log_message("✓ Black-screen recovery reboot reached HOME")
                                pre_boot_home_validation.update({
                                    'screen_matched': True,
                                    'recovery_reboot_performed': True
                                })
                                pre_boot_failure_reasons = []
                            else:
                                log_message(
                                    f"❌ Black screen detected but device power state is "
                                    f"{power_state or 'UNKNOWN'} - not issuing systemctl reboot"
                                )
                                ssh.close()
                                return {
                                    "iteration": iteration, "screenshots": screenshots_list, "logs": logs_list,
                                    "success": False, "boot_type": boot_type, "device_name": device_name,
                                    "pre_boot_home_validation": pre_boot_home_validation
                                }
                        else:
                            # The HOME log alone is insufficient: confirm the visible screen is HOME.
                            pre_boot_home_validation = validate_soft_boot_home_screen(
                                before_screenshot_path, log_message
                            )
                            pre_boot_home_validation['log_found'] = True
                            pre_boot_home_validation['screen_matched'] = pre_boot_home_validation.get('is_match', False)
                            if not pre_boot_home_validation['screen_matched']:
                                log_message("❌ SOFT BOOT stopped: current screen is not the expected HOME screen")
                                ssh.close()
                                return {
                                    "iteration": iteration, "screenshots": screenshots_list, "logs": logs_list,
                                    "success": False, "boot_type": boot_type, "device_name": device_name,
                                    "pre_boot_home_validation": pre_boot_home_validation
                                }
                    else:
                        log_message("❌ SOFT BOOT stopped: HOME screenshot is required for pre-validation")
                        ssh.close()
                        return {
                            "iteration": iteration, "screenshots": screenshots_list, "logs": logs_list,
                            "success": False, "boot_type": boot_type, "device_name": device_name,
                            "pre_boot_home_validation": {'log_found': True, 'screen_matched': False, 'error': 'BEFORE screenshot unavailable'}
                        }
        except Exception as e:
            log_message(f"⚠ Warning: Failed to press HOME button: {e}")
            if boot_type == "SOFT":
                pre_boot_failure_reasons.extend([
                    'Device Not on Home Screen Before Boot',
                    'Home Screen Recovery Failed'
                ])
                log_message("❌ SOFT BOOT HOME precheck failed - collecting diagnostics")
                crash_check, custom_log_results = collect_iteration_failure_diagnostics(
                    ssh, device_ip, device_name, iteration, optional_checks,
                    core_log_baseline, log_message, logs_list,
                    pre_boot_failure_reasons, boot_type
                )
                ssh.close()
                return {
                    "iteration": iteration, "screenshots": screenshots_list, "logs": logs_list,
                    "success": False, "boot_type": boot_type, "device_name": device_name,
                    "pre_boot_home_validation": {
                        'log_found': False, 'screen_matched': False,
                        'recovery_reasons': pre_boot_failure_reasons, 'error': str(e)
                    },
                    "crash_check": crash_check,
                    "custom_log_results": custom_log_results
                }
            log_message("   Continuing with HARD boot sequence anyway...")
        
        log_message("✓ Pre-boot setup complete")
        
        # STEP 2: SEND REBOOT COMMAND OR NAVIGATE SETTINGS
        boot_start_time = recovery_reboot_start_time or datetime.now(timezone.utc)
        
        if recovery_reboot_performed:
            log_message("\n[STEP 2] Recovery reboot already completed - skipping Settings restart to prevent a second reboot")
        elif boot_type == "HARD":
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
            resolved_navigation_keys = navigation_keys if navigation_keys is not None else optional_checks.get('navigation_keys')
            navigation_screenshots = []
            last_key_time = launch_settings_and_navigate_to_restart(
                ssh, log_message, boot_start_time,
                navigation_keys=resolved_navigation_keys,
                device_ip=device_ip,
                device_name=device_name,
                iteration=iteration,
                screenshots_dir=screenshots_dir,
                captured_screenshots=navigation_screenshots,
                language=language
            )
            # Settings/Restart-device screenshots are captured mid-navigation even when
            # validation later fails there - always fold them into the saved results.
            screenshots_list.extend(navigation_screenshots)
            
            if not last_key_time:
                log_message("❌ Failed to navigate Settings for SOFT BOOT")
                # Device is still up (reboot never triggered) - collect rdk_milestones.log for parity with HARD boot
                rdk_milestones_log = collect_rdk_milestones_log(ssh, device_ip, device_name, iteration, log_message)
                ssh.close()
                return {"iteration": iteration, "screenshots": screenshots_list, "logs": logs_list, "success": False, "rdk_milestones_log": rdk_milestones_log, "boot_type": boot_type, "device_name": device_name}
            
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
            log_message("❌ Device did not come back online within the SSH probe window")
            ssh = reconnect_after_boot_timeout(
                device_ip, port, username, password,
                timeout_seconds=30, probe_interval=5, log_callback=log_message
            )
            if not ssh:
                failure_reason = 'Device did not reconnect after boot; post-boot diagnostics unavailable'
                log_message(f"❌ Failure reason: {failure_reason}")
                return {
                    "iteration": iteration,
                    "screenshots": screenshots_list,
                    "logs": logs_list,
                    "success": False,
                    "performance_seconds": None,
                    "boot_type": boot_type,
                    "build_info": build_info,
                    "failure_reason": failure_reason,
                    "recovery_reboot_performed": recovery_reboot_performed,
                    "recovery_reboot_start_time": (
                        recovery_reboot_start_time.isoformat()
                        if recovery_reboot_start_time else None
                    ),
                    "diagnostics_unavailable": True,
                    "device_name": device_name
                }
            home_found = False
            home_log_line = None
            home_time = None
        
        log_message("✓ Device is back online - SSH connection established")
        
        # STEP 4: MONITOR LOGS FOR HOME SCREEN
        elapsed_since_boot = time.time() - boot_start_time.timestamp()
        remaining_timeout = max(30, home_screen_timeout - elapsed_since_boot)
        
        log_message(f"\n[STEP 4] Monitoring logs for HOME screen detection...")
        log_message(f"   Elapsed since boot: {elapsed_since_boot:.0f}s")
        log_message(f"   Will monitor for up to: {remaining_timeout:.0f}s more (total timeout: {home_screen_timeout}s)")
        
        if recovery_reboot_performed:
            log_message("   HOME screen was already validated after the recovery reboot")
            home_found = True
        else:
            home_found, home_log_line, home_time = check_for_home_log_continuously(
                ssh, timeout_seconds=int(remaining_timeout), log_message_func=log_message,
                reboot_start_time=boot_start_time, baseline_line_count=None
            )
        time.sleep(5)

        # STEP 5: COLLECT RDK MILESTONES LOG
        log_message("\n[STEP 5] Collecting diagnostic logs...")
        rdk_milestones_log = collect_rdk_milestones_log(ssh, device_ip, device_name, iteration, log_message)

        # Always run post-reboot checks for both HARD and SOFT boots, regardless of HOME detection.
        crash_check = check_process_crash(ssh, log_message, core_log_baseline)

        if crash_check.get('crash_found'):
            try:
                crash_wait_minutes = float(optional_checks.get('crash_wait_minutes', 8) or 0)
            except (TypeError, ValueError):
                crash_wait_minutes = 8
            if crash_wait_minutes > 0:
                log_message(
                    f"\n⏳ Process crash detected - waiting {crash_wait_minutes:.0f} minute(s) "
                    f"for the crash to upload to the crash portal before continuing..."
                )
                time.sleep(crash_wait_minutes * 60)
                log_message("✓ Wait complete - proceeding")

        custom_log_commands = optional_checks.get('custom_log_commands')
        if custom_log_commands is None:
            custom_log_commands = [
                f"grep -R -F -m 1 -- {shlex.quote(pattern)} /opt/logs 2>/dev/null | head -1"
                for pattern in optional_checks.get('custom_log_patterns', [])
                if str(pattern).strip()
            ]
        custom_log_results = check_custom_log_commands(ssh, custom_log_commands, log_message)

        matched_custom_logs = [
            check for check in custom_log_results.get('checks', []) if check.get('matched')
        ]
        if not home_found:
            log_message("\n[NETWORK/REALTEK CHECK] Validating post-boot device errors before log collection...")
            check_network_and_realtek_errors(ssh, log_message)
        collection_reasons = []
        if not home_found:
            collection_reasons.append('Device Not on Home Screen After Boot')
        collection_reasons.extend(pre_boot_failure_reasons)
        if crash_check.get('crash_found'):
            collection_reasons.append('Process Crash Detected')
        if matched_custom_logs:
            collection_reasons.append(f"Custom Log Pattern Matched ({len(matched_custom_logs)})")

        if collection_reasons:
            collection_reasons = list(dict.fromkeys(collection_reasons))

            # Only query power state for failing iterations (this IS a failure - the same
            # conditions that trigger device log collection), and before any screen capture.
            log_message("\n[POWER STATE CHECK] Iteration failed - querying device power state after boot...")
            power_state_after_boot = query_device_power_state(ssh, log_message)
            log_message(f"[POWER STATE AFTER BOOT] Iteration {iteration}: {power_state_after_boot or 'UNKNOWN'}")

            log_message(
                f"\n[LOG COLLECTION] {' and '.join(collection_reasons)} - "
                f"collecting device logs to /media/apps ({boot_type} boot)..."
            )
            from methods.method_reboot_perf_v2_optimized import collect_device_logs_to_media_app
            collected_log_path = collect_device_logs_to_media_app(
                ssh, device_ip, device_name, iteration, log_message
            )
            if collected_log_path:
                log_message(f"✓ Device logs collected: {collected_log_path}")
                logs_list.append(collected_log_path)
            else:
                log_message("⚠ Failed to collect device logs to /media/apps")
        
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
            
            if screenshots_dir:
                os.makedirs(screenshots_dir, exist_ok=True)
                screenshot_folder = screenshots_dir
            else:
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
                    context=f"{boot_type}_AFTERBOOT"
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
            post_reboot_checks_passed = (
                not crash_check['crash_found'] and not matched_custom_logs
            )
            if post_reboot_checks_passed:
                log_message(f"✓ SOFT/HARD BOOT TEST {boot_type} PASSED")
            else:
                log_message(f"❌ SOFT/HARD BOOT TEST {boot_type} FAILED - post-reboot validation failed")
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
                "success": post_reboot_checks_passed,
                "performance_seconds": reboot_duration,
                "rdk_milestones_log": rdk_milestones_log,
                "boot_type": boot_type,
                "optional_checks": check_results,
                "stop_iterations": check_results.get('stop_iterations', False),
                "screen_validation": screen_validation,
                "pre_boot_home_validation": pre_boot_home_validation,
                "recovery_reboot_performed": recovery_reboot_performed,
                "recovery_reboot_start_time": (
                    recovery_reboot_start_time.isoformat()
                    if recovery_reboot_start_time else None
                ),
                "crash_check": crash_check,
                "custom_log_results": custom_log_results,
                "build_info": build_info,
                "device_name": device_name,
                "power_state_after_boot": power_state_after_boot
            }
        
        else:
            # HOME screen not found - capture failure screenshot
            log_message("\n[STEP 6] HOME screen NOT found - Capturing failure screenshot...")
            
            # Re-activate screencapture service
            log_message("Re-activating ScreenCapture service...")
            activate_screencapture_service(ssh, log_message)
            log_message("Waiting 3 seconds for service to fully initialize...")
            time.sleep(3)
            
            if screenshots_dir:
                os.makedirs(screenshots_dir, exist_ok=True)
                screenshot_folder = screenshots_dir
            else:
                screenshot_folder = create_screenshot_folder(device_ip, device_name, iteration, "FAILED", method_name=f"soft_hard_boot_{boot_type.lower()}", execution_timestamp=timestamp)
            screenshot_name = f"{device_ip}_{safe_device_name}_Iteration-{iteration}_After-{boot_type}Boot-FAILED_{timestamp}"
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
                    context=f"{boot_type}_AFTERBOOT"
                )
                if screenshot_result and screenshot_result.get('success'):
                    screenshots_list.append(screenshot_result.get('local_path', ''))
                    log_message(f"✓ Failure screenshot saved: {screenshot_result.get('local_path', 'N/A')}")
                else:
                    log_message("⚠ Failure screenshot not captured - continuing anyway")
            except Exception as e:
                log_message(f"⚠ Screenshot capture exception: {e}")

            # Failure screen comparison is informational and never changes the failure result.
            screen_validation = None
            if screenshot_result_before and screenshot_result:
                screen_validation = validate_screen_comparison(
                    screenshot_result_before, screenshot_result, log_message
                )
                log_message(
                    "⚠ Failure screen comparison completed (informational): "
                    f"{screen_validation.get('message', 'no comparison message')}"
                )
            else:
                log_message("⚠ Failure screen comparison skipped - BEFORE or AFTER screenshot unavailable")

            failure_reason = 'Device did not reach HOME screen after boot'
            if crash_check.get('crash_found'):
                failure_reason += '; Process Crash Detected'
            if matched_custom_logs:
                failure_reason += f"; Custom Log Pattern Matched ({len(matched_custom_logs)})"
            
            log_message("\n" + "="*80)
            log_message(f"❌ SOFT/HARD BOOT TEST {boot_type} FAILED")
            log_message(f"❌ Failure reason: {failure_reason}")
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
                "crash_check": crash_check,
                "custom_log_results": custom_log_results,
                "pre_boot_home_validation": pre_boot_home_validation,
                "screen_validation": screen_validation,
                "failure_reason": failure_reason,
                "recovery_reboot_performed": recovery_reboot_performed,
                "recovery_reboot_start_time": (
                    recovery_reboot_start_time.isoformat()
                    if recovery_reboot_start_time else None
                ),
                "optional_checks": check_results or {
                    'custom_checks': [],
                    'overall_passed': False,
                    'stop_iterations': False,
                    'collected_logs': []
                },
                "stop_iterations": False,
                "device_name": device_name,
                "power_state_after_boot": power_state_after_boot
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
            "device_name": device_name,
            "power_state_after_boot": power_state_after_boot
        }
