#!/usr/bin/env python3
"""
Utility to manually cancel and kill stuck background jobs on devices
"""

import json
import sys
import argparse
from services.job_cancellation_service import JobCancellationService
from models.job import Job
from models.device import Device

def kill_job_on_device(job_id: str):
    """Kill a specific job by terminating its process on the device"""
    
    print(f"\n{'='*60}")
    print(f"Killing Job: {job_id}")
    print('='*60)
    
    # Get job details
    job = Job.get_job(job_id)
    if not job:
        print(f"❌ Job not found: {job_id}")
        return False
    
    print(f"📋 Job Details:")
    print(f"   Device: {job.device_name} ({job.device_ip})")
    print(f"   Status: {job.status}")
    print(f"   Iterations: {job.iterations}")
    print(f"   Current Iteration: {job.current_iteration}")
    
    # Get device details
    devices = Device.load_all()
    device = None
    for d in devices:
        if d.ip == job.device_ip:
            device = d
            break
    
    if not device:
        print(f"❌ Device not found: {job.device_ip}")
        return False
    
    # Kill the process on device
    success, message = JobCancellationService.kill_job_process_on_device(
        device_ip=job.device_ip,
        device_name=job.device_name,
        username=device.username,
        password=device.password,
        port=device.port or 10022,
        use_jump_host=device.use_jump_host,
        jump_host_config=device.jump_host_config
    )
    
    if success:
        print(f"\n✅ SUCCESS: {message}")
        
        # Also cancel the job in the database
        Job.cancel_job(job_id)
        print(f"✓ Job marked as cancelled in database")
        
        return True
    else:
        print(f"\n❌ FAILED: {message}")
        return False

def list_running_jobs():
    """List all running jobs"""
    jobs = Job.get_running_jobs()
    
    print(f"\n{'='*60}")
    print(f"Running Jobs: {len(jobs)}")
    print('='*60)
    
    if not jobs:
        print("No running jobs")
        return
    
    for job in jobs:
        print(f"\n📌 Job ID: {job.job_id}")
        print(f"   Device: {job.device_name} ({job.device_ip})")
        print(f"   Status: {job.status}")
        print(f"   Iteration: {job.current_iteration}/{job.iterations}")

def main():
    parser = argparse.ArgumentParser(description='Kill stuck background jobs')
    parser.add_argument('--job-id', help='Job ID to kill')
    parser.add_argument('--list', action='store_true', help='List running jobs')
    
    args = parser.parse_args()
    
    if args.list:
        list_running_jobs()
    elif args.job_id:
        success = kill_job_on_device(args.job_id)
        sys.exit(0 if success else 1)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == '__main__':
    main()
