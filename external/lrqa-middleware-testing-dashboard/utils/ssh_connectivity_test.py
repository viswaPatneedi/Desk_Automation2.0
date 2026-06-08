"""SSH Connectivity Tester - Validates device SSH accessibility before job execution"""

import paramiko
import socket
import time
import os


class SSHConnectivityTester:
    """Test SSH connectivity to devices with retry logic"""
    
    @staticmethod
    def test_connectivity(device_ip, port=10022, username='root', password='',
                          timeout=10, retries=3):
        """
        Test SSH connectivity to a device.
        
        Args:
            device_ip: Device IP address
            port: SSH port (default 10022)
            username: SSH username (default 'root')
            password: SSH password
            timeout: Connection timeout in seconds
            retries: Number of retry attempts
        
        Returns:
            dict: {
                'success': bool - Overall success status,
                'connected': bool - SSH connection successful,
                'attempts': int - Number of attempts made,
                'error': str or None - Error message if failed,
                'device_info': dict or None - Device info if connected,
                'retry_count': int - Number of retries performed
            }
        """
        result = {
            'success': False,
            'connected': False,
            'attempts': 0,
            'error': None,
            'device_info': None,
            'retry_count': 0
        }
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            for attempt in range(retries):
                result['attempts'] = attempt + 1
                
                try:
                    # Try to connect
                    client.connect(
                        hostname=device_ip,
                        port=port,
                        username=username,
                        password=password,
                        timeout=timeout,
                        look_for_keys=False,
                        allow_agent=False
                    )
                    
                    # Connection successful
                    result['connected'] = True
                    
                    # Get device info
                    try:
                        stdin, stdout, stderr = client.exec_command('uptime')
                        uptime = stdout.read().decode().strip()
                        result['device_info'] = {'uptime': uptime}
                    except:
                        pass
                    
                    result['success'] = True
                    break
                        
                except socket.timeout:
                    result['error'] = f"Connection timeout (attempt {attempt + 1}/{retries})"
                    result['retry_count'] = attempt + 1
                    if attempt < retries - 1:
                        time.sleep(2)  # Wait before retry
                
                except paramiko.AuthenticationException:
                    result['error'] = "Authentication failed - check credentials"
                    result['retry_count'] = attempt + 1
                    break
                
                except paramiko.SSHException as e:
                    result['error'] = f"SSH error: {str(e)}"
                    result['retry_count'] = attempt + 1
                    if attempt < retries - 1:
                        time.sleep(1)  # Wait before retry
                
                except ConnectionRefusedError:
                    result['error'] = f"Connection refused (attempt {attempt + 1}/{retries})"
                    result['retry_count'] = attempt + 1
                    if attempt < retries - 1:
                        time.sleep(2)  # Wait before retry
                
                except Exception as e:
                    result['error'] = f"Connection error: {str(e)}"
                    result['retry_count'] = attempt + 1
                    if attempt < retries - 1:
                        time.sleep(1)  # Wait before retry
        
        finally:
            try:
                client.close()
            except:
                pass
        
        return result
    
    @staticmethod
    def diagnose_connectivity(device_ip, port=10022, username='root', password=''):
        """
        Perform comprehensive connectivity diagnosis.
        
        Args:
            device_ip: Device IP address
            port: SSH port
            username: SSH username
            password: SSH password
        
        Returns:
            dict: Diagnostic information with ping and SSH status
        """
        diagnosis = {
            'device_ip': device_ip,
            'port': port,
            'timestamp': str(int(time.time())),
            'ping_reachable': False,
            'ssh_connectable': False,
            'error': None,
            'details': {}
        }
        
        # Test basic connectivity (ping)
        try:
            response = os.system(f"ping -c 1 -W 2 {device_ip} > /dev/null 2>&1")
            diagnosis['ping_reachable'] = (response == 0)
            if diagnosis['ping_reachable']:
                diagnosis['details']['ping'] = 'Device responds to ping'
            else:
                diagnosis['details']['ping'] = 'Device does not respond to ping (may be in deep sleep or offline)'
        except Exception as e:
            diagnosis['details']['ping'] = f"Ping test failed: {e}"
        
        # Test SSH connectivity
        result = SSHConnectivityTester.test_connectivity(
            device_ip=device_ip,
            port=port,
            username=username,
            password=password,
            timeout=5,
            retries=2
        )
        
        diagnosis['ssh_connectable'] = result['connected']
        if not result['success']:
            diagnosis['error'] = result['error']
            diagnosis['details']['ssh'] = {
                'status': 'Failed',
                'attempts': result['attempts'],
                'error': result['error']
            }
        else:
            diagnosis['details']['ssh'] = {
                'status': 'Connected',
                'attempts': result['attempts'],
                'device_info': result['device_info']
            }
        
        return diagnosis
    
    @staticmethod
    def validate_before_job_start(device_ip, port=10022, username='root', password='', 
                                 device_name='Unknown', log_callback=None):
        """
        Full validation before starting a job. This is the recommended interface.
        
        Args:
            device_ip: Device IP address
            port: SSH port
            username: SSH username
            password: SSH password  
            device_name: Device name for logging
            log_callback: Optional callback function for logging (e.g., log_service.log)
        
        Returns:
            dict: Validation result with success flag and error details
        """
        def log_msg(msg):
            if log_callback:
                log_callback(msg)
            else:
                print(msg)
        
        log_msg(f"\n🔍 [SSH-VALIDATION] Validating SSH accessibility for {device_name} ({device_ip})")
        
        # First check if reachable via ping
        log_msg(f"  Step 1: Testing network reachability...")
        try:
            response = os.system(f"ping -c 1 -W 2 {device_ip} > /dev/null 2>&1")
            if response != 0:
                log_msg(f"    ⚠️  Device does not respond to ping (may be offline or in deep sleep)")
                # Still try SSH connection even if ping fails
            else:
                log_msg(f"    ✓ Device responds to ping")
        except Exception as e:
            log_msg(f"    ⚠️  Ping test error: {e}")
        
        # Test SSH connection
        log_msg(f"  Step 2: Testing SSH connection...")
        result = SSHConnectivityTester.test_connectivity(
            device_ip=device_ip,
            port=port,
            username=username,
            password=password,
            timeout=10,
            retries=3
        )
        
        if result['success']:
            log_msg(f"    ✅ SSH connection successful")
            if result['device_info']:
                log_msg(f"    Device info: {result['device_info']}")
            return {
                'success': True,
                'connected': True,
                'message': f"Device {device_ip} is accessible"
            }
        else:
            log_msg(f"    ❌ SSH connection failed after {result['attempts']} attempts")
            log_msg(f"    Error: {result['error']}")
            return {
                'success': False,
                'connected': False,
                'error': result['error'],
                'message': f"Cannot connect to device {device_ip}: {result['error']}"
            }
