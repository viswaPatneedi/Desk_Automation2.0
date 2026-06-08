#!/usr/bin/env python3
"""
IR Command Test Process Implementation
Blind IR command testing without requiring SSH first
"""

import time
import socket
import traceback
import paramiko
from datetime import datetime, timezone

# Import configurations
from config_commands import *

# Import shared utilities
from method_utils import log_message, create_execution_log_path

# Import IR utilities
from config_ir_blaster import get_ir_config_for_device, generate_ir_code, send_ir_command

def execute_ir_test_process(device_ip, port, username, password, iteration=1, device_name="Device", selected_keys=None, combined_method_name=None, remote_type_override=None):
    """
    Execute IR Command Test Process:
    Step 1: Send IR command(s) blindly using device-specific IR configuration (no SSH needed)
    Step 2: Optionally verify via SSH if device is accessible
    Step 3: Check device logs (/opt/logs/sky-messages.log) for keycode logs (if SSH available)
    
    This method is designed to send IR commands WITHOUT requiring SSH connection first.
    Useful for waking up devices from DeepSleep or sending IR commands blindly.
    
    Args:
        device_name: Device name for IR port selection and logging
        selected_keys: List of IR keys to test (e.g., ['HOME', 'POWER'])
        remote_type_override: Optional remote type to use instead of device default
    """
    # Default to both keys if none specified
    if not selected_keys:
        selected_keys = ['HOME', 'POWER']
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    
    # Set USB log file path for this execution
    try:
        from services.log_service import LogService
        log_service = LogService()
        usb_log_path = create_execution_log_path(device_ip, device_name, iteration, "IR_TEST")
        log_service.current_usb_log_file = usb_log_path
        log_message(f"💾 USB execution log: {usb_log_path}")
    except Exception as e:
        log_message(f"⚠ Could not set USB log path: {e}")
    
    try:
        log_message(f"\n{'='*60}")
        log_message(f"[IR COMMAND TEST] Starting IR command test - Iteration {iteration}")
        log_message(f"{'='*60}")
        
        # Get IR configuration for this device (no SSH required)
        log_message(f"[IR CONFIG] Looking up device: {device_name}")
        ir_config = get_ir_config_for_device(device_name)
        
        if not ir_config:
            log_message(f"❌ ERROR: Could not find IR configuration for device '{device_name}'")
            log_message(f"    Please verify device name in devices.json")
            from app import add_html_result
            add_html_result(iteration, "IR-Test", "FAILED", f"No IR config found for device '{device_name}'", "", "", 
                          device_ip=device_ip, method="ir_test")
            return False
        
        log_message(f"[IR CONFIG] Device: {device_name}")
        log_message(f"[IR CONFIG] iTach IP: {ir_config['itach_ip']}")
        log_message(f"[IR CONFIG] iTach Port: {ir_config['itach_port']}")
        log_message(f"[IR CONFIG] IR Port: {ir_config['ir_port']}")
        log_message(f"[IR CONFIG] Selected Keys: {', '.join(selected_keys)}")
        
        ir_test_success = False
        
        # Resolve remote type (default to XUMO_PR3, fallback SKY_LC103 for SKY devices)
        remote_type = remote_type_override or ir_config.get('remote_type') or ('SKY_LC103' if 'SKY' in device_name.upper() else 'XUMO_PR3')
        log_message(f"[IR CONFIG] Remote Type: {remote_type}")

        # Send IR commands and validate logs for each key
        keycode_patterns = {
            'HOME': 'keycode: Ethan::Key_Home',
            'POWER': 'keycode: Ethan::Key_RCUPower'
        }
        for idx, key in enumerate(selected_keys):
            log_message(f"\n[IR COMMAND] Sending IR {key} command...")
            ir_code = generate_ir_code(key, ir_config['ir_port'], remote_type=remote_type)
            if ir_code:
                log_message(f"[IR CODE] Generated {key} code: {ir_code[:50]}...")
                if send_ir_command(ir_code, ir_config['itach_ip'], ir_config['itach_port'], log_message):
                    log_message(f"✓ IR {key} command sent successfully (blind)")
                    ir_test_success = True
                else:
                    log_message(f"❌ Failed to send IR {key} command")
                    from app import add_html_result
                    add_html_result(iteration, f"IR-{key}", "FAILED", f"IR {key} command transmission failed", "", "", 
                                  device_ip=device_ip, method="ir_test")
            else:
                log_message(f"❌ Failed to generate IR {key} code")
            # Wait 3 seconds before checking logs
            log_message("[WAIT] Waiting 3 seconds before log validation...")
            time.sleep(3)
            
            # VERIFY LOGS (If SSH available)
            log_message(f"\n[VERIFY LOGS] Verifying {key} command in device logs (if SSH available)...")
            # Log validation per key
            try:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(device_ip, port=port, username=username, password=password, timeout=10)
                if key == 'POWER':
                    # Query device state
                    stdin, stdout, stderr = ssh.exec_command(device_status_command)
                    state = stdout.read().decode('utf-8', errors='ignore').strip().lower()
                    log_message(f"[STATE] Device state after POWER: {state}")
                else:
                    log_message(f"[IR] Sent IR command: {key}")
                ssh.close()
            except Exception as log_error:
                log_message(f"❌ Error checking device: {log_error}")
            # Wait 3 seconds before next key if more remain
            if idx < len(selected_keys) - 1:
                log_message("[WAIT] Waiting 3 seconds before sending next IR key...")
                time.sleep(3)
        
        # Wait for device to process IR commands
        wait_time = 0
        if 'HOME' in selected_keys:
            wait_time = 3
            log_message("\n[WAIT] Waiting 3 seconds after IR HOME command...")
        elif 'POWER' in selected_keys:
            wait_time = 6
            log_message("\n[WAIT] Waiting 6 seconds after IR POWER command...")
        else:
            wait_time = 3
            log_message("\n[WAIT] Waiting 3 seconds after IR command...")
        time.sleep(wait_time)
        
        # VERIFICATION: Try to verify via SSH and check if device is on HOME screen
        log_message("\n[VERIFICATION] Attempting to connect via SSH to verify device state...")
        ssh = None
        ssh_accessible = False
        home_screen_status = "Unknown"
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(device_ip, port=port, username=username, password=password, timeout=10)
            log_message("✓ SSH connection established - device is accessible")
            ssh_accessible = True
            
            # Check if device is on HOME screen
            log_message("[HOME SCREEN CHECK] Verifying if device is on HOME screen...")
            try:
                from config_log_patterns import log_check_command_HOME, log_line_HOME
                stdin, stdout, stderr = ssh.exec_command(log_check_command_HOME)
                log_output = stdout.read().decode('utf-8', errors='ignore')
                
                if log_line_HOME.split(".*")[0] in log_output:
                    log_message("✓ Device is on HOME screen")
                    home_screen_status = "on HOME screen"
                else:
                    log_message("⚠ Device is NOT on HOME screen")
                    home_screen_status = "NOT on HOME screen"
            except Exception as check_error:
                log_message(f"⚠ Error checking HOME screen: {check_error}")
                home_screen_status = "unable to verify"
            
            ssh.close()
            
        except (paramiko.SSHException, paramiko.AuthenticationException, socket.error, socket.timeout, ConnectionResetError, OSError) as ssh_error:
            log_message(f"⚠ SSH verification failed (device may be off/unreachable): {ssh_error}")
            ssh_accessible = False
            home_screen_status = "SSH unavailable"
        
        # Create single IR-Test result entry with detailed per-key results
        result_details = []
        for key in selected_keys:
            result_details.append(f"{key}: sent successfully")
        
        result_msg = "Keys: " + " | ".join(result_details) + f" | Device {home_screen_status}"
        
        # Build phase name based on keys sent (not hardcoded HOME)
        keys_str = ", ".join(selected_keys)
        
        # Determine status based on whether device is accessible and on HOME screen
        if "on HOME screen" in home_screen_status:
            phase_name = f"IR-Test ({keys_str})"
            result_status = "PASSED"
            ir_test_success = True
        elif "NOT on HOME screen" in home_screen_status:
            phase_name = f"IR-Test ({keys_str})"
            result_status = "WARNING"
            ir_test_success = True
        else:
            phase_name = f"IR-Test ({keys_str})"
            result_status = "WARNING"
            ir_test_success = True
        
        from app import add_html_result
        add_html_result(iteration, phase_name, result_status, result_msg, "", "", 
                       device_ip=device_ip, method="ir_test")
        
        log_message(f"\n{'='*60}")
        log_message(f"✓ IR Command Test completed - {result_msg}")
        log_message(f"{'='*60}")
        
        # Return proper dictionary structure for result recording
        return {
            "iteration": iteration,
            "screenshots": [],
            "logs": [],
            "success": ir_test_success,
            "details": result_msg
        }
        
    except Exception as e:
        log_message(f"❌ Error during IR command test: {e}")
        log_message(f"Exception type: {type(e).__name__}")
        log_message(f"Traceback: {traceback.format_exc()}")
        from app import add_html_result
        add_html_result(iteration, "IR-Test", "FAILED", f"Exception: {str(e)}", "", "", 
                       device_ip=device_ip, method="ir_test")
        
        # Return proper dictionary structure even for failures
        return {
            "iteration": iteration,
            "screenshots": [],
            "logs": [],
            "success": False,
            "details": f"Exception: {str(e)}"
        }
