#!/usr/bin/env python3
"""
SSH Command Execution Service - Universal Pattern
Provides reusable SSH command execution layer with R-Pi tunnel support
Used by all methods that need SSH access to devices

Features:
- R-Pi tunnel management
- Device SSH connection
- Command execution with timeout
- Output parsing and streaming
- Error handling and reconnection
- Connection lifecycle management
"""

import paramiko
import socket
import time
import threading
from typing import Tuple, Optional, Callable, Dict, List
from datetime import datetime, timezone


class SSHCommandService:
    """
    Universal SSH command execution service
    Handles tunnel setup, device connection, and command execution
    
    Usage:
        ssh = SSHCommandService(device_config, log_callback)
        ssh.connect()
        success, output, error = ssh.execute_and_get_output("whoami")
        ssh.disconnect()
    """
    
    def __init__(self, device_config: Dict, log_callback: Optional[Callable] = None):
        """
        Initialize SSH service with device configuration
        
        Args:
            device_config: {
                "lab_ip": "10.0.0.28",              # Device IP
                "lab_port": 22,                      # SSH port
                "lab_username": "root",              # SSH username
                "lab_password": "password",          # SSH password (or encrypted)
                "rpi_config": {                      # Optional R-Pi tunnel config
                    "rpi_ip": "10.138.17.42",
                    "rpi_port": 60201,
                    "rpi_username": "pi",
                    "rpi_password": "password"       # Optional
                }
            }
            log_callback: Optional function(message) for logging
        """
        self.device_config = device_config
        self.log_callback = log_callback or print
        
        # Extract configuration
        self.device_ip = device_config.get('lab_ip')
        self.device_port = device_config.get('lab_port', 22)
        self.device_username = device_config.get('lab_username')
        self.device_password = device_config.get('lab_password')
        
        # R-Pi tunnel config
        self.rpi_config = device_config.get('rpi_config')
        self.use_tunnel = bool(self.rpi_config)
        
        # Connection state
        self.ssh_client = None
        self.tunnel_service = None
        self.is_connected = False
        self.last_command_time = None
        self.connection_lock = threading.Lock()
    
    def log(self, message: str, level: str = "INFO"):
        """Log message with optional level"""
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        formatted = f"[{timestamp}] [{level}] [SSH] {message}"
        self.log_callback(formatted)
    
    def connect(self) -> bool:
        """
        Establish SSH connection (via R-Pi tunnel if configured)
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        with self.connection_lock:
            try:
                if self.is_connected:
                    self.log("Already connected, skipping reconnect")
                    return True
                
                self.log(f"Connecting to device {self.device_ip}:{self.device_port}")
                
                # If using R-Pi tunnel, initialize tunnel service
                if self.use_tunnel:
                    self.log(f"Using R-Pi tunnel via {self.rpi_config['rpi_ip']}:{self.rpi_config['rpi_port']}")
                    
                    # Import tunnel service
                    from services.gdf_ssh_tunnel_service import GDFSSHTunnelService
                    
                    self.tunnel_service = GDFSSHTunnelService(
                        rpi_ip=self.rpi_config['rpi_ip'],
                        rpi_port=self.rpi_config['rpi_port'],
                        rpi_username=self.rpi_config['rpi_username'],
                        rpi_password=self.rpi_config.get('rpi_password'),
                        device_ip=self.device_ip,
                        device_username=self.device_username,
                        device_password=self.device_password,
                        log_callback=self.log
                    )
                    
                    # Connect tunnel
                    if not self.tunnel_service.connect():
                        self.log("Failed to establish R-Pi tunnel", "ERROR")
                        return False
                    
                    # Tunnel provides direct device connection
                    self.is_connected = True
                    self.log("R-Pi tunnel established successfully")
                    return True
                
                else:
                    # Direct SSH connection (no tunnel)
                    self.ssh_client = paramiko.SSHClient()
                    self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    
                    try:
                        self.ssh_client.connect(
                            hostname=self.device_ip,
                            port=self.device_port,
                            username=self.device_username,
                            password=self.device_password,
                            timeout=10,
                            allow_agent=False,
                            look_for_keys=False
                        )
                        
                        self.is_connected = True
                        self.log("Direct SSH connection established")
                        return True
                    
                    except paramiko.AuthenticationException as e:
                        self.log(f"Authentication failed: {str(e)}", "ERROR")
                        return False
                    
                    except socket.timeout:
                        self.log("Connection timeout (device not responding)", "ERROR")
                        return False
                    
                    except Exception as e:
                        self.log(f"Connection failed: {str(e)[:100]}", "ERROR")
                        return False
            
            except Exception as e:
                self.log(f"Unexpected error during connect: {str(e)}", "ERROR")
                return False
    
    def disconnect(self):
        """
        Clean shutdown of SSH connection and tunnel
        """
        with self.connection_lock:
            try:
                if self.tunnel_service:
                    self.log("Disconnecting R-Pi tunnel")
                    self.tunnel_service.disconnect()
                    self.tunnel_service = None
                
                if self.ssh_client:
                    self.log("Closing SSH connection")
                    self.ssh_client.close()
                    self.ssh_client = None
                
                self.is_connected = False
                self.log("Disconnected successfully")
            
            except Exception as e:
                self.log(f"Error during disconnect: {str(e)}", "WARNING")
    
    def execute_command(self, command: str, timeout: int = 10) -> Tuple[bool, str, str]:
        """
        Execute single SSH command and return (success, stdout, stderr)
        
        Args:
            command: Command to execute
            timeout: Timeout in seconds
        
        Returns:
            Tuple: (success: bool, output: str, error: str)
        """
        if not self.is_connected:
            self.log("Not connected - attempting reconnect", "WARNING")
            if not self.connect():
                return False, "", "Not connected to device"
        
        try:
            # Using tunnel service
            if self.tunnel_service:
                success, output, error = self.tunnel_service.execute_command(
                    command,
                    timeout=timeout
                )
                self.last_command_time = datetime.now(timezone.utc)
                return success, output, error
            
            # Direct SSH execution
            else:
                stdin, stdout, stderr = self.ssh_client.exec_command(
                    command,
                    timeout=timeout
                )
                
                # Set channel timeout
                stdout.channel.settimeout(timeout)
                stderr.channel.settimeout(timeout)
                
                try:
                    output = stdout.read().decode('utf-8', errors='ignore').strip()
                    error = stderr.read().decode('utf-8', errors='ignore').strip()
                    
                    self.last_command_time = datetime.now(timezone.utc)
                    
                    success = True if not error else False
                    return success, output, error
                
                except socket.timeout:
                    self.log(f"Command timeout after {timeout}s: {command[:50]}", "WARNING")
                    return False, "", f"Timeout after {timeout}s"
                
                finally:
                    try:
                        stdout.channel.close()
                        stderr.channel.close()
                    except:
                        pass
        
        except Exception as e:
            self.log(f"Command execution error: {str(e)[:100]}", "ERROR")
            return False, "", str(e)
    
    def execute_and_get_output(self, command: str, timeout: int = 10) -> Tuple[bool, str, str]:
        """
        Convenience method - execute command and return output
        ONE-LINER for method implementation
        
        Args:
            command: Command to execute
            timeout: Timeout in seconds
        
        Returns:
            Tuple: (success: bool, output: str, error: str)
        
        Example:
            success, output, error = ssh.execute_and_get_output("whoami", timeout=5)
            if success:
                print(f"User: {output}")
            else:
                print(f"Error: {error}")
        """
        return self.execute_command(command, timeout)
    
    def execute_with_parsing(self, command: str, parser_func: Optional[Callable] = None,
                           timeout: int = 10):
        """
        Execute command and parse output with custom function
        
        Args:
            command: Command to execute
            parser_func: Function to parse output (takes string, returns parsed result)
            timeout: Timeout in seconds
        
        Returns:
            Parsed result from parser_func, or None if error
        
        Example:
            def parse_uptime(output):
                lines = output.split('\n')
                return lines[0] if lines else None
            
            uptime = ssh.execute_with_parsing("uptime", parse_uptime)
        """
        success, output, error = self.execute_command(command, timeout)
        
        if success and parser_func:
            try:
                return parser_func(output)
            except Exception as e:
                self.log(f"Error in parser function: {str(e)}", "ERROR")
                return None
        
        return output if success else None
    
    def execute_multiple_commands(self, commands_list: List[str], timeout: int = 10) -> Dict:
        """
        Execute multiple commands sequentially
        
        Args:
            commands_list: List of commands to execute
            timeout: Timeout per command
        
        Returns:
            Dict: {command: (success, output, error), ...}
        
        Example:
            cmds = ["whoami", "pwd", "df -h"]
            results = ssh.execute_multiple_commands(cmds)
            for cmd, (success, output, error) in results.items():
                print(f"{cmd}: {output if success else error}")
        """
        results = {}
        
        for command in commands_list:
            success, output, error = self.execute_command(command, timeout)
            results[command] = (success, output, error)
        
        return results
    
    def get_file_content(self, remote_path: str, timeout: int = 10) -> Optional[str]:
        """
        Retrieve entire file content via SSH
        
        Args:
            remote_path: Path to file on device
            timeout: Timeout in seconds
        
        Returns:
            File content as string, or None if error
        
        Example:
            log_content = ssh.get_file_content("/opt/logs/sky-messages.log")
        """
        command = f"cat {remote_path}"
        success, output, error = self.execute_command(command, timeout)
        
        return output if success else None
    
    def fetch_command_output(self, command: str, lines_count: int = 100, timeout: int = 10) -> str:
        """
        Execute command and return last N lines
        
        Args:
            command: Command to execute
            lines_count: Number of lines to return
            timeout: Timeout in seconds
        
        Returns:
            Last N lines of output
        
        Example:
            last_logs = ssh.fetch_command_output("tail -f /opt/logs/sky-messages.log", 20)
        """
        full_command = f"{command} | tail -n {lines_count}"
        success, output, error = self.execute_command(full_command, timeout)
        
        return output if success else error
    
    def is_alive(self) -> bool:
        """
        Check if SSH connection is still alive
        
        Returns:
            bool: True if connected and responsive
        
        Example:
            if not ssh.is_alive():
                ssh.connect()
        """
        if not self.is_connected:
            return False
        
        # Try simple command
        success, _, _ = self.execute_command("echo 'ping'", timeout=3)
        return success
    
    def reconnect(self) -> bool:
        """
        Attempt to reconnect if connection lost
        
        Returns:
            bool: True if reconnection successful
        """
        self.log("Attempting reconnection...")
        self.disconnect()
        time.sleep(1)
        return self.connect()
    
    def get_status(self) -> Dict:
        """
        Get current connection status
        
        Returns:
            Dict with connection info
        """
        return {
            'connected': self.is_connected,
            'using_tunnel': self.use_tunnel,
            'device_ip': self.device_ip,
            'device_port': self.device_port,
            'tunnel_ip': self.rpi_config['rpi_ip'] if self.use_tunnel else None,
            'last_command': self.last_command_time.isoformat() if self.last_command_time else None,
        }


# ============================================================================
# HELPER FUNCTION - Use this in test_execution_service.py
# ============================================================================

def create_ssh_service_from_device(device, log_callback=None) -> SSHCommandService:
    """
    Create SSH service from Device model
    
    Args:
        device: Device model instance with all config
        log_callback: Logging callback
    
    Returns:
        Initialized SSHCommandService (not yet connected)
    
    Usage in test_execution_service.py:
        
        device = Device.get_device_by_id(device_id)
        ssh_service = create_ssh_service_from_device(device, log_service.log)
        
        try:
            ssh_service.connect()
            
            # Use in multiple methods
            result1 = method_reboot(..., tunnel_service=ssh_service, ...)
            result2 = method_check_logs(..., tunnel_service=ssh_service, ...)
            
        finally:
            ssh_service.disconnect()
    """
    
    device_config = {
        "lab_ip": device.ip,
        "lab_port": device.port,
        "lab_username": device.username,
        "lab_password": device.password,
        "rpi_config": device.rpi_config if hasattr(device, 'rpi_config') else None
    }
    
    return SSHCommandService(device_config, log_callback)


# ============================================================================
# UNIT TEST EXAMPLES
# ============================================================================

if __name__ == "__main__":
    """
    Example usage and testing
    """
    
    # Example 1: Direct connection
    print("=" * 60)
    print("Example 1: Direct SSH Connection")
    print("=" * 60)
    
    direct_config = {
        "lab_ip": "192.168.1.100",
        "lab_port": 22,
        "lab_username": "root",
        "lab_password": "password",
        "rpi_config": None
    }
    
    ssh = SSHCommandService(direct_config)
    # ssh.connect()
    # success, output, error = ssh.execute_and_get_output("whoami")
    # ssh.disconnect()
    
    # Example 2: R-Pi tunnel connection
    print("\n" + "=" * 60)
    print("Example 2: R-Pi Tunnel Connection")
    print("=" * 60)
    
    tunnel_config = {
        "lab_ip": "10.0.0.28",
        "lab_port": 22,
        "lab_username": "root",
        "lab_password": "password",
        "rpi_config": {
            "rpi_ip": "10.138.17.42",
            "rpi_port": 60201,
            "rpi_username": "pi",
            "rpi_password": None
        }
    }
    
    ssh = SSHCommandService(tunnel_config)
    # ssh.connect()
    # success, output, error = ssh.execute_and_get_output("uptime")
    # ssh.disconnect()
    
    # Example 3: Multiple commands
    print("\n" + "=" * 60)
    print("Example 3: Multiple Commands")
    print("=" * 60)
    
    # ssh.connect()
    # results = ssh.execute_multiple_commands([
    #     "whoami",
    #     "pwd",
    #     "df -h",
    #     "free -m"
    # ])
    # for cmd, (success, output, error) in results.items():
    #     print(f"{cmd}: {output if success else error}")
    # ssh.disconnect()
    
    # Example 4: Command with parsing
    print("\n" + "=" * 60)
    print("Example 4: Custom Parsing")
    print("=" * 60)
    
    def parse_df_output(output):
        lines = output.split('\n')
        return lines[1].split() if len(lines) > 1 else []
    
    # ssh.connect()
    # disk_info = ssh.execute_with_parsing("df -h /", parse_df_output)
    # print(f"Disk info: {disk_info}")
    # ssh.disconnect()
    
    print("\n✅ SSH Service is ready for use!")
    print("Import and use in your methods like:")
    print("  ssh = SSHCommandService(config, log)")
    print("  ssh.connect()")
    print("  success, output, error = ssh.execute_and_get_output('command')")
    print("  ssh.disconnect()")
