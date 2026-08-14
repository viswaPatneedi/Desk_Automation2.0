#!/usr/bin/env python3
"""
Parallel Multi-R-Pi SSH Connection Test
Tests simultaneous SSH connections to multiple R-Pi devices and their target devices
Verifies:
1. Connection to DESK R-Pi (10.26.52.151:22)
2. Connection to LAB R-Pi (10.138.17.42:60201)
3. Device access via R-Pi: OD-AB (10.0.0.140), DESK LAB (10.0.0.28)
4. Get /version.txt from each device
"""

import paramiko
from sshtunnel import SSHTunnelForwarder
import threading
import time
import json
from datetime import datetime
from typing import Dict, List, Tuple

# Color codes for output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}{Colors.ENDC}\n")

def print_info(text):
    print(f"{Colors.CYAN}[INFO]{Colors.ENDC} {text}")

def print_success(text):
    print(f"{Colors.GREEN}[✓]{Colors.ENDC} {text}")

def print_error(text):
    print(f"{Colors.RED}[✗]{Colors.ENDC} {text}")

def print_warn(text):
    print(f"{Colors.YELLOW}[!]{Colors.ENDC} {text}")

class RPiSSHConnectionTest:
    """Test SSH connections to multiple R-Pi devices in parallel"""
    
    def __init__(self):
        # DESK R-Pi Configuration (Controls CELLO devices)
        self.desk_rpi = {
            'name': 'DESK-R-Pi',
            'ip': '10.26.52.151',
            'port': 22,
            'username': 'lrqa',
            'password': 'Viswa123!',
            'devices': [
                {
                    'name': 'CELLO-SKY',
                    'ip': '10.0.0.95',
                    'port': 10022,
                    'username': 'root',
                    'description': 'SKY STREAM device via DESK R-Pi',
                    'local_tunnel_port': 11022  # Use different local port
                },
                {
                    'name': 'SKY-Glass',
                    'ip': '10.0.0.166',
                    'port': 10022,
                    'username': 'root',
                    'description': 'SKY Glass device via DESK R-Pi',
                    'local_tunnel_port': 11023  # Use different local port
                },
                {
                    'name': 'ELEMENT_A4K',
                    'ip': '10.0.0.172',
                    'port': 10022,
                    'username': 'root',
                    'description': 'ELEMENT A4K device via DESK R-Pi',
                    'local_tunnel_port': 11024  # Use different local port
                }
            ]
        }
        
        # LAB R-Pi Configuration (Controls lab devices)
        self.lab_rpi = {
            'name': 'LAB-R-Pi',
            'ip': '10.138.17.42',
            'port': 60201,
            'username': 'pi',
            'password': 'Eastcoast-Goldfish-Progress',
            'devices': [
                {
                    'name': 'DT-XIONE_UK-0D-AB',
                    'ip': '10.0.0.140',
                    'port': 10022,
                    'username': 'root',
                    'description': 'Lab device DT-XIONE',
                    'local_tunnel_port': 12022  # Use different local port
                },
                {
                    'name': 'DT-XIONE_UK-17-97',
                    'ip': '10.0.0.28',
                    'port': 10022,
                    'username': 'root',
                    'description': 'Lab device DT-XIONE UK-17-97',
                    'local_tunnel_port': 12023  # Use different local port
                },
                {
                    'name': 'DT-XIONE_UK-5D-54',
                    'ip': '10.0.0.199',
                    'port': 10022,
                    'username': 'root',
                    'description': 'Lab device DT-XIONE UK-5D-54',
                    'local_tunnel_port': 12024  # Use different local port
                }
            ]
        }
        
        self.results = {}
        self.lock = threading.Lock()

    def test_rpi_direct_connection(self, rpi_config: Dict) -> Tuple[bool, str, paramiko.SSHClient]:
        """
        Test direct SSH connection to R-Pi
        
        Returns:
            Tuple of (success, message, ssh_client)
        """
        rpi_ip = rpi_config['ip']
        rpi_port = rpi_config['port']
        rpi_user = rpi_config['username']
        rpi_pass = rpi_config['password']
        
        try:
            print_info(f"Connecting to {rpi_config['name']} ({rpi_user}@{rpi_ip}:{rpi_port})...")
            
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect with timeout
            client.connect(
                hostname=rpi_ip,
                port=rpi_port,
                username=rpi_user,
                password=rpi_pass,
                timeout=10,
                allow_agent=False,
                look_for_keys=False
            )
            
            # Verify connection with simple command
            stdin, stdout, stderr = client.exec_command('echo "R-Pi connection test" && hostname')
            output = stdout.read().decode('utf-8').strip()
            error = stderr.read().decode('utf-8').strip()
            
            if error:
                return False, f"Command error: {error}", None
            
            print_success(f"Successfully connected to {rpi_config['name']}")
            print_info(f"  R-Pi Hostname: {output.split(chr(10))[-1]}")
            
            return True, "Connected", client
            
        except Exception as e:
            print_error(f"Failed to connect to {rpi_config['name']}: {str(e)}")
            return False, str(e), None

    def test_device_via_rpi(self, rpi_config: Dict, device_config: Dict, rpi_client: paramiko.SSHClient) -> Dict:
        """
        Test SSH connection to device via R-Pi using direct IP access
        Executes SSH command on R-Pi to reach device directly
        
        Returns:
            Result dictionary with success status and output
        """
        result = {
            'device_name': device_config['name'],
            'device_ip': device_config['ip'],
            'rpi_name': rpi_config['name'],
            'success': False,
            'output': '',
            'error': '',
            'version_info': '',
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            print_info(f"[{rpi_config['name']}] Accessing {device_config['name']} ({device_config['ip']}:{device_config['port']}) via R-Pi...")
            
            # Use R-Pi to execute SSH command to reach device directly
            device_ip = device_config['ip']
            device_port = device_config['port']
            device_user = device_config.get('username', 'root')
            device_password = device_config.get('password', '')
            
            # Build SSH command for direct device access through R-Pi
            # Using StrictHostKeyChecking=no to avoid interactive prompts
            # Using empty password with SSH keys (no password flag)
            ssh_cmd_version = f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p {device_port} {device_user}@{device_ip} 'cat /version.txt'"
            ssh_cmd_hostname = f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p {device_port} {device_user}@{device_ip} 'hostname'"
            
            commands = [
                (ssh_cmd_hostname, 'Get device hostname'),
                (ssh_cmd_version, 'Get version info')
            ]
            
            outputs = []
            for ssh_cmd, desc in commands:
                print_info(f"  Executing: {desc}")
                
                try:
                    # Execute SSH command on R-Pi to access device
                    stdin, stdout, stderr = rpi_client.exec_command(ssh_cmd, get_pty=False)
                    
                    out_data = stdout.read().decode('utf-8', errors='ignore').strip()
                    err_data = stderr.read().decode('utf-8', errors='ignore').strip()
                    exit_code = stdout.channel.recv_exit_status()
                    
                    if exit_code == 0:
                        outputs.append(f"{desc}: {out_data}")
                        if 'version' in desc.lower():
                            result['version_info'] = out_data
                        print_success(f"    ✓ {out_data}")
                    else:
                        if 'version' in desc.lower() and 'No such file' in err_data:
                            # Version file might not exist
                            print_warn(f"    ⚠ Version file not found: {err_data}")
                            result['version_info'] = 'Not available'
                        else:
                            print_warn(f"    ✗ Command failed (exit code {exit_code}): {err_data}")
                            
                except Exception as cmd_err:
                    print_error(f"    ✗ Command execution error: {str(cmd_err)}")
                    result['error'] = str(cmd_err)
            
            if outputs:
                result['output'] = '\n'.join(outputs)
                result['success'] = True
                print_success(f"[{rpi_config['name']}] Successfully accessed {device_config['name']} ({device_config['ip']})")
            else:
                result['error'] = "No successful commands executed"
                print_error(f"[{rpi_config['name']}] Failed to execute commands on {device_config['name']}")
            
        except Exception as e:
            result['error'] = str(e)
            print_error(f"[{rpi_config['name']}] Failed to access {device_config['name']} ({device_config['ip']}): {str(e)}")
        
        return result

    def test_rpi_with_device_tunnel(self, rpi_config: Dict, device_config: Dict) -> Dict:
        """
        Test R-Pi connection and then access device directly via R-Pi as proxy
        
        Returns:
            Result dictionary
        """
        result = {
            'rpi_name': rpi_config['name'],
            'devices_tested': [],
            'success': False,
            'errors': []
        }
        
        try:
            # Step 1: Test direct R-Pi connection
            rpi_success, rpi_msg, rpi_client = self.test_rpi_direct_connection(rpi_config)
            
            if not rpi_success:
                result['errors'].append(f"R-Pi connection failed: {rpi_msg}")
                return result
            
            # Step 2: Access device through R-Pi using direct IP connection
            print_info(f"Creating connection: {rpi_config['name']} → {device_config['name']} ({device_config['ip']}:{device_config['port']})")
            
            try:
                # Test device access through R-Pi connection
                device_result = self.test_device_via_rpi(rpi_config, device_config, rpi_client)
                result['devices_tested'].append(device_result)
                
                if device_result['success']:
                    result['success'] = True
                
            except Exception as connection_error:
                result['errors'].append(f"Device connection failed: {str(connection_error)}")
            
            # Close R-Pi connection
            if rpi_client:
                rpi_client.close()
                
        except Exception as e:
            result['errors'].append(f"Test failed: {str(e)}")
        
        return result

    def run_parallel_tests(self):
        """
        Run all R-Pi and device tests in parallel
        """
        print_header("PARALLEL MULTI-R-Pi SSH CONNECTION TEST")
        print_info("Testing simultaneous connections to multiple R-Pi infrastructures")
        print_info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        threads = []
        
        # Test DESK R-Pi with its devices
        print_header("DESK R-Pi Infrastructure (CELLO Devices)")
        desk_devices = self.desk_rpi['devices']
        
        for device in desk_devices:
            thread = threading.Thread(
                target=self._run_test_thread,
                args=(self.desk_rpi, device, 'desk')
            )
            threads.append(thread)
            thread.start()
        
        # Test LAB R-Pi with its devices
        print_header("LAB R-Pi Infrastructure (Lab Devices)")
        lab_devices = self.lab_rpi['devices']
        
        for device in lab_devices:
            thread = threading.Thread(
                target=self._run_test_thread,
                args=(self.lab_rpi, device, 'lab')
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        print_info("Waiting for all parallel connections to complete...")
        for thread in threads:
            thread.join(timeout=60)
        
        # Print results
        self.print_results()

    def _run_test_thread(self, rpi_config, device_config, key):
        """Run test in thread"""
        try:
            result = self.test_rpi_with_device_tunnel(rpi_config, device_config)
            with self.lock:
                if key not in self.results:
                    self.results[key] = []
                self.results[key].append(result)
        except Exception as e:
            print_error(f"Thread error: {str(e)}")

    def print_results(self):
        """Print summary of all test results"""
        print_header("TEST RESULTS SUMMARY")
        
        total_tests = 0
        total_success = 0
        total_devices = 0
        
        for infrastructure_key, results in self.results.items():
            print_info(f"\n{Colors.BOLD}{infrastructure_key.upper()} Infrastructure:{Colors.ENDC}")
            
            for result in results:
                total_tests += 1
                
                print(f"\n  R-Pi: {result['rpi_name']}")
                
                if result['errors']:
                    for error in result['errors']:
                        print_error(f"    {error}")
                
                if result['devices_tested']:
                    for device_result in result['devices_tested']:
                        total_devices += 1
                        
                        if device_result['success']:
                            total_success += 1
                            print_success(f"    ✓ {device_result['device_name']} ({device_result['device_ip']})")
                            if device_result['version_info']:
                                version_lines = device_result['version_info'].split('\n')[:2]
                                for line in version_lines:
                                    print(f"      {Colors.GREEN}→{Colors.ENDC} {line}")
                        else:
                            print_error(f"    ✗ {device_result['device_name']} ({device_result['device_ip']})")
                            print_error(f"      Error: {device_result['error']}")
        
        # Print statistics
        print_header("STATISTICS")
        print(f"Total R-Pi Tests: {total_tests}")
        print(f"Total Devices Tested: {total_devices}")
        print(f"Successful Connections: {total_success}/{total_devices}")
        
        if total_devices > 0:
            success_rate = (total_success / total_devices) * 100
            if success_rate == 100:
                print_success(f"Success Rate: {success_rate:.1f}% - ALL TESTS PASSED ✓")
            elif success_rate >= 75:
                print_warn(f"Success Rate: {success_rate:.1f}% - PARTIAL SUCCESS")
            else:
                print_error(f"Success Rate: {success_rate:.1f}% - MOSTLY FAILED")
        
        print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def main():
    """Main entry point"""
    try:
        tester = RPiSSHConnectionTest()
        tester.run_parallel_tests()
        
    except KeyboardInterrupt:
        print_error("\nTest interrupted by user")
    except Exception as e:
        print_error(f"Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
