#!/usr/bin/env python3
"""
Reboot Process Implementation
Complete reboot workflow matching Device-Reboot-DeepSleep-Wakeup_Updated.py
"""

import sys
import time
import paramiko
from methods.method_utils import get_execution_ssh_client
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

def execute_reboot_process(device_ip, port, username, password, iteration=1, device_name="Device", combined_method_name=None, has_deepsleep=False, job_id=None, tunnel_service=None, device_config=None):
    """
    Execute Reboot Process - Complete implementation matching Device-Reboot-DeepSleep-Wakeup_Updated.py:
    Step 1: Pre-Reboot validation (HOME screen check, screenshot)
    Step 2: Execute reboot command
    Step 3: Wait for device to come back online
    Step 4: Activate ScreenCapture service after reboot
    Step 5: Post-Reboot validation (HOME screen check with screenshot or error diagnostics)
    Step 6: Wait for maintenance tasks (15 minutes only if combined with DeepSleep, else 2 minutes)
    """
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    screenshots_list = []
    logs_list = []
    screenshot_result_before = None  # Store BEFORE screenshot for comparison
    
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
        usb_log_path = create_execution_log_path(device_ip, device_name, iteration, "REBOOT")
        log_service.current_usb_log_file = usb_log_path
        log_message(f"💾 USB execution log: {usb_log_path}")
    except Exception as e:
        log_message(f"⚠ Could not set USB log path: {e}")
    
    # PRE-REBOOT VALIDATION
    log_message("[PRE-REBOOT VALIDATION] Checking device and preparing for reboot...")
    try:
        ssh = None
        if tunnel_service:
            log_message("✓ Using R-Pi interactive shell tunnel for device connection")
            from utils.ssh_wrapper import wrap_tunnel_service_as_ssh
            ssh = wrap_tunnel_service_as_ssh(tunnel_service, device_config)
        else:
            ssh = get_execution_ssh_client()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(device_ip, port=port, username=username, password=password)
        log_message("✓ Connected to device successfully")
        
        # Fetch build details from device
        fetch_build_details(ssh, log_message)
        
        # Activate ScreenCapture service before reboot
        activate_screencapture_service(ssh, log_message)
        
        # Send HOME key to load HOME screen
        log_message("Sending HOME key to load HOME screen...")
        stdin, stdout, stderr = ssh.exec_command(home_key_command)
        time.sleep(3)
        log_message("✓ HOME key sent")
        
        # Wait for HOME screen to load
        log_message("Waiting 10 seconds for HOME screen to load...")
        time.sleep(10)
        
        # Check for HOME screen before reboot
        log_message("Checking if device is on HOME screen...")
        stdin, stdout, stderr = ssh.exec_command(log_check_command_HOME)
        log_output = stdout.read().decode('utf-8', errors='ignore')
        
        if log_line_HOME.split(".*")[0] in log_output:
            log_message("✓ Device is on HOME screen")
            # Take BEFORE screenshot
            method_for_folder = get_folder_method_name() or combined_method_name or "reboot"
            screenshot_folder = create_screenshot_folder(device_ip, safe_device_name, iteration, "Before", method_for_folder)
            screenshot_result_before = take_vnc_screenshot_with_fallback(
                ssh=ssh,
                device_ip=device_ip,
                device_name=safe_device_name,
                iteration=iteration,
                screenshot_folder=screenshot_folder,
                log_callback=log_message,
                fallback_to_plugin=True,
                context="Before-Reboot"
            )
            if screenshot_result_before and screenshot_result_before.get('success'):
                log_message(f"✓ Screenshot saved: {screenshot_result_before.get('local_path')}")
                screenshots_list.append(screenshot_result_before.get('local_path', ''))
                log_message(f"✓ Pre-Reboot PASSED: Device on HOME screen")
        else:
            log_message("⚠ Device is not on HOME screen before reboot")
        
        # EXECUTE REBOOT
        log_message("Sending reboot command to device...")
        stdin, stdout, stderr = ssh.exec_command(reboot_command)
        error_output = stderr.read().decode('utf-8', errors='ignore')
        if error_output:
            log_message(f"⚠ Reboot command stderr: {error_output}")
        ssh.close()
        
        # Mandatory wait for device reboot (minimum 75 seconds)
        mandatory_wait = 120  # seconds
        log_message(f"✓ Reboot command sent - Waiting {mandatory_wait}s for device to reboot...")
        
        # Chunked wait with progress logging every 20 seconds
        for i in range(12):  # 12 chunks of 10 seconds = 120 seconds
            # Check if job has been cancelled
            from methods.method_utils import is_job_cancelled
            if is_job_cancelled():
                log_message("\n❌ Job cancelled during reboot wait - stopping execution")
                return False
            
            time.sleep(10)
            elapsed = (i + 1) * 10
            if (i + 1) % 2 == 0:  # Log every 20 seconds (every 2 chunks)
                log_message(f"  ⏱ Reboot wait: {elapsed}/{mandatory_wait} seconds")
        
        log_message("Starting SSH reconnection attempts...")
        
        # WAIT FOR DEVICE TO COME BACK ONLINE (active polling after mandatory wait)
        ssh = wait_for_device(device_ip, port, username, password, log_message)
        if not ssh:
            log_message("❌ Reboot process failed - device did not come back online")
            return False
        
        # Fetch build details from device after reboot
        fetch_build_details(ssh, log_message)
        
        # ACTIVATE SCREENCAPTURE SERVICE AFTER REBOOT
        log_message("Activating ScreenCapture service after reboot...")
        activate_screencapture_service(ssh, log_message)
        
        # POST-REBOOT VALIDATION - CHECK FOR HOME SCREEN
        log_message("Checking if device reached HOME screen after reboot...")
        stdin, stdout, stderr = ssh.exec_command(log_check_command_HOME)
        log_output = stdout.read().decode('utf-8', errors='ignore')
        
        # CAPTURE SCREENSHOT (ALWAYS - whether HOME screen or not)
        method_for_folder = get_folder_method_name() or combined_method_name or "reboot"
        screenshot_folder = create_screenshot_folder(device_ip, safe_device_name, iteration, "After", method_for_folder)
        
        if log_line_HOME.split(".*")[0] in log_output:
            log_message("✓ Device is on HOME screen after reboot")
            # Take AFTER screenshot
            screenshot_result = take_vnc_screenshot_with_fallback(
                ssh=ssh,
                device_ip=device_ip,
                device_name=safe_device_name,
                iteration=iteration,
                screenshot_folder=screenshot_folder,
                log_callback=log_message,
                fallback_to_plugin=True,
                context="After-Reboot"
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
                    # Capture logs for analysis
                    log_filename = f"{device_ip}_{safe_device_name}_Iteration-{iteration}_Network-Error-Logs_{timestamp}.tar.gz"
                    log_path = capture_device_logs_sftp(ssh, log_filename, log_message, iteration, device_ip)
                    if log_path:
                        logs_list.append(log_path)
                
                # VALIDATE SCREEN COMPARISON: BEFORE vs AFTER (Informational only)
                screen_validation = validate_screen_comparison(screenshot_result_before, screenshot_result, log_message)
                
                # Screen validation is informational only - don't fail test based on it
                # Some devices have 0-byte screenshot issues, log check is primary validation
                if screen_validation and not screen_validation.get('screen_validation_passed'):
                    log_message("\n" + "="*80)
                    log_message("⚠ Screen Validation INFO: Screen comparison did not pass")
                    log_message(f"⚠ {screen_validation.get('message', 'Unknown validation issue')}")
                    log_message("⚠ NOTE: Test continues - Log check is primary validation criterion")
                    log_message("="*80)
                elif screen_validation and screen_validation.get('screen_validation_passed'):
                    log_message(f"✓ Post-Reboot PASSED: Device on HOME screen after reboot")
            
            # No need to capture device logs if device is on expected screen (HOME)
            log_message("✓ Skipping device log capture: device is on expected screen after reboot.")
            
            # Wait for maintenance tasks
            # 15 minutes if combined with DeepSleep, 2 minutes otherwise
            if has_deepsleep:
                maintenance_wait = 15 * 60  # 15 minutes = 900 seconds
                log_message(f"⏱ DeepSleep detected in combined methods: Waiting {maintenance_wait} seconds (15 minutes) for maintenance tasks...")
                
                # Sleep in 10-second chunks with progress logging every 3 minutes
                for i in range(90):  # 90 chunks of 10 seconds each = 900 seconds
                    # Check if job has been cancelled
                    from methods.method_utils import is_job_cancelled
                    if is_job_cancelled():
                        log_message("\n❌ Job cancelled during maintenance wait - stopping execution")
                        ssh.close()
                        return False
                    
                    time.sleep(10)
                    elapsed = (i + 1) * 10
                    if (i + 1) % 18 == 0:  # Log every 180 seconds (every 18 chunks = 3 minutes)
                        minutes_elapsed = elapsed // 60
                        minutes_remaining = (maintenance_wait - elapsed) // 60
                        log_message(f"  ⏱ Maintenance progress: {elapsed}/{maintenance_wait} seconds ({minutes_elapsed} min elapsed, {minutes_remaining} min remaining)")
                
                log_message("✓ Maintenance wait complete (900 seconds)")
            else:
                maintenance_wait = 2 * 60  # 2 minutes = 120 seconds
                log_message(f"⏱ Standalone reboot: Waiting {maintenance_wait} seconds (2 minutes) for maintenance tasks...")
                
                # Sleep in 10-second chunks with progress logging
                for i in range(12):  # 12 chunks of 10 seconds each = 120 seconds
                    # Check if job has been cancelled
                    from methods.method_utils import is_job_cancelled
                    if is_job_cancelled():
                        log_message("\n❌ Job cancelled during maintenance wait - stopping execution")
                        ssh.close()
                        return False
                    
                    time.sleep(10)
                    elapsed = (i + 1) * 10
                    if (i + 1) % 6 == 0:  # Log every 60 seconds (every 6 chunks = 1 minute)
                        minutes_elapsed = elapsed // 60
                        log_message(f"  ⏱ Maintenance progress: {elapsed}/{maintenance_wait} seconds ({minutes_elapsed} min elapsed)")
                
                log_message("✓ Maintenance wait complete (120 seconds)")
            
            ssh.close()
            log_message(f"✓ Reboot process completed successfully for iteration {iteration}")
            return {"iteration": iteration, "screenshots": screenshots_list, "logs": logs_list, "success": True, "device_name": device_name}
        
        else:
            log_message("❌ Device is NOT on HOME screen after reboot - starting error diagnostics...")
            # Take screenshot anyway for diagnostics
            screenshot_result = take_vnc_screenshot_with_fallback(
                ssh=ssh,
                device_ip=device_ip,
                device_name=safe_device_name,
                iteration=iteration,
                screenshot_folder=screenshot_folder,
                log_callback=log_message,
                fallback_to_plugin=True,
                context="After-Reboot-ERROR"
            )
            if screenshot_result and screenshot_result.get('success'):
                screenshots_list.append(screenshot_result.get('local_path', ''))

            # Check OCR text for network errors
            extracted_text = screenshot_result.get('extracted_text', '') if screenshot_result else ''
            screen_state = screenshot_result.get('screen_state', {}) if screenshot_result else {}
            has_network_error = screen_state.get('has_network_error', False)
            
            if has_network_error:
                log_message("⚠ NETWORK ERROR DETECTED in screenshot text:")
                log_message(f"   Text preview: {extracted_text[:300]}")
            
            # Check for network/Realtek errors in device logs
            check_network_and_realtek_errors(ssh, log_message)
            
            # Capture device logs for analysis (ALWAYS when HOME screen not found)
            log_message("Capturing device logs from /opt/logs/* for error analysis...")
            log_filename = f"{device_ip}_{safe_device_name}_Iteration-{iteration}_Reboot-ERROR-Logs_{timestamp}.tar.gz"
            log_path = capture_device_logs_sftp(ssh, log_filename, log_message, iteration, device_ip)
            if log_path:
                logs_list.append(log_path)
            else:
                # Fallback to minimal log capture
                fallback_logs = capture_minimal_logs_fallback(ssh, f"Iteration-{iteration}_Reboot-ERROR", log_message, iteration, device_ip)
                logs_list.extend(fallback_logs)
            
            ssh.close()
            
            log_message(f"❌ Reboot process failed for iteration {iteration}")
            return {"iteration": iteration, "screenshots": screenshots_list, "logs": logs_list, "success": False, "device_name": device_name}
        
    except Exception as e:
        import traceback
        log_message(f"❌ Error during Reboot process: {e}")
        log_message(f"Full traceback:\n{traceback.format_exc()}")
        return {"iteration": iteration, "screenshots": screenshots_list, "logs": logs_list, "success": False, "device_name": device_name}
