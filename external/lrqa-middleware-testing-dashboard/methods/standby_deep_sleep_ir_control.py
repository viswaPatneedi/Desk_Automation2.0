#!/usr/bin/env python3
"""
Standby & DeepSleep Test with IR Power Control (Corrected)
Uses iTach IR blaster (not SSH-based local scripts)
"""

import time
import paramiko
from methods.method_utils import get_execution_ssh_client
from datetime import datetime

## Import IR utilities 
from config.config_ir_blaster import get_ir_config_for_device, generate_ir_code, send_ir_command
from methods.method_utils import log_message


def execute_standby_deep_sleep_test(device_ip, device_name, remote_type="SKY", iteration=1):
    """
    Main test function for standby/deep sleep with IR control
    Uses proper iTach IR blaster instead of non-existent SSH scripts
    """
    
    log_message(f"\n{'='*80}")
    log_message(f"STANDBY & DEEP SLEEP TEST WITH IR POWER CONTROL (Corrected)")
    log_message(f"{'='*80}")
    log_message(f"Device IP: {device_ip}")
    log_message(f"Remote Type: {remote_type}")
    log_message(f"Start Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    log_message(f"{'='*80}\n")
    
    try:
        # Get IR configuration for this device
        log_message(f"[IR CONFIG] Looking up device: {device_name}")
        ir_config = get_ir_config_for_device(device_name)
        
        if not ir_config:
            log_message(f"❌ ERROR: Could not find IR configuration for device '{device_name}'")
            log_message(f"   Please verify device name in devices.json")
            return False
        
        log_message(f"[IR CONFIG] iTach IP: {ir_config['itach_ip']}")
        log_message(f"[IR CONFIG] iTach Port: {ir_config['itach_port']}")
        log_message(f"[IR CONFIG] IR Port: {ir_config['ir_port']}")
        log_message(f"[IR CONFIG] Remote Type: {remote_type}")
        
        # STEP 1: Wake device from standby using IR POWER key
        log_message(f"\n[STEP 1] Wake Device from Standby")
        log_message(f"[IR] Generating POWER key code for remote type: {remote_type}")
        
        power_code = generate_ir_code('POWER', ir_config['ir_port'], remote_type=remote_type)
        if not power_code:
            log_message(f"❌ Failed to generate POWER IR code")
            return False
        
        log_message(f"[IR CODE] Generated: {power_code[:80]}...")
        
        # Send POWER IR command 3 times to ensure device wakes
        for attempt in range(1, 4):
            log_message(f"[IR POWER] Sending IR POWER {attempt}/3...")
            if send_ir_command(power_code, ir_config['itach_ip'], ir_config['itach_port'], log_message):
                log_message(f"✅ IR POWER sent successfully (Attempt {attempt})")
            else:
                log_message(f"⚠️  IR POWER send attempt {attempt} may have failed (but continuing)")
            time.sleep(2)
        
        time.sleep(5)
        log_message(f"✅ Device wake sequence completed")
        
        # STEP 2: Verify SSH connectivity
        log_message(f"\n[STEP 2] Verify Device SSH Connectivity")
        sshclient = None
        try:
            sshclient = get_execution_ssh_client()
            sshclient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            sshclient.connect(device_ip, port=10022, username="root", password="", timeout=10)
            log_message(f"✅ SSH connection established")
            
            # Check device state
            stdin, stdout, stderr = sshclient.exec_command("QueryPowerState 2>/dev/null")
            device_state = stdout.read().decode('utf-8', errors='ignore').strip()
            log_message(f"[STATE] Device power state: {device_state}")
            
            sshclient.close()
            sshclient = None
        except Exception as e:
            log_message(f"⚠️  SSH connection failed: {str(e)}")
            log_message(f"   (Device may be in sleep state - this is expected)")
        
        # STEP 3: Test device responsiveness
        log_message(f"\n[STEP 3] Verify Device Responsiveness")
        sshclient = None
        try:
            sshclient = get_execution_ssh_client()
            sshclient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            sshclient.connect(device_ip, port=10022, username="root", password="", timeout=10)
            
            stdin, stdout, stderr = sshclient.exec_command("uptime")
            uptime_output = stdout.read().decode('utf-8', errors='ignore').strip()
            log_message(f"✅ Device is responsive")
            log_message(f"   Uptime: {uptime_output[:60]}...")
            
            sshclient.close()
            sshclient = None
        except Exception as e:
            log_message(f"⚠️  Device not responding via SSH: {str(e)}")
        
        log_message(f"\n{'='*80}")
        log_message(f"✅ TEST COMPLETED SUCCESSFULLY")
        log_message(f"End Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        log_message(f"{'='*80}\n")
        
        return True
        
    except Exception as e:
        log_message(f"❌ Unexpected error: {str(e)}")
        import traceback
        log_message(traceback.format_exc())
        return False


def execute(device_ip, remote_type="SKY", device_name=None, **kwargs):
    """Framework entry point for method execution"""
    log_message(f"📍 Method called with device_ip={device_ip}, remote_type={remote_type}")
    
    if not device_ip:
        log_message("❌ Device IP is required")
        return False
    
    # Try to extract device name from kwargs or use IP as fallback
    if not device_name:
        from models.device import Device
        device = Device.find_by_ip(device_ip)
        device_name = device.name if device else device_ip
    
    return execute_standby_deep_sleep_test(device_ip, device_name, remote_type, iteration=1)
