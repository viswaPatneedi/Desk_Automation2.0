#!/usr/bin/env python3
"""
GDF SSH Tunnel Service - CORRECTED IMPLEMENTATION
Uses native SSH port forwarding via subprocess instead of manual Paramiko forwarding

Approach:
1. Step 1: Start SSH subprocess with -L flags to create port forwarding
   ssh -p 60201 -L 8090:10.0.0.28:8090 -L 10022:10.0.0.28:10022 ... pi@10.138.17.42
   
2. Step 2: Connect to device via tunnel
   ssh -p 10022 root@127.0.0.1 (which goes through R-Pi to 10.0.0.28:10022)
   
3. Step 3: Execute any device commands
"""

import subprocess
import time
import signal
import os
from typing import Tuple, Optional, Dict
import socket


class GDFSSHTunnelService:
    """
    Manages SSH tunnel to GDF_RACK devices using native SSH port forwarding
    This is the CORRECT approach - uses SSH's -L flag, not manual Paramiko
    """
    
    # Port mappings for lab devices
    PORT_MAPPINGS = {
        8090: 8090,      # Service port (UI/API)
        10022: 10022,    # SSH port (main connection)
        8023: 8023,      # Additional service
        9005: 9005       # Additional service
    }
    
    def __init__(self, rpi_config: Dict, lab_device_config: Dict):
        """
        Initialize GDF SSH Tunnel Service
        
        Args:
            rpi_config: R-Pi configuration dict with keys:
                - rpi_ip: R-Pi IP address (e.g., 10.138.17.42)
                - rpi_port: R-Pi SSH port (default: 60201)
                - rpi_username: R-Pi SSH username (e.g., pi)
                - rpi_password: R-Pi SSH password
            
            lab_device_config: Lab device configuration dict with keys:
                - lab_ip: Lab device IP (e.g., 10.0.0.28)
                - lab_port: Lab SSH port (default: 10022)
                - lab_username: Lab device username (default: root)
                - lab_password: Lab device password (optional for key-based auth)
                - device_name: Name for logging
        """
        # R-Pi Configuration
        self.rpi_ip = rpi_config.get('rpi_ip')
        self.rpi_port = int(rpi_config.get('rpi_port', 60201))
        self.rpi_username = rpi_config.get('rpi_username')
        self.rpi_password = rpi_config.get('rpi_password')
        
        # Lab Device Configuration
        self.lab_ip = lab_device_config.get('lab_ip')
        self.lab_port = int(lab_device_config.get('lab_port', 10022))
        self.lab_username = lab_device_config.get('lab_username', 'root')
        self.lab_password = lab_device_config.get('lab_password')
        self.device_name = lab_device_config.get('device_name', 'Lab Device')
        
        # Tunnel process management
        self.tunnel_process = None
        self.is_connected = False
        
        self._validate_config()
        self._check_sshpass()
    
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
    
    def _check_sshpass(self):
        """Verify sshpass is installed"""
        try:
            subprocess.run(['which', 'sshpass'], check=True, 
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            print("⚠️  WARNING: sshpass not installed")
            print("   Install with: sudo apt-get install sshpass")
            print("   Without sshpass, password-based tunnel may fail")
    
    def connect(self) -> Tuple[bool, str]:
        """
        Establish SSH tunnel with native port forwarding
        
        This is Step 1: Create R-Pi tunnel with all port mappings
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            print(f"\n[TUNNEL] Step 1: Establishing R-Pi tunnel to {self.rpi_ip}:{self.rpi_port}")
            print(f"[TUNNEL] Device: {self.device_name} ({self.lab_ip}:{self.lab_port})")
            
            # Build port mapping arguments
            # Convert: {8090: 8090} -> "-L 8090:10.0.0.28:8090"
            port_args = []
            for local_port, remote_port in self.PORT_MAPPINGS.items():
                forwarding = f"{local_port}:{self.lab_ip}:{remote_port}"
                port_args.extend(['-L', forwarding])
                print(f"[TUNNEL] Port mapping: 127.0.0.1:{local_port} → {self.lab_ip}:{remote_port}")
            
            # Build SSH command
            ssh_cmd = [
                'ssh',
                '-p', str(self.rpi_port),
                '-N',                      # No remote command (port forwarding only)
                '-f',                       # Fork to background
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null',
            ]
            
            # Add port forwarding arguments
            ssh_cmd.extend(port_args)
            
            # Add connection string
            ssh_cmd.append(f'{self.rpi_username}@{self.rpi_ip}')
            
            print(f"[TUNNEL] SSH command: ssh -p {self.rpi_port} -N -f {self.rpi_username}@{self.rpi_ip}")
            
            # Use sshpass to automate password input
            sshpass_cmd = ['sshpass', '-p', self.rpi_password] + ssh_cmd
            
            # Start tunnel process
            self.tunnel_process = subprocess.Popen(
                sshpass_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # Create process group for clean shutdown
            )
            
            # Wait for tunnel to establish
            time.sleep(1.5)
            
            # Check if process is still running
            poll_result = self.tunnel_process.poll()
            if poll_result is not None:
                stdout, stderr = self.tunnel_process.communicate()
                error_msg = stderr.decode('utf-8', errors='ignore')
                return False, f"SSH tunnel failed to start: {error_msg}"
            
            # Verify that port 10022 is actually listening
            print(f"[TUNNEL] Verifying port forwarding is established...")
            if not self._verify_port_listening(10022):
                self._cleanup_tunnel()
                return False, "Port 10022 not listening after tunnel setup"
            
            self.is_connected = True
            msg = f"✅ SSH tunnel established to {self.device_name} via R-Pi {self.rpi_ip}"
            print(f"[TUNNEL] {msg}")
            return True, msg
        
        except FileNotFoundError:
            return False, "sshpass not found. Install with: sudo apt-get install sshpass"
        except Exception as e:
            import traceback
            error_msg = f"Tunnel connection error: {str(e)}\n{traceback.format_exc()}"
            print(f"[TUNNEL] ❌ {error_msg}")
            return False, error_msg
    
    def _verify_port_listening(self, port: int, timeout: int = 5) -> bool:
        """
        Verify that local port is listening
        
        Args:
            port: Local port to check
            timeout: Max seconds to wait
        
        Returns:
            True if port is listening, False otherwise
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                sock = socket.create_connection(('127.0.0.1', port), timeout=1)
                sock.close()
                print(f"[TUNNEL] ✓ Verified: 127.0.0.1:{port} listening")
                return True
            except (socket.timeout, ConnectionRefusedError, OSError):
                time.sleep(0.2)
        
        print(f"[TUNNEL] ✗ Port {port} not listening after {timeout}s")
        return False
    
    def execute_command(self, command: str, timeout: int = 30) -> Tuple[bool, str, str]:
        """
        Step 2: Execute command on device via tunnel
        
        Connects to: ssh -p 10022 root@10.0.0.28 "command"
        Device IP is accessed directly through R-Pi tunnel
        
        Args:
            command: Command to execute on device
            timeout: Command timeout in seconds
        
        Returns:
            Tuple of (success: bool, stdout: str, stderr: str)
        """
        if not self.is_connected:
            return False, "", "❌ Tunnel not connected"
        
        try:
            print(f"\n[DEVICE] Step 2: Connecting to device via tunnel")
            print(f"[DEVICE] Target: {self.lab_username}@{self.lab_ip}:{self.lab_port}")
            print(f"[DEVICE] Command: {command}")
            
            # Build SSH command to device
            # Connect directly to device IP (not 127.0.0.1)
            # R-Pi tunnel allows direct connection to device
            ssh_cmd = [
                'ssh',
                '-p', str(self.lab_port),
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null',
                '-o', 'ConnectTimeout=10',
                f'{self.lab_username}@{self.lab_ip}',
                command
            ]
            
            # Use sshpass if password is provided
            if self.lab_password:
                ssh_cmd = ['sshpass', '-p', self.lab_password] + ssh_cmd
            
            # Execute command
            print(f"[DEVICE] Executing via tunnel (10022 → {self.lab_ip}:10022)...")
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                print(f"[DEVICE] ✓ Command executed successfully")
                return True, result.stdout, result.stderr
            else:
                print(f"[DEVICE] ✗ Command failed with code {result.returncode}")
                return False, result.stdout, result.stderr
        
        except subprocess.TimeoutExpired:
            error_msg = f"Command timed out after {timeout}s"
            print(f"[DEVICE] ✗ {error_msg}")
            return False, "", error_msg
        
        except Exception as e:
            error_msg = f"Command execution error: {str(e)}"
            print(f"[DEVICE] ✗ {error_msg}")
            import traceback
            print(traceback.format_exc())
            return False, "", error_msg
    
    def disconnect(self):
        """Close SSH tunnel and cleanup"""
        try:
            if self.tunnel_process and self.tunnel_process.poll() is None:
                print(f"\n[TUNNEL] Closing tunnel...")
                self._cleanup_tunnel()
                print(f"[TUNNEL] ✓ SSH tunnel closed")
        except Exception as e:
            print(f"[TUNNEL] ⚠️  Error closing tunnel: {e}")
        
        self.is_connected = False
    
    def _cleanup_tunnel(self):
        """Kill tunnel process and its children"""
        try:
            if self.tunnel_process is None:
                return
            
            # Kill entire process group (in case there are child processes)
            try:
                os.killpg(os.getpgid(self.tunnel_process.pid), signal.SIGTERM)
            except:
                # Fallback if process group kill fails
                self.tunnel_process.terminate()
            
            # Wait for process to finish
            try:
                self.tunnel_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if process won't terminate
                self.tunnel_process.kill()
                self.tunnel_process.wait()
        
        except Exception as e:
            print(f"[TUNNEL] ⚠️  Warning during cleanup: {e}")
        
        self.tunnel_process = None
    
    def __del__(self):
        """Cleanup on object destruction"""
        self.disconnect()


def example_usage():
    """
    Example showing how to use the SSH tunnel service
    """
    print("=" * 70)
    print("GDF SSH Tunnel Service - Example Usage")
    print("=" * 70)
    
    # Configuration
    rpi_config = {
        'rpi_ip': '10.138.17.42',
        'rpi_port': 60201,
        'rpi_username': 'pi',
        'rpi_password': 'your-rpi-password-here'  # Replace with actual password
    }
    
    lab_device_config = {
        'lab_ip': '10.0.0.28',
        'lab_port': 10022,
        'lab_username': 'root',
        'lab_password': '',  # Empty = use SSH keys
        'device_name': 'DT_LAB_SKY_XIONE-UK-0D_AB'
    }
    
    # Create tunnel service
    tunnel = GDFSSHTunnelService(rpi_config, lab_device_config)
    
    try:
        # Step 1: Establish tunnel
        success, msg = tunnel.connect()
        if not success:
            print(f"Failed to connect: {msg}")
            return
        
        print(f"\n✅ Tunnel established!")
        print(f"Local ports now forward through R-Pi to device:")
        print(f"  127.0.0.1:10022 → {lab_device_config['lab_ip']}:10022 (SSH)")
        print(f"  127.0.0.1:8090 → {lab_device_config['lab_ip']}:8090 (Service)")
        print(f"  127.0.0.1:8023 → {lab_device_config['lab_ip']}:8023 (Service)")
        print(f"  127.0.0.1:9005 → {lab_device_config['lab_ip']}:9005 (Service)")
        
        # Step 2: Execute commands via tunnel
        print("\n" + "=" * 70)
        print("Executing device commands via tunnel...")
        print("=" * 70)
        
        # Example 1: Basic command
        success, stdout, stderr = tunnel.execute_command('whoami')
        if success:
            print(f"Command result: {stdout.strip()}")
        else:
            print(f"Command failed: {stderr}")
        
        # Example 2: Check device logs
        success, stdout, stderr = tunnel.execute_command('tail -5 /opt/logs/sky-messages.log')
        if success:
            print(f"Device logs:\n{stdout}")
        else:
            print(f"Could not read logs: {stderr}")
        
        # Example 3: Device status
        success, stdout, stderr = tunnel.execute_command('uptime')
        if success:
            print(f"Device uptime: {stdout.strip()}")
    
    finally:
        # Step 3: Close tunnel
        tunnel.disconnect()
        print("\n✓ All done!")


if __name__ == "__main__":
    example_usage()
