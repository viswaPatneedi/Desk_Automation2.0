"""
Test Suite for IR Command Router

Tests both delivery methods:
1. Direct socket to iTach
2. R-Pi tunnel delivery

Run with: python3 test_ir_command_router.py
"""

import sys
import logging
from datetime import datetime

# Add project to path
sys.path.insert(0, '/home/guser/Desk-automation/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard')

from services.ir_command_router import IRCommandRouter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IRCommandRouterTester:
    """Test suite for IR command router"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []
    
    def print_header(self, title: str):
        """Print test section header"""
        print(f"\n{'='*70}")
        print(f"  {title}")
        print(f"{'='*70}\n")
    
    def print_test(self, name: str, passed: bool, result: dict = None):
        """Print test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
        
        if result:
            print(f"     Method: {result.get('method')}")
            print(f"     Success: {result.get('success')}")
            print(f"     Message: {result.get('message')}")
        
        if passed:
            self.passed += 1
        else:
            self.failed += 1
        
        self.results.append({'name': name, 'passed': passed, 'result': result})
    
    def test_1_direct_socket_to_itach(self):
        """Test 1: Direct socket connection to iTach"""
        self.print_header("TEST 1: Direct Socket to iTach (10.0.0.12:4998)")
        
        print("Configuration:")
        print("  Target: iTach IR blaster")
        print("  Address: 10.0.0.12:4998")
        print("  Device: CELLO-SKY (10.0.0.95)")
        print("  IR Code: SEND_COMMAND DEVICE:39 ID:POWER\n")
        
        print("Attempting direct socket delivery...")
        
        result = IRCommandRouter.send_ir_command(
            ir_code="SEND_COMMAND DEVICE:39 ID:POWER",
            device_ip="10.0.0.95",
            device_name="CELLO-SKY",
            itach_ip='10.0.0.12',
            itach_port=4998,
            log_callback=lambda msg: print(f"  📡 {msg}")
        )
        
        # Note: May fail if iTach offline, but test the router logic
        passed = result['method'] == 'direct' and 'message' in result
        self.print_test("Direct socket delivery", passed, result)
        
        return result
    
    def test_2_tunnel_via_rpi_desk(self):
        """Test 2: Tunnel delivery via DESK R-Pi"""
        self.print_header("TEST 2: Tunnel Delivery via DESK R-Pi (10.26.52.151)")
        
        rpi_config = {
            'rpi_ip': '10.26.52.151',
            'rpi_port': 22,
            'rpi_username': 'lrqa',
            'rpi_password': 'Viswa123!'
        }
        
        print("Configuration:")
        print("  R-Pi: DESK (10.26.52.151:22)")
        print("  Target Device: CELLO-SKY (10.0.0.95)")
        print("  IR Code: SEND_COMMAND DEVICE:39 ID:POWER\n")
        
        print("Attempting tunnel delivery via R-Pi...")
        
        result = IRCommandRouter.send_ir_command(
            ir_code="SEND_COMMAND DEVICE:39 ID:POWER",
            device_ip="10.0.0.95",
            device_name="CELLO-SKY",
            rpi_config=rpi_config,
            log_callback=lambda msg: print(f"  🔌 {msg}")
        )
        
        passed = result['method'] == 'tunnel' and 'message' in result
        self.print_test("R-Pi tunnel delivery (DESK)", passed, result)
        
        return result
    
    def test_3_tunnel_via_rpi_lab(self):
        """Test 3: Tunnel delivery via LAB R-Pi"""
        self.print_header("TEST 3: Tunnel Delivery via LAB R-Pi (10.138.17.42)")
        
        rpi_config = {
            'rpi_ip': '10.138.17.42',
            'rpi_port': 60201,
            'rpi_username': 'pi',
            'rpi_password': 'Eastcoast-Goldfish-Progress'
        }
        
        print("Configuration:")
        print("  R-Pi: LAB (10.138.17.42:60201)")
        print("  Target Device: DT-XIONE_UK-5D-54 (10.0.0.199)")
        print("  IR Code: SEND_COMMAND DEVICE:39 ID:HOME\n")
        
        print("Attempting tunnel delivery via LAB R-Pi...")
        
        result = IRCommandRouter.send_ir_command(
            ir_code="SEND_COMMAND DEVICE:39 ID:HOME",
            device_ip="10.0.0.199",
            device_name="DT-XIONE_UK-5D-54",
            rpi_config=rpi_config,
            log_callback=lambda msg: print(f"  🔌 {msg}")
        )
        
        passed = result['method'] == 'tunnel' and 'message' in result
        self.print_test("R-Pi tunnel delivery (LAB)", passed, result)
        
        return result
    
    def test_4_ir_code_parsing(self):
        """Test 4: IR code format parsing"""
        self.print_header("TEST 4: IR Code Parsing")
        
        test_cases = [
            ("SEND_COMMAND DEVICE:39 ID:POWER", "POWER"),
            ("SEND_COMMAND DEVICE:39 ID:HOME", "HOME"),
            ("SEND_COMMAND DEVICE:39 ID:RED", "RED"),
            ("SEND_COMMAND DEVICE:39 ID:GREEN", "GREEN"),
        ]
        
        print("Testing IR code parsing...\n")
        
        for ir_code, expected_cmd in test_cases:
            device_cmd = IRCommandRouter._build_device_ir_command(ir_code)
            passed = expected_cmd in device_cmd
            
            print(f"Input:    {ir_code}")
            print(f"Expected: {expected_cmd}")
            print(f"Output:   {device_cmd}")
            print()
            
            self.print_test(f"Parse '{expected_cmd}' from IR code", passed)
        
        return True
    
    def test_5_error_handling_missing_config(self):
        """Test 5: Error handling with missing configuration"""
        self.print_header("TEST 5: Error Handling - Missing Config")
        
        print("Attempting tunnel delivery with incomplete config...\n")
        
        incomplete_config = {
            'rpi_ip': '10.26.52.151'
            # Missing: rpi_port, rpi_username, rpi_password
        }
        
        result = IRCommandRouter.send_ir_command(
            ir_code="SEND_COMMAND DEVICE:39 ID:POWER",
            device_ip="10.0.0.95",
            device_name="CELLO-SKY",
            rpi_config=incomplete_config,
            log_callback=lambda msg: print(f"  ⚠️ {msg}")
        )
        
        # Should fail gracefully with error message
        passed = result['success'] is False and result['message'] != 'Not attempted'
        self.print_test("Handle incomplete R-Pi config", passed, result)
        
        return result
    
    def test_6_error_handling_invalid_itach(self):
        """Test 6: Error handling with invalid iTach address"""
        self.print_header("TEST 6: Error Handling - Invalid iTach")
        
        print("Attempting direct delivery to invalid iTach address...\n")
        
        result = IRCommandRouter.send_ir_command(
            ir_code="SEND_COMMAND DEVICE:39 ID:POWER",
            device_ip="10.0.0.95",
            device_name="CELLO-SKY",
            itach_ip='999.999.999.999',  # Invalid
            itach_port=4998,
            timeout=1.0,  # Short timeout
            log_callback=lambda msg: print(f"  ⚠️ {msg}")
        )
        
        # Should fail gracefully
        passed = result['success'] is False and result['method'] == 'direct'
        self.print_test("Handle invalid iTach address", passed, result)
        
        return result
    
    def test_7_response_format(self):
        """Test 7: Verify response format"""
        self.print_header("TEST 7: Response Format Validation")
        
        print("Testing response format structure...\n")
        
        result = IRCommandRouter.send_ir_command(
            ir_code="SEND_COMMAND DEVICE:39 ID:TEST",
            device_ip="10.0.0.95",
            device_name="TEST-DEVICE"
        )
        
        # Check required fields
        required_fields = ['success', 'method', 'message', 'attempted_at', 'ir_code', 'device_ip', 'device_name']
        
        all_present = all(field in result for field in required_fields)
        
        print("Response structure:")
        for field, value in result.items():
            print(f"  {field}: {value}")
        print()
        
        self.print_test("All required response fields present", all_present)
        
        return result
    
    def run_all_tests(self):
        """Run complete test suite"""
        print("\n" + "="*70)
        print("  IR COMMAND ROUTER - TEST SUITE")
        print("  Starting:", datetime.now().isoformat())
        print("="*70)
        
        # Run tests (some may fail due to network/device state)
        self.test_1_direct_socket_to_itach()
        self.test_2_tunnel_via_rpi_desk()
        self.test_3_tunnel_via_rpi_lab()
        self.test_4_ir_code_parsing()
        self.test_5_error_handling_missing_config()
        self.test_6_error_handling_invalid_itach()
        self.test_7_response_format()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        total = self.passed + self.failed
        pass_rate = (self.passed / total * 100) if total > 0 else 0
        
        print("\n" + "="*70)
        print("  TEST SUMMARY")
        print("="*70)
        print(f"\n  Total:   {total}")
        print(f"  Passed:  {self.passed} ({pass_rate:.1f}%)")
        print(f"  Failed:  {self.failed} ({100-pass_rate:.1f}%)")
        print("\n  Details:")
        
        for test in self.results:
            status = "✅" if test['passed'] else "❌"
            print(f"  {status} {test['name']}")
        
        print("\n" + "="*70)
        print(f"  Status: {'ALL TESTS PASSED ✅' if self.failed == 0 else f'{self.failed} TESTS FAILED ❌'}")
        print("="*70 + "\n")


def main():
    """Main test entry point"""
    tester = IRCommandRouterTester()
    tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if tester.failed == 0 else 1)


if __name__ == '__main__':
    main()
