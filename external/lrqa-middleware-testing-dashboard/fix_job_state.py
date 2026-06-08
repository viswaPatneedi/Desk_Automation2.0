#!/usr/bin/env python3
"""
Fix job state issues - handle stuck running jobs and queue sync
"""

import json
import os
from datetime import datetime
import sys

JOBS_FILE = 'jobs.json'
QUEUE_FILE = 'device_job_queue.json'

def load_json(filepath):
    """Load JSON file safely"""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading {filepath}: {e}")
        return None

def save_json(filepath, data):
    """Save JSON file with backup"""
    try:
        # Create backup
        if os.path.exists(filepath):
            backup_path = f"{filepath}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            with open(filepath, 'r') as f:
                backup_data = f.read()
            with open(backup_path, 'w') as f:
                f.write(backup_data)
            print(f"✓ Backup created: {backup_path}")
        
        # Save new data
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"✓ Updated {filepath}")
        return True
    except Exception as e:
        print(f"❌ Error saving {filepath}: {e}")
        return False

def fix_stuck_running_jobs():
    """Fix jobs stuck in 'running' state with no end_time"""
    print("\n📋 Checking for stuck 'running' jobs...")
    
    jobs = load_json(JOBS_FILE)
    if not jobs:
        return False
    
    fixed_count = 0
    current_time = datetime.utcnow().isoformat()
    
    for job in jobs:
        if job.get('status') == 'running' and job.get('end_time') is None:
            print(f"\n⚠️  Found stuck job: {job['job_id']}")
            print(f"   Device: {job.get('device_name')}")
            print(f"   Start time: {job.get('start_time')}")
            print(f"   Current iteration: {job.get('current_iteration')}/{job.get('iterations')}")
            
            # Check if process has been running for too long (>6 hours)
            try:
                from datetime import timedelta
                start = datetime.fromisoformat(job['start_time'].replace('+00:00', ''))
                elapsed = datetime.utcnow() - start
                
                if elapsed > timedelta(hours=6):
                    print(f"   ⏱️  Has been running for {elapsed.total_seconds()/3600:.1f} hours")
                    
                    # Mark as failed and set end_time
                    job['status'] = 'failed'
                    job['end_time'] = current_time
                    print(f"   ✓ Marked as FAILED with end time")
                    fixed_count += 1
                else:
                    print(f"   ℹ️  Still within reasonable time ({elapsed.total_seconds()/3600:.1f}h) - skipping")
            except Exception as e:
                print(f"   ⚠️  Error checking time: {e}")
    
    if fixed_count > 0:
        print(f"\n✓ Fixed {fixed_count} stuck jobs")
        return save_json(JOBS_FILE, jobs)
    else:
        print("ℹ️  No stuck jobs found or all within reasonable runtime")
        return True

def remove_cancelled_from_queue():
    """Remove cancelled jobs from device queue"""
    print("\n📋 Checking for cancelled jobs in queue...")
    
    jobs = load_json(JOBS_FILE)
    queue = load_json(QUEUE_FILE)
    
    if not jobs or not queue:
        return False
    
    # Get all cancelled job IDs
    cancelled_ids = {job['job_id'] for job in jobs if job.get('status') == 'cancelled'}
    
    if not cancelled_ids:
        print("ℹ️  No cancelled jobs found")
        return True
    
    print(f"Found {len(cancelled_ids)} cancelled jobs")
    
    removed_count = 0
    for device_ip, queue_jobs in queue.items():
        original_len = len(queue_jobs)
        queue_jobs_filtered = [j for j in queue_jobs if j['job_id'] not in cancelled_ids]
        
        if len(queue_jobs_filtered) < original_len:
            removed = original_len - len(queue_jobs_filtered)
            print(f"✓ Removed {removed} cancelled job(s) from queue for {device_ip}")
            queue[device_ip] = queue_jobs_filtered
            removed_count += removed
    
    if removed_count > 0:
        print(f"\n✓ Removed {removed_count} cancelled job(s) from queue")
        return save_json(QUEUE_FILE, queue)
    else:
        print("ℹ️  No cancelled jobs in queue")
        return True

def sync_pending_jobs():
    """Sync pending jobs from queue to jobs.json if missing"""
    print("\n📋 Checking for pending jobs to sync...")
    
    jobs = load_json(JOBS_FILE)
    queue = load_json(QUEUE_FILE)
    
    if not jobs or not queue:
        return False
    
    job_ids = {job['job_id'] for job in jobs}
    synced_count = 0
    
    for device_ip, queue_jobs in queue.items():
        for q_job in queue_jobs:
            if q_job['job_id'] not in job_ids:
                print(f"\n⚠️  Found unsync'd pending job: {q_job['job_id']}")
                print(f"   Device: {q_job.get('device_name')}")
                print(f"   Method: {q_job.get('methods')}")
                print(f"   Iterations: {q_job.get('iterations')}")
                print(f"   ✓ Adding to jobs.json")
                
                jobs.append(q_job)
                synced_count += 1
    
    if synced_count > 0:
        print(f"\n✓ Synced {synced_count} pending job(s)")
        return save_json(JOBS_FILE, jobs)
    else:
        print("ℹ️  All queue jobs are synced")
        return True

def main():
    """Run all fixes"""
    print("=" * 60)
    print("🔧 JOB STATE RECOVERY TOOL")
    print("=" * 60)
    
    try:
        # Step 1: Fix stuck running jobs
        if not fix_stuck_running_jobs():
            print("❌ Failed to fix stuck jobs")
            return 1
        
        # Step 2: Remove cancelled jobs from queue
        if not remove_cancelled_from_queue():
            print("❌ Failed to remove cancelled jobs")
            return 1
        
        # Step 3: Sync pending jobs
        if not sync_pending_jobs():
            print("❌ Failed to sync pending jobs")
            return 1
        
        print("\n" + "=" * 60)
        print("✅ JOB STATE RECOVERY COMPLETED")
        print("=" * 60)
        print("\n🔄 Please restart the application to load the fixed state:")
        print("   python app.py")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
