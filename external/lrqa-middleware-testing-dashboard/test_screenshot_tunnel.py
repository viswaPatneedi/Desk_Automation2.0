#!/usr/bin/env python3
"""
Test screenshot accessibility through R-Pi tunnel port forwarding
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.gdf_rpi_shell_service import GDFRPiShellService
import json
import requests
import time

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
print("TESTING Screenshot Service via R-Pi Tunnel")
print("="*80)

print(f"\n📋 Device Configuration:")
print(f"   Device IP: {device_config.get('ip')}")
print(f"   Device Name: {device_config.get('name')}")

rpi_config = device_config.get('rpi_config', {})

# Create service instance
lab_device_config = {
    'lab_ip': device_config.get('ip'),
    'lab_port': device_config.get('port'),
    'lab_username': device_config.get('username'),
    'lab_password': device_config.get('password'),
    'device_name': device_config.get('name')
}

print(f"\n🔌 Establishing tunnel...")
try:
    service = GDFRPiShellService(rpi_config, lab_device_config)
    success, message = service.connect()
    if not success:
        print(f"❌ Tunnel failed: {message}")
        sys.exit(1)
    print(f"✓ {message}")
except Exception as e:
    print(f"❌ Failed to initialize: {e}")
    sys.exit(1)

# Test various screenshot endpoints
screenshot_ports = [8090, 8023, 9005, 5800]
screenshot_endpoints = [
    '/screenshot',
    '/api/screenshot',
    '/api/capture',
    '/screenshot.png',
    '/'
]

print(f"\n🧪 Scanning for screenshot service on forwarded ports...")
print(f"   Accessible via: 127.0.0.1:10022 (tunnel)")
print(f"   Forwarded ports: 8090, 8023, 9005, 5800\n")

found_service = False

for port in screenshot_ports:
    print(f"\n📍 Checking port 127.0.0.1:{port}...")
    
    # First try a simple connection test via SSH
    success, stdout, stderr = service.execute_command(f"curl -s -m 2 http://127.0.0.1:{port}/ 2>&1 | head -20", timeout=10)
    
    if success and stdout:
        print(f"   ✓ Port {port} responding")
        print(f"   Response preview: {stdout[:100]}")
        found_service = True
    else:
        # Try netstat to see if port is listening
        success2, stdout2, stderr2 = service.execute_command(f"netstat -tuln 2>/dev/null | grep :{port}", timeout=5)
        if success2 and stdout2:
            print(f"   ✓ Port {port} is listening locally on device")
            print(f"   Local binding: {stdout2.strip()}")
        else:
            print(f"   - Port {port} not responding or not listening")

# Test VNC service (typically on 5800)
print(f"\n📍 Testing VNC service (port 5800)...")
success, stdout, stderr = service.execute_command("ps aux | grep -i vnc | grep -v grep", timeout=5)
if success and stdout:
    print(f"   ✓ VNC process found:")
    print(f"   {stdout}")
else:
    print(f"   - No VNC process found")

# Try to get screenshot info via SSH
print(f"\n📍 Checking for screenshot utilities on device...")
success, stdout, stderr = service.execute_command("ls -la /usr/bin/*screenshot* /usr/bin/*vnc* 2>/dev/null | head -10", timeout=5)
if success and stdout:
    print(f"   ✓ Screenshot/VNC tools found:")
    print(f"   {stdout}")
else:
    print(f"   - No screenshot utilities found in /usr/bin/")

# Disconnect
print(f"\n🔌 Closing tunnel...")
service.disconnect()
print(f"✓ Tunnel closed")

print("\n" + "="*80)
print("✅ Screenshot Service Test Complete")
if found_service:
    print("   Screenshot service IS accessible through tunnel!")
else:
    print("   Screenshot service requires further investigation")
print("="*80 + "\n")
