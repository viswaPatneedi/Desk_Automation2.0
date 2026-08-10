#!/usr/bin/env python3
"""
Test v4 parallel execution fix
Execute both devices in quick succession and monitor for tunnel sharing
"""

import requests
import json
import time
from datetime import datetime
import sys

BASE_URL = "http://localhost:11079"

# Device IPs we want to test
DEVICES = [
    "10.0.0.140",  # DT_LAB_SKY_XIONE-UK-0D_AB
    "10.0.0.28",   # DT_LAB_XIONE-UK-17-97
]

def execute_test(device_ip):
    """Execute test on a device"""
    url = f"{BASE_URL}/api/execute"
    payload = {
        "device_ip": device_ip,
        "test_name": "basic_sanity",
        "timeout": 300  # 5 minutes timeout
    }
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📤 Sending test request for device {device_ip}...")
    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        data = response.json()
        job_id = data.get('job_id')
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Job created: {job_id}")
        return job_id
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Failed to execute test: {e}")
        return None

def get_job_status(job_id):
    """Get status of a job"""
    url = f"{BASE_URL}/api/job-status/{job_id}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        return data.get('status'), data.get('error')
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Failed to get job status: {e}")
        return None, None

def monitor_jobs(job_ids, max_wait=180):
    """Monitor job execution until completion or timeout"""
    start_time = datetime.utcnow()
    previous_statuses = {jid: None for jid in job_ids}
    
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🔍 Monitoring jobs...")
    print(f"Job IDs: {job_ids}\n")
    
    while (datetime.utcnow() - start_time).total_seconds() < max_wait:
        all_done = True
        
        for job_id in job_ids:
            status, error = get_job_status(job_id)
            
            # Print status changes
            if status != previous_statuses[job_id]:
                previous_statuses[job_id] = status
                status_line = f"[{datetime.now().strftime('%H:%M:%S')}] Job {job_id[:8]}... Status: {status}"
                if error:
                    status_line += f" | Error: {error}"
                print(status_line)
            
            if status not in ['completed', 'failed', 'error']:
                all_done = False
        
        if all_done:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ✅ All jobs completed!")
            break
        
        time.sleep(2)
    
    # Final status check
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 📊 Final job statuses:")
    for job_id in job_ids:
        status, error = get_job_status(job_id)
        result_line = f"  {job_id[:8]}... : {status}"
        if error:
            result_line += f" (Error: {error})"
        print(result_line)

def check_tunnel_logs(job_id):
    """Check tunnel-related logs for a job"""
    import os
    log_file = f"/home/guser/Desk-automation/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard/logs/jobs/{job_id}/execution.log"
    
    if not os.path.exists(log_file):
        return []
    
    tunnel_keywords = ['TUNNEL', 'tunnel', 'REGISTRY', 'registry', 'SHARED', 'shared', 'PENDING', 'acquiring']
    tunnel_logs = []
    
    try:
        with open(log_file) as f:
            for line in f:
                if any(kw in line for kw in tunnel_keywords):
                    tunnel_logs.append(line.strip())
    except:
        pass
    
    return tunnel_logs

def main():
    print("=" * 70)
    print("PARALLEL EXECUTION TEST v4 - Pending Tunnel Registration")
    print("=" * 70)
    print(f"\nTest will trigger both devices in quick succession.")
    print(f"Expected: Both devices execute in parallel, sharing tunnel\n")
    
    # Clear any old console output
    time.sleep(1)
    
    # Execute both devices in quick succession
    job_ids = []
    for device_ip in DEVICES:
        job_id = execute_test(device_ip)
        if job_id:
            job_ids.append(job_id)
        time.sleep(1)  # 1 second between requests (vs 16 seconds between initiation before)
    
    if not job_ids:
        print("❌ Failed to create any jobs")
        return
    
    # Monitor execution
    monitor_jobs(job_ids)
    
    # Check tunnel logs
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 📋 Tunnel-related logs:")
    for job_id in job_ids:
        print(f"\n  Job {job_id[:8]}...:")
        tunnel_logs = check_tunnel_logs(job_id)
        if tunnel_logs:
            for log_line in tunnel_logs[:10]:  # First 10 relevant lines
                print(f"    {log_line}")
        else:
            print("    (No tunnel-related logs found)")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️ Test interrupted by user")
        sys.exit(0)
