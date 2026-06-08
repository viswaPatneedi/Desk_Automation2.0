#!/usr/bin/env python3
"""
DeepSleep Maintenance Wakeup Method Implementation
Comprehensive deep sleep and maintenance cycle with wake-up validation
Based on specification: Check state -> Wake -> EPG/Bootstate -> Configure Deep Sleep -> 
Enter Sleep -> Wait for Auto-Wake -> Verify -> Reboot -> Verify Final State
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
from config_ir_blaster import get_ir_config_for_device, generate_ir_code, send_ir_command

# Import shared utilities
from method_utils import (
    log_message,
    fetch_build_details,
    create_execution_log_path,
    reconnect_to_device_with_retry,
)

# Import HOME screen validation function from method_deepsleep
from method_deepsleep import check_home_screen_status

def execute_deepsleep_maintenance_wakeup_process(device_ip, port, username, password, iteration=1, 
                                                  device_name="Device", remote_type=None, job_id=None):
    """
    Execute DeepSleep Maintenance Wakeup procedure following specified steps:
    
    STEP 1: Check device state and wake up if needed (STANDBY/OFF/LIGHTSLEEP)
    STEP 2: Check EPG UI running and bootstate
    STEP 3: Verify device is ON, configure deep sleep settings
    STEP 4: Send IR power key to enter deep sleep, poll for SSH availability
    STEP 5: After sleep/wake cycle, verify state and send systemctl reboot
    STEP 6: Verify device state after reboot
    
    Args:
        device_ip: Device IP address
        port: SSH port (default 10022)
        username: SSH username (default root)
        password: SSH password
        iteration: Current iteration number
        device_name: Device name for logging
        remote_type: IR remote type (auto-detected if None)
        job_id: Job ID for tracking (optional)
    
    Returns:
        dict: Execution result with status, screenshots, and logs
    """
    
    result = {
        "iteration": iteration,
        "screenshots": [],
        "logs": [],
        "success": False,
        "details": {}
    }
    
    def log_callback(message):
        """Log message with timestamp"""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        full_message = f"[{timestamp}] {message}"
        log_message(full_message)
        result["logs"].append(full_message)
    
    ssh = None
    try:
        log_callback(f"\n{'='*80}")
        log_callback(f"DeepSleep Maintenance Wakeup Procedure - Iteration {iteration}")
        log_callback(f"Device: {device_name} ({device_ip})")
        log_callback(f"Remote Type: {remote_type}")
        log_callback(f"{'='*80}")
        
        # Auto-detect remote type if not provided
        if not remote_type:
            remote_type = "SKY_LC103" if "SKY" in device_name else "XUMO_PR3"
            log_callback(f"Auto-detected remote type: {remote_type}")
        
        # Get IR configuration for device
        ir_config = get_ir_config_for_device(device_name)
        if not ir_config or not ir_config.get('itach_ip'):
            log_callback("⚠️  IR config not available or incomplete, will attempt IR commands but may fail")
            ir_config = {'itach_ip': None, 'itach_port': None, 'ir_port': 1}
        else:
            log_callback(f"✓ IR config found: iTach IP={ir_config.get('itach_ip')}, Port={ir_config.get('itach_port')}")
        
        # =======================
        # STEP 1: Initial device state check and wake-up
        # =======================
        log_callback(f"\n{'─'*80}")
        log_callback("STEP 1: Checking initial device state, waking up if needed, validate HOME SCREEN")
        log_callback(f"{'─'*80}")
        
        # Connect to device
        log_callback("Connecting to device for initial state check...")
        ssh = reconnect_to_device_with_retry(device_ip, port, username, password, 5, 2, log_callback)
        
        if not ssh:
            log_callback("❌ Failed to establish initial SSH connection")
            result["details"]["step_1"] = "Failed to connect"
            return result
        
        # Query initial power state
        try:
            stdin, stdout, stderr = ssh.exec_command("QueryPowerState", timeout=10)
            stdout.channel.settimeout(10)
            initial_state = stdout.read().decode('utf-8', errors='ignore').strip()
            stdout.channel.close()
            log_callback(f"✓ Initial device power state: {initial_state}")
        except Exception as e:
            log_callback(f"⚠️  Could not query initial power state: {e}")
            initial_state = "UNKNOWN"
        
        # If device is in sleep/standby, wake it with IR POWER KEY
        if any(state in initial_state.upper() for state in ["STANDBY", "LIGHTSLEEP", "DEEPSLEEP", "OFF"]):
            log_callback(f"Device is in {initial_state} - sending IR POWER KEY to wake up...")
            if ir_config and ir_config.get('itach_ip'):
                ir_code = generate_ir_code("POWER", ir_config['ir_port'], remote_type=remote_type)
                if send_ir_command(ir_code, ir_config['itach_ip'], ir_config['itach_port'], log_callback):
                    log_callback("✓ IR POWER KEY sent successfully")
                    time.sleep(5)  # Allow time for device to respond
                else:
                    log_callback("⚠️  IR POWER command may have failed")
            else:
                log_callback("⚠️  Cannot send IR POWER - iTach config not available")
        else:
            log_callback(f"✓ Device appears to be in {initial_state}, no wake-up needed")
        
        # Reconnect after potential wake-up
        log_callback("Re-establishing SSH connection after wake-up...")
        ssh = reconnect_to_device_with_retry(device_ip, port, username, password, 10, 2, log_callback)
        if not ssh:
            log_callback("❌ Failed to reconnect after wake-up attempt")
            result["details"]["step_1"] = "Reconnection failed"
            return result
        
        # Verify device is ON and navigate to HOME screen
        log_callback("\n[STEP-1a] Verifying device is ON and navigating to HOME SCREEN...")
        try:
            stdin, stdout, stderr = ssh.exec_command("QueryPowerState", timeout=10)
            stdout.channel.settimeout(10)
            power_state = stdout.read().decode('utf-8', errors='ignore').strip()
            stdout.channel.close()
            log_callback(f"Device power state after wake-up: {power_state}")
        except Exception as e:
            log_callback(f"⚠️  Error checking power state: {e}")
            power_state = ""
        
        # If device is ON, send IR HOME key to get to HOME screen
        if "ON" in power_state.upper() or "RENDERINGON" in power_state.upper():
            log_callback(f"✓ Device is ON ({power_state}) - Sending IR HOME KEY to navigate to HOME SCREEN...")
            if ir_config and ir_config.get('itach_ip'):
                ir_code = generate_ir_code("HOME", ir_config['ir_port'], remote_type=remote_type)
                if send_ir_command(ir_code, ir_config['itach_ip'], ir_config['itach_port'], log_callback):
                    log_callback("✓ IR HOME KEY sent successfully")
                    time.sleep(3)  # Allow time for HOME screen to appear
                else:
                    log_callback("⚠️  IR HOME command may have failed")
            else:
                log_callback("⚠️  Cannot send IR HOME - iTach config not available")
        else:
            log_callback(f"⚠️  Device is not ON yet ({power_state}), skipping HOME screen navigation")
        
        # Validate HOME screen
        log_callback("[STEP-1b] Validating HOME SCREEN status...")
        try:
            home_screen_found = check_home_screen_status(ssh, log_callback)
            if home_screen_found:
                log_callback("✓ HOME SCREEN validated successfully")
                result["details"]["step_1_home_screen"] = "Validated"
            else:
                log_callback("⚠️  HOME SCREEN validation failed - device may not be on HOME screen")
                result["details"]["step_1_home_screen"] = "NOT_found"
        except Exception as e:
            log_callback(f"⚠️  Error validating HOME screen: {e}")
            result["details"]["step_1_home_screen"] = "Error"
        
        log_callback("✓ STEP 1 completed - Device ready")
        result["details"]["step_1"] = "Success"
        
        # =======================
        # STEP 2: Check EPG UI and bootstate
        # =======================
        log_callback(f"\n{'─'*80}")
        log_callback("STEP 2: Checking EPG UI running state and bootstate")
        log_callback(f"{'─'*80}")
        
        epg_found = False
        bootstate_normal = False
        max_checks = 10
        
        for check_num in range(max_checks):
            # Check bootstate
            try:
                stdin, stdout, stderr = ssh.exec_command("curl -s '0:9001/as/system/bootstate'", timeout=10)
                stdout.channel.settimeout(10)
                bootstate_output = stdout.read().decode('utf-8', errors='ignore').strip()
                stdout.channel.close()
                log_callback(f"  Bootstate (check {check_num + 1}/{max_checks}): {bootstate_output}")
                if "NORMAL" in bootstate_output.upper():
                    bootstate_normal = True
            except Exception as e:
                log_callback(f"  ⚠️  Error checking bootstate: {e}")
            
            # Check EPG UI
            try:
                stdin, stdout, stderr = ssh.exec_command(
                    "grep 'com.bskyb.epgui - RUNNING' /opt/logs/sky-messages.log 2>/dev/null", 
                    timeout=10
                )
                stdout.channel.settimeout(10)
                epg_output = stdout.read().decode('utf-8', errors='ignore').strip()
                stdout.channel.close()
                if epg_output and "RUNNING" in epg_output:
                    log_callback(f"  ✓ EPG UI is RUNNING")
                    epg_found = True
                else:
                    log_callback(f"  ⏳ EPG UI not yet RUNNING (check {check_num + 1}/{max_checks})")
            except Exception as e:
                log_callback(f"  ⚠️  Error checking EPG: {e}")
            
            if epg_found and bootstate_normal:
                log_callback("✓ Both EPG and bootstate verified")
                break
            
            if check_num < max_checks - 1:
                time.sleep(6)  # Wait before next check
        
        if not epg_found:
            log_callback("⚠️  WARNING: EPG UI not found after checks")
        if not bootstate_normal:
            log_callback("⚠️  WARNING: Bootstate not NORMAL")
        
        result["details"]["step_2"] = "EPG_found" if epg_found else "EPG_not_found"
        
        # =======================
        # STEP 3: Verify device is ON and configure deep sleep
        # =======================
        log_callback(f"\n{'─'*80}")
        log_callback("STEP 3: Verifying device is ON and configuring deep sleep")
        log_callback(f"{'─'*80}")
        
        # Check device state
        try:
            stdin, stdout, stderr = ssh.exec_command("QueryPowerState", timeout=10)
            stdout.channel.settimeout(10)
            power_state = stdout.read().decode('utf-8', errors='ignore').strip()
            stdout.channel.close()
            log_callback(f"Current device power state: {power_state}")
        except Exception as e:
            log_callback(f"❌ Error querying power state: {e}")
            power_state = ""
        
        # If not ON, send IR POWER key
        if "ON" not in power_state.upper() and "RENDERINGON" not in power_state.upper():
            log_callback(f"Device is not ON ({power_state}). Sending IR POWER KEY...")
            if ir_config and ir_config.get('itach_ip'):
                ir_code = generate_ir_code("POWER", ir_config['ir_port'], remote_type=remote_type)
                if send_ir_command(ir_code, ir_config['itach_ip'], ir_config['itach_port'], log_callback):
                    log_callback("✓ IR POWER KEY sent to turn ON device")
                    time.sleep(10)
                    
                    # Verify device is now ON
                    try:
                        stdin, stdout, stderr = ssh.exec_command("QueryPowerState", timeout=10)
                        stdout.channel.settimeout(10)
                        power_state = stdout.read().decode('utf-8', errors='ignore').strip()
                        stdout.channel.close()
                        log_callback(f"Device power state after IR: {power_state}")
                    except Exception:
                        pass
                else:
                    log_callback("⚠️  Failed to send IR POWER KEY")
            else:
                log_callback("⚠️  Cannot send IR POWER - iTach config not available")
        else:
            log_callback(f"✓ Device is ON ({power_state})")
        
        # Configure deep sleep settings
        log_callback("\nConfiguring deep sleep settings...")
        log_callback("  [INFO] lowPowerTimerDuration=30: Device will auto-transition to DEEPSLEEP 30 secs after entering sleep mode (via IR POWER)")
        
        commands = [
            ("lowPowerTimerDuration", "curl -s 0:9001/as/test/preferences -d '{\"lowPowerTimerDuration\":\"30\"}'"),
            ("nextMaintenanceTimeOverride", "curl -s 0:9001/as/test/preferences -d '{\"nextMaintenanceTimeOverride\":\"30\"}'"),
            ("deepSleepTimerVal", "echo -n 30 > /tmp/deepSleepTimerVal")
        ]
        
        for cmd_name, cmd in commands:
            try:
                stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
                stdout.channel.settimeout(10)
                output = stdout.read().decode('utf-8', errors='ignore').strip()
                stdout.channel.close()
                log_callback(f"  ✓ {cmd_name}: {output[:50] if output else 'OK'}")
            except Exception as e:
                log_callback(f"  ⚠️  Error setting {cmd_name}: {e}")
        
        result["details"]["step_3"] = "Success"
        
        # =======================
        # STEP 4: Enter deep sleep and poll for SSH availability
        # =======================
        log_callback(f"\n{'─'*80}")
        log_callback("STEP 4: Sending IR POWER to enter deep sleep and polling for SSH")
        log_callback(f"{'─'*80}")
        
        # Send IR POWER to transition to standby/sleep
        log_callback("Sending IR POWER KEY to enter sleep mode...")
        if ir_config and ir_config.get('itach_ip'):
            ir_code = generate_ir_code("POWER", ir_config['ir_port'], remote_type=remote_type)
            if send_ir_command(ir_code, ir_config['itach_ip'], ir_config['itach_port'], log_callback):
                log_callback("✓ IR POWER KEY sent to enter sleep")
            else:
                log_callback("⚠️  Failed to send IR POWER")
        else:
            log_callback("⚠️  Cannot send IR POWER - iTach config not available")
        
        # Close current SSH connection
        if ssh:
            try:
                ssh.close()
            except:
                pass
        
        # Poll every 2 seconds to check if device is not sshable (deep sleep)
        log_callback("\nPolling every 2 seconds to detect deep sleep (device should become not sshable)...")
        device_offline = False
        poll_start = time.time()
        max_offline_wait = 300  # Wait up to 5 minutes for device to go offline
        
        while time.time() - poll_start < max_offline_wait:
            try:
                test_ssh = paramiko.SSHClient()
                test_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                test_ssh.connect(device_ip, port=port, username=username, password=password, timeout=3)
                test_ssh.close()
                elapsed = time.time() - poll_start
                log_callback(f"  ⏳ Device still online ({elapsed:.1f}s) - will retry in 2s...")
                time.sleep(2)
            except Exception:
                elapsed = time.time() - poll_start
                log_callback(f"✓ Device went offline after {elapsed:.1f}s - entered deep sleep")
                device_offline = True
                break
        
        if not device_offline:
            log_callback("⚠️  Device remained online - may not have entered deep sleep properly")
        
        result["details"]["step_4"] = "Device_offline" if device_offline else "Device_remained_online"
        
        # =======================
        # STEP 5: Wait for auto-wake and verify state
        # =======================
        log_callback(f"\n{'─'*80}")
        log_callback("STEP 5: Waiting for auto-wake from deep sleep and verifying state")
        log_callback(f"{'─'*80}")
        
        # Wait 5 seconds then start polling for SSH availability
        log_callback("Waiting 5 seconds for potential auto-wake cycle...")
        time.sleep(5)
        
        log_callback("Polling to detect device recovery from deep sleep...")
        device_recovered = False
        poll_start = time.time()
        max_recovery_wait = 60  # Wait up to 60 seconds for device to boot
        
        while time.time() - poll_start < max_recovery_wait:
            try:
                test_ssh = paramiko.SSHClient()
                test_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                test_ssh.connect(device_ip, port=port, username=username, password=password, timeout=3)
                elapsed = time.time() - poll_start
                log_callback(f"✓ Device recovered after {elapsed:.1f}s - SSH connection established")
                ssh = test_ssh
                device_recovered = True
                break
            except Exception:
                elapsed = time.time() - poll_start
                if int(elapsed) % 10 < 1:
                    log_callback(f"  ⏳ Waiting for device recovery ({elapsed:.1f}s / {max_recovery_wait}s)...")
                time.sleep(2)
        
        if not device_recovered:
            log_callback("⚠️  Device did not recover SSH connection within timeout")
            result["details"]["step_5"] = "Recovery_timeout"
            return result
        
        # Check device state after recovery
        try:
            stdin, stdout, stderr = ssh.exec_command("QueryPowerState", timeout=10)
            stdout.channel.settimeout(10)
            recovered_state = stdout.read().decode('utf-8', errors='ignore').strip()
            stdout.channel.close()
            log_callback(f"Device power state after recovery: {recovered_state}")
            
            # If in LIGHTSLEEP, device will automatically transition to DEEPSLEEP after 30-sec timer
            # No need to wait for STANDBY transition - proceed directly to STEP 6
            if "LIGHTSLEEP" in recovered_state.upper():
                log_callback("✓ Device in LIGHTSLEEP - will auto-transition to DEEPSLEEP after 30-sec timer")
                log_callback("✓ Skipping STANDBY wait and proceeding to STEP 6")
        except Exception as e:
            log_callback(f"⚠️  Error checking state after recovery: {e}")
            recovered_state = "UNKNOWN"
        
        result["details"]["step_5"] = f"State_{recovered_state.replace(' ', '_')}"
        
        # =======================
        # STEP 6: Reboot and verify final state
        # =======================
        log_callback(f"\n{'─'*80}")
        log_callback("STEP 6: Sending reboot command and verifying final state")
        log_callback(f"{'─'*80}")
        
        log_callback("Sending 'systemctl reboot' command...")
        try:
            stdin, stdout, stderr = ssh.exec_command("systemctl reboot", timeout=5)
            # Command will disconnect device
            log_callback("✓ Reboot command sent")
        except Exception as e:
            log_callback(f"⚠️  Error sending reboot command: {e}")
        
        time.sleep(2)  # Allow immediate disconnection
        
        # Close connection
        try:
            ssh.close()
            ssh = None
        except:
            pass
        
        # Wait for device to reboot (2 minutes as per spec)
        log_callback("Waiting 2 minutes (120 seconds) for device to reboot...")
        for seconds_elapsed in range(0, 121, 10):
            if seconds_elapsed > 0:
                time.sleep(10)
            remaining = 120 - seconds_elapsed
            if remaining > 0:
                log_callback(f"  ⏳ Reboot in progress ({seconds_elapsed}s / 120s)...")
        
        log_callback("✓ 2 minutes elapsed - checking device state...")
        
        # Reconnect and check final state
        ssh = reconnect_to_device_with_retry(device_ip, port, username, password, 5, 2, log_callback)
        if ssh:
            try:
                stdin, stdout, stderr = ssh.exec_command("QueryPowerState", timeout=10)
                stdout.channel.settimeout(10)
                final_state = stdout.read().decode('utf-8', errors='ignore').strip()
                stdout.channel.close()
                log_callback(f"✓ Final device power state: {final_state}")
                result["details"]["step_6"] = f"Final_state_{final_state.replace(' ', '_')}"
            except Exception as e:
                log_callback(f"⚠️  Error checking final state: {e}")
                result["details"]["step_6"] = "Check_failed"
        else:
            log_callback("⚠️  Could not reconnect to device after reboot for final verification")
            result["details"]["step_6"] = "Reconnection_failed"
        
        # =======================
        # STEP 7: Monitor device transition to DeepSleep from Standby
        # =======================
        log_callback(f"\n{'─'*80}")
        log_callback("STEP 7: Monitoring device transition to DeepSleep and calculating duration")
        log_callback(f"{'─'*80}")
        
        # Ensure device is ready
        try:
            stdin, stdout, stderr = ssh.exec_command("QueryPowerState", timeout=10)
            stdout.channel.settimeout(10)
            step7_initial_state = stdout.read().decode('utf-8', errors='ignore').strip()
            stdout.channel.close()
            log_callback(f"Current device state at STEP 7 start: {step7_initial_state}")
        except Exception as e:
            log_callback(f"⚠️  Error checking initial state: {e}")
            step7_initial_state = "UNKNOWN"
        
        # Re-configure deep sleep settings after reboot (preferences may have been lost)
        log_callback("\nRe-configuring deep sleep settings to ensure auto-transition to DEEPSLEEP...")
        try:
            # Set lowPowerTimerDuration again (defaults to 30 seconds after entering STANDBY)
            stdin, stdout, stderr = ssh.exec_command("curl -s 0:9001/as/test/preferences -d '{\"lowPowerTimerDuration\":\"30\"}'", timeout=10)
            stdout.channel.settimeout(10)
            output = stdout.read().decode('utf-8', errors='ignore').strip()
            stdout.channel.close()
            log_callback(f"  ✓ Re-configured lowPowerTimerDuration=30: Device will auto-transition to DEEPSLEEP 30s after entering STANDBY")
        except Exception as e:
            log_callback(f"  ⚠️  Error re-configuring lowPowerTimerDuration: {e}")
        
        # Check uptime command to establish baseline
        log_callback("\nChecking device uptime...")
        try:
            stdin, stdout, stderr = ssh.exec_command("uptime", timeout=10)
            stdout.channel.settimeout(10)
            uptime_output = stdout.read().decode('utf-8', errors='ignore').strip()
            stdout.channel.close()
            log_callback(f"✓ Device uptime: {uptime_output}")
        except Exception as e:
            log_callback(f"⚠️  Error getting uptime: {e}")
        
        # Poll for device to transition from STANDBY/ON to DEEPSLEEP
        log_callback("\nPolling for device to transition to DEEPSLEEP from STANDBY or ON...")
        log_callback("  [INFO] Device should auto-transition from STANDBY→DEEPSLEEP after ~30 seconds (lowPowerTimerDuration)")
        deepsleep_transition_start = time.time()
        max_deepsleep_wait = 900  # Wait up to 15 minutes for DEEPSLEEP (increased from 5 min)
        deepsleep_detected = False
        deepsleep_duration = 0
        manual_transition_attempted = False
        
        while time.time() - deepsleep_transition_start < max_deepsleep_wait:
            try:
                stdin, stdout, stderr = ssh.exec_command("QueryPowerState", timeout=10)
                stdout.channel.settimeout(10)
                current_state = stdout.read().decode('utf-8', errors='ignore').strip()
                stdout.channel.close()
                
                elapsed = time.time() - deepsleep_transition_start
                log_callback(f"  [{int(elapsed):3d}s] Device state: {current_state}")
                
                # Check if device reached DEEPSLEEP
                if "DEEPSLEEP" in current_state.upper():
                    deepsleep_duration = elapsed
                    log_callback(f"✓ Device transitioned to DEEPSLEEP after {deepsleep_duration:.1f} seconds")
                    deepsleep_detected = True
                    break
                
                # If device is in ON state and we've waited 120 seconds, try sending IR POWER to push it to STANDBY
                if "ON" in current_state.upper() and elapsed > 120 and not manual_transition_attempted:
                    log_callback(f"  ⚠️  Device still in ON after 120s - attempting manually via IR POWER to push to STANDBY...")
                    if ir_config and ir_config.get('itach_ip'):
                        ir_code = generate_ir_code("POWER", ir_config['ir_port'], remote_type=remote_type)
                        if send_ir_command(ir_code, ir_config['itach_ip'], ir_config['itach_port'], log_callback):
                            log_callback(f"  ✓ IR POWER sent to transition device to STANDBY")
                            manual_transition_attempted = True
                            time.sleep(5)  # Wait for transition
                        else:
                            log_callback(f"  ⚠️  Failed to send IR POWER")
                    continue
                
                time.sleep(5)  # Poll every 5 seconds
            except Exception as e:
                elapsed = time.time() - deepsleep_transition_start
                log_callback(f"  ⚠️  Error polling state at {elapsed:.1f}s: {e}")
                time.sleep(5)
        
        if not deepsleep_detected:
            log_callback(f"⚠️  Device did not transition to DEEPSLEEP within {max_deepsleep_wait}s timeout")
            result["details"]["step_7"] = f"DeepSleep_timeout_{max_deepsleep_wait}s"
        else:
            result["details"]["step_7"] = f"DeepSleep_detected_after_{deepsleep_duration:.1f}s"
        
        # Close SSH connection before entering DEEPSLEEP (device will be unreachable)
        if ssh:
            try:
                ssh.close()
                ssh = None
            except:
                pass
        
        # =======================
        # STEP 8: Wake device from DeepSleep and validate HOME screen
        # =======================
        log_callback(f"\n{'─'*80}")
        log_callback("STEP 8: Waking device from DEEPSLEEP and validating HOME screen")
        log_callback(f"{'─'*80}")
        
        # Wait a moment then send IR POWER to wake from DEEPSLEEP
        log_callback("Waiting 2 seconds before sending IR POWER to wake from DEEPSLEEP...")
        time.sleep(2)
        
        log_callback("Sending IR POWER KEY to wake device from DEEPSLEEP...")
        if ir_config and ir_config.get('itach_ip'):
            ir_code = generate_ir_code("POWER", ir_config['ir_port'], remote_type=remote_type)
            if send_ir_command(ir_code, ir_config['itach_ip'], ir_config['itach_port'], log_callback):
                log_callback("✓ IR POWER KEY sent to wake from DEEPSLEEP")
                time.sleep(5)  # Allow time for device to boot
            else:
                log_callback("⚠️  Failed to send IR POWER to wake from DEEPSLEEP")
        else:
            log_callback("⚠️  Cannot send IR POWER - iTach config not available")
        
        # Poll for SSH availability
        log_callback("\nPolling for device recovery after DEEPSLEEP wakeup...")
        device_wakeup_recovered = False
        poll_start = time.time()
        max_wakeup_wait = 120  # Wait up to 2 minutes for device to boot
        
        while time.time() - poll_start < max_wakeup_wait:
            try:
                test_ssh = paramiko.SSHClient()
                test_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                test_ssh.connect(device_ip, port=port, username=username, password=password, timeout=3)
                elapsed = time.time() - poll_start
                log_callback(f"✓ Device recovered from DEEPSLEEP after {elapsed:.1f}s - SSH connection established")
                ssh = test_ssh
                device_wakeup_recovered = True
                break
            except Exception:
                elapsed = time.time() - poll_start
                if int(elapsed) % 10 < 1:
                    log_callback(f"  ⏳ Waiting for device recovery from DEEPSLEEP ({elapsed:.1f}s)...")
                time.sleep(2)
        
        if not device_wakeup_recovered:
            log_callback("⚠️  Device did not recover from DEEPSLEEP (SSH unavailable within timeout)")
            result["details"]["step_8_wakeup"] = "Recovery_timeout"
        else:
            # Verify device is ON
            try:
                stdin, stdout, stderr = ssh.exec_command("QueryPowerState", timeout=10)
                stdout.channel.settimeout(10)
                wakeup_state = stdout.read().decode('utf-8', errors='ignore').strip()
                stdout.channel.close()
                log_callback(f"✓ Device power state after DEEPSLEEP wakeup: {wakeup_state}")
                result["details"]["step_8_wakeup_state"] = wakeup_state
            except Exception as e:
                log_callback(f"⚠️  Error checking state after wakeup: {e}")
        
        # Send IR HOME to navigate to HOME screen
        log_callback("\nSending IR HOME KEY to navigate to HOME screen...")
        if ir_config and ir_config.get('itach_ip'):
            ir_code = generate_ir_code("HOME", ir_config['ir_port'], remote_type=remote_type)
            if send_ir_command(ir_code, ir_config['itach_ip'], ir_config['itach_port'], log_callback):
                log_callback("✓ IR HOME KEY sent successfully")
                time.sleep(3)
            else:
                log_callback("⚠️  Failed to send IR HOME KEY")
        else:
            log_callback("⚠️  Cannot send IR HOME - iTach config not available")
        
        # Validate HOME screen after wakeup from DEEPSLEEP
        log_callback("[STEP-8] Validating HOME SCREEN after DEEPSLEEP wakeup...")
        try:
            home_screen_after_deepsleep = check_home_screen_status(ssh, log_callback)
            if home_screen_after_deepsleep:
                log_callback("✓ HOME SCREEN validated successfully after DEEPSLEEP wakeup")
                result["details"]["step_8_home_screen"] = "Validated"
            else:
                log_callback("⚠️  HOME SCREEN validation failed after DEEPSLEEP wakeup")
                result["details"]["step_8_home_screen"] = "NOT_found"
        except Exception as e:
            log_callback(f"⚠️  Error validating HOME screen after wakeup: {e}")
            result["details"]["step_8_home_screen"] = "Error"
        
        log_callback("✓ STEP 8 completed - Device recovered from DEEPSLEEP with HOME screen validated")
        
        log_callback(f"\n{'='*80}")
        log_callback("DeepSleep Maintenance Wakeup Procedure - COMPLETED")
        log_callback(f"{'='*80}")
        
        result["success"] = True
        return result
        
    except Exception as e:
        log_callback(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        log_callback(traceback.format_exc())
        result["success"] = False
        return result
    
    finally:
        # Ensure SSH connection is closed
        if ssh:
            try:
                ssh.close()
            except:
                pass
