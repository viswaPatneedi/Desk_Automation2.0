#!/usr/bin/env python3
"""
Fix Stuck Jobs Utility
Analyzes log files and corrects job statuses that weren't updated properly
"""

import json
import os
from datetime import datetime, timezone, timedelta

def fix_stuck_jobs():
    """Fix jobs that are stuck in running/pending state despite being completed."""
    
    jobs_file = 'jobs.json'
    
    if not os.path.exists(jobs_file):
        print("❌ jobs.json not found")
        return
    
    try:
        with open(jobs_file, 'r') as f:
            jobs = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Error reading jobs.json: {e}")
        return
    
    print("="*60)
    print("JOB STATUS RECOVERY UTILITY")
    print("="*60)
    print(f"\nTotal jobs: {len(jobs)}")
    
    # Find stuck jobs
    stuck_jobs = [j for j in jobs if j['status'] in ['running', 'pending']]
    
    if not stuck_jobs:
        print("\n✅ No stuck jobs found - all jobs have correct status")
        return
    
    print(f"\n⚠️  Found {len(stuck_jobs)} potentially stuck jobs\n")
    
    fixed_count = 0
    abandoned_count = 0
    
    for job in jobs:
        if job['status'] not in ['running', 'pending']:
            continue
        
        job_id = job['job_id']
        device_name = job['device_name']
        log_file = job.get('log_file_path')
        start_time_str = job.get('start_time')
        
        # Check if job started more than 30 minutes ago
        is_old = False
        if start_time_str:
            try:
                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                age_minutes = (datetime.now(timezone.utc) - start_time).total_seconds() / 60
                is_old = age_minutes > 30
            except:
                pass
        
        # Analyze log file
        if log_file and os.path.exists(log_file):
            try:
                with open(log_file, 'r') as lf:
                    log_content = lf.read()
                
                if 'completed successfully' in log_content:
                    print(f"✅ Job {job_id} ({device_name})")
                    print(f"   Status: {job['status']} -> completed")
                    print(f"   Reason: Log shows successful completion")
                    job['status'] = 'completed'
                    if not job.get('end_time'):
                        job['end_time'] = datetime.now(timezone.utc).isoformat()
                    fixed_count += 1
                    
                elif 'Job.*failed' in log_content or '❌ Error' in log_content:
                    print(f"❌ Job {job_id} ({device_name})")
                    print(f"   Status: {job['status']} -> failed")
                    print(f"   Reason: Log shows errors/failure")
                    job['status'] = 'failed'
                    if not job.get('end_time'):
                        job['end_time'] = datetime.now(timezone.utc).isoformat()
                    fixed_count += 1
                    
                elif is_old:
                    print(f"⏱️  Job {job_id} ({device_name})")
                    print(f"   Status: {job['status']} -> failed (timeout)")
                    print(f"   Reason: Running >30min without completion marker")
                    job['status'] = 'failed'
                    if not job.get('end_time'):
                        job['end_time'] = datetime.now(timezone.utc).isoformat()
                    abandoned_count += 1
                    
            except Exception as e:
                print(f"⚠️  Error reading log {log_file}: {e}")
        
        elif job['status'] == 'pending' and is_old:
            print(f"🗑️  Job {job_id} ({device_name})")
            print(f"   Status: pending -> cancelled")
            print(f"   Reason: Pending >30min without starting")
            job['status'] = 'cancelled'
            abandoned_count += 1
    
    # Save if any changes
    if fixed_count > 0 or abandoned_count > 0:
        # Backup before saving
        backup_file = f'{jobs_file}.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        with open(backup_file, 'w') as f:
            json.dump(jobs, f, indent=2)
        print(f"\n💾 Created backup: {backup_file}")
        
        # Save fixed jobs
        with open(jobs_file, 'w') as f:
            json.dump(jobs, f, indent=2)
        
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        print(f"✅ Fixed (from logs): {fixed_count}")
        print(f"⏱️  Timeout/abandoned: {abandoned_count}")
        print(f"📊 Total corrected: {fixed_count + abandoned_count}")
        
        # Show updated status distribution
        statuses = {}
        for job in jobs:
            status = job.get('status', 'unknown')
            statuses[status] = statuses.get(status, 0) + 1
        
        print("\nUpdated job status distribution:")
        for status, count in sorted(statuses.items()):
            print(f"  {status}: {count}")
        
        print("\n✅ Job statuses have been corrected")
    else:
        print("\n✅ All jobs already have correct status")
    
    print("="*60)

if __name__ == '__main__':
    fix_stuck_jobs()
