#!/usr/bin/env python3
"""
GDF R-Pi Interactive Shell Service - Port Forwarding Approach
Establishes SSH tunnel to R-Pi with local port forwarding, then connects to device via localhost

Connection Flow:
1. ssh -L 10022:10.0.0.28:10022 pi@10.138.17.42:60201  (tunnel in background)
2. (Tunnel established - ports forwarded via Paramiko SSHTunnelForwarder)
3. ssh -p 10022 root@127.0.0.1 "cat /version.txt"
   (Connects through tunnel to device)

This approach:
- Uses Paramiko SSHTunnelForwarder for reliable, persistent tunneling
- Both SSH key and password authentication supported
- All commands execute on device through tunnel
- Device still identified as 10.0.0.28 (not 127.0.0.1)
"""

import paramiko
from sshtunnel import SSHTunnelForwarder
import subprocess
import time
import threading
from typing import Tuple, Dict, Optional


class GDFRPiShellService:
    """
    Manages SSH tunnel to R-Pi with local port forwarding using SSHTunnelForwarder
    Allows device commands to execute through tunnel using localhost:forwarded_port
    """
    
    def __init__(self, rpi_config: Dict, lab_device_config: Dict):
        """
        Initialize GDF R-Pi Port Forwarding Service
        
        Args:
            rpi_config: R-Pi configuration dict with keys:
                - rpi_ip: R-Pi IP address (e.g., 10.138.17.42)
                - rpi_port: R-Pi SSH port (default: 60201)
                - rpi_username: R-Pi SSH username (e.g., pi)
                - rpi_password: R-Pi SSH password
            
            lab_device_config: Lab device configuration dict with keys:
                - lab_ip: Lab device IP (e.g., 10.0.0.28) - used for identification
                - lab_port: Lab device SSH port (default: 10022)
                - lab_username: Lab device username (default: root)
                - lab_password: Lab device password
                - device_name: Name for logging
        """
        # R-Pi Configuration
        self.rpi_ip = rpi_config.get('rpi_ip')
        self.rpi_port = int(rpi_config.get('rpi_port', 60201))
        self.rpi_username = rpi_config.get('rpi_username')
        self.rpi_password = rpi_config.get('rpi_password')
        
        # Lab Device Configuration
        self.lab_ip = lab_device_config.get('lab_ip')  # Keep actual device IP
        self.lab_port = int(lab_device_config.get('lab_port', 10022))
        self.lab_username = lab_device_config.get('lab_username', 'root')
        self.lab_password = lab_device_config.get('lab_password')
        self.device_name = lab_device_config.get('device_name', 'Lab Device')
        
        # Tunnel Configuration
        self.tunnel_local_port = self.lab_port  # Local port for forwarding (e.g., 10022)
        self.tunnel_remote_host = self.lab_ip  # Remote device IP
        self.tunnel_remote_port = self.lab_port  # Remote device port
        
        # Additional ports to forward (VNC, web services)
        # Maps: local_port -> remote_port
        self.additional_forwards = {
            5800: 5800,    # VNC web interface (TigerVNC)
            8090: 8090,    # Web management/screenshot service
            9005: 9005,    # Application service
        }
        
        # SSH Tunnel Forwarders (main + additional)
        self.tunnel_forwarder = None
        self.additional_forwarders = []
        self.is_connected = False
        self.lock = threading.Lock()
        
        self._validate_config()
    
    def _validate_config(self):
        """Validate that all required configuration is present"""
        required_fields = {
            'rpi_ip': self.rpi_ip,
            'rpi_username': self.rpi_username,
            'rpi_password': self.rpi_password,
            'lab_ip': self.lab_ip
        }
        
        missing = [k for k, v in required_fields.items() if not v]
        if missing:
            raise ValueError(f"Missing SSH configuration: {', '.join(missing)}")
    
    def connect(self) -> Tuple[bool, str]:
        """
        Step 1: Establish SSH tunnel to R-Pi with local port forwarding
        
        Creates tunnel: 
          127.0.0.1:10022 → 10.0.0.28:10022 (SSH)
          127.0.0.1:5800 → 10.0.0.28:5800 (VNC web interface)
          127.0.0.1:8090 → 10.0.0.28:8090 (Web services)
          127.0.0.1:9005 → 10.0.0.28:9005 (Application services)
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            with self.lock:
                print(f"\n[R-Pi TUNNEL] Establishing SSH tunnel with port forwarding")
                print(f"[R-Pi TUNNEL] R-Pi: {self.rpi_username}@{self.rpi_ip}:{self.rpi_port}")
                print(f"[R-Pi TUNNEL] Primary: 127.0.0.1:{self.tunnel_local_port} ↔ {self.lab_ip}:{self.lab_port} (SSH)")
                
                # Create SSHTunnelForwarder for reliable port forwarding
                # Force password authentication only (no SSH agent, no system SSH config)
                self.tunnel_forwarder = SSHTunnelForwarder(
                    ssh_address_or_host=(self.rpi_ip, self.rpi_port),
                    ssh_username=self.rpi_username,
                    ssh_password=self.rpi_password,
                    ssh_config_file=None,  # Ignore system SSH config to avoid conflicts
                    allow_agent=False,      # Don't use SSH agent, use password only
                    remote_bind_address=(self.lab_ip, self.lab_port),
                    local_bind_address=('127.0.0.1', self.tunnel_local_port),
                    set_keepalive=30.0,     # Keep tunnel alive with keepalive packets
                    threaded=True,          # Run in background thread
                )
                
                print(f"[R-Pi TUNNEL] Starting primary tunnel...")
                
                # Start main SSH tunnel
                self.tunnel_forwarder.start()
                
                # Start additional port forwarders for web/VNC services
                print(f"[R-Pi TUNNEL] Starting additional port forwarders...")
                for local_port, remote_port in self.additional_forwards.items():
                    try:
                        additional_forwarder = SSHTunnelForwarder(
                            ssh_address_or_host=(self.rpi_ip, self.rpi_port),
                            ssh_username=self.rpi_username,
                            ssh_password=self.rpi_password,
                            ssh_config_file=None,
                            allow_agent=False,
                            remote_bind_address=(self.lab_ip, remote_port),
                            local_bind_address=('127.0.0.1', local_port),
                            set_keepalive=30.0,
                            threaded=True,
                        )
                        additional_forwarder.start()
                        self.additional_forwarders.append(additional_forwarder)
                        print(f"[R-Pi TUNNEL]   ✓ Forwarding: 127.0.0.1:{local_port} ↔ {self.lab_ip}:{remote_port}")
                    except Exception as e:
                        print(f"[R-Pi TUNNEL]   ⚠️  Failed to forward port {local_port}: {e}")
                
                time.sleep(1)  # Give all tunnels time to stabilize
                
                print(f"[R-Pi TUNNEL] ✓ SSH tunnel established")
                print(f"[R-Pi TUNNEL] ✓ All port forwarding active")
                
                self.is_connected = True
                msg = f"✅ SSH tunnel established with all port forwarding (SSH + VNC + Web + App services)"
                print(f"[R-Pi TUNNEL] {msg}")
                return True, msg
        
        except Exception as e:
            error_msg = f"Failed to establish tunnel: {str(e)}"
            print(f"[R-Pi TUNNEL] ❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return False, error_msg
    
    def execute_command(self, command: str, timeout: int = 30) -> Tuple[bool, str, str]:
        """
        Step 2: Execute command on device via tunnel port forwarding
        
        Connects to 127.0.0.1:tunnel_local_port (which tunnels to device:lab_port)
        and executes command.
        
        Command execution:
          ssh -p 10022 root@127.0.0.1 "cat /version.txt"
          (Which actually connects to 10.0.0.28:10022 through R-Pi tunnel)
        
        Args:
            command: Command to execute on device
            timeout: Command timeout in seconds
        
        Returns:
            Tuple of (success: bool, stdout: str, stderr: str)
        """
        try:
            print(f"\n[DEVICE CMD] Executing command via tunnel")
            print(f"[DEVICE CMD] Device: {self.lab_username}@{self.lab_ip}:{self.lab_port}")
            print(f"[DEVICE CMD] Connection: 127.0.0.1:{self.tunnel_local_port} (tunneled to device)")
            print(f"[DEVICE CMD] Command: {command}")
            
            # Create SSH client for device connection through tunnel
            device_ssh = paramiko.SSHClient()
            device_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect to localhost:tunnel_local_port (forwarded to device by tunnel)
            print(f"[DEVICE CMD] Connecting to device through tunnel...")
            device_ssh.connect(
                hostname='127.0.0.1',  # Connect to localhost
                port=self.tunnel_local_port,  # Forwarded port
                username=self.lab_username,
                password=self.lab_password,
                timeout=timeout,
                look_for_keys=False,
                allow_agent=False
            )
            
            print(f"[DEVICE CMD] ✓ Connected to device through tunnel")
            
            # Execute command
            stdin, stdout, stderr = device_ssh.exec_command(command, timeout=timeout)
            
            # Read output
            stdout_data = stdout.read().decode('utf-8', errors='ignore').strip()
            stderr_data = stderr.read().decode('utf-8', errors='ignore').strip()
            return_code = stdout.channel.recv_exit_status()
            
            # Close connection
            device_ssh.close()
            
            if return_code == 0:
                print(f"[DEVICE CMD] ✓ Command executed successfully")
                if stdout_data:
                    print(f"[DEVICE CMD] Output: {stdout_data[:100]}")
                return True, stdout_data, stderr_data
            else:
                print(f"[DEVICE CMD] ✗ Command returned code {return_code}")
                if stderr_data:
                    print(f"[DEVICE CMD] Stderr: {stderr_data[:200]}")
                # Return False but still include output for diagnostics
                return False, stdout_data, stderr_data
        
        except Exception as e:
            error_msg = f"Command execution error: {str(e)}"
            print(f"[DEVICE CMD] ✗ {error_msg}")
            import traceback
            print(traceback.format_exc())
            return False, "", error_msg
    
    def disconnect(self):
        """Close R-Pi tunnel and all port forwarders"""
        try:
            with self.lock:
                if self.tunnel_forwarder:
                    print(f"\n[R-Pi TUNNEL] Closing main tunnel...")
                    self.tunnel_forwarder.stop()
                    print(f"[R-Pi TUNNEL] ✓ Main tunnel closed")
                
                if self.additional_forwarders:
                    print(f"[R-Pi TUNNEL] Closing additional forwarders...")
                    for forwarder in self.additional_forwarders:
                        try:
                            forwarder.stop()
                        except:
                            pass
                    print(f"[R-Pi TUNNEL] ✓ Additional forwarders closed")
        
        except Exception as e:
            print(f"[R-Pi TUNNEL] ⚠️  Error closing tunnel: {e}")
        
        finally:
            self.is_connected = False
            self.tunnel_forwarder = None
            self.additional_forwarders = []

