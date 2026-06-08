#!/usr/bin/env python3
"""
Test script for jump host integration
Tests both direct SSH and jump host connections
"""

import sys
import json
from models.device import Device
from services.jump_host_service import test_jump_host_connection
from services.ssh_connection_helper import SSHConnectionHelper, execute_device_command

def test_direct_ssh_connection():
    """Test direct SSH connection (existing functionality)"""
    print("\n" + "="*70)
    print("TEST 1: Direct SSH Connection (Existing Functionality)")
    print("="*70)
    
    # Load a device with direct SSH
    devices = Device.load_all()
    direct_devices = [d for d in devices if not d.use_jump_host]
    
    if not direct_devices:
        print("⚠ No devices configured for direct SSH. Skipping test.")
        return False
    
    device = direct_devices[0]
    print(f"Testing device: {device.name} ({device.ip})")
    
    success, message = device.validate_connection()
    if success:
        print(f"✓ Direct SSH connection successful: {message}")
        return True
    else:
        print(f"✗ Direct SSH connection failed: {message}")
        return False


def test_jump_host_service():
    """Test jump host service directly"""
    print("\n" + "="*70)
    print("TEST 2: Jump Host Service (Low-level)")
    print("="*70)
    
    # Get jump host config from user
    print("\nEnter jump host credentials:")
    jump_host = input("Jump host IP (default: 96.118.26.235): ").strip() or "96.118.26.235"
    jump_user = input("Jump host username: ").strip()
    jump_pass = input("Jump host password: ").strip()
    device_mac = input("Device MAC address (XX:XX:XX:XX:XX:XX): ").strip()
    
    if not all([jump_user, jump_pass, device_mac]):
        print("✗ Missing required credentials. Skipping test.")
        return False
    
    print(f"\nTesting connection to device {device_mac} via jump host {jump_host}...")
    
    result = test_jump_host_connection(
        jump_host=jump_host,
        jump_user=jump_user,
        jump_pass=jump_pass,
        device_mac=device_mac,
        test_command="uname -a"
    )
    
    print("\nTest Results:")
    print(f"  Jump Host Connection: {'✓' if result['jump_host_connection'] else '✗'}")
    print(f"  Device Connection:    {'✓' if result['device_connection'] else '✗'}")
    print(f"  Command Execution:    {'✓' if result['command_execution'] else '✗'}")
    
    if result['output']:
        print(f"\nCommand Output:\n{result['output']}")
    
    if result['errors']:
        print(f"\nErrors:")
        for error in result['errors']:
            print(f"  - {error}")
    
    return all([
        result['jump_host_connection'],
        result['device_connection'],
        result['command_execution']
    ])


def test_device_with_jump_host():
    """Test device connection via jump host (high-level)"""
    print("\n" + "="*70)
    print("TEST 3: Device Connection via Jump Host (High-level)")
    print("="*70)
    
    # Find device configured with jump host
    devices = Device.load_all()
    jump_devices = [d for d in devices if d.use_jump_host]
    
    if not jump_devices:
        print("⚠ No devices configured with jump host. Skipping test.")
        print("\nTo test this, add jump_host_config to a device in devices.json:")
        print(json.dumps({
            "use_jump_host": True,
            "jump_host_config": {
                "host": "96.118.26.235",
                "username": "your_username",
                "password": "your_password",
                "port": 22
            }
        }, indent=4))
        return False
    
    device = jump_devices[0]
    print(f"Testing device: {device.name} (MAC: {device.mac_address})")
    print(f"Jump host: {device.jump_host_config.get('host', 'N/A')}")
    
    # Test connection
    success, message = device.validate_connection()
    if success:
        print(f"✓ Connection validation successful: {message}")
    else:
        print(f"✗ Connection validation failed: {message}")
        return False
    
    # Test command execution
    print("\nTesting command execution...")
    success, output = execute_device_command(device, "cat /version.txt", timeout=10)
    
    if success:
        print(f"✓ Command execution successful")
        print(f"\nOutput:\n{output}")
        return True
    else:
        print(f"✗ Command execution failed: {output}")
        return False


def test_ssh_connection_helper():
    """Test SSHConnectionHelper with context manager"""
    print("\n" + "="*70)
    print("TEST 4: SSH Connection Helper (Context Manager)")
    print("="*70)
    
    devices = Device.load_all()
    if not devices:
        print("✗ No devices found in devices.json")
        return False
    
    device = devices[0]
    print(f"Testing device: {device.name}")
    print(f"Connection method: {'Jump Host' if device.use_jump_host else 'Direct SSH'}")
    
    try:
        with SSHConnectionHelper(device) as ssh:
            print("✓ Connection established")
            
            # Test command
            success, output = ssh.execute_command("hostname")
            if success:
                print(f"✓ Command execution successful")
                print(f"  Hostname: {output.strip()}")
                return True
            else:
                print(f"✗ Command execution failed: {output}")
                return False
                
    except Exception as e:
        print(f"✗ Connection failed: {str(e)}")
        return False


def test_mixed_device_configuration():
    """Test handling of mixed direct and jump host devices"""
    print("\n" + "="*70)
    print("TEST 5: Mixed Device Configuration")
    print("="*70)
    
    devices = Device.load_all()
    direct_count = sum(1 for d in devices if not d.use_jump_host)
    jump_count = sum(1 for d in devices if d.use_jump_host)
    
    print(f"Total devices: {len(devices)}")
    print(f"  Direct SSH devices: {direct_count}")
    print(f"  Jump host devices:  {jump_count}")
    
    if len(devices) == 0:
        print("✗ No devices configured")
        return False
    
    # Test each device type
    results = {'direct': 0, 'jump': 0, 'failed': 0}
    
    for device in devices[:3]:  # Test first 3 devices
        print(f"\nTesting: {device.name}")
        success, message = device.validate_connection()
        
        if success:
            if device.use_jump_host:
                results['jump'] += 1
                print(f"  ✓ Jump host connection OK")
            else:
                results['direct'] += 1
                print(f"  ✓ Direct SSH connection OK")
        else:
            results['failed'] += 1
            print(f"  ✗ Connection failed: {message}")
    
    print(f"\nResults:")
    print(f"  Direct SSH successful: {results['direct']}")
    print(f"  Jump host successful:  {results['jump']}")
    print(f"  Failed:                {results['failed']}")
    
    return results['failed'] == 0


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("JUMP HOST INTEGRATION TEST SUITE")
    print("="*70)
    
    tests = [
        ("Direct SSH Connection", test_direct_ssh_connection, True),
        ("Jump Host Service", test_jump_host_service, False),  # Requires user input
        ("Device with Jump Host", test_device_with_jump_host, True),
        ("SSH Connection Helper", test_ssh_connection_helper, True),
        ("Mixed Device Config", test_mixed_device_configuration, True)
    ]
    
    results = {}
    
    # Ask which tests to run
    print("\nAvailable tests:")
    for i, (name, func, auto) in enumerate(tests, 1):
        auto_str = "(auto)" if auto else "(manual)"
        print(f"  {i}. {name} {auto_str}")
    
    choice = input("\nRun all auto tests (a), all tests (m), or specific test (1-5)? [a]: ").strip().lower()
    
    if choice == 'm':
        selected_tests = tests
    elif choice.isdigit() and 1 <= int(choice) <= len(tests):
        selected_tests = [tests[int(choice) - 1]]
    else:
        # Default: run only auto tests
        selected_tests = [(name, func, auto) for name, func, auto in tests if auto]
    
    # Run selected tests
    for name, func, auto in selected_tests:
        try:
            result = func()
            results[name] = result
        except Exception as e:
            print(f"\n✗ Test '{name}' crashed: {str(e)}")
            results[name] = False
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {name}")
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    print(f"\nTotal: {passed}/{total} passed")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
