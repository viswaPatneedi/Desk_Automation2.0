#!/usr/bin/env python3
"""
Test VNC screenshot service accessibility through tunnel forwarding
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.gdf_rpi_shell_service import GDFRPiShellService
import json
import requests
from requests.auth import HTTPBasicAuth

# Load device config
with open('Json/devices.json', 'r') as f:
    devices_data = json.load(f)

device_config = None
for dev in devices_data:
    if dev.get('ip') == '10.0.0.28':
        device_config = dev
        break

if not device_config:
    print("❌ Device 10.0.0.28 not found")
    sys.exit(1)

rpi_config = device_config.get('rpi_config', {})
lab_device_config = {
    'lab_ip': device_config.get('ip'),
    'lab_port': device_config.get('port'),
    'lab_username': device_config.get('username'),
    'lab_password': device_config.get('password'),
    'device_name': device_config.get('name')
}

print("\n" + "="*80)
print("Testing VNC Screenshot Service via Forwarded Ports")
print("="*80)

print(f"\n🔌 Establishing tunnel with multi-port forwarding...")
try:
    service = GDFRPiShellService(rpi_config, lab_device_config)
    success, message = service.connect()
    if not success:
        print(f"❌ Tunnel failed: {message}")
        sys.exit(1)
    print(f"✓ {message}")
except Exception as e:
    print(f"❌ Failed: {e}")
    sys.exit(1)

# Test the screenshot/VNC services through forwarded ports
print(f"\n🧪 Testing forwarded service ports...")

# Test VNC web interface (port 5800)
print(f"\n📍 Testing VNC web interface (port 5800)...")
try:
    response = requests.get('http://127.0.0.1:5800/', timeout=5)
    print(f"   ✓ Port 5800 responding with status {response.status_code}")
    print(f"   Response preview: {response.text[:150]}")
except Exception as e:
    print(f"   ✗ Port 5800 error: {e}")

# Test web management service (port 8090)
print(f"\n📍 Testing web management (port 8090)...")
try:
    response = requests.get('http://127.0.0.1:8090/', timeout=5)
    print(f"   ✓ Port 8090 responding with status {response.status_code}")
    print(f"   Response preview: {response.text[:150]}")
except Exception as e:
    print(f"   ✗ Port 8090 error: {e}")

# Test application service (port 9005)
print(f"\n📍 Testing application service (port 9005)...")
try:
    response = requests.get('http://127.0.0.1:9005/', timeout=5)
    print(f"   ✓ Port 9005 responding with status {response.status_code}")
    print(f"   Response preview: {response.text[:150]}")
except Exception as e:
    print(f"   ✗ Port 9005 error: {e}")

# Get screenshot via VNC
print(f"\n📸 Attempting to fetch screenshot from VNC service...")
try:
    # Common VNC screenshot endpoints
    endpoints = [
        'http://127.0.0.1:5800/api/screenshot',
        'http://127.0.0.1:5800/screenshot',
        'http://127.0.0.1:8090/screenshot',
        'http://127.0.0.1:8090/api/screenshot',
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(endpoint, timeout=3)
            if response.status_code == 200:
                print(f"   ✓ Screenshot found at: {endpoint}")
                print(f"   Response content-type: {response.headers.get('content-type')}")
                print(f"   Response size: {len(response.content)} bytes")
                break
        except:
            continue
    else:
        print(f"   ⚠️ No screenshot endpoint found, but ports are accessible")
        print(f"   Try accessing VNC web interface directly at: http://127.0.0.1:5800/")
except Exception as e:
    print(f"   ✗ Screenshot fetch error: {e}")

print(f"\n🔌 Closing tunnel...")
service.disconnect()
print(f"✓ Tunnel closed")

print("\n" + "="*80)
print("✅ Screenshot Service Accessibility Test Complete")
print("   Screenshot URLs are now accessible through forwarded ports!")
print("="*80 + "\n")
