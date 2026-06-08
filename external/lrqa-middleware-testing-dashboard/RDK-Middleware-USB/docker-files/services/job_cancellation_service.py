"""
Job Cancellation Service - Handle graceful and forceful termination of running jobs
"""

import paramiko
import time
from typing import Tuple, Optional
from services.ssh_connection_helper import SSHConnectionHelper
from models.device import Device
from services.jump_host_service import JumpHostService

class JobCancellationService:
    """Service for cancelling jobs and terminating running processes on devices"""
    
    # Process names that might be running job executions
    PYTHON_PROCESS_PATTERNS = [
        'method_reboot.py',
        'method_deepsleep.py',
        'method_voice_command.py',
        'method_navigate_inputs.py',
        'method_screen_validation.py',
        'method_ir_test.py',
        'method_system_command.py',
        'python.*app.py',
        'pytest',
        'automation',
        'test_execution'
    ]
    
    @staticmethod
    def kill_job_process_on_device(device_ip: str, device_name: str, 
                                   username: str, password: str, port: int = 10022,
                                   use_jump_host: bool = False, jump_host_config: dict = None) -> Tuple[bool, str]:
        """
        Kill running job process on device
        
        Args:
            device_ip: Device IP address
            device_name: Device name
            username: SSH username
            password: SSH password
            port: SSH port
            use_jump_host: Whether to use jump host
            jump_host_config: Jump host configuration
            
        Returns:
            Tuple of (success, message)
        """
        try:
            print(f"🔄 Attempting to terminate running processes on {device_name} ({device_ip})...")
            
            # Try to get list of running Python processes
            success, pids = JobCancellationService._find_running_job_processes(
                device_ip, username, password, port, use_jump_host, jump_host_config
            )
            
            if not success:
                print(f"⚠ Could not enumerate processes on device: {pids}")
                # Still try to kill generic processes
                return JobCancellationService._kill_all_method_processes(
                    device_ip, username, password, port, use_jump_host, jump_host_config
                )
            
            if not pids:
                print(f"ℹ No running job processes found on {device_name}")
                return True, "No running job processes found"
            
            # Kill the processes
            print(f"📋 Found PIDs: {pids}")
            return JobCancellationService._kill_processes_by_pid(
                device_ip, pids, username, password, port, use_jump_host, jump_host_config
            )
            
        except Exception as e:
            print(f"❌ Error terminating processes: {str(e)}")
            return False, str(e)
    
    @staticmethod
    def _find_running_job_processes(device_ip: str, username: str, password: str, port: int,
                                    use_jump_host: bool, jump_host_config: dict) -> Tuple[bool, list]:
        """
        Find PIDs of running job processes
        
        Returns:
            Tuple of (success, list_of_pids_or_error_message)
        """
        try:
            # Build ps command to find Python processes
            command = r"ps aux | grep -E '(python.*method_|python.*app\.py|pytest|automation)' | grep -v grep"
            
            success, output = JobCancellationService._execute_command_on_device(
                device_ip, command, username, password, port, use_jump_host, jump_host_config
            )
            
            if not success:
                return False, output
            
            if not output.strip():
                return True, []
            
            # Parse PIDs from ps output
            pids = []
            for line in output.strip().split('\n'):
                if line.strip():
                    parts = line.split()
                    if len(parts) > 1:
                        try:
                            pid = int(parts[1])
                            pids.append(pid)
                        except (ValueError, IndexError):
                            pass
            
            return True, pids
            
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def _kill_processes_by_pid(device_ip: str, pids: list, username: str, password: str, 
                               port: int, use_jump_host: bool, jump_host_config: dict) -> Tuple[bool, str]:
        """
        Kill processes by PID using SIGTERM then SIGKILL
        
        Returns:
            Tuple of (success, message)
        """
        killed_count = 0
        failed_pids = []
        
        for pid in pids:
            try:
                # Try SIGTERM first (graceful)
                print(f"  Sending SIGTERM to PID {pid}...")
                command = f"kill -TERM {pid}"
                success, output = JobCancellationService._execute_command_on_device(
                    device_ip, command, username, password, port, use_jump_host, jump_host_config
                )
                
                if success:
                    killed_count += 1
                    # Wait a bit for graceful termination
                    time.sleep(1)
                    
                    # Check if process still exists
                    check_cmd = f"kill -0 {pid} 2>/dev/null && echo 'alive' || echo 'dead'"
                    success, check_output = JobCancellationService._execute_command_on_device(
                        device_ip, check_cmd, username, password, port, use_jump_host, jump_host_config
                    )
                    
                    if check_output.strip() == 'alive':
                        print(f"  Process {pid} still alive, sending SIGKILL...")
                        kill_cmd = f"kill -9 {pid}"
                        JobCancellationService._execute_command_on_device(
                            device_ip, kill_cmd, username, password, port, use_jump_host, jump_host_config
                        )
                        print(f"  ✓ Forcefully killed PID {pid}")
                    else:
                        print(f"  ✓ Gracefully terminated PID {pid}")
                else:
                    failed_pids.append(pid)
                    
            except Exception as e:
                print(f"  ❌ Error killing PID {pid}: {str(e)}")
                failed_pids.append(pid)
        
        message = f"Terminated {killed_count} running job process(es)"
        if failed_pids:
            message += f". Failed to terminate: {failed_pids}"
            return False, message
        
        return True, message
    
    @staticmethod
    def _kill_all_method_processes(device_ip: str, username: str, password: str, port: int,
                                   use_jump_host: bool, jump_host_config: dict) -> Tuple[bool, str]:
        """
        Kill all method execution processes (fallback approach)
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Use killall to terminate all Python method processes
            command = "killall -9 python3 2>/dev/null; true"
            
            success, output = JobCancellationService._execute_command_on_device(
                device_ip, command, username, password, port, use_jump_host, jump_host_config
            )
            
            if success:
                return True, "Killed all Python processes on device"
            else:
                return False, output
                
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def _execute_command_on_device(device_ip: str, command: str, username: str, password: str,
                                   port: int, use_jump_host: bool, jump_host_config: dict) -> Tuple[bool, str]:
        """
        Execute command on device via SSH
        
        Returns:
            Tuple of (success, output)
        """
        try:
            if use_jump_host and jump_host_config:
                return JobCancellationService._execute_via_jump_host(
                    device_ip, command, jump_host_config
                )
            else:
                return JobCancellationService._execute_direct_ssh(
                    device_ip, command, username, password, port
                )
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def _execute_direct_ssh(device_ip: str, command: str, username: str, 
                           password: str, port: int) -> Tuple[bool, str]:
        """
        Execute command via direct SSH
        
        Returns:
            Tuple of (success, output)
        """
        ssh = None
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            ssh.connect(
                hostname=device_ip,
                port=port,
                username=username,
                password=password,
                timeout=10,
                banner_timeout=10,
                auth_timeout=10
            )
            
            stdin, stdout, stderr = ssh.exec_command(command, timeout=10)
            output = stdout.read().decode('utf-8', errors='ignore')
            error = stderr.read().decode('utf-8', errors='ignore')
            
            ssh.close()
            
            if error:
                # Some commands write to stderr but still succeed
                return True, output or error
            
            return True, output
            
        except Exception as e:
            return False, str(e)
        finally:
            if ssh:
                try:
                    ssh.close()
                except:
                    pass
    
    @staticmethod
    def _execute_via_jump_host(device_ip: str, command: str, jump_host_config: dict) -> Tuple[bool, str]:
        """
        Execute command via jump host
        
        Returns:
            Tuple of (success, output)
        """
        try:
            jump_service = JumpHostService(jump_host_config)
            
            # For jump host, we need the device MAC  
            # For now, use the IP to identify the device
            success, output = jump_service.execute_command_simple(
                device_ip, command, timeout=10
            )
            
            return success, output
            
        except Exception as e:
            return False, str(e)
