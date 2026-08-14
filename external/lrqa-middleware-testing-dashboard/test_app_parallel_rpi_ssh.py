#!/usr/bin/env python3
"""
Application Integration Test - Parallel Multi-R-Pi SSH
Tests the application's GDFRPiShellService with multiple R-Pi connections
Verifies the application can handle simultaneous connections to multiple R-Pi infrastructures
"""

import sys
import os
import threading
import time
from datetime import datetime
from typing import Dict, List, Tuple

# Add application to path
sys.path.insert(0, '/home/guser/Desk-automation/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard')

from services.gdf_rpi_shell_service import GDFRPiShellService
from models.device import Device

# Color codes
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

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

class ApplicationRPiSSHTest:
    """Test application's SSH capabilities with multiple R-Pi devices"""
    
    def __init__(self):
        # DESK R-Pi Configuration (Controls CELLO devices)
        self.desk_rpi_config = {
            'rpi_ip': '10.26.52.151',
            'rpi_port': 22,
            'rpi_username': 'lrqa',
            'rpi_password': 'Viswa123!'
        }
        
        # CELLO devices via DESK R-Pi
        self.desk_devices = [
            {
                'name': 'CELLO-SKY',
                'ip': '10.0.0.95',
                'port': 10022,
                'username': 'root',
                'device_name': 'CELLO SKY Device'
            },
            {
                'name': 'ELEMENT_A4K',
                'ip': '10.0.0.172',
                'port': 10022,
                'username': 'root',
                'device_name': 'ELEMENT A4K Device'
            }
        ]
        
        # LAB R-Pi Configuration (Controls lab devices)
        self.lab_rpi_config = {
            'rpi_ip': '10.138.17.42',
            'rpi_port': 60201,
            'rpi_username': 'pi',
            'rpi_password': 'Eastcoast-Goldfish-Progress'
        }
        
        # Lab devices via LAB R-Pi
        self.lab_devices = [
            {
                'name': 'DT-XIONE_UK-0D-AB',
                'ip': '10.0.0.140',
                'port': 10022,
                'username': 'root',
                'device_name': 'Lab DT-XIONE Device'
            }
        ]
        
        self.results = {
            'desk': [],
            'lab': []
        }
        self.lock = threading.Lock()

    def test_gdf_tunnel_connection(self, rpi_config: Dict, device_config: Dict, infrastructure_name: str) -> Dict:
        """
        Test SSH connection using GDFRPiShellService
        
        Args:
            rpi_config: R-Pi configuration
            device_config: Target device configuration
            infrastructure_name: Name of infrastructure (desk/cello)
            
        Returns:
            Result dictionary with connection details
        """
        result = {
            'infrastructure': infrastructure_name,
            'device_name': device_config['name'],
            'device_ip': device_config['ip'],
            'rpi_ip': rpi_config['rpi_ip'],
            'success': False,
            'tunnel_status': 'Not started',
            'connection_time': 0,
            'version_info': '',
            'error': '',
            'details': []
        }
        
        try:
            start_time = time.time()
            
            # Create lab device config for GDFRPiShellService
            lab_device_config = {
                'lab_ip': device_config['ip'],
                'lab_port': device_config['port'],
                'lab_username': device_config['username'],
                'lab_password': '',  # Empty password, using SSH key if available
                'device_name': device_config['device_name']
            }
            
            print_info(f"[{infrastructure_name.upper()}] Initializing tunnel to {device_config['name']} via {rpi_config['rpi_ip']}")
            
            # Create tunnel service
            try:
                tunnel_service = GDFRPiShellService(rpi_config, lab_device_config)
                result['details'].append(f"Tunnel service created for {device_config['name']}")
            except Exception as init_error:
                result['error'] = f"Tunnel service initialization failed: {str(init_error)}"
                result['tunnel_status'] = 'Initialization failed'
                print_error(f"Tunnel init failed: {init_error}")
                return result
            
            # Connect
            print_info(f"[{infrastructure_name.upper()}] Establishing SSH tunnel...")
            success, message = tunnel_service.connect()
            
            if not success:
                result['error'] = message
                result['tunnel_status'] = 'Connection failed'
                print_error(f"Tunnel connection failed: {message}")
                return result
            
            result['tunnel_status'] = 'Connected'
            result['details'].append(f"Tunnel established successfully")
            print_success(f"[{infrastructure_name.upper()}] Tunnel established")
            
            # Execute command on device
            print_info(f"[{infrastructure_name.upper()}] Executing command on device...")
            
            # Try to get version info
            cmd = 'cat /version.txt'
            output, error = tunnel_service.execute_command(cmd)
            
            if error:
                print_warn(f"Command error: {error}")
                result['version_info'] = 'Command failed (file may not exist)'
            else:
                result['version_info'] = output[:200] if output else 'No output'
                result['details'].append(f"Successfully retrieved version info")
                print_success(f"[{infrastructure_name.upper()}] Version info retrieved")
            
            # Test additional command
            cmd2 = 'hostname'
            output2, error2 = tunnel_service.execute_command(cmd2)
            if not error2:
                result['details'].append(f"Device hostname: {output2.strip()}")
                print_info(f"  Device hostname: {output2.strip()}")
            
            # Close tunnel
            tunnel_service.disconnect()
            result['tunnel_status'] = 'Closed'
            
            result['success'] = True
            result['connection_time'] = time.time() - start_time
            
            print_success(f"[{infrastructure_name.upper()}] Test completed for {device_config['name']}")
            
        except Exception as e:
            result['error'] = str(e)
            result['tunnel_status'] = 'Error'
            print_error(f"Test failed for {device_config['name']}: {str(e)}")
            import traceback
            result['details'].append(f"Exception: {traceback.format_exc()}")

        return result

    def run_infrastructure_tests(self, infrastructure_name: str, rpi_config: Dict, devices: List[Dict]) -> List[Dict]:
        """
        Run tests for all devices in an infrastructure
        
        Returns:
            List of result dictionaries
        """
        results = []
        
        for device in devices:
            result = self.test_gdf_tunnel_connection(rpi_config, device, infrastructure_name)
            results.append(result)
            
            # Small delay between connections
            time.sleep(2)
        
        return results

    def run_parallel_tests(self):
        """
        Run all tests in parallel threads
        """
        print_header("APPLICATION INTEGRATION TEST - PARALLEL MULTI-R-Pi SSH")
        print_info("Testing GDFRPiShellService with multiple R-Pi infrastructures")
        print_info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        threads = []
        
        # Test DESK infrastructure (CELLO devices)
        print_header("DESK R-Pi Infrastructure (CELLO Devices) Tests")
        desk_thread = threading.Thread(
            target=self._run_infra_thread,
            args=('desk', self.desk_rpi_config, self.desk_devices)
        )
        threads.append(desk_thread)
        desk_thread.start()
        
        # Small delay to ensure sequential infrastructure testing
        time.sleep(3)
        
        # Test LAB infrastructure
        print_header("LAB R-Pi Infrastructure (Lab Devices) Tests")
        lab_thread = threading.Thread(
            target=self._run_infra_thread,
            args=('lab', self.lab_rpi_config, self.lab_devices)
        )
        threads.append(lab_thread)
        lab_thread.start()
        
        # Wait for all threads
        print_info("Waiting for all tests to complete...")
        for thread in threads:
            thread.join(timeout=120)
        
        # Print results
        self.print_results()

    def _run_infra_thread(self, infra_name, rpi_config, devices):
        """Run infrastructure tests in thread"""
        try:
            results = self.run_infrastructure_tests(infra_name, rpi_config, devices)
            with self.lock:
                self.results[infra_name] = results
        except Exception as e:
            print_error(f"Infrastructure thread error: {str(e)}")

    def print_results(self):
        """Print detailed test results"""
        print_header("DETAILED TEST RESULTS")
        
        total_tests = 0
        total_success = 0
        total_time = 0
        
        for infra_name, results in self.results.items():
            if not results:
                continue
                
            print(f"\n{Colors.BOLD}{infra_name.upper()} Infrastructure:{Colors.ENDC}")
            
            for result in results:
                total_tests += 1
                
                status = "✓ SUCCESS" if result['success'] else "✗ FAILED"
                status_color = Colors.GREEN if result['success'] else Colors.RED
                
                print(f"\n  {status_color}{status}{Colors.ENDC}")
                print(f"  Device: {result['device_name']} ({result['device_ip']})")
                print(f"  R-Pi: {result['rpi_ip']}:{60201 if '17.42' in result['rpi_ip'] else 22}")
                print(f"  Tunnel Status: {result['tunnel_status']}")
                print(f"  Connection Time: {result['connection_time']:.2f}s")
                
                if result['success']:
                    total_success += 1
                    total_time += result['connection_time']
                
                if result['version_info']:
                    version_lines = result['version_info'].split('\n')[:3]
                    print(f"  Version Info:")
                    for line in version_lines:
                        if line.strip():
                            print(f"    {line}")
                
                if result['error']:
                    print_error(f"  Error: {result['error']}")
                
                if result['details']:
                    print(f"  Details:")
                    for detail in result['details']:
                        print(f"    • {detail}")
        
        # Statistics
        print_header("STATISTICS")
        print(f"Total Tests: {total_tests}")
        print(f"Successful: {total_success}/{total_tests}")
        
        if total_tests > 0:
            success_rate = (total_success / total_tests) * 100
            avg_time = total_time / total_success if total_success > 0 else 0
            
            if success_rate == 100:
                print_success(f"Success Rate: {success_rate:.1f}% - ALL TESTS PASSED ✓")
            elif success_rate >= 50:
                print_warn(f"Success Rate: {success_rate:.1f}% - PARTIAL SUCCESS")
            else:
                print_error(f"Success Rate: {success_rate:.1f}% - MOSTLY FAILED")
            
            if total_success > 0:
                print(f"Average Connection Time: {avg_time:.2f}s")
        
        print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

def main():
    """Main entry point"""
    try:
        tester = ApplicationRPiSSHTest()
        tester.run_parallel_tests()
        
    except KeyboardInterrupt:
        print_error("\nTest interrupted by user")
    except Exception as e:
        print_error(f"Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
