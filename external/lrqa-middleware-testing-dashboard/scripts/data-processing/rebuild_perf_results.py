#!/usr/bin/env python3
"""
Rebuild test results from execution log, extracting performance_seconds data
"""

import json
import re
from datetime import datetime, timezone

def extract_performance_data(log_file_path):
    """Extract reboot performance data from execution log"""
    performance_data = {}
    
    try:
        with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            log_content = f.read()
    except Exception as e:
        print(f"Error reading log: {e}")
        return performance_data
    
    # Pattern to find iteration blocks and performance times
    # Look for "Calculated Reboot Duration: X.XX seconds"
    iteration_pattern = r'\[(\d+)/(\d+)\]'  # ITERATION X/Y
    duration_pattern = r'✓ Calculated Reboot Duration: ([\d.]+) seconds'
    
    current_iteration = None
    
    for line in log_content.split('\n'):
        # Find iteration markers
        iter_match = re.search(r'ITERATION\s+(\d+)/\d+', line)
        if iter_match:
            current_iteration = int(iter_match.group(1))
            print(f"Found iteration: {current_iteration}")
        
        # Find duration values
        duration_match = re.search(duration_pattern, line)
        if duration_match and current_iteration is not None:
            duration = float(duration_match.group(1))
            performance_data[current_iteration] = duration
            print(f"  Duration for iteration {current_iteration}: {duration}s")
    
    return performance_data

def rebuild_results(job_id, results_file='test_results_history.json', log_dir='logs/jobs'):
    """Rebuild results with performance_seconds data"""
    log_path = f"{log_dir}/{job_id}/execution.log"
    print(f"Reading log from: {log_path}")
    
    # Extract performance data
    performance_data = extract_performance_data(log_path)
    print(f"Extracted {len(performance_data)} performance records")
    
    if not performance_data:
        print("No performance data found in log")
        return False
    
    # Load existing results
    try:
        with open(results_file, 'r') as f:
            all_results = json.load(f)
    except Exception as e:
        print(f"Error reading results file: {e}")
        return False
    
    # Update results for this job with performance_seconds
    updated_count = 0
    for result in all_results:
        if result.get('job_id') == job_id and 'reboot' in result.get('method', '').lower():
            iteration = result.get('iteration')
            if iteration in performance_data:
                result['performance_seconds'] = performance_data[iteration]
                updated_count += 1
                print(f"Updated iteration {iteration} with {performance_data[iteration]}s")
    
    # Save updated results
    try:
        with open(results_file, 'w') as f:
            json.dump(all_results, f, indent=2)
        print(f"✓ Updated {updated_count} results with performance data")
        return True
    except Exception as e:
        print(f"Error saving results: {e}")
        return False

if __name__ == '__main__':
    job_id = 'e2a9a09c-7871-46eb-bd4c-ca33989f3af2'
    
    print(f"Rebuilding results for job: {job_id}\n")
    success = rebuild_results(job_id)
    
    if success:
        print(f"\n✓ Results rebuilt successfully!")
        print("Reboot performance times should now appear in the reboot-perf-results table")
    else:
        print(f"\n✗ Failed to rebuild results")
