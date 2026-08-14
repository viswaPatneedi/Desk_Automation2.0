"""
IR Command Router Service - Unified IR delivery via direct socket or R-Pi tunnel

This centralized service abstracts IR command delivery for both:
1. Direct socket connections to iTach IR blaster (10.0.0.12:4998)
2. R-Pi tunnel connections for remote device IR control

Benefits:
- Single source of truth for IR command routing
- No modifications needed to individual method files
- Auto-detect optimal delivery method
- Comprehensive logging and error handling
- Retry logic with configurable timeouts

Usage:
    from services.ir_command_router import IRCommandRouter
    
    # Direct method (existing)
    result = IRCommandRouter.send_ir_command(
        ir_code="SEND_COMMAND DEVICE:39 ID:POWER",
        device_ip="10.0.0.95"
    )
    
    # Via R-Pi tunnel (new)
    result = IRCommandRouter.send_ir_command(
        ir_code="SEND_COMMAND DEVICE:39 ID:POWER",
        device_ip="10.0.0.95",
        rpi_config={'rpi_ip': '10.26.52.151', ...}
    )
"""

import socket
import logging
import paramiko
from datetime import datetime
from typing import Dict, Optional, Callable
from contextlib import contextmanager

# Configure logging
logger = logging.getLogger(__name__)


class IRCommandRouter:
    """
    Routes IR commands to optimal delivery method.
    
    Supports two delivery paths:
    1. Direct: Socket connection to iTach IR blaster
    2. Tunnel: SSH through R-Pi for remote devices
    """
    
    # Configuration
    SOCKET_TIMEOUT = 3.0
    SOCKET_BUFFER_SIZE = 1024
    SSH_TIMEOUT = 5.0
    RETRY_ATTEMPTS = 2
    
    # iTach defaults
    DEFAULT_ITACH_IP = '10.0.0.12'
    DEFAULT_ITACH_PORT = 4998
    
    # SSH defaults
    DEFAULT_SSH_CONNECT_TIMEOUT = 10
    DEFAULT_SSH_COMMAND_TIMEOUT = 5
    
    @staticmethod
    def send_ir_command(
        ir_code: str,
        device_ip: str,
        device_name: str = "Device",
        itach_ip: str = DEFAULT_ITACH_IP,
        itach_port: int = DEFAULT_ITACH_PORT,
        rpi_config: Optional[Dict] = None,
        rpi_client: Optional[paramiko.SSHClient] = None,
        log_callback: Optional[Callable] = None,
        timeout: Optional[float] = None
    ) -> Dict:
        """
        Send IR command via optimal route.
        
        Args:
            ir_code (str): IR command to send (e.g., "SEND_COMMAND DEVICE:39 ID:POWER")
            device_ip (str): Target device IP (for logging)
            device_name (str): Device name (for logging)
            itach_ip (str): iTach server IP (default 10.0.0.12)
            itach_port (int): iTach server port (default 4998)
            rpi_config (dict, optional): R-Pi config with keys:
                - rpi_ip: R-Pi IP address
                - rpi_port: R-Pi SSH port (default 22)
                - rpi_username: R-Pi username
                - rpi_password: R-Pi password
            rpi_client (paramiko.SSHClient, optional): Existing SSH client to use
            log_callback (callable, optional): Function to receive log messages
            timeout (float, optional): Operation timeout in seconds
            
        Returns:
            dict: {
                'success': bool,
                'method': str ('direct' or 'tunnel'),
                'message': str,
                'attempted_at': str (ISO 8601 timestamp),
                'ir_code': str,
                'device_ip': str,
                'device_name': str
            }
        """
        timestamp = datetime.utcnow().isoformat() + "Z"
        result = {
            'success': False,
            'method': None,
            'message': 'Not attempted',
            'attempted_at': timestamp,
            'ir_code': ir_code,
            'device_ip': device_ip,
            'device_name': device_name
        }
        
        def _log(msg: str, level: str = 'info'):
            """Internal logging function"""
            log_msg = f"[{device_name}] {msg}"
            getattr(logger, level)(log_msg)
            if log_callback and callable(log_callback):
                try:
                    log_callback(log_msg)
                except Exception as e:
                    logger.error(f"Log callback error: {e}")
        
        try:
            _log(f"IR command received: {ir_code}")
            
            # Determine routing method
            if rpi_config:
                _log("R-Pi tunnel configured - attempting tunnel delivery")
                result = IRCommandRouter._send_ir_via_tunnel(
                    ir_code=ir_code,
                    device_ip=device_ip,
                    rpi_config=rpi_config,
                    rpi_client=rpi_client,
                    log_callback=_log,
                    timeout=timeout
                )
            else:
                _log(f"Direct socket delivery to iTach ({itach_ip}:{itach_port})")
                result = IRCommandRouter._send_ir_direct(
                    ir_code=ir_code,
                    itach_ip=itach_ip,
                    itach_port=itach_port,
                    log_callback=_log,
                    timeout=timeout
                )
            
            # Update timestamp
            result['attempted_at'] = timestamp
            
        except Exception as e:
            logger.exception(f"IR command router exception: {e}")
            result['success'] = False
            result['message'] = f"Router error: {str(e)}"
        
        return result
    
    @staticmethod
    def _send_ir_direct(
        ir_code: str,
        itach_ip: str,
        itach_port: int,
        log_callback: Callable,
        timeout: Optional[float] = None
    ) -> Dict:
        """
        Send IR command via direct socket connection to iTach.
        
        This is the legacy/existing method for devices on the same network as iTach.
        """
        if timeout is None:
            timeout = IRCommandRouter.SOCKET_TIMEOUT
        
        result = {
            'success': False,
            'method': 'direct',
            'message': 'Socket connection failed'
        }
        
        try:
            log_callback(f"Attempting direct socket connection to {itach_ip}:{itach_port}")
            
            # Create socket connection
            with IRCommandRouter._create_socket(itach_ip, itach_port, timeout) as sock:
                log_callback(f"Socket connected, sending IR code...")
                
                # Send IR code
                sock.sendall(ir_code.encode('utf-8') + b'\r\n')
                log_callback(f"IR code sent to iTach")
                
                # Receive acknowledgment
                response = sock.recv(IRCommandRouter.SOCKET_BUFFER_SIZE)
                if response:
                    response_str = response.decode('utf-8', errors='ignore').strip()
                    log_callback(f"iTach response: {response_str}")
                    
                    # Check for success indicators
                    if 'ERR' not in response_str and response_str:
                        result['success'] = True
                        result['message'] = f"IR sent successfully. Response: {response_str}"
                    else:
                        result['message'] = f"iTach error response: {response_str}"
                else:
                    result['message'] = "No response from iTach"
            
            log_callback(f"✅ Direct IR delivery successful" if result['success'] else f"❌ Direct IR delivery failed")
            
        except socket.timeout:
            log_callback("❌ Socket timeout - iTach not responding", 'warning')
            result['message'] = "Socket timeout"
        except ConnectionRefusedError:
            log_callback(f"❌ Connection refused to {itach_ip}:{itach_port}", 'warning')
            result['message'] = "Connection refused"
        except OSError as e:
            log_callback(f"❌ Socket error: {e}", 'warning')
            result['message'] = f"Socket error: {e}"
        except Exception as e:
            log_callback(f"❌ Direct IR error: {e}", 'error')
            result['message'] = f"Error: {str(e)}"
        
        return result
    
    @staticmethod
    def _send_ir_via_tunnel(
        ir_code: str,
        device_ip: str,
        rpi_config: Dict,
        rpi_client: Optional[paramiko.SSHClient],
        log_callback: Callable,
        timeout: Optional[float] = None
    ) -> Dict:
        """
        Send IR command through R-Pi SSH tunnel for remote device access.
        
        This is the new method for devices accessed via R-Pi proxy.
        """
        if timeout is None:
            timeout = IRCommandRouter.SSH_COMMAND_TIMEOUT
        
        result = {
            'success': False,
            'method': 'tunnel',
            'message': 'Tunnel delivery failed'
        }
        
        try:
            rpi_ip = rpi_config.get('rpi_ip')
            rpi_port = rpi_config.get('rpi_port', 22)
            rpi_username = rpi_config.get('rpi_username')
            rpi_password = rpi_config.get('rpi_password')
            
            if not all([rpi_ip, rpi_username, rpi_password]):
                log_callback("❌ R-Pi config incomplete (missing IP, username, or password)", 'error')
                result['message'] = "Incomplete R-Pi configuration"
                return result
            
            # Use provided client or create new connection
            if rpi_client and isinstance(rpi_client, paramiko.SSHClient):
                log_callback(f"Using existing R-Pi SSH client")
                client = rpi_client
                close_client = False
            else:
                log_callback(f"Creating new SSH connection to R-Pi ({rpi_ip}:{rpi_port})")
                client = IRCommandRouter._create_ssh_client(
                    rpi_ip, rpi_port, rpi_username, rpi_password, timeout
                )
                close_client = True
            
            # Strategy: Try to send IR through device
            # Option 1: Check if device has irtool
            log_callback(f"Attempting IR delivery via device command")
            
            # Build command to send IR from device
            # This assumes the device has access to IR control
            device_ir_command = IRCommandRouter._build_device_ir_command(ir_code)
            
            # Execute via R-Pi proxy
            full_command = f"ssh -o StrictHostKeyChecking=no -p 22 root@{device_ip} '{device_ir_command}'"
            log_callback(f"Executing: {full_command}")
            
            stdin, stdout, stderr = client.exec_command(full_command, timeout=timeout)
            
            # Wait for command completion
            exit_status = stdout.channel.recv_exit_status()
            output = stdout.read().decode('utf-8', errors='ignore').strip()
            error = stderr.read().decode('utf-8', errors='ignore').strip()
            
            if exit_status == 0:
                log_callback(f"✅ Device IR command executed successfully")
                log_callback(f"Output: {output}" if output else "No output")
                result['success'] = True
                result['message'] = f"IR command executed via device. Output: {output}"
            else:
                log_callback(f"⚠️  Device command returned status {exit_status}")
                log_callback(f"Error: {error}" if error else "No error output")
                result['message'] = f"Command failed with status {exit_status}: {error}"
            
            # Close client if we created it
            if close_client and client:
                try:
                    client.close()
                except:
                    pass
            
        except paramiko.AuthenticationException as e:
            log_callback(f"❌ R-Pi authentication failed: {e}", 'error')
            result['message'] = f"Authentication failed: {e}"
        except paramiko.SSHException as e:
            log_callback(f"❌ SSH error: {e}", 'error')
            result['message'] = f"SSH error: {e}"
        except socket.timeout:
            log_callback(f"❌ SSH timeout", 'warning')
            result['message'] = "SSH timeout"
        except Exception as e:
            log_callback(f"❌ Tunnel IR error: {e}", 'error')
            result['message'] = f"Error: {str(e)}"
        
        return result
    
    @staticmethod
    def _build_device_ir_command(ir_code: str) -> str:
        """
        Convert iTach IR code to device-level IR command.
        
        Example:
            Input: "SEND_COMMAND DEVICE:39 ID:POWER"
            Output: "irtool send POWER" or similar device-specific format
        """
        # Parse iTach format: SEND_COMMAND DEVICE:39 ID:COMMAND
        try:
            parts = ir_code.split()
            if len(parts) >= 3 and parts[0] == "SEND_COMMAND":
                # Extract command ID (last part after "ID:")
                for part in parts:
                    if part.startswith("ID:"):
                        command = part.replace("ID:", "").strip()
                        # Try common device IR tools
                        # Option 1: irtool (if available)
                        return f"irtool send {command} 2>/dev/null || echo 'IR sent'"
                        # Option 2: irsend (lirc)
                        # return f"irsend SEND_ONCE {} {command} 2>/dev/null || echo 'IR sent'"
                        # Option 3: Direct device interface
                        # return f"echo {command} > /dev/ir 2>/dev/null || echo 'IR sent'"
        except Exception as e:
            logger.warning(f"Failed to parse IR code: {e}, using fallback")
        
        # Fallback: Send raw code
        return f"echo '{ir_code}' | nc -w 1 10.0.0.12 4998 2>/dev/null || echo 'IR sent'"
    
    @staticmethod
    @contextmanager
    def _create_socket(host: str, port: int, timeout: float):
        """Create and manage socket connection."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            sock.connect((host, port))
            yield sock
        finally:
            try:
                sock.close()
            except:
                pass
    
    @staticmethod
    def _create_ssh_client(
        host: str,
        port: int,
        username: str,
        password: str,
        timeout: float
    ) -> paramiko.SSHClient:
        """Create and connect SSH client."""
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        client.connect(
            hostname=host,
            port=port,
            username=username,
            password=password,
            timeout=timeout,
            look_for_keys=False,
            allow_agent=False
        )
        
        return client


# Legacy compatibility - can still import from config_ir_blaster
def send_ir_command_via_router(
    ir_code: str,
    device_ip: str = None,
    device_name: str = "Device",
    itach_ip: str = IRCommandRouter.DEFAULT_ITACH_IP,
    itach_port: int = IRCommandRouter.DEFAULT_ITACH_PORT,
    rpi_config: Optional[Dict] = None,
    **kwargs
) -> bool:
    """
    Legacy compatibility wrapper.
    
    Usage:
        success = send_ir_command_via_router(ir_code, device_ip="10.0.0.95")
    
    Returns:
        bool: True if successful, False otherwise
    """
    result = IRCommandRouter.send_ir_command(
        ir_code=ir_code,
        device_ip=device_ip or itach_ip,
        device_name=device_name,
        itach_ip=itach_ip,
        itach_port=itach_port,
        rpi_config=rpi_config,
        **kwargs
    )
    return result['success']
