#!/usr/bin/env python3
"""
Test screenshot capture from device via R-Pi tunnel
Captures screenshot, saves locally, and verifies
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.gdf_rpi_shell_service import GDFRPiShellService
from services.screenshot_capture_service import ScreenshotCaptureService
import json
import time

# Load device config
with open('Json/devices.json', 'r') as f:
    devices_data = json.load(f)

device_config = None
for dev in devices_data:
    if dev.get('ip') == '10.0.0.28':
        device_config = dev
        break

if not device_config:
    print("[ERROR] Device 10.0.0.28 not found")
    sys.exit(1)

print("\n" + "="*80)
print("Testing Screenshot Capture via R-Pi Tunnel")
print("="*80)

device_ip = device_config.get('ip')
device_name = device_config.get('name')
rpi_config = device_config.get('rpi_config', {})

print(f"\n[INFO] Device: {device_name} ({device_ip})")
print(f"[INFO] R-Pi: {rpi_config.get('rpi_ip')}:{rpi_config.get('rpi_port')}")

# Step 1: Establish tunnel
print(f"\n[STEP 1] Establishing tunnel with port forwarding...")
lab_device_config = {
    'lab_ip': device_ip,
    'lab_port': device_config.get('port'),
    'lab_username': device_config.get('username'),
    'lab_password': device_config.get('password'),
    'device_name': device_name
}

try:
    ssh_service = GDFRPiShellService(rpi_config, lab_device_config)
    success, message = ssh_service.connect()
    if not success:
        print(f"[ERROR] Tunnel failed: {message}")
        sys.exit(1)
    print(f"[OK] {message}")
except Exception as e:
    print(f"[ERROR] Initialization failed: {e}")
    sys.exit(1)

# Wait for tunnel to fully stabilize
time.sleep(2)

# Step 2: Capture screenshot
print(f"\n[STEP 2] Capturing screenshot from device...")
print(f"[INFO] Device URL: http://{device_ip}:5800/screenshot.png")
print(f"[INFO] Tunnel access: http://127.0.0.1:5800/screenshot.png")

screenshot_service = ScreenshotCaptureService(os.getcwd())

result = screenshot_service.capture_screenshot(
    device_ip=device_ip,
    screenshot_port=5800,
    timeout=15
)

if not result['success']:
    print(f"[ERROR] Screenshot capture failed: {result.get('error')}")
    ssh_service.disconnect()
    sys.exit(1)

screenshot_path = result['screenshot_path']
print(f"[OK] Screenshot captured: {result['filename']}")
print(f"[INFO] Size: {result['size_bytes']} bytes")
print(f"[INFO] Path: {screenshot_path}")

# Step 3: Verify screenshot
print(f"\n[STEP 3] Verifying screenshot file...")
verification = screenshot_service.verify_screenshot(screenshot_path)

if verification['valid']:
    print(f"[OK] Screenshot is a valid PNG file")
    print(f"[OK] File size: {verification['size']} bytes")
    print(f"[OK] Format: {verification['format']}")
else:
    print(f"[ERROR] Screenshot verification failed: {verification.get('error')}")
    print(f"[ERROR] Details: {verification}")

# Step 4: List all screenshots
print(f"\n[STEP 4] Screenshot storage...")
screenshots = screenshot_service.list_screenshots(device_ip)
print(f"[INFO] Screenshots directory: {screenshot_service.get_screenshots_dir()}")
print(f"[INFO] Total screenshots for {device_ip}: {len(screenshots)}")
if screenshots:
    print(f"[INFO] Latest screenshots:")
    for ss in screenshots[:3]:
        print(f"        {ss['filename']} ({ss['size']} bytes)")

# Step 5: Cleanup
print(f"\n[STEP 5] Closing tunnel...")
ssh_service.disconnect()
print(f"[OK] Tunnel closed")

print("\n" + "="*80)
if verification.get('valid'):
    print("[SUCCESS] Screenshot captured and verified!")
    print(f"[INFO] Screenshot saved to: {screenshot_path}")
else:
    print("[WARNING] Screenshot captured but verification inconclusive")
print("="*80 + "\n")
