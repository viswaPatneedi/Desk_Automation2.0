"""
GDF Rack Tunnel Service - Handles SSH connections to lab devices via R-Pi tunnel
Provides 2-stage SSH tunnel: R-Pi jump host with port forwarding to lab device
"""

import paramiko
import time
from typing import Optional, Tuple, Dict
from threading import Lock

class GDFRackTunnelService:
    """Service for establishing and managing SSH tunnels through R-Pi to GDF_RACK lab devices"""
    
    # Connection configurations
    DEFAULT_RPI_PORT = 60201
    DEFAULT_LAB_PORT = 10022
    DEFAULT_LAB_USERNAME = "root"
    TUNNEL_LOCALHOST = "127.0.0.1"
    
    # Timeouts
    TIMEOUT_RPI_CONNECT = 10
    TIMEOUT_COMMAND = 30
    
    # Forwarded ports
    FORWARDED_PORTS = {
        8090: 8090,    # Service port
        10022: 10022,  # SSH port
        8023: 8023,    # Additional service port
        9005: 9005     # Additional service port
    }
    
    def __init__(self, rpi_config: Dict, lab_device_config: Dict):
        """
        Initialize GDF Rack tunnel service
        
        Args:
            rpi_config: R-Pi connection configuration dict with keys:
                - rpi_ip: R-Pi IP address (e.g., 10.138.17.42)
                - rpi_port: R-Pi SSH port (default: 60201)
                - rpi_username: R-Pi username (e.g., pi)
                - rpi_password: R-Pi password
            lab_device_config: Lab device configuration dict with keys:
                - lab_ip: Lab device IP (e.g., 10.0.0.28)
                - lab_port: Lab device SSH port (default: 10022)
                - lab_username: Lab device username (default: root)
                - lab_password: Lab device password
                - device_name: Name of the lab device (for logging)
        """
        # R-Pi Configuration
        self.rpi_ip = rpi_config.get('rpi_ip')
        self.rpi_port = rpi_config.get('rpi_port', self.DEFAULT_RPI_PORT)
        self.rpi_username = rpi_config.get('rpi_username')
        self.rpi_password = rpi_config.get('rpi_password')
        
        # Lab Device Configuration
        self.lab_ip = lab_device_config.get('lab_ip')
        self.lab_port = lab_device_config.get('lab_port', self.DEFAULT_LAB_PORT)
        self.lab_username = lab_device_config.get('lab_username', self.DEFAULT_LAB_USERNAME)
        self.lab_password = lab_device_config.get('lab_password')
        self.device_name = lab_device_config.get('device_name', 'Lab Device')
        
        # Connection objects
        self.rpi_ssh_client = None
        self.lab_ssh_client = None
        self.transport = None
        self.connection_lock = Lock()
        self.is_connected = False
        
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration has all required fields"""
        required_rpi = ['rpi_ip', 'rpi_username', 'rpi_password']
        required_lab = ['lab_ip', 'lab_password']
        
        rpi_config = {
            'rpi_ip': self.rpi_ip,
            'rpi_username': self.rpi_username,
            'rpi_password': self.rpi_password
        }
        lab_config = {
            'lab_ip': self.lab_ip,
            'lab_password': self.lab_password
        }
        
        missing_rpi = [f for f in required_rpi if not rpi_config.get(f)]
        missing_lab = [f for f in required_lab if not lab_config.get(f)]
        
        if missing_rpi:
            raise ValueError(f"Missing R-Pi configuration: {', '.join(missing_rpi)}")
        if missing_lab:
            raise ValueError(f"Missing lab device configuration: {', '.join(missing_lab)}")
    
    def connect(self) -> Tuple[bool, str]:
        """
        Establish tunnel connection (R-Pi → Lab Device)
        This performs 2-stage SSH connection with port forwarding
        
        Returns:
            Tuple of (success, message)
        """
        with self.connection_lock:
            try:
                # Step 1: Connect to R-Pi
                success, msg = self._connect_to_rpi()
                if not success:
                    return False, f"R-Pi connection failed: {msg}"
                
                # Step 2: Set up port forwarding through R-Pi
                success, msg = self._setup_port_forwarding()
                if not success:
                    self._disconnect_rpi()
                    return False, f"Port forwarding setup failed: {msg}"
                
                # Step 3: Connect to lab device through tunnel
                success, msg = self._connect_to_lab_device()
                if not success:
                    self._disconnect_rpi()
                    return False, f"Lab device connection failed: {msg}"
                
                self.is_connected = True
                return True, f"Tunnel established to {self.device_name} via R-Pi successfully"
                
            except Exception as e:
                self._cleanup()
                return False, f"Tunnel connection error: {str(e)}"
    
    def _connect_to_rpi(self) -> Tuple[bool, str]:
        """
        Connect to R-Pi jump host
        
        Returns:
            Tuple of (success, message)
        """
        try:
            self.rpi_ssh_client = paramiko.SSHClient()
            self.rpi_ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.rpi_ssh_client.connect(
                self.rpi_ip,
                port=self.rpi_port,
                username=self.rpi_username,
                password=self.rpi_password,
                timeout=self.TIMEOUT_RPI_CONNECT
            )
            
            print(f"✅ Connected to R-Pi: {self.rpi_ip}:{self.rpi_port}")
            return True, "R-Pi connection successful"
            
        except paramiko.AuthenticationException as e:
            return False, f"Authentication failed: {str(e)}"
        except paramiko.SSHException as e:
            return False, f"SSH error: {str(e)}"
        except Exception as e:
            return False, f"Connection error: {str(e)}"
    
    def _setup_port_forwarding(self) -> Tuple[bool, str]:
        """
        Set up port forwarding from R-Pi to lab device
        This uses SSH's built-in LocalTunnelForwarder capability
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Get the transport object for setting up local port forwards
            self.transport = self.rpi_ssh_client.get_transport()
            
            if not self.transport or not self.transport.is_active():
                return False, "R-Pi transport not active"
            
            # Set up port forwarding for each required port
            # Maps local port to remote (lab device) IP:port through R-Pi
            for local_port, remote_port in self.FORWARDED_PORTS.items():
                try:
                    # Set up local port forward: local_port -> R-Pi -> lab_device:remote_port
                    self.transport.request_port_forward(
                        self.lab_ip,  # Request forward to lab device IP
                        remote_port,   # On this remote port
                        self._port_forward_handler
                    )
                    print(f"✅ Port forwarding: {self.TUNNEL_LOCALHOST}:{local_port} → {self.lab_ip}:{remote_port}")
                except Exception as e:
                    print(f"⚠️  Warning: Port {local_port} forwarding failed: {str(e)}")
                    # Continue with other ports even if one fails
            
            return True, "Port forwarding established"
            
        except Exception as e:
            return False, f"Port forwarding error: {str(e)}"
    
    def _port_forward_handler(self, channel, origin, server_addr):
        """
        Handler for incoming port forward connections
        Called when a connection arrives on a forwarded port
        """
        # This handler accepts the forwarded connection
        pass
    
    def _connect_to_lab_device(self) -> Tuple[bool, str]:
        """
        Connect to lab device through tunnel (via localhost forwarded port)
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Wait a moment for port forwarding to be ready
            time.sleep(0.5)
            
            self.lab_ssh_client = paramiko.SSHClient()
            self.lab_ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.lab_ssh_client.connect(
                self.TUNNEL_LOCALHOST,  # Connect through tunnel
                port=self.lab_port,
                username=self.lab_username,
                password=self.lab_password,
                timeout=self.TIMEOUT_RPI_CONNECT
            )
            
            print(f"✅ Connected to lab device {self.device_name} through tunnel")
            return True, f"Lab device connection through tunnel successful"
            
        except paramiko.AuthenticationException as e:
            return False, f"Lab device authentication failed: {str(e)}"
        except paramiko.SSHException as e:
            return False, f"Lab device SSH error: {str(e)}"
        except Exception as e:
            return False, f"Lab device connection error: {str(e)}"
    
    def disconnect(self):
        """Safely disconnect tunnel (R-Pi and lab device)"""
        with self.connection_lock:
            self._cleanup()
    
    def _cleanup(self):
        """Internal cleanup of all connections"""
        self.is_connected = False
        
        if self.lab_ssh_client:
            try:
                self.lab_ssh_client.close()
            except:
                pass
            self.lab_ssh_client = None
        
        if self.rpi_ssh_client:
            try:
                self.rpi_ssh_client.close()
            except:
                pass
            self.rpi_ssh_client = None
        
        self.transport = None
    
    def _disconnect_rpi(self):
        """Disconnect from R-Pi only (for cleanup on error)"""
        if self.rpi_ssh_client:
            try:
                self.rpi_ssh_client.close()
            except:
                pass
            self.rpi_ssh_client = None
        self.transport = None
    
    def execute_command(self, command: str, timeout: int = None) -> Tuple[bool, str]:
        """
        Execute command on lab device through tunnel
        
        Args:
            command: Command to execute
            timeout: Command timeout in seconds (default: TIMEOUT_COMMAND)
            
        Returns:
            Tuple of (success, output)
        """
        if not self.is_connected or not self.lab_ssh_client:
            return False, "Not connected to lab device. Call connect() first."
        
        if timeout is None:
            timeout = self.TIMEOUT_COMMAND
        
        try:
            stdin, stdout, stderr = self.lab_ssh_client.exec_command(
                command,
                timeout=timeout
            )
            
            # Get command output
            output = stdout.read().decode('utf-8', errors='replace').strip()
            error = stderr.read().decode('utf-8', errors='replace').strip()
            exit_status = stdout.channel.recv_exit_status()
            
            if exit_status != 0 and error:
                return False, f"Command failed: {error}"
            
            return True, output
            
        except Exception as e:
            return False, f"Command execution error: {str(e)}"
    
    def get_status(self) -> Dict:
        """
        Get tunnel connection status
        
        Returns:
            Dictionary with tunnel status information
        """
        return {
            'is_connected': self.is_connected,
            'rpi_ip': self.rpi_ip,
            'rpi_port': self.rpi_port,
            'lab_device': self.device_name,
            'lab_ip': self.lab_ip,
            'lab_port': self.lab_port
        }
    
    def __del__(self):
        """Cleanup on object destruction"""
        try:
            self._cleanup()
        except:
            pass
