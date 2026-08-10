#!/usr/bin/env python3
"""
Direct test of GDFRPiShellService with port forwarding
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.gdf_rpi_shell_service import GDFRPiShellService
import json

# Load device config
with open('Json/devices.json', 'r') as f:
    devices_data = json.load(f)

# Find device 10.0.0.28
device_config = None
for dev in devices_data:
    if dev.get('ip') == '10.0.0.28':
        device_config = dev
        break

if not device_config:
    print("❌ Device 10.0.0.28 not found in configuration")
    sys.exit(1)

print("\n" + "="*80)
print("TESTING GDF R-Pi Port Forwarding Service")
print("="*80)

print(f"\n📋 Device Configuration:")
print(f"   Device IP: {device_config.get('ip')}")
print(f"   Device Name: {device_config.get('name')}")
print(f"   Device Port: {device_config.get('port')}")
print(f"   Device Username: {device_config.get('username')}")

rpi_config = device_config.get('rpi_config', {})
print(f"\n📋 R-Pi Configuration:")
print(f"   R-Pi IP: {rpi_config.get('rpi_ip')}")
print(f"   R-Pi Port: {rpi_config.get('rpi_port')}")
print(f"   R-Pi Username: {rpi_config.get('rpi_username')}")

# Create service instance
lab_device_config = {
    'lab_ip': device_config.get('ip'),
    'lab_port': device_config.get('port'),
    'lab_username': device_config.get('username'),
    'lab_password': device_config.get('password'),
    'device_name': device_config.get('name')
}

print(f"\n🚀 Initializing GDFRPiShellService...")
try:
    service = GDFRPiShellService(rpi_config, lab_device_config)
    print(f"   ✓ Service initialized")
except Exception as e:
    print(f"   ❌ Failed to initialize: {e}")
    sys.exit(1)

# Step 1: Connect
print(f"\n🔌 Step 1: Establishing tunnel...")
success, message = service.connect()
if success:
    print(f"   ✓ {message}")
else:
    print(f"   ❌ {message}")
    sys.exit(1)

# Step 2: Simple test command (echo)
print(f"\n🧪 Step 2: Testing with simple 'echo' command...")
success, stdout, stderr = service.execute_command("echo 'Tunnel Test OK'", timeout=10)
if success:
    print(f"   ✓ Command executed")
    print(f"   Output: {stdout}")
else:
    print(f"   ⚠️  Command execution issue")
    print(f"   Stdout: {stdout}")
    print(f"   Stderr: {stderr}")

# Step 3: Build details test
print(f"\n🧪 Step 3: Testing build details fetch (cat /version.txt)...")
success, stdout, stderr = service.execute_command("cat /version.txt", timeout=10)
if success:
    print(f"   ✓ Build details retrieved")
    print(f"   Version: {stdout}")
else:
    print(f"   ⚠️  Build details fetch issue")
    print(f"   Stdout: {stdout}")
    print(f"   Stderr: {stderr[:200] if stderr else '(empty)'}")

# Step 4: Disconnect
print(f"\n🔌 Step 4: Closing tunnel...")
service.disconnect()
print(f"   ✓ Tunnel closed")

print("\n" + "="*80)
print("✅ TEST COMPLETE")
print("="*80 + "\n")
