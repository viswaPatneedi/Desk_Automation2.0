#!/usr/bin/env python3
"""
SSH Wrapper for R-Pi Shell Service
Provides a paramiko-compatible interface to GDFRPiShellService
Allows existing methods to work without modification
"""

class SSHShellChannel:
    """Wrapper that mimics paramiko's SSHClient.exec_command response"""
    
    def __init__(self, command_output, error_output=""):
        self.stdout_data = command_output
        self.stderr_data = error_output
        self.channel = self  # Self-reference for channel operations
    
    def read(self, bufsize=-1):
        """Read output from command (mimics file-like object)
        
        Args:
            bufsize: Optional buffer size (ignored, for compatibility)
        
        Returns:
            bytes: Command output as bytes
        """
        return self.stdout_data.encode('utf-8') if isinstance(self.stdout_data, str) else self.stdout_data
    
    def readlines(self):
        return [line.encode('utf-8') if isinstance(line, str) else line 
                for line in self.stdout_data.split('\n') if line]
    
    def settimeout(self, timeout):
        """Mock settimeout for compatibility"""
        pass
    
    def close(self):
        """Mock close for compatibility"""
        pass


class RPiShellSSHWrapper:
    """
    Wrapper that mimics paramiko.SSHClient interface but uses R-Pi interactive shell
    
    This allows existing methods that use:
        stdin, stdout, stderr = ssh.exec_command("command")
    
    To work seamlessly with the R-Pi shell approach:
        ssh = RPiShellSSHWrapper(tunnel_service, device_config)
        stdin, stdout, stderr = ssh.exec_command("command")
    
    Each wrapper instance is device-specific, allowing multiple devices to use
    the same tunnel service without race conditions.
    """
    
    def __init__(self, tunnel_service, device_config: Dict = None):
        """
        Initialize wrapper with R-Pi shell service
        
        Args:
            tunnel_service: GDFRPiShellService instance (already connected)
            device_config: Optional device config dict with keys:
                - lab_ip: Device IP address (e.g., 10.0.0.28)
                - lab_port: Device SSH port (e.g., 10022)
                - lab_username: Device SSH username (e.g., root)
                - lab_password: Device SSH password
        """
        self.tunnel_service = tunnel_service
        
        # Store device-specific config for this wrapper instance
        # This allows multiple wrappers to use the same tunnel_service without race conditions
        if device_config:
            self.device_ip = device_config.get('lab_ip')
            self.device_port = device_config.get('lab_port', 10022)
            self.device_username = device_config.get('lab_username', 'root')
            self.device_password = device_config.get('lab_password', '')
        else:
            # Fall back to tunnel service's stored config if no device config provided
            self.device_ip = None
            self.device_port = 10022
            self.device_username = 'root'
            self.device_password = ''
    
    def exec_command(self, command, timeout=30):
        """
        Execute command on device via R-Pi shell
        
        Mimics paramiko's exec_command interface:
            stdin, stdout, stderr = ssh.exec_command(command)
        
        Args:
            command: Command to execute
            timeout: Command timeout in seconds
        
        Returns:
            Tuple of (stdin, stdout, stderr) where stdout/stderr are file-like objects
        """
        # Execute command through R-Pi shell, using THIS wrapper's device config
        # (not the tunnel service's config, which might be shared with other devices)
        # This prevents race conditions when multiple devices reuse the same tunnel
        
        if self.device_ip:
            # Use wrapper's specific device config (no race condition)
            success, stdout_data, stderr_data = self.tunnel_service.execute_command(
                command, 
                timeout=timeout,
                device_ip=self.device_ip,
                device_port=self.device_port,
                device_username=self.device_username,
                device_password=self.device_password
            )
        else:
            # Fall back to tunnel service's stored config (single device or backward compat)
            success, stdout_data, stderr_data = self.tunnel_service.execute_command(command, timeout=timeout)
        
        # Convert response to file-like objects that methods expect
        stdout = SSHShellChannel(stdout_data)
        stderr = SSHShellChannel(stderr_data)
        stdin = None  # R-Pi shell doesn't need stdin for command execution
        
        return stdin, stdout, stderr
    
    def close(self):
        """Close the connection"""
        # R-Pi shell will be closed by tunnel_service.disconnect() in main execution
        pass


def wrap_tunnel_service_as_ssh(tunnel_service, device_config: Dict = None):
    """
    Helper function to wrap tunnel service as paramiko-compatible SSH object
    
    Usage:
        tunnel_service = GDFRPiDirectShellService(rpi_config, device_name, device_config)
        tunnel_service.connect()
        ssh = wrap_tunnel_service_as_ssh(tunnel_service, device_config)
        
        # Now use ssh as if it were a paramiko SSHClient
        stdin, stdout, stderr = ssh.exec_command("whoami")
    
    Args:
        tunnel_service: Connected GDFRPiDirectShellService instance
        device_config: Device-specific configuration dict with keys:
            - lab_ip: Device IP address
            - lab_port: Device SSH port
            - lab_username: Device SSH username
            - lab_password: Device SSH password
    
    Returns:
        RPiShellSSHWrapper that acts like paramiko.SSHClient
        with device-specific configuration (no race conditions)
    """
    return RPiShellSSHWrapper(tunnel_service, device_config)
