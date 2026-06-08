#!/usr/bin/env python3
"""
Standby & Deep Sleep IR Control Process Wrapper
Wraps the standby_deep_sleep_ir_control method for test execution service
With pre-flight connectivity check and timeout protection
"""

import sys
import os
import subprocess
import threading
import time

# Add methods directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'methods'))

from standby_deep_sleep_ir_control import execute as execute_standby_method


def check_ssh_connectivity(device_ip, port=10022, username="root", password="", timeout=5):
    """
    Quick pre-flight SSH connectivity check
    Returns True if device is reachable, False otherwise
    """
    try:
        cmd = f'timeout {timeout} ssh -y -p {port} {username}@{device_ip} "echo connected" 2>&1'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout+1)
        is_connected = result.returncode == 0 and "connected" in result.stdout
        
        if is_connected:
            print(f"✅ SSH connectivity check PASSED for {device_ip}:{port}")
            return True
        else:
            print(f"❌ SSH connectivity check FAILED for {device_ip}:{port}")
            print(f"   Output: {result.stdout}")
            print(f"   Error: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"❌ SSH connectivity check TIMEOUT for {device_ip}:{port}")
        return False
    except Exception as e:
        print(f"❌ SSH connectivity check ERROR: {str(e)}")
        return False


def execute_standby_deep_sleep_ir_control_process(device_ip, port, username, password, iteration=1, device_name="Device", combined_method_name=None, remote_type=None, job_id=None, timeout_seconds=600):
    """
    Execute Standby & Deep Sleep IR Control method with timeout protection
    
    Args:
        device_ip: Device IP address
        port: SSH port
        username: SSH username
        password: SSH password
        iteration: Iteration number
        device_name: Device name for logging
        combined_method_name: Combined method name for multi-method execution
        remote_type: IR remote type (e.g., XUMO_PR3, SKY_LC103)
        job_id: Job ID for tracking
        timeout_seconds: Maximum execution time (default 10 minutes)
    
    Returns:
        dict: Result with keys {success, details, screenshots, logs}
    """
    
    # Pre-flight connectivity check
    print(f"\n[PRE-FLIGHT CHECK] Testing SSH connectivity to {device_ip}:{port}...")
    if not check_ssh_connectivity(device_ip, port, username, password, timeout=5):
        print(f"❌ Device not reachable. Aborting execution.")
        return {
            "iteration": iteration,
            "screenshots": [],
            "logs": [],
            "success": False,
            "details": f"Device {device_ip}:{port} is not reachable via SSH. Execution aborted.",
            "device_name": device_name
        }
    
    # Thread-safe result container
    result_container = {'result': None, 'completed': False}
    
    def execute_with_timeout():
        """Execute method with timeout protection"""
        try:
            # Call the method's execute function with device_ip and remote_type
            result = execute_standby_method(device_ip=device_ip, remote_type=remote_type or "SKY")
            
            # Format result for test execution service
            result_container['result'] = {
                "iteration": iteration,
                "screenshots": [],
                "logs": [],
                "success": result if isinstance(result, bool) else result.get("success", False) if isinstance(result, dict) else False,
                "details": f"Standby Deep Sleep IR Control executed with remote_type={remote_type or 'SKY'}" if (result if isinstance(result, bool) else result.get("success", False) if isinstance(result, dict) else False) else f"Method execution failed",
                "device_name": device_name
            }
            result_container['completed'] = True
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"❌ Standby Deep Sleep IR Control failed: {str(e)}")
            print(f"[ERROR-TRACE] {error_trace}")
            
            result_container['result'] = {
                "iteration": iteration,
                "screenshots": [],
                "logs": [],
                "success": False,
                "details": f"Error: {str(e)}",
                "device_name": device_name
            }
            result_container['completed'] = True
    
    # Execute in thread with timeout
    print(f"[EXECUTION] Starting method with {timeout_seconds}s timeout...")
    execution_thread = threading.Thread(target=execute_with_timeout, daemon=False)
    execution_thread.start()
    execution_thread.join(timeout=timeout_seconds)
    
    # Check if timeout occurred
    if execution_thread.is_alive():
        print(f"⏱️  TIMEOUT: Method execution exceeded {timeout_seconds}s limit")
        return {
            "iteration": iteration,
            "screenshots": [],
            "logs": [],
            "success": False,
            "details": f"Method execution timed out after {timeout_seconds}s (likely device connectivity issue or long-running operation)",
            "device_name": device_name
        }
    
    # Return result if completed
    if result_container['completed'] and result_container['result']:
        return result_container['result']
    
    # Fallback if result not set
    return {
        "iteration": iteration,
        "screenshots": [],
        "logs": [],
        "success": False,
        "details": "Method execution completed but result was not properly captured",
        "device_name": device_name
    }
