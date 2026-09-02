"""
Execute System Command Method
Execute system commands on device via SSH (e.g., systemctl restart ermgr)
"""

import time
import paramiko
from methods.method_utils import get_execution_ssh_client
import socket
import re
from datetime import datetime, timezone

from methods.method_utils import (
    log_message,
    get_folder_method_name,
    get_lexar_base_path
)
import os


def _get_execute_command_log_path(device_ip, device_name, iteration, method_folder=None):
    current_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    safe_device_name = device_name.replace(' ', '-').replace('/', '_').replace('\\', '_').replace('__', '_').replace('--', '-').upper()
    safe_ip = device_ip.replace('.', '-')
    device_folder = f"{safe_ip}_{safe_device_name}"
    folder_name = (method_folder or "EXECUTE_COMMAND").replace(' ', '_')
    itr_dir = os.path.join(get_lexar_base_path(), "EXECUTION_LOGS", current_date, device_folder, folder_name, f"ITR-{iteration}")
    os.makedirs(itr_dir, exist_ok=True)
    return os.path.join(itr_dir, f"EXECUTE_COMMAND_ITR_{iteration}.log")


def execute_system_command(device_ip, port, username, password, command_text, iteration=1, device_name="Device",
                          combined_method_name=None, log_callback=None, expected_output=None, validation_type=None):
    """
    Execute a system command on the device via SSH.
    
    Args:
        device_ip: Device IP address
        port: SSH port
        username: SSH username
        password: SSH password
        command_text: System command to execute (e.g., "systemctl restart ermgr")
        iteration: Iteration number
        device_name: Device name
        combined_method_name: Combined method name for sequence context
        log_callback: Optional callback for logging
        expected_output: Optional expected output to validate (for conditional checks)
        validation_type: Type of validation:
            - 'contains' (default): output should contain the text
            - 'exact': output should match exactly
            - 'not_contains': output should NOT contain the text
            - 'regex': output should match the regex pattern
            - 'not_regex': output should NOT match the regex pattern (useful for multiple patterns with alternation)
            - 'null': output should be empty (no value returned from command)
            - 'not_null': output should NOT be empty (command returns some value)
    
    Returns:
        dict: {
            'success': bool,
            'details': str,
            'output': str,
            'command': str,
            'exit_code': int,
            'logs': list,
            'validation_passed': bool (if expected_output provided)
        }
    """
    
    def log_message_wrapper(msg):
        print(msg)
        if log_callback:
            log_callback(msg)
    
    start_time = datetime.now(timezone.utc)
    method_folder = get_folder_method_name() or combined_method_name or None
    log_file = _get_execute_command_log_path(device_ip, device_name, iteration, method_folder)
    logs = []
    
    try:
        log_message_wrapper(f"EXECUTE_COMMAND - START")
        log_message_wrapper(f"Device: {device_name} ({device_ip}:{port})")
        log_message_wrapper(f"Command: {command_text}")
        
        if not command_text or not command_text.strip():
            msg = "No command provided"
            log_message_wrapper(f"❌ {msg}")
            return {
                'success': False,
                'details': msg,
                'output': '',
                'command': '',
                'exit_code': -1,
                'logs': logs,
                'validation_passed': False
            }
        
        # Connect to device via SSH
        ssh = get_execution_ssh_client()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        log_message_wrapper(f"🔌 Connecting to {device_ip}:{port}...")
        ssh.connect(device_ip, port=int(port), username=username, password=password, timeout=30)
        log_message_wrapper(f"✓ Connected to device")
        logs.append(f"Connected to {device_ip}:{port}")
        
        # Execute command directly without login shell to avoid profile sourcing delays
        log_message_wrapper(f"\n📝 Executing command: {command_text}")
        # Direct execution is faster than bash -l -c which sources all profiles (adds 30-60s delay)
        # For commands needing specific PATH, use explicit PATH if needed
        
        # Check if command needs extended PATH (mount-copybind usually available globally)
        command_lower = command_text.lower()
        if 'mount-copybind' in command_lower:
            # Add explicit PATH for mount-copybind if needed
            wrapped_command = f'bash -c "export PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH; {command_text}"'
            log_message_wrapper(f"ℹ️  Using bash with explicit PATH for mount-copybind")
        else:
            # Execute directly without login shell wrapper for fast execution
            wrapped_command = command_text
        
        # Determine timeout based on command type and complexity
        if any(keyword in command_lower for keyword in ['grep', 'cat /opt/logs', 'cat /var/log', 'find']):
            # File search operations: typically complete in seconds (user test: 6s)
            command_timeout = 60  # 60s is safe margin for grep/cat/find operations
            log_message_wrapper(f"⏱️  Using standard timeout (60s) for file search")
        elif 'top' in command_lower:
            command_timeout = 120  # TOP collections need more time
        else:
            command_timeout = 30  # 30 seconds for quick commands
        
        stdin, stdout, stderr = ssh.exec_command(wrapped_command, timeout=command_timeout)
        
        # Read output and error
        output = stdout.read().decode('utf-8', errors='ignore')
        error = stderr.read().decode('utf-8', errors='ignore')
        exit_code = stdout.channel.recv_exit_status()
        
        log_message_wrapper(f"⏱️  Exit Code: {exit_code}")
        logs.append(f"Exit Code: {exit_code}")
        
        if output.strip():
            log_message_wrapper(f"\n📤 Command Output:")
            for line in output.strip().split('\n'):
                log_message_wrapper(f"  {line}")
                logs.append(line)
        
        if error.strip():
            log_message_wrapper(f"\n⚠️  Stderr:")
            for line in error.strip().split('\n'):
                log_message_wrapper(f"  {line}")
                logs.append(f"[STDERR] {line}")
        
        ssh.close()
        
        # Determine success based on exit code
        # Exit code 0 = success
        # Exit code 1 with grep = success (no matches is valid result)
        # Exit code 1 with cat/other info commands = success (command executed)
        # Exit code > 1 = failure (actual error)
        success = exit_code == 0
        
        # For grep, cat, and other informational commands that return 1 on no-match/no-error
        if exit_code == 1 and ('grep' in command_text.lower() or 
                               'cat' in command_text.lower() or 
                               'find' in command_text.lower() or
                               'ls' in command_text.lower()):
            # Check if it's a shell error (no stderr = success)
            if not error.strip() or 'command not found' not in error.lower():
                success = True
                details = f"Command executed successfully (no matches/no results - exit code: {exit_code})"
            else:
                success = False
                details = f"Command failed with exit code: {exit_code}"
        else:
            details = f"Command executed successfully (exit code: {exit_code})" if success else f"Command failed with exit code: {exit_code}"
        
        # STEP 2: VALIDATE OUTPUT IF EXPECTED OUTPUT PROVIDED
        validation_passed = True
        if expected_output and validation_type:
            log_message_wrapper(f"\n[VALIDATION] Checking output against expected result...")
            log_message_wrapper(f"Expected output: '{expected_output}'")
            log_message_wrapper(f"Validation type: {validation_type}")
            
            if validation_type == "contains":
                # Check if expected output is contained in command output
                if expected_output in output:
                    validation_passed = True
                    log_message_wrapper(f"✓ Output CONTAINS expected text: '{expected_output}'")
                else:
                    validation_passed = False
                    log_message_wrapper(f"❌ Output does NOT contain expected text: '{expected_output}'")
                    log_message_wrapper(f"   Actual output (first 500 chars): {output[:500]}")
            
            elif validation_type == "exact":
                # Check for exact match
                if output.strip() == expected_output.strip():
                    validation_passed = True
                    log_message_wrapper(f"✓ Output EXACTLY matches expected text")
                else:
                    validation_passed = False
                    log_message_wrapper(f"❌ Output does NOT match expected text exactly")
                    log_message_wrapper(f"   Expected: '{expected_output}'")
                    log_message_wrapper(f"   Got:      '{output.strip()[:200]}{'...' if len(output) > 200 else ''}'")
            
            elif validation_type == "not_contains":
                # Check that output does NOT contain the text
                if expected_output not in output:
                    validation_passed = True
                    log_message_wrapper(f"✓ Output correctly does NOT contain: '{expected_output}'")
                else:
                    validation_passed = False
                    log_message_wrapper(f"❌ Output incorrectly CONTAINS: '{expected_output}'")
            
            elif validation_type == "regex":
                # Check if regex pattern matches in command output
                try:
                    if re.search(expected_output, output):
                        validation_passed = True
                        log_message_wrapper(f"✓ Output MATCHES regex pattern: '{expected_output}'")
                    else:
                        validation_passed = False
                        log_message_wrapper(f"❌ Output does NOT match regex pattern: '{expected_output}'")
                        log_message_wrapper(f"   Actual output (first 500 chars): {output[:500]}")
                except re.error as regex_err:
                    validation_passed = False
                    log_message_wrapper(f"❌ Invalid regex pattern: {regex_err}")
                    log_message_wrapper(f"   Pattern: '{expected_output}'")
            
            elif validation_type == "not_regex":
                # Check that regex pattern does NOT match in command output (inverse of regex)
                # Useful for validating that unwanted patterns are absent
                try:
                    if re.search(expected_output, output):
                        validation_passed = False
                        log_message_wrapper(f"❌ Validation FAILED: Output MATCHES unwanted regex pattern: '{expected_output}'")
                    else:
                        validation_passed = True
                        log_message_wrapper(f"✓ Validation PASSED: Output does NOT contain unwanted pattern: '{expected_output}'")
                except re.error as regex_err:
                    validation_passed = False
                    log_message_wrapper(f"❌ Invalid regex pattern: {regex_err}")
                    log_message_wrapper(f"   Pattern: '{expected_output}'")
            
            elif validation_type == "null":
                # Check if output is empty (no value returned)
                if not output.strip():
                    validation_passed = True
                    log_message_wrapper(f"✓ Output is NULL (empty) - validation PASSED")
                else:
                    validation_passed = False
                    log_message_wrapper(f"❌ Output is NOT NULL - validation FAILED")
                    log_message_wrapper(f"   Actual output: {output[:200]}")
            
            elif validation_type == "not_null":
                # Check if output is NOT empty (has some value)
                if output.strip():
                    validation_passed = True
                    log_message_wrapper(f"✓ Output is NOT NULL - validation PASSED")
                    log_message_wrapper(f"   Output (first 200 chars): {output[:200]}")
                else:
                    validation_passed = False
                    log_message_wrapper(f"❌ Output is NULL (empty) - validation FAILED")
            
            else:
                validation_passed = False
                log_message_wrapper(f"❌ Unknown validation type: '{validation_type}'")
            
            # Update success based on validation result
            success = success and validation_passed
            if not validation_passed:
                details = f"Command executed but output validation FAILED: {details}"
        elif validation_type and not expected_output:
            # Handle case where validation_type is specified but no expected_output given
            log_message_wrapper(f"\n[VALIDATION] Validation type specified: {validation_type} (without expected output)")
            
            if validation_type == "null":
                # Check if output is empty
                if not output.strip():
                    validation_passed = True
                    log_message_wrapper(f"✓ Output is NULL (empty) - validation PASSED")
                else:
                    validation_passed = False
                    log_message_wrapper(f"❌ Output is NOT NULL - validation FAILED")
                    log_message_wrapper(f"   Actual output: {output[:200]}")
            
            elif validation_type == "not_null":
                # Check if output is NOT empty
                if output.strip():
                    validation_passed = True
                    log_message_wrapper(f"✓ Output is NOT NULL - validation PASSED")
                    log_message_wrapper(f"   Output (first 200 chars): {output[:200]}")
                else:
                    validation_passed = False
                    log_message_wrapper(f"❌ Output is NULL (empty) - validation FAILED")
            
            success = success and validation_passed
            if not validation_passed:
                details = f"Command executed but output validation FAILED: {details}"
        
        log_message_wrapper(f"\n{'✓' if success else '✗'} {details}")
        
        # Write to log file
        with open(log_file, 'w') as f:
            f.write(f"EXECUTE_COMMAND - ITR {iteration}\n")
            f.write(f"Device: {device_name} ({device_ip}:{port})\n")
            f.write(f"Command: {command_text}\n")
            f.write(f"Exit Code: {exit_code}\n")
            f.write(f"Timestamp: {start_time.isoformat()}\n")
            f.write(f"\n--- Output ---\n")
            f.write(output)
            if error.strip():
                f.write(f"\n--- Stderr ---\n")
                f.write(error)
        
        log_message_wrapper(f"📄 Log saved to: {log_file}")
        
        return {
            'success': success,
            'details': details,
            'output': output,
            'error': error,
            'command': command_text,
            'exit_code': exit_code,
            'logs': logs,
            'validation_passed': validation_passed
        }
    
    except paramiko.AuthenticationException as e:
        msg = f"SSH Authentication failed: {str(e)}"
        log_message_wrapper(f"❌ {msg}")
        return {
            'success': False,
            'details': msg,
            'output': '',
            'command': command_text,
            'exit_code': -1,
            'logs': logs,
            'validation_passed': False
        }
    
    except paramiko.SSHException as e:
        msg = f"SSH connection error: {str(e)}"
        log_message_wrapper(f"❌ {msg}")
        return {
            'success': False,
            'details': msg,
            'output': '',
            'command': command_text,
            'exit_code': -1,
            'logs': logs,
            'validation_passed': False
        }
    
    except socket.timeout as e:
        msg = f"Command execution timeout after {command_timeout} seconds - likely searching large log file or slow operation"
        log_message_wrapper(f"❌ {msg}")
        log_message_wrapper(f"   Original error: {str(e)}")
        return {
            'success': False,
            'details': msg,
            'output': '',
            'command': command_text,
            'exit_code': -1,
            'logs': logs,
            'validation_passed': False
        }
    
    except Exception as e:
        import traceback
        msg = f"Error executing command: {str(e)}"
        log_message_wrapper(f"❌ {msg}")
        log_message_wrapper(f"   Exception type: {type(e).__name__}")
        log_message_wrapper(f"   Traceback: {traceback.format_exc()}")
        return {
            'success': False,
            'details': msg,
            'output': '',
            'command': command_text,
            'exit_code': -1,
            'logs': logs,
            'validation_passed': False
        }
