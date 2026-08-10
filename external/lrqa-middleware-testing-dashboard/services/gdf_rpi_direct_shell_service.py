#!/usr/bin/env python3
"""
GDF R-Pi Direct Shell Service - Shared Connection Approach
Establishes single SSH connection to R-Pi, then all devices connect through it directly

Connection Flow:
1. ssh -p 60201 pi@10.138.17.42         (Create R-Pi shell connection - SHARED)
2. (Inside R-Pi shell)
3. ssh -p 10022 root@10.0.0.28 "cmd"    (Device 1 connects through R-Pi)
4. ssh -p 10022 root@10.0.0.140 "cmd"   (Device 2 connects through R-Pi - SIMULTANEOUS)

This approach:
- One shared R-Pi SSH connection per R-Pi (not per device)
- Multiple devices execute SIMULTANEOUSLY through same R-Pi connection
- NO local port forwarding conflicts
- No 127.0.0.1:port conflicts since each device has real IP
- R-Pi connection stays alive across multiple device actions
"""

import paramiko
import subprocess
import time
import threading
from typing import Tuple, Dict, Optional, Any
from io import StringIO


class GDFRPiDirectShellService:
    """
    Manages single SSH connection to R-Pi and executes device commands through it.
    Designed to be SHARED across multiple device executions on the same R-Pi.
    """
    
    def __init__(self, rpi_config: Dict, device_identifier: str = "Generic"):
        """
        Initialize GDF R-Pi Direct Shell Service
        
        Args:
            rpi_config: R-Pi configuration dict with keys:
                - rpi_ip: R-Pi IP address (e.g., 10.138.17.42)
                - rpi_port: R-Pi SSH port (default: 60201)
                - rpi_username: R-Pi SSH username (e.g., pi)
                - rpi_password: R-Pi SSH password
            
            device_identifier: Name/identifier for logging (e.g., device name)
        """
        # R-Pi Configuration
        self.rpi_ip = rpi_config.get('rpi_ip')
        self.rpi_port = int(rpi_config.get('rpi_port', 60201))
        self.rpi_username = rpi_config.get('rpi_username')
        self.rpi_password = rpi_config.get('rpi_password')
        
        # Connection State
        self.device_identifier = device_identifier
        self.ssh_client = None
        self.is_connected = False
        self.lock = threading.Lock()
        
        # Connection stats
        self.connection_established_at = None
        self.commands_executed = 0
        self.last_command_result = None
        
        self._validate_config()
    
    def _validate_config(self):
        """Validate that all required configuration is present"""
        required_fields = {
            'rpi_ip': self.rpi_ip,
            'rpi_username': self.rpi_username,
            'rpi_password': self.rpi_password,
        }
        
        missing = [k for k, v in required_fields.items() if not v]
        if missing:
            raise ValueError(f"Missing R-Pi SSH configuration: {', '.join(missing)}")
    
    def connect(self) -> Tuple[bool, str]:
        """
        Step 1: Establish SSH connection to R-Pi
        
        This connection is SHARED - kept open for multiple device executions.
        Can be called multiple times; returns existing connection if already established.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            with self.lock:
                # If already connected, return success
                if self.is_connected and self.ssh_client:
                    msg = f"✅ [R-Pi DIRECT] Already connected to {self.rpi_username}@{self.rpi_ip}:{self.rpi_port}"
                    print(msg)
                    return True, msg
                
                print(f"\n[R-Pi DIRECT] Establishing SSH connection to R-Pi")
                print(f"[R-Pi DIRECT] Target: {self.rpi_username}@{self.rpi_ip}:{self.rpi_port}")
                print(f"[R-Pi DIRECT] Identifier: {self.device_identifier}")
                
                # Create SSH client
                self.ssh_client = paramiko.SSHClient()
                self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
                # Connect to R-Pi
                print(f"[R-Pi DIRECT] Connecting...")
                self.ssh_client.connect(
                    hostname=self.rpi_ip,
                    port=self.rpi_port,
                    username=self.rpi_username,
                    password=self.rpi_password,
                    timeout=30,
                    allow_agent=False,           # Use password only
                    look_for_keys=False,         # Don't look for SSH keys
                    auth_timeout=30
                )
                
                self.is_connected = True
                self.connection_established_at = time.time()
                self.commands_executed = 0
                
                msg = f"✅ [R-Pi DIRECT] SSH connection established successfully to {self.rpi_ip}:{self.rpi_port}"
                print(msg)
                return True, msg
        
        except paramiko.AuthenticationException as e:
            msg = f"❌ [R-Pi DIRECT] Authentication failed: {str(e)}"
            print(msg)
            self.is_connected = False
            self.ssh_client = None
            return False, msg
        
        except paramiko.SSHException as e:
            msg = f"❌ [R-Pi DIRECT] SSH connection failed: {str(e)}"
            print(msg)
            self.is_connected = False
            self.ssh_client = None
            return False, msg
        
        except Exception as e:
            msg = f"❌ [R-Pi DIRECT] Unexpected error: {str(e)}"
            print(msg)
            self.is_connected = False
            self.ssh_client = None
            return False, msg
    
    def execute_device_command(self, device_ip: str, device_port: int, 
                               device_username: str, command: str,
                               device_password: Optional[str] = None,
                               timeout: int = 30) -> Tuple[bool, str, str]:
        """
        Execute command on device through R-Pi shell
        
        Command flow:
        1. Use existing R-Pi SSH connection
        2. Execute: ssh -p <device_port> <device_username>@<device_ip> "<command>"
        3. Capture output and return
        
        Args:
            device_ip: Device IP (actual IP, e.g., 10.0.0.28)
            device_port: Device SSH port (e.g., 10022)
            device_username: Device SSH username (e.g., root, pi)
            command: Command to execute on device
            device_password: Optional password for device SSH (if needed for interactive)
            timeout: Command timeout in seconds
        
        Returns:
            Tuple of (success: bool, stdout: str, stderr: str)
        """
        if not self.is_connected or not self.ssh_client:
            return False, "", "R-Pi connection not established"
        
        try:
            with self.lock:
                # Build SSH command to execute on device through R-Pi
                # Format: ssh -p <device_port> -o StrictHostKeyChecking=no <username>@<device_ip> "<command>"
                ssh_cmd = (
                    f"ssh -p {device_port} "
                    f"-o StrictHostKeyChecking=no "
                    f"-o ConnectTimeout=10 "
                    f"{device_username}@{device_ip} "
                    f'"{command}"'
                )
                
                print(f"\n[R-Pi DIRECT] Executing on {device_username}@{device_ip}:{device_port}")
                print(f"[R-Pi DIRECT] Command: {command[:80]}{'...' if len(command) > 80 else ''}")
                
                # Execute through R-Pi SSH connection
                stdin, stdout, stderr = self.ssh_client.exec_command(ssh_cmd, timeout=timeout)
                
                # Read output
                out_str = stdout.read().decode('utf-8', errors='ignore')
                err_str = stderr.read().decode('utf-8', errors='ignore')
                exit_code = stdout.channel.recv_exit_status()
                
                # Update stats
                self.commands_executed += 1
                self.last_command_result = {
                    'device_ip': device_ip,
                    'command': command,
                    'exit_code': exit_code,
                    'timestamp': time.time()
                }
                
                if exit_code == 0:
                    msg = f"✅ [R-Pi DIRECT] Command succeeded on {device_ip}"
                    print(msg)
                    return True, out_str, err_str
                else:
                    msg = f"⚠️  [R-Pi DIRECT] Command failed on {device_ip} (exit code: {exit_code})"
                    print(msg)
                    return False, out_str, err_str
        
        except Exception as e:
            msg = f"❌ [R-Pi DIRECT] Error executing command: {str(e)}"
            print(msg)
            return False, "", msg
    
    def disconnect(self) -> Tuple[bool, str]:
        """
        Step N: Disconnect from R-Pi
        
        Should only be called when NO devices on this R-Pi are executing.
        Caller should check if other devices still need this connection.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            with self.lock:
                if self.ssh_client:
                    self.ssh_client.close()
                    self.is_connected = False
                    self.ssh_client = None
                    
                    elapsed = time.time() - self.connection_established_at if self.connection_established_at else 0
                    msg = (
                        f"✅ [R-Pi DIRECT] Disconnected from {self.rpi_ip} "
                        f"(duration: {elapsed:.1f}s, commands: {self.commands_executed})"
                    )
                    print(msg)
                    return True, msg
                else:
                    msg = "ℹ️  [R-Pi DIRECT] Not connected"
                    return True, msg
        
        except Exception as e:
            msg = f"❌ [R-Pi DIRECT] Error disconnecting: {str(e)}"
            print(msg)
            return False, msg
    
    def is_healthy(self) -> bool:
        """Check if R-Pi connection is still alive"""
        if not self.is_connected or not self.ssh_client:
            return False
        
        try:
            # Try executing a simple command to verify connection
            stdin, stdout, stderr = self.ssh_client.exec_command('echo "health check"', timeout=5)
            exit_code = stdout.channel.recv_exit_status()
            return exit_code == 0
        except:
            return False
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get statistics about this R-Pi connection"""
        return {
            'rpi_ip': self.rpi_ip,
            'rpi_port': self.rpi_port,
            'is_connected': self.is_connected,
            'connection_duration_seconds': (
                time.time() - self.connection_established_at 
                if self.connection_established_at else 0
            ),
            'commands_executed': self.commands_executed,
            'last_command': self.last_command_result
        }
    
    def __repr__(self) -> str:
        """String representation"""
        status = "✅ Connected" if self.is_connected else "❌ Disconnected"
        return f"GDFRPiDirectShellService({self.rpi_username}@{self.rpi_ip}:{self.rpi_port} - {status})"
