"""
Jump Host Service - Handles SSH connections via jump host with MAC-based device resolution
"""

import paramiko
import time
import re
from typing import Optional, Tuple

class JumpHostService:
    """Service for managing SSH connections through GRRE jump hosts"""
    
    # Menu prompts to expect
    MAIN_MENU_PROMPT = "Choose an action to do"
    DEVICE_TYPE_PROMPT = "Enter the device type"
    MAC_PROMPT = "Enter the MAC address"
    DEVICE_SHELL_PROMPT_PATTERN = r"root@[\w\-]+:~#"
    
    # Menu selections
    MENU_REVERSE_SSH = "1"
    MENU_DEVICE_TYPE_XUMO = "1"
    
    # Timeouts
    TIMEOUT_MENU = 2
    TIMEOUT_CONNECTION = 10
    TIMEOUT_COMMAND = 5
    
    def __init__(self, jump_host: str, jump_user: str, jump_pass: str, jump_port: int = 22):
        """
        Initialize jump host service
        
        Args:
            jump_host: Jump host IP or hostname (e.g., 96.118.26.235)
            jump_user: Username for jump host (e.g., vpatne290)
            jump_pass: Password for jump host
            jump_port: SSH port for jump host (default: 22)
        """
        self.jump_host = jump_host
        self.jump_user = jump_user
        self.jump_pass = jump_pass
        self.jump_port = jump_port
        self.ssh_client = None
        self.channel = None
    
    def connect(self) -> Tuple[bool, str]:
        """
        Connect to jump host
        
        Returns:
            Tuple of (success, message)
        """
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(
                self.jump_host,
                port=self.jump_port,
                username=self.jump_user,
                password=self.jump_pass,
                timeout=10
            )
            return True, "Connected to jump host successfully"
        except Exception as e:
            return False, f"Failed to connect to jump host: {str(e)}"
    
    def disconnect(self):
        """Disconnect from jump host"""
        if self.channel:
            try:
                self.channel.close()
            except:
                pass
            self.channel = None
        
        if self.ssh_client:
            try:
                self.ssh_client.close()
            except:
                pass
            self.ssh_client = None
    
    def _wait_for_prompt(self, expected_text: str, timeout: int = 5) -> Tuple[bool, str]:
        """
        Wait for expected text in output
        
        Args:
            expected_text: Text to wait for
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (found, full_output)
        """
        start_time = time.time()
        output = ""
        
        while time.time() - start_time < timeout:
            if self.channel.recv_ready():
                chunk = self.channel.recv(4096).decode('utf-8', errors='ignore')
                output += chunk
                if expected_text.lower() in output.lower():
                    return True, output
            time.sleep(0.1)
        
        return False, output
    
    def _wait_for_device_prompt(self, timeout: int = 10) -> Tuple[bool, str]:
        """
        Wait for device shell prompt (root@...)
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (found, full_output)
        """
        start_time = time.time()
        output = ""
        
        while time.time() - start_time < timeout:
            if self.channel.recv_ready():
                chunk = self.channel.recv(4096).decode('utf-8', errors='ignore')
                output += chunk
                if re.search(self.DEVICE_SHELL_PROMPT_PATTERN, output):
                    return True, output
            time.sleep(0.1)
        
        return False, output
    
    def connect_to_device_by_mac(self, device_mac: str) -> Tuple[bool, str]:
        """
        Navigate jump host menu to connect to device by MAC address
        
        Args:
            device_mac: Device MAC address (format: XX:XX:XX:XX:XX:XX or XXXXXXXXXXXX)
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Open interactive shell
            self.channel = self.ssh_client.invoke_shell()
            time.sleep(1)
            
            # Clear welcome banner
            if self.channel.recv_ready():
                self.channel.recv(9999)
            
            # Wait for main menu
            found, output = self._wait_for_prompt(self.MAIN_MENU_PROMPT, self.TIMEOUT_MENU)
            if not found:
                return False, f"Main menu not found. Output: {output[:500]}"
            
            # Select option 1: Reverse/Forward SSH
            self.channel.send(f"{self.MENU_REVERSE_SSH}\n")
            time.sleep(self.TIMEOUT_MENU)
            
            # Wait for device type menu
            found, output = self._wait_for_prompt(self.DEVICE_TYPE_PROMPT, self.TIMEOUT_MENU)
            if not found:
                return False, f"Device type menu not found. Output: {output[:500]}"
            
            # Select option 1: XUMO/XGLOBAL/PLATCO_DEVICE
            self.channel.send(f"{self.MENU_DEVICE_TYPE_XUMO}\n")
            time.sleep(self.TIMEOUT_MENU)
            
            # Wait for MAC address prompt
            found, output = self._wait_for_prompt(self.MAC_PROMPT, self.TIMEOUT_MENU)
            if not found:
                return False, f"MAC address prompt not found. Output: {output[:500]}"
            
            # Send MAC address
            self.channel.send(f"{device_mac}\n")
            
            # Wait for device shell prompt
            found, output = self._wait_for_device_prompt(self.TIMEOUT_CONNECTION)
            if not found:
                return False, f"Device shell prompt not found. Connection may have failed. Output: {output[:500]}"
            
            return True, f"Connected to device {device_mac} successfully"
            
        except Exception as e:
            return False, f"Error connecting to device: {str(e)}"
    
    def execute_command(self, command: str, timeout: int = None) -> Tuple[bool, str]:
        """
        Execute command on connected device
        
        Args:
            command: Command to execute
            timeout: Command timeout in seconds (default: TIMEOUT_COMMAND)
            
        Returns:
            Tuple of (success, output)
        """
        if not self.channel:
            return False, "Not connected to device"
        
        timeout = timeout or self.TIMEOUT_COMMAND
        
        try:
            # Clear any pending output
            if self.channel.recv_ready():
                self.channel.recv(9999)
            
            # Send command
            self.channel.send(f"{command}\n")
            time.sleep(0.5)
            
            # Collect output
            start_time = time.time()
            output = ""
            
            while time.time() - start_time < timeout:
                if self.channel.recv_ready():
                    chunk = self.channel.recv(4096).decode('utf-8', errors='ignore')
                    output += chunk
                    # Check if we got back to prompt
                    if re.search(self.DEVICE_SHELL_PROMPT_PATTERN, chunk):
                        break
                time.sleep(0.1)
            
            # Clean up output (remove command echo and prompt)
            lines = output.split('\n')
            if len(lines) > 1:
                # Remove first line (command echo) and last line (prompt)
                output = '\n'.join(lines[1:-1])
            
            return True, output.strip()
            
        except Exception as e:
            return False, f"Error executing command: {str(e)}"
    
    def execute_command_simple(self, device_mac: str, command: str, timeout: int = None) -> Tuple[bool, str]:
        """
        One-shot command execution: connect, execute, disconnect
        
        Args:
            device_mac: Device MAC address
            command: Command to execute
            timeout: Command timeout in seconds
            
        Returns:
            Tuple of (success, output)
        """
        try:
            # Connect to jump host
            success, msg = self.connect()
            if not success:
                return False, msg
            
            # Connect to device
            success, msg = self.connect_to_device_by_mac(device_mac)
            if not success:
                self.disconnect()
                return False, msg
            
            # Execute command
            success, output = self.execute_command(command, timeout)
            
            return success, output
            
        finally:
            self.disconnect()


def test_jump_host_connection(jump_host: str, jump_user: str, jump_pass: str, 
                               device_mac: str, test_command: str = "uname -a") -> dict:
    """
    Test jump host connection and command execution
    
    Args:
        jump_host: Jump host IP
        jump_user: Jump host username
        jump_pass: Jump host password
        device_mac: Device MAC address
        test_command: Command to test (default: uname -a)
        
    Returns:
        Dictionary with test results
    """
    service = JumpHostService(jump_host, jump_user, jump_pass)
    
    result = {
        'jump_host_connection': False,
        'device_connection': False,
        'command_execution': False,
        'output': '',
        'errors': []
    }
    
    try:
        # Test jump host connection
        success, msg = service.connect()
        result['jump_host_connection'] = success
        if not success:
            result['errors'].append(f"Jump host: {msg}")
            return result
        
        # Test device connection
        success, msg = service.connect_to_device_by_mac(device_mac)
        result['device_connection'] = success
        if not success:
            result['errors'].append(f"Device: {msg}")
            return result
        
        # Test command execution
        success, output = service.execute_command(test_command)
        result['command_execution'] = success
        result['output'] = output
        if not success:
            result['errors'].append(f"Command: {output}")
        
    except Exception as e:
        result['errors'].append(f"Exception: {str(e)}")
    finally:
        service.disconnect()
    
    return result
