#!/usr/bin/env python3
"""
Comprehensive IR Button Test Script
Tests all IR codes and validates against device logs
"""

import sys
import time
import json
from tools.ir_validation_tool import IRValidator
from config.config_paths import IR_KEYCODES_FILE

def test_all_buttons(device_ip, device_password, device_username='root', ir_port=1):
    """Test all IR buttons systematically"""
    
    # Load IR keycodes
    with open(IR_KEYCODES_FILE, 'r') as f:
        data = json.load(f)
    
    keycodes = data.get('keycodes', {})
    
    print("="*80)
    print("COMPREHENSIVE IR BUTTON TEST")
    print("="*80)
    print(f"Device: {device_ip}")
    print(f"iTach: 10.0.0.33")
    print(f"Total Buttons: {len(keycodes)}")
    print(f"IR Port: {ir_port}")
    print("="*80)
    
    # Create validator
    validator = IRValidator(
        device_ip=device_ip,
        device_username=device_username,
        device_password=device_password,
        device_port=10022,
        itach_ip='10.0.0.33',
        itach_port=4998
    )
    
    # Connect to device
    print("\n🔌 Connecting to device...")
    ssh = validator.connect_to_device()
    if not ssh:
        print("❌ Cannot connect to device. Exiting.")
        return
    
    try:
        results = {
            'passed': [],
            'failed': [],
            'no_validation': []
        }
        
        button_list = list(keycodes.keys())
        
        for idx, key_name in enumerate(button_list, 1):
            print(f"\n{'='*80}")
            print(f"Testing Button {idx}/{len(button_list)}: {key_name}")
            print(f"{'='*80}")
            
            success, details = validator.validate_key(key_name, ssh, ir_port)
            
            key_data = keycodes[key_name]
            has_validation = 'validation' in key_data
            
            if success:
                if has_validation:
                    results['passed'].append(key_name)
                    print(f"✅ PASSED")
                else:
                    results['no_validation'].append(key_name)
                    print(f"✓ SENT (No validation data)")
            else:
                results['failed'].append(key_name)
                print(f"❌ FAILED: {details}")
            
            # Wait between tests to avoid overwhelming device
            if idx < len(button_list):
                print(f"\n⏳ Waiting 10 seconds before next test...")
                time.sleep(10)
        
        # Final Summary
        print(f"\n{'='*80}")
        print("FINAL TEST SUMMARY")
        print(f"{'='*80}")
        
        total_tested = len(button_list)
        total_passed = len(results['passed'])
        total_failed = len(results['failed'])
        total_no_val = len(results['no_validation'])
        
        print(f"\n📊 Overall Results:")
        print(f"   Total Buttons Tested: {total_tested}")
        print(f"   ✅ Passed (Validated): {total_passed}")
        print(f"   ✓  Sent (No Validation): {total_no_val}")
        print(f"   ❌ Failed: {total_failed}")
        print(f"   Success Rate: {((total_passed + total_no_val) / total_tested * 100):.1f}%")
        
        if results['passed']:
            print(f"\n✅ PASSED Buttons ({len(results['passed'])}):")
            for btn in results['passed']:
                print(f"   • {btn}")
        
        if results['no_validation']:
            print(f"\n✓ SENT Buttons (No Validation Data) ({len(results['no_validation'])}):")
            for btn in results['no_validation']:
                print(f"   • {btn}")
        
        if results['failed']:
            print(f"\n❌ FAILED Buttons ({len(results['failed'])}):")
            for btn in results['failed']:
                print(f"   • {btn}")
            
            print(f"\n💡 Recommendations for Failed Buttons:")
            print(f"   1. Check if your physical remote has these buttons")
            print(f"   2. Test with physical remote and check device logs for HEX codes")
            print(f"   3. Update ir_keycodes.json with correct IR patterns")
        
        # Save results to file
        results_file = f"ir_test_results_{int(time.time())}.json"
        with open(results_file, 'w') as f:
            json.dump({
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'device_ip': device_ip,
                'total_tested': total_tested,
                'passed': results['passed'],
                'no_validation': results['no_validation'],
                'failed': results['failed']
            }, f, indent=2)
        
        print(f"\n📄 Test results saved to: {results_file}")
        
    finally:
        ssh.close()
        print(f"\n{'='*80}")
        print("Test Complete!")
        print(f"{'='*80}")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 test_all_ir_buttons.py <device_ip> <device_password> [ir_port]")
        print("\nExample:")
        print("  python3 test_all_ir_buttons.py 192.168.1.100 mypassword 1")
        sys.exit(1)
    
    device_ip = sys.argv[1]
    device_password = sys.argv[2]
    ir_port = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    
    test_all_buttons(device_ip, device_password, ir_port=ir_port)
