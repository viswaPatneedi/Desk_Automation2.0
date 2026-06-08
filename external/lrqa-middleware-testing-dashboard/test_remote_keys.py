#!/usr/bin/env python3
"""
Test script to verify send_remote_keys method actually sends keys to device
"""
import sys
import time
from method_remote_keys import send_remote_keys

# Test device configuration
TEST_DEVICE_IP = "10.0.0.126"  # WestingHouse-4K-DESK
TEST_PORT = 10022
TEST_USERNAME = "root"
TEST_PASSWORD = ""

print("=" * 70)
print("REMOTE KEY SEND TEST - Verifying keySimulator on Device")
print("=" * 70)
print(f"Target Device: {TEST_DEVICE_IP}")
print(f"Test Sequence: HOME -> RIGHT -> DOWN -> SELECT")
print("=" * 70)
print()

# Test 1: Send HOME key first (go to home screen)
print("Test 1: Sending HOME key...")
result = send_remote_keys(TEST_DEVICE_IP, "HOME", TEST_PORT, TEST_USERNAME, TEST_PASSWORD)
print(f"  Result: {result}")
if not result['success']:
    print("  ❌ FAILED - HOME key did not send")
    sys.exit(1)
print("  ✓ HOME key sent successfully")
time.sleep(2)

# Test 2: Send RIGHT key (should move focus right on home screen)
print("\nTest 2: Sending RIGHT key...")
result = send_remote_keys(TEST_DEVICE_IP, "RIGHT", TEST_PORT, TEST_USERNAME, TEST_PASSWORD)
print(f"  Result: {result}")
if not result['success']:
    print("  ❌ FAILED - RIGHT key did not send")
    sys.exit(1)
print("  ✓ RIGHT key sent successfully")
time.sleep(1)

# Test 3: Send DOWN key (should move focus down)
print("\nTest 3: Sending DOWN key...")
result = send_remote_keys(TEST_DEVICE_IP, "DOWN", TEST_PORT, TEST_USERNAME, TEST_PASSWORD)
print(f"  Result: {result}")
if not result['success']:
    print("  ❌ FAILED - DOWN key did not send")
    sys.exit(1)
print("  ✓ DOWN key sent successfully")
time.sleep(1)

# Test 4: Send multiple keys in sequence
print("\nTest 4: Sending multiple keys (RIGHT,RIGHT,DOWN)...")
result = send_remote_keys(TEST_DEVICE_IP, "RIGHT,RIGHT,DOWN", TEST_PORT, TEST_USERNAME, TEST_PASSWORD)
print(f"  Result: {result}")
if not result['success']:
    print("  ❌ FAILED - Multiple keys did not send")
    sys.exit(1)
print("  ✓ Multiple keys sent successfully")
time.sleep(1)

# Test 5: Direct SSH verification - check if keySimulator exists and is executable
print("\nTest 5: Verifying keySimulator command on device...")
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect(TEST_DEVICE_IP, port=TEST_PORT, username=TEST_USERNAME, password=TEST_PASSWORD, timeout=15)
    
    # Check if keySimulator exists
    stdin, stdout, stderr = ssh.exec_command("which keySimulator")
    which_output = stdout.read().decode('utf-8').strip()
    print(f"  keySimulator location: {which_output}")
    
    if not which_output:
        print("  ❌ keySimulator command NOT FOUND on device")
        sys.exit(1)
    
    # Test a simple key press and capture raw output
    stdin, stdout, stderr = ssh.exec_command("keySimulator -kup -r1")
    exit_code = stdout.channel.recv_exit_status()
    stdout_output = stdout.read().decode('utf-8').strip()
    stderr_output = stderr.read().decode('utf-8').strip()
    
    print(f"  Command: keySimulator -kup -r1")
    print(f"  Exit Code: {exit_code}")
    print(f"  STDOUT: {stdout_output if stdout_output else '(empty)'}")
    print(f"  STDERR: {stderr_output if stderr_output else '(empty)'}")
    
    if exit_code == 0:
        print("  ✓ keySimulator is working correctly")
    else:
        print(f"  ❌ keySimulator returned error code {exit_code}")
        sys.exit(1)
    
finally:
    ssh.close()

# Test 6: Send BACK key to return to previous state
print("\nTest 6: Sending BACK key to cleanup...")
result = send_remote_keys(TEST_DEVICE_IP, "BACK", TEST_PORT, TEST_USERNAME, TEST_PASSWORD)
print(f"  Result: {result}")
if not result['success']:
    print("  ⚠ WARNING - BACK key did not send (cleanup failed)")
else:
    print("  ✓ BACK key sent successfully")

print("\n" + "=" * 70)
print("✓ ALL TESTS PASSED")
print("=" * 70)
print("\nConclusion:")
print("  - keySimulator command exists on device")
print("  - SSH connection is working")
print("  - Keys are being sent to the device")
print("  - Command execution returns success codes")
print("\nNote: Visual verification recommended - watch the device screen")
print("      during test execution to confirm UI navigation is working.")
