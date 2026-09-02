"""
Check Available Logs Method - Validate logs on device based on log patterns
Fetches latest log patterns from log_patterns.json and allows user to select specific patterns to check
"""

import paramiko
from methods.method_utils import get_execution_ssh_client
import time
import json
import os
from datetime import datetime, timezone
from methods.method_utils import log_message, create_execution_log_path, fetch_build_details


def get_available_logs():
    """
    Fetch all available log patterns from log_patterns.json
    Returns: dict with log patterns and system commands categorized
    """
    try:
        with open('log_patterns.json', 'r') as f:
            patterns_data = json.load(f)
        
        return {
            'log_patterns': patterns_data.get('LOG_PATTERNS', {}),
            'system_commands': patterns_data.get('SYSTEM_COMMAND_PATTERNS', {}),
            'status': 'success'
        }
    except Exception as e:
        return {
            'log_patterns': {},
            'system_commands': {},
            'status': 'error',
            'error': str(e)
        }


def execute_check_logs(device_ip, port, username, password, iteration=1, device_name="Device",
                      selected_patterns=None, log_callback=None, job_id=None):
    """
    Execute log validation - Check selected log patterns on device
    
    Args:
        device_ip: Device IP address
        port: SSH port
        username: SSH username
        password: SSH password
        iteration: Iteration number
        device_name: Device name for logging
        selected_patterns: List of pattern names to check (e.g., ['HOME', 'Network_Error', 'Process_Crash'])
        log_callback: Callback function for logging
        job_id: Job ID for tracking
    
    Returns:
        dict: {
            'success': bool,
            'details': str,
            'log_results': dict,
            'logs': list,
            'archive_path': str (if logs collected),
            'matched_patterns': list
        }
    """
    def log_msg(msg):
        print(msg)
        if log_callback:
            log_callback(msg)
    
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    screenshots_list = []
    logs_list = []
    
    # Initialize result dict
    result = {
        'success': False,
        'details': '',
        'log_results': {},
        'matched_patterns': [],
        'logs': logs_list
    }
    
    try:
        # Set USB log file path
        from services.log_service import LogService
        log_service = LogService()
        usb_log_path = create_execution_log_path(device_ip, device_name, iteration, "CHECK_LOGS")
        log_service.current_usb_log_file = usb_log_path
        
        # Header
        log_msg("="*80)
        log_msg("LOG VALIDATION - START")
        log_msg("="*80)
        log_msg(f"Device: {device_name} ({device_ip})")
        log_msg(f"Iteration: {iteration}")
        log_msg(f"Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        log_msg("")
        
        # Load available log patterns
        available_logs = get_available_logs()
        if available_logs['status'] != 'success':
            log_msg(f"⚠ Warning: Could not load log patterns from log_patterns.json")
            log_msg(f"  Error: {available_logs.get('error', 'Unknown error')}")
        
        all_log_patterns = available_logs.get('log_patterns', {})
        all_system_commands = available_logs.get('system_commands', {})
        
        log_msg(f"📋 Available log patterns: {list(all_log_patterns.keys())}")
        log_msg(f"📋 Available system commands: {list(all_system_commands.keys())}")
        log_msg("")
        
        # If no patterns selected, warn user
        if not selected_patterns:
            log_msg("⚠ No log patterns selected for validation")
            log_msg("")
            result['details'] = "No log patterns selected"
            return result
        
        log_msg(f"[STEP 1] Connecting to device...")
        # Establish SSH connection
        ssh = get_execution_ssh_client()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(device_ip, port=port, username=username, password=password, timeout=15)
        log_msg("✓ Connected to device successfully")
        log_msg("")
        
        log_msg(f"[STEP 2] Checking {len(selected_patterns)} selected pattern(s)...")
        
        # Check each selected pattern
        for pattern_name in selected_patterns:
            log_msg(f"\n  Checking pattern: {pattern_name}")
            
            # Determine if it's a log pattern or system command
            if pattern_name in all_log_patterns:
                pattern_data = all_log_patterns[pattern_name]
                log_pattern = pattern_data.get('log_pattern', '')
                file_path = pattern_data.get('file_path', '/opt/logs/sky-messages.log')
                description = pattern_data.get('description', '')
                
                if log_pattern and file_path:
                    # Execute grep command for log pattern
                    check_cmd = f"grep -E \"{log_pattern}\" \"{file_path}\" | head -20"
                    
                    try:
                        stdin, stdout, stderr = ssh.exec_command(check_cmd)
                        output = stdout.read().decode('utf-8', errors='ignore')
                        error = stderr.read().decode('utf-8', errors='ignore')
                        
                        if output.strip():
                            result['log_results'][pattern_name] = {
                                'found': True,
                                'count': len(output.strip().split('\n')),
                                'sample_output': output.strip().split('\n')[:5],
                                'file_path': file_path
                            }
                            result['matched_patterns'].append(pattern_name)
                            log_msg(f"    ✓ Found {result['log_results'][pattern_name]['count']} match(es)")
                            log_msg(f"    File: {file_path}")
                        else:
                            result['log_results'][pattern_name] = {
                                'found': False,
                                'count': 0,
                                'file_path': file_path
                            }
                            log_msg(f"    ✗ No matches found")
                            log_msg(f"    File: {file_path}")
                    except Exception as e:
                        result['log_results'][pattern_name] = {
                            'found': False,
                            'error': str(e)
                        }
                        log_msg(f"    ❌ Error checking pattern: {e}")
                else:
                    log_msg(f"    ⚠ Pattern incomplete (log_pattern or file_path missing)")
            
            elif pattern_name in all_system_commands:
                command_data = all_system_commands[pattern_name]
                command = command_data.get('command', '')
                description = command_data.get('description', '')
                
                if command:
                    # Execute system command (e.g., 'top', 'df', 'free')
                    try:
                        stdin, stdout, stderr = ssh.exec_command(command)
                        output = stdout.read().decode('utf-8', errors='ignore')
                        error = stderr.read().decode('utf-8', errors='ignore')
                        
                        if output.strip():
                            result['log_results'][pattern_name] = {
                                'type': 'system_command',
                                'command': command,
                                'output': output.strip().split('\n')[:20],
                                'error': error if error else None
                            }
                            log_msg(f"    ✓ Command executed successfully")
                            log_msg(f"    Output lines: {len(output.strip().split(chr(10)))}")
                        else:
                            result['log_results'][pattern_name] = {
                                'type': 'system_command',
                                'command': command,
                                'output': [],
                                'error': error if error else 'No output'
                            }
                            log_msg(f"    ⚠ Command executed (no output)")
                    except Exception as e:
                        result['log_results'][pattern_name] = {
                            'type': 'system_command',
                            'command': command,
                            'error': str(e)
                        }
                        log_msg(f"    ❌ Error executing command: {e}")
                else:
                    log_msg(f"    ⚠ System command incomplete (command missing)")
            else:
                log_msg(f"    ⚠ Pattern not found in available patterns")
        
        log_msg("")
        log_msg(f"[STEP 3] Collecting device logs if patterns matched...")
        
        # If any patterns matched, collect device logs
        if result['matched_patterns']:
            log_msg(f"\n  📋 Found {len(result['matched_patterns'])} matching pattern(s): {result['matched_patterns']}")
            
            try:
                # Create /media/apps directory
                mkdir_cmd = "mkdir -p /media/apps && echo 'DIR_READY'"
                stdin, stdout, stderr = ssh.exec_command(mkdir_cmd)
                mkdir_output = stdout.read().decode('utf-8', errors='ignore').strip()
                
                if 'DIR_READY' in mkdir_output:
                    # Collect logs
                    safe_device_name = device_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
                    remote_log_archive = f"/media/apps/{device_ip}_{safe_device_name}_ITR-{iteration}_CHECK_LOGS_{timestamp}.tar.gz"
                    
                    log_msg(f"  Compressing logs to: {remote_log_archive}")
                    
                    compress_cmd = f"tar -czf {remote_log_archive} -C /opt logs/ 2>&1 && ls -lh {remote_log_archive}"
                    stdin, stdout, stderr = ssh.exec_command(compress_cmd)
                    compress_output = stdout.read().decode('utf-8', errors='ignore').strip()
                    
                    if compress_output and remote_log_archive in compress_output:
                        # Extract file size
                        file_info = compress_output.split('\n')[-1]
                        result['archive_path'] = remote_log_archive
                        log_msg(f"  ✓ Logs collected successfully")
                        log_msg(f"    Archive: {compress_output}")
                    else:
                        log_msg(f"  ⚠ Log collection completed but could not verify archive")
                else:
                    log_msg(f"  ⚠ Could not create /media/apps directory")
            except Exception as e:
                log_msg(f"  ❌ Error collecting logs: {e}")
        else:
            log_msg("  No matching patterns - skipping log collection")
        
        # Close SSH connection
        ssh.close()
        log_msg("")
        
        # Final summary
        log_msg("[STEP 4] Summary")
        log_msg(f"  Total patterns checked: {len(selected_patterns)}")
        log_msg(f"  Patterns matched: {len(result['matched_patterns'])}")
        log_msg(f"  Patterns not matched: {len(selected_patterns) - len(result['matched_patterns'])}")
        
        result['success'] = True
        result['details'] = f"Checked {len(selected_patterns)} patterns, found {len(result['matched_patterns'])} matches"
        
        log_msg("")
        log_msg("="*80)
        log_msg("LOG VALIDATION - COMPLETE")
        log_msg("="*80)
        
        return result
    
    except paramiko.AuthenticationException:
        error_msg = "❌ Authentication failed - Invalid credentials"
        log_msg(error_msg)
        result['details'] = error_msg
        return result
    
    except paramiko.SSHException as e:
        error_msg = f"❌ SSH Error: {str(e)}"
        log_msg(error_msg)
        result['details'] = error_msg
        return result
    
    except Exception as e:
        error_msg = f"❌ Unexpected error: {str(e)}"
        log_msg(error_msg)
        import traceback
        log_msg(f"  Traceback: {traceback.format_exc()}")
        result['details'] = error_msg
        return result
