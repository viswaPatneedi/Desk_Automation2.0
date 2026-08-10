#!/usr/bin/env python3
"""
Simple v4 Tunnel Sharing Test - Tests registration and waiting logic directly
No job creation needed - just tests the tunnel registry and wait mechanism
"""

import sys
import os
import time
import threading
from datetime import datetime

sys.path.insert(0, '/home/guser/Desk-automation/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard')
os.chdir('/home/guser/Desk-automation/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard')

from services.test_execution_service import (
    register_tunnel, 
    get_tunnel, 
    find_companion_tunnel,
    unregister_tunnel,
    _ACTIVE_TUNNELS,
    _TUNNEL_LOCK
)

print("="*80)
print("v4 TUNNEL REGISTRY TEST - Pending Registration Logic")
print("="*80)
print()

# Test 1: Register pending tunnel
print("[Test 1] Register pending tunnel on device 10.0.0.140")
register_tunnel("10.0.0.140", {
    'tunnel_service': None,
    'rpi_ip': '10.138.17.42',
    'status': 'acquiring',
    'job_id': 'job-1'
})
print("  ✅ Registered pending tunnel")

# Test 2: Verify registry contains the pending tunnel
print("\n[Test 2] Check registry has pending tunnel")
tunnel_data = get_tunnel("10.0.0.140")
if tunnel_data:
    print(f"  ✅ Found tunnel data: status={tunnel_data.get('status')}, job_id={tunnel_data.get('job_id')}")
else:
    print(f"  ❌ Tunnel not found in registry!")

# Test 3: Companion device finds pending tunnel
print("\n[Test 3] Companion device (10.0.0.28) looks for tunnel")
companion_tunnel = find_companion_tunnel("10.0.0.28", "10.138.17.42")
if companion_tunnel:
    print(f"  ✅ Companion found tunnel: status={companion_tunnel.get('status')}")
else:
    print(f"  ❌ Companion couldn't find tunnel!")

# Test 4: Test waiting logic - simulate Job 2 waiting for Job 1's tunnel
print("\n[Test 4] Simulate Job 2 waiting for Job 1's tunnel to connect")

def simulate_job_2_wait():
    """Simulate job 2 waiting for companion tunnel"""
    print("  [Job 2] Starting wait for companion tunnel...")
    start = datetime.utcnow()
    
    while (datetime.utcnow() - start).total_seconds() < 10:
        # Check if tunnel is connected
        tunnel = get_tunnel("10.0.0.140")
        if tunnel and tunnel.get('tunnel_service'):
            elapsed = (datetime.utcnow() - start).total_seconds()
            print(f"  ✅ [Job 2] Tunnel connected after {elapsed:.2f}s!")
            return True
        
        # Still acquiring
        if tunnel and tunnel.get('status') == 'acquiring':
            print(f"  ⏳ [Job 2] Still waiting for tunnel connection...")
            time.sleep(1)
        else:
            print(f"  ❌ [Job 2] Tunnel disappeared!")
            return False
    
    print(f"  ⏰ [Job 2] Timeout waiting for tunnel")
    return False

def simulate_job_1_connect():
    """Simulate job 1 connecting its tunnel"""
    print("  [Job 1] Simulating tunnel connection in 3 seconds...")
    time.sleep(3)
    
    # Update tunnel with mock service
    register_tunnel("10.0.0.140", {
        'tunnel_service': object(),  # Mock tunnel service
        'rpi_ip': '10.138.17.42',
        'status': 'connected',
        'job_id': 'job-1'
    })
    print("  ✅ [Job 1] Tunnel connected!")

# Run both simulations in parallel
job1_thread = threading.Thread(target=simulate_job_1_connect)
job2_thread = threading.Thread(target=simulate_job_2_wait)

job1_thread.start()
job2_thread.start()

job1_thread.join()
job2_thread.join()

# Test 5: Verify final state
print("\n[Test 5] Final registry state")
tunnel_data = get_tunnel("10.0.0.140")
if tunnel_data:
    print(f"  ✅ Device 10.0.0.140: status={tunnel_data.get('status')}, has_service={tunnel_data.get('tunnel_service') is not None}")
else:
    print(f"  ❌ Device 10.0.0.140: NOT IN REGISTRY")

# Test 6: Cleanup
print("\n[Test 6] Cleanup")
unregister_tunnel("10.0.0.140")
tunnel_data = get_tunnel("10.0.0.140")
if tunnel_data:
    print(f"  ❌ Tunnel still in registry after cleanup!")
else:
    print(f"  ✅ Tunnel cleaned up successfully")

# Test 7: Show final registry state
print("\n[Test 7] Final global registry state:")
with _TUNNEL_LOCK:
    if _ACTIVE_TUNNELS:
        for device_ip, data in _ACTIVE_TUNNELS.items():
            print(f"  {device_ip}: {data.get('status', 'unknown')}")
    else:
        print(f"  [Empty - all tunnels cleaned up]")

print("\n" + "="*80)
print("✅ v4 TUNNEL REGISTRY TEST COMPLETED")
print("="*80)
