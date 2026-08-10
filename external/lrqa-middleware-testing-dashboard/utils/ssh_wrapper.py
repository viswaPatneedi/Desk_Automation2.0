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
    
    def read(self):
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
        ssh = RPiShellSSHWrapper(tunnel_service)
        stdin, stdout, stderr = ssh.exec_command("command")
    """
    
    def __init__(self, tunnel_service):
        """
        Initialize wrapper with R-Pi shell service
        
        Args:
            tunnel_service: GDFRPiShellService instance (already connected)
        """
        self.tunnel_service = tunnel_service
    
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
        # Execute command through R-Pi shell
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


def wrap_tunnel_service_as_ssh(tunnel_service):
    """
    Helper function to wrap tunnel service as paramiko-compatible SSH object
    
    Usage:
        tunnel_service = GDFRPiShellService(rpi_config, lab_device_config)
        tunnel_service.connect()
        ssh = wrap_tunnel_service_as_ssh(tunnel_service)
        
        # Now use ssh as if it were a paramiko SSHClient
        stdin, stdout, stderr = ssh.exec_command("whoami")
    
    Args:
        tunnel_service: Connected GDFRPiShellService instance
    
    Returns:
        RPiShellSSHWrapper that acts like paramiko.SSHClient
    """
    return RPiShellSSHWrapper(tunnel_service)
