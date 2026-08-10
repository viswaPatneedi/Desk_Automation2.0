#!/usr/bin/env python3
"""
Direct test of v4 tunnel sharing - calls Python methods directly without HTTP API
"""

import sys
import os
import time
import threading
from datetime import datetime

# Add project to path
sys.path.insert(0, '/home/guser/Desk-automation/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard')

os.chdir('/home/guser/Desk-automation/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard')

from models.device import Device
from models.job import Job
from services.test_execution_service import TestExecutionService, register_tunnel, get_tunnel, find_companion_tunnel
from services.log_service import LogService
import uuid

print("="*80)
print("DIRECT TUNNEL SHARING TEST v4 - Pending Registration")
print("="*80)
print()

# Device IPs to test
DEVICE_IPS = ["10.0.0.140", "10.0.0.28"]

def execute_device_in_thread(device_ip, job_index):
    """Execute test for a device in a background thread"""
    print(f"\n[Thread-{job_index}] 🚀 Starting execution for device {device_ip}")
    
    try:
        # Create job  
        job = Job.create_job(
            user_id='test_user',
            device_ip=device_ip,
            device_name=f"Test Device {job_index}",
            methods=['basic_sanity'],
            iterations=1
        )
        job_id = job.job_id
        print(f"[Thread-{job_index}] ✅ Job created: {job_id}")
        
        # Initialize execution service
        log_service = LogService(job_id)
        test_service = TestExecutionService()
        test_service.current_job_id = job_id  # Store job ID for tunnel registration
        
        # Load device
        device = Device.load_by_ip(device_ip)
        if not device:
            print(f"[Thread-{job_index}] ❌ Device not found: {device_ip}")
            return False
        
        print(f"[Thread-{job_index}] 📱 Device loaded: {device.name}")
        
        # Attempt tunnel establishment
        print(f"[Thread-{job_index}] 🔧 Attempting tunnel establishment...")
        success, msg, tunnel_service = test_service.establish_tunnel_for_device(device, log_service)
        
        if success:
            print(f"[Thread-{job_index}] ✅ TUNNEL SUCCESS: {msg}")
            job.update_status('running')
            time.sleep(5)  # Simulate work
            job.update_status('completed')
            print(f"[Thread-{job_index}] ✅ Job completed successfully")
            return True
        else:
            print(f"[Thread-{job_index}] ❌ TUNNEL FAILED: {msg}")
            job.update_status('failed', error=msg)
            print(f"[Thread-{job_index}] ❌ Job failed")
            return False
            
    except Exception as e:
        print(f"[Thread-{job_index}] ❌ EXCEPTION: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def check_tunnel_registry():
    """Check current state of global tunnel registry"""
    print(f"\n[Monitor] 📊 Checking global tunnel registry...")
    tunnel_data = get_tunnel("10.0.0.140")
    if tunnel_data:
        status = tunnel_data.get('status', 'unknown')
        has_service = tunnel_data.get('tunnel_service') is not None
        print(f"  Device 10.0.0.140: status={status}, has_tunnel_service={has_service}")
    else:
        print(f"  Device 10.0.0.140: NOT IN REGISTRY")
    
    tunnel_data = get_tunnel("10.0.0.28")
    if tunnel_data:
        status = tunnel_data.get('status', 'unknown')
        has_service = tunnel_data.get('tunnel_service') is not None
        print(f"  Device 10.0.0.28: status={status}, has_tunnel_service={has_service}")
    else:
        print(f"  Device 10.0.0.28: NOT IN REGISTRY")

def main():
    print(f"Test: Trigger both devices in parallel\n")
    print(f"Expected behavior:")
    print(f"  1. Device 1 (10.0.0.140) starts tunnel acquisition FIRST")
    print(f"  2. Device 1 registers 'acquiring' status in global registry")
    print(f"  3. Device 2 (10.0.0.28) starts shortly after")
    print(f"  4. Device 2 detects Device 1's 'acquiring' tunnel in registry")
    print(f"  5. Device 2 WAITS for tunnel to complete instead of competing")
    print(f"  6. Both devices execute WITHOUT 60s timeout\n")
    
    check_tunnel_registry()
    
    # Start both devices in threads with slight delay
    threads = []
    start_time = datetime.utcnow()
    
    for i, device_ip in enumerate(DEVICE_IPS):
        delay = i * 1  # 1 second between thread starts
        thread = threading.Thread(
            target=lambda ip=device_ip, idx=i: (
                time.sleep(delay),
                execute_device_in_thread(ip, idx + 1)
            ),
            daemon=False
        )
        threads.append(thread)
        thread.start()
    
    print(f"\n[Main] ⏳ Waiting for all threads to complete...")
    for thread in threads:
        thread.join(timeout=180)  # Wait up to 3 minutes
    
    elapsed = (datetime.utcnow() - start_time).total_seconds()
    print(f"\n[Main] ✅ Test completed in {elapsed:.1f} seconds")
    
    # Print final registry state
    check_tunnel_registry()
    
    # Check job statuses
    print(f"\n[Main] 📋 Final job statuses:")
    all_jobs = Job.load_all()
    for device_ip in DEVICE_IPS:
        device_jobs = [j for j in all_jobs if j.device_ip == device_ip]
        if device_jobs:
            latest_job = sorted(device_jobs, key=lambda j: j.created_at or '', reverse=True)[0]
            print(f"  Device {device_ip}: {latest_job.status}")
        else:
            print(f"  Device {device_ip}: NO JOBS")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
