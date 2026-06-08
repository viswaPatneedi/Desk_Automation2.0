"""
SSH Connection Helper - Unified interface for direct and jump host SSH connections
"""

import paramiko
from typing import Optional, Tuple
from services.jump_host_service import JumpHostService

class SSHConnectionHelper:
    """Helper class to manage SSH connections via direct or jump host"""
    
    def __init__(self, device):
        """
        Initialize SSH connection helper
        
        Args:
            device: Device object from models.device
        """
        self.device = device
        self.ssh_client = None
        self.jump_service = None
    
    def connect(self) -> Tuple[bool, str]:
        """
        Connect to device via direct SSH or jump host
        
        Returns:
            Tuple of (success, message)
        """
        if self.device.use_jump_host and self.device.jump_host_config:
            return self._connect_via_jump_host()
        else:
            return self._connect_direct()
    
    def _connect_direct(self) -> Tuple[bool, str]:
        """Connect via direct SSH"""
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(
                self.device.ip,
                port=self.device.port,
                username=self.device.username,
                password=self.device.password,
                timeout=10
            )
            return True, "Connected successfully"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
    
    def _connect_via_jump_host(self) -> Tuple[bool, str]:
        """Connect via jump host"""
        if not self.device.mac_address:
            return False, "MAC address required for jump host connection"
        
        jump_config = self.device.jump_host_config
        required_fields = ['host', 'username', 'password']
        for field in required_fields:
            if field not in jump_config:
                return False, f"Jump host config missing: {field}"
        
        try:
            self.jump_service = JumpHostService(
                jump_host=jump_config['host'],
                jump_user=jump_config['username'],
                jump_pass=jump_config['password'],
                jump_port=jump_config.get('port', 22)
            )
            
            # Connect to jump host
            success, msg = self.jump_service.connect()
            if not success:
                return False, f"Jump host connection failed: {msg}"
            
            # Connect to device via MAC
            success, msg = self.jump_service.connect_to_device_by_mac(self.device.mac_address)
            if not success:
                self.jump_service.disconnect()
                return False, f"Device connection failed: {msg}"
            
            return True, "Connected via jump host successfully"
            
        except Exception as e:
            return False, f"Jump host error: {str(e)}"
    
    def execute_command(self, command: str, timeout: int = 30) -> Tuple[bool, str]:
        """
        Execute command on device
        
        Args:
            command: Command to execute
            timeout: Command timeout in seconds
            
        Returns:
            Tuple of (success, output)
        """
        if self.jump_service:
            return self.jump_service.execute_command(command, timeout)
        elif self.ssh_client:
            return self._execute_direct(command, timeout)
        else:
            return False, "Not connected to device"
    
    def _execute_direct(self, command: str, timeout: int) -> Tuple[bool, str]:
        """Execute command via direct SSH"""
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(command, timeout=timeout)
            output = stdout.read().decode('utf-8', errors='ignore')
            error = stderr.read().decode('utf-8', errors='ignore')
            
            if error:
                return False, error
            return True, output
            
        except Exception as e:
            return False, f"Command execution failed: {str(e)}"
    
    def disconnect(self):
        """Disconnect from device"""
        if self.jump_service:
            self.jump_service.disconnect()
            self.jump_service = None
        
        if self.ssh_client:
            try:
                self.ssh_client.close()
            except:
                pass
            self.ssh_client = None
    
    def __enter__(self):
        """Context manager entry"""
        success, msg = self.connect()
        if not success:
            raise ConnectionError(msg)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


def execute_device_command(device, command: str, timeout: int = 30) -> Tuple[bool, str]:
    """
    Convenience function to execute a single command on a device
    
    Args:
        device: Device object
        command: Command to execute
        timeout: Command timeout in seconds
        
    Returns:
        Tuple of (success, output)
    """
    try:
        with SSHConnectionHelper(device) as ssh:
            return ssh.execute_command(command, timeout)
    except Exception as e:
        return False, str(e)
