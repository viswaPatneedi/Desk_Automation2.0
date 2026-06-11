#!/usr/bin/env python3
"""
Activate Flux Widget Method Implementation
Enables Flux Server on EPG widget and extracts the Flux Server IP:port for use in other methods
"""

import sys
import time
import re
import paramiko
from datetime import datetime, timezone

# Import shared utilities
from methods.method_utils import (
    log_message,
    fetch_build_details,
    create_execution_log_path,
    get_folder_method_name
)

def activate_flux_widget(device_ip, port, username, password, iteration=1, device_name="Device", combined_method_name=None):
    """
    Activate Flux Server on EPG widget
    
    Performs the following steps:
    1. Execute combined curl command to download Flux_widget.sh
    2. Run the script and monitor for success message
    3. Extract Flux Server IP:port from output for use in other methods
    
    Args:
        device_ip: Device IP address
        port: SSH port
        username: SSH username
        password: SSH password
        iteration: Current iteration number
        device_name: Display name of device
        combined_method_name: Name for combined method execution (optional)
    
    Returns:
        Dict with iteration, logs, success status, activation details, and extracted Flux Server IP:port
    """
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    logs_list = []
    
    # Clean device name for filename
    safe_device_name = device_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    
    # Set USB log file path for this execution
    try:
        from services.log_service import LogService
        log_service = LogService()
        usb_log_path = create_execution_log_path(device_ip, device_name, iteration, "ACTIVATE_FLUX")
        log_service.current_usb_log_file = usb_log_path
        log_message(f"💾 USB execution log: {usb_log_path}")
    except Exception as e:
        log_message(f"⚠ Could not set USB log path: {e}")
    
    log_message("="*80)
    log_message("ACTIVATE FLUX WIDGET - START")
    log_message("="*80)
    
    try:
        # STEP 1: CONNECT TO DEVICE
        log_message("\n[STEP 1] Connecting to device...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(device_ip, port=port, username=username, password=password, timeout=15)
        log_message("✓ Connected to device successfully")
        
        # Fetch build details from device
        fetch_build_details(ssh, log_message)
        
        # STEP 2: DOWNLOAD AND SETUP FLUX WIDGET
        log_message("\n[STEP 2] Downloading Flux_widget.sh script...")
        download_cmd = (
            'curl -H "x-firecert-xact: `curl --header "Content-Type: application/json" --request POST '
            '--data \'{"jsonrpc":"2.0","id":"3","method": "org.rdk.AuthService.1.getAuthToken"}\' '
            'http://127.0.0.1:9998/jsonrpc | sed -nE \'s/.*"token":"([^"]*)",".*/\\1/p\'`" -L '
            'https://rdkautotool.ccp.xcal.tv/AutoVault/api/download?fileName=Automatics2dot0/Flux_widget.sh '
            '-o \'/opt/Flux_widget.sh\' -w "status_code:%{http_code}\\n" '
            '--header \'authorization: Basic YXV0b3ZhdWx0ZGV2Ok5lVmVyMm8yNUdpVmVVcEA=\' && chmod 755 /opt/Flux_widget.sh'
        )
        
        try:
            stdin, stdout, stderr = ssh.exec_command(download_cmd, timeout=60)
            download_output = stdout.read().decode('utf-8', errors='ignore').strip()
            download_error = stderr.read().decode('utf-8', errors='ignore').strip()
            exit_status = stdout.channel.recv_exit_status()
            
            if "status_code:200" in download_output:
                log_message("✓ Flux_widget.sh downloaded successfully (HTTP 200)")
            else:
                log_message(f"⚠ Download output: {download_output[-100:]}")
            
            if download_error:
                log_message(f"⚠ Download warning: {download_error[:200]}")
        
        except Exception as download_error:
            log_message(f"❌ Error downloading script: {download_error}")
            ssh.close()
            return {
                "iteration": iteration,
                "logs": logs_list,
                "success": False,
                "details": f"Failed to download Flux_widget.sh: {str(download_error)}",
                "flux_server_ip_port": None
            }
        
        # STEP 3: EXECUTE FLUX ACTIVATION SCRIPT AND MONITOR OUTPUT
        log_message("\n[STEP 3] Executing Flux activation script...")
        execute_cmd = "sh /opt/Flux_widget.sh"
        
        try:
            stdin, stdout, stderr = ssh.exec_command(execute_cmd, timeout=120)
            script_output = stdout.read().decode('utf-8', errors='ignore')
            script_error = stderr.read().decode('utf-8', errors='ignore').strip()
            exit_status = stdout.channel.recv_exit_status()
            
            log_message(f"✓ Script execution completed (Exit Status: {exit_status})")
            
            # Display script output
            if script_output:
                log_message(f"\n📤 Script Output:")
                log_message("-" * 80)
                log_message(script_output)
                log_message("-" * 80)
            
            if script_error:
                log_message(f"\n⚠ Script Errors:")
                log_message(script_error[:500])
        
        except Exception as execute_error:
            log_message(f"❌ Error executing script: {execute_error}")
            ssh.close()
            return {
                "iteration": iteration,
                "logs": logs_list,
                "success": False,
                "details": f"Failed to execute script: {str(execute_error)}",
                "flux_server_ip_port": None
            }
        
        # STEP 4: VALIDATE AND EXTRACT FLUX SERVER IP:PORT
        log_message("\n[STEP 4] Validating Flux Server activation and extracting IP:port...")
        
        # Check for success message
        success_msg = "Flux Server successfully enabled for EPG"
        activation_success = success_msg in script_output
        
        if activation_success:
            log_message(f"✓ Success message found: '{success_msg}'")
        else:
            log_message(f"❌ Success message NOT found in output")
        
        # Extract Flux Server IP:port from output
        # Looking for patterns like: "Checking Flux Server health at 100.64.11.2:8023/hi"
        flux_server_ip_port = None
        flux_ip_pattern = r'Checking Flux Server health at (\d+\.\d+\.\d+\.\d+):(\d+)/'
        matches = re.findall(flux_ip_pattern, script_output)
        
        if matches:
            # Get the last match (should be the final health check)
            last_match = matches[-1]
            flux_server_ip = last_match[0]
            flux_server_port = last_match[1]
            flux_server_ip_port = f"{flux_server_ip}:{flux_server_port}"
            
            log_message(f"✓ Extracted Flux Server IP:port: {flux_server_ip_port}")
            log_message(f"  Found {len(matches)} Flux Server reference(s) in output")
            for i, (ip, p) in enumerate(matches, 1):
                log_message(f"    [{i}] {ip}:{p}")
        else:
            log_message("⚠ Could not extract Flux Server IP:port from output")
            log_message("  Looking for pattern: 'Checking Flux Server health at <IP>:<PORT>/'")
        
        # Close SSH connection
        ssh.close()
        
        # FINAL RESULT
        log_message("\n" + "="*80)
        if activation_success:
            log_message("✓ ACTIVATE FLUX WIDGET - PASSED")
            validation_details = f"Flux Server successfully activated at {flux_server_ip_port}" if flux_server_ip_port else "Flux Server successfully activated"
        else:
            log_message("❌ ACTIVATE FLUX WIDGET - FAILED")
            validation_details = "Flux Server activation failed - success message not found in output"
        
        log_message(f"Details: {validation_details}")
        log_message("="*80)
        
        return {
            "iteration": iteration,
            "logs": logs_list,
            "success": activation_success,
            "details": validation_details,
            "flux_server_ip_port": flux_server_ip_port,
            "script_output": script_output,
            "timestamp": timestamp
        }
    
    except paramiko.SSHException as ssh_error:
        log_message(f"❌ SSH Error: {ssh_error}")
        return {
            "iteration": iteration,
            "logs": logs_list,
            "success": False,
            "details": f"SSH connection failed: {str(ssh_error)}",
            "flux_server_ip_port": None
        }
    
    except Exception as e:
        import traceback
        log_message(f"❌ Error during Flux activation: {e}")
        log_message(f"Full traceback:\n{traceback.format_exc()}")
        return {
            "iteration": iteration,
            "logs": logs_list,
            "success": False,
            "details": f"Execution error: {str(e)}",
            "flux_server_ip_port": None
        }


# Allow script to be executed standalone for testing
if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python method_activate_flux.py <device_ip> <port> <username> <password> [iteration] [device_name]")
        sys.exit(1)
    
    device_ip = sys.argv[1]
    port = int(sys.argv[2])
    username = sys.argv[3]
    password = sys.argv[4]
    iteration = int(sys.argv[5]) if len(sys.argv) > 5 else 1
    device_name = sys.argv[6] if len(sys.argv) > 6 else "Device"
    
    result = activate_flux_widget(device_ip, port, username, password, iteration, device_name)
    print("\n" + "="*80)
    print("EXECUTION RESULT")
    print("="*80)
    print(f"Success: {result['success']}")
    print(f"Details: {result['details']}")
    print(f"Flux Server IP:port: {result['flux_server_ip_port']}")
    print(f"Iteration: {result['iteration']}")

def activate_flux_widget(device_ip, port, username, password, iteration=1, device_name="Device", combined_method_name=None):
    """
    Activate Flux Server on EPG widget
    
    Performs the following steps:
    1. Get auth token from AuthService
    2. Download Flux_widget.sh script from AutoVault
    3. Execute the script to enable Flux Server
    4. Verify successful activation
    5. Perform final Flux health check
    
    Args:
        device_ip: Device IP address
        port: SSH port
        username: SSH username
        password: SSH password
        iteration: Current iteration number
        device_name: Display name of device
        combined_method_name: Name for combined method execution (optional)
    
    Returns:
        Dict with iteration, logs, success status, and activation details
    """
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    logs_list = []
    
    # Clean device name for filename
    safe_device_name = device_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    
    # Set USB log file path for this execution
    try:
        from services.log_service import LogService
        log_service = LogService()
        usb_log_path = create_execution_log_path(device_ip, device_name, iteration, "ACTIVATE_FLUX")
        log_service.current_usb_log_file = usb_log_path
        log_message(f"💾 USB execution log: {usb_log_path}")
    except Exception as e:
        log_message(f"⚠ Could not set USB log path: {e}")
    
    log_message("="*80)
    log_message("ACTIVATE FLUX WIDGET - START")
    log_message("="*80)
    
    try:
        # STEP 1: CONNECT TO DEVICE
        log_message("\n[STEP 1] Connecting to device...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(device_ip, port=port, username=username, password=password, timeout=15)
        log_message("✓ Connected to device successfully")
        
        # Fetch build details from device
        fetch_build_details(ssh, log_message)
        
        # STEP 2: GET AUTH TOKEN
        log_message("\n[STEP 2] Getting authentication token...")
        get_token_cmd = (
            'curl --header "Content-Type: application/json" --request POST '
            '--data \'{"jsonrpc":"2.0","id":"3","method": "org.rdk.AuthService.1.getAuthToken"}\' '
            'http://127.0.0.1:9998/jsonrpc | sed -nE \'s/.*"token":"([^"]*)",".*/\\1/p\''
        )
        
        try:
            stdin, stdout, stderr = ssh.exec_command(get_token_cmd, timeout=30)
            auth_token = stdout.read().decode('utf-8', errors='ignore').strip()
            token_error = stderr.read().decode('utf-8', errors='ignore').strip()
            
            if token_error:
                log_message(f"⚠ Token retrieval warning: {token_error[:200]}")
            
            if not auth_token:
                log_message("❌ ERROR: Could not retrieve authentication token")
                return {
                    "iteration": iteration,
                    "screenshots": [],
                    "logs": logs_list,
                    "success": False,
                    "details": "Failed to retrieve authentication token"
                }
            
            log_message(f"✓ Authentication token retrieved (length: {len(auth_token)})")
            log_message(f"  Token (first 20 chars): {auth_token[:20]}...")
        
        except Exception as token_error:
            log_message(f"❌ Error getting auth token: {token_error}")
            return {
                "iteration": iteration,
                "screenshots": [],
                "logs": logs_list,
                "success": False,
                "details": f"Failed to get auth token: {str(token_error)}"
            }
        
        # STEP 3: DOWNLOAD FLUX_WIDGET.SH
        log_message("\n[STEP 3] Downloading Flux_widget.sh script...")
        download_cmd = (
            'curl -H "x-firecert-xact: `curl --header "Content-Type: application/json" --request POST '
            '--data \'{"jsonrpc":"2.0","id":"3","method": "org.rdk.AuthService.1.getAuthToken"}\' '
            'http://127.0.0.1:9998/jsonrpc | sed -nE \'s/.*"token":"([^"]*)",".*/\\1/p\'`" -L '
            'https://rdkautotool.ccp.xcal.tv/AutoVault/api/download?fileName=Automatics2dot0/Flux_widget.sh '
            '-o \'/opt/Flux_widget.sh\' -w "status_code:%{http_code}\\n" '
            '--header \'authorization: Basic YXV0b3ZhdWx0ZGV2Ok5lVmVyMm8yNUdpVmVVcEA=\' && chmod 755 /opt/Flux_widget.sh'
        )
        
        try:
            stdin, stdout, stderr = ssh.exec_command(download_cmd, timeout=60)
            download_output = stdout.read().decode('utf-8', errors='ignore').strip()
            download_error = stderr.read().decode('utf-8', errors='ignore').strip()
            exit_status = stdout.channel.recv_exit_status()
            
            # Check for successful download (status_code:200)
            if "status_code:200" in download_output:
                log_message("✓ Flux_widget.sh downloaded successfully (HTTP 200)")
                log_message(f"  Download output: {download_output[-100:]}")
            else:
                # Check second download status
                if "status_code:200" not in download_output:
                    log_message("⚠ Warning: Download status unclear")
                    log_message(f"  Output: {download_output[-200:]}")
            
            if download_error:
                log_message(f"⚠ Download stderr: {download_error[:200]}")
            
            if exit_status != 0:
                log_message(f"⚠ Download command exited with status {exit_status}")
        
        except Exception as download_error:
            log_message(f"❌ Error downloading script: {download_error}")
            return {
                "iteration": iteration,
                "screenshots": [],
                "logs": logs_list,
                "success": False,
                "details": f"Failed to download Flux_widget.sh: {str(download_error)}"
            }
        
        # STEP 4: VERIFY SCRIPT EXISTS
        log_message("\n[STEP 4] Verifying script exists...")
        verify_cmd = "ls -lah /opt/Flux_widget.sh && file /opt/Flux_widget.sh"
        
        try:
            stdin, stdout, stderr = ssh.exec_command(verify_cmd, timeout=10)
            verify_output = stdout.read().decode('utf-8', errors='ignore').strip()
            
            if verify_output:
                log_message("✓ Script file verified:")
                for line in verify_output.split('\n'):
                    log_message(f"  {line}")
            else:
                log_message("❌ Script file not found")
                return {
                    "iteration": iteration,
                    "screenshots": [],
                    "logs": logs_list,
                    "success": False,
                    "details": "Flux_widget.sh script not found after download"
                }
        
        except Exception as verify_error:
            log_message(f"⚠ Error verifying script: {verify_error}")
        
        # STEP 5: EXECUTE FLUX ACTIVATION SCRIPT
        log_message("\n[STEP 5] Executing Flux activation script...")
        execute_cmd = "sh /opt/Flux_widget.sh"
        
        try:
            stdin, stdout, stderr = ssh.exec_command(execute_cmd, timeout=120)
            script_output = stdout.read().decode('utf-8', errors='ignore').strip()
            script_error = stderr.read().decode('utf-8', errors='ignore').strip()
            exit_status = stdout.channel.recv_exit_status()
            
            log_message(f"✓ Script execution completed (Exit Status: {exit_status})")
            
            # Display full script output
            if script_output:
                log_message(f"\n📤 Script Output:")
                log_message("-" * 80)
                log_message(script_output)
                log_message("-" * 80)
            
            if script_error:
                log_message(f"\n⚠ Script Error Output:")
                log_message(script_error)
        
        except Exception as execute_error:
            log_message(f"❌ Error executing script: {execute_error}")
            ssh.close()
            return {
                "iteration": iteration,
                "screenshots": [],
                "logs": logs_list,
                "success": False,
                "details": f"Failed to execute script: {str(execute_error)}"
            }
        
        # STEP 6: VALIDATE FLUX ACTIVATION
        log_message("\n[STEP 6] Validating Flux Server activation...")
        activation_success = False
        validation_details = ""
        
        # Check for success indicators in output
        success_indicators = [
            "Flux Server successfully enabled for EPG",
            "Flux Server is healthy",
            "HTTP status:200"
        ]
        
        failure_indicators = [
            "Did not find Flux Server running",
            "Flux Server not responding",
            "ERROR",
            "failed"
        ]
        
        has_success = any(indicator in script_output for indicator in success_indicators)
        has_failure = any(indicator in script_output for indicator in failure_indicators)
        
        if has_success and not has_failure:
            activation_success = True
            validation_details = "✓ Flux Server successfully activated and responding"
            log_message(f"✓ {validation_details}")
        elif has_success and has_failure:
            # Some warnings but ultimately successful
            activation_success = True
            validation_details = "⚠ Flux activation completed with warnings but server is responding"
            log_message(f"⚠ {validation_details}")
        elif has_failure:
            activation_success = False
            validation_details = "❌ Flux activation failed or server not responding"
            log_message(f"❌ {validation_details}")
        else:
            # Parse manually for Flux health check
            if "HTTP status:200" in script_output:
                activation_success = True
                validation_details = "✓ Flux Server health check successful (HTTP 200)"
                log_message(f"✓ {validation_details}")
            else:
                activation_success = False
                validation_details = "⚠ Could not determine Flux activation status from output"
                log_message(f"⚠ {validation_details}")
        
        # STEP 7: VERIFY FLUX HEALTH (OPTIONAL POST-CHECK)
        if activation_success:
            log_message("\n[STEP 7] Performing final Flux health check...")
            health_cmd = 'curl -s http://100.64.11.2:8023/hi || echo "Health check failed"'
            
            try:
                stdin, stdout, stderr = ssh.exec_command(health_cmd, timeout=15)
                health_output = stdout.read().decode('utf-8', errors='ignore').strip()
                
                if health_output and "Health check failed" not in health_output:
                    log_message(f"✓ Flux health check passed: {health_output[:100]}")
                else:
                    log_message(f"⚠ Flux health check result: {health_output[:100]}")
            except Exception as health_error:
                log_message(f"⚠ Error during health check: {health_error}")
        
        # Close SSH connection
        ssh.close()
        
        # FINAL RESULT
        log_message("\n" + "="*80)
        if activation_success:
            log_message("✓ ACTIVATE FLUX WIDGET - PASSED")
        else:
            log_message("⚠ ACTIVATE FLUX WIDGET - COMPLETED WITH WARNINGS")
        log_message(f"✓ {validation_details}")
        log_message("="*80)
        
        return {
            "iteration": iteration,
            "screenshots": [],
            "logs": logs_list,
            "success": activation_success,
            "details": validation_details,
            "script_output_summary": script_output[-500:] if script_output else "",
            "timestamp": timestamp
        }
    
    except paramiko.SSHException as ssh_error:
        log_message(f"❌ SSH Error: {ssh_error}")
        return {
            "iteration": iteration,
            "screenshots": [],
            "logs": logs_list,
            "success": False,
            "details": f"SSH connection failed: {str(ssh_error)}"
        }
    
    except Exception as e:
        import traceback
        log_message(f"❌ Error during Flux activation: {e}")
        log_message(f"Full traceback:\n{traceback.format_exc()}")
        return {
            "iteration": iteration,
            "screenshots": [],
            "logs": logs_list,
            "success": False,
            "details": f"Execution error: {str(e)}"
        }


# Allow script to be executed standalone for testing
if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python method_activate_flux.py <device_ip> <port> <username> <password> [iteration] [device_name]")
        sys.exit(1)
    
    device_ip = sys.argv[1]
    port = int(sys.argv[2])
    username = sys.argv[3]
    password = sys.argv[4]
    iteration = int(sys.argv[5]) if len(sys.argv) > 5 else 1
    device_name = sys.argv[6] if len(sys.argv) > 6 else "Device"
    
    result = activate_flux_widget(device_ip, port, username, password, iteration, device_name)
    print("\n" + "="*80)
    print("EXECUTION RESULT")
    print("="*80)
    print(f"Success: {result['success']}")
    print(f"Details: {result['details']}")
    print(f"Iteration: {result['iteration']}")
    print(f"Screenshots: {len(result['screenshots'])} captured")
