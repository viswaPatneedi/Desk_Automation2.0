#!/usr/bin/env python3
"""
Rebuild tiles_summary data from execution log and inject into test results
"""

import json
import re
import os
from pathlib import Path

job_id = "e2a9a09c-7871-46eb-bd4c-ca33989f3af2"
log_file = f"logs/jobs/{job_id}/execution.log"
results_file = "test_results_history.json"

# Extract tiles data from log
tiles_data_by_iteration = {}

try:
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    iteration = 0
    for i, line in enumerate(lines):
        # Look for the tiles found line
        if "✓ Found" in line and "input tiles" in line:
            iteration += 1
            
            # Extract found count (e.g., "8/8")
            found_match = re.search(r'Found (\d+)/(\d+)', line)
            if found_match:
                found_count = int(found_match.group(1))
                total_count = int(found_match.group(2))
                
                # Extract found tiles list
                found_tiles = []
                missing_tiles = []
                
                # Look for "Found:" part
                if "Found:" in line:
                    found_part = line.split("Found:")[-1]
                    # Extract tiles between "Found:" and "Missing:"
                    if "Missing:" in found_part:
                        tiles_str = found_part.split("Missing:")[0].strip()
                        missing_str = found_part.split("Missing:")[-1].strip()
                        
                        # Parse tiles
                        found_tiles = [t.strip().rstrip('.') for t in tiles_str.split(',') if t.strip()]
                        if missing_str and missing_str != 'None.':
                            missing_tiles = [t.strip().rstrip('.') for t in missing_str.split(',') if t.strip()]
                
                tiles_data_by_iteration[iteration] = {
                    'found_count': found_count,
                    'total_count': total_count,
                    'tiles_found': found_tiles,
                    'tiles_missing': missing_tiles,
                    'status': f"{found_count}/{total_count}"
                }
    
    print(f"\n{'='*80}")
    print(f"TILES REBUILD SCRIPT - Job {job_id}")
    print(f"{'='*80}\n")
    print(f"Extracted tiles data for {len(tiles_data_by_iteration)} iterations")
    
    # Now update test_results_history.json
    if os.path.exists(results_file):
        with open(results_file, 'r') as f:
            results = json.load(f)
    else:
        results = []
    
    # Count how many we update
    updated_count = 0
    skipped_count = 0
    
    for result in results:
        # Filter for this job's navigate_inputs_xumo results
        if result.get('job_id') == job_id and result.get('method') == 'navigate_inputs_xumo':
            iteration = result.get('iteration')
            if iteration in tiles_data_by_iteration:
                result['tiles_summary'] = tiles_data_by_iteration[iteration]
                updated_count += 1
            else:
                skipped_count += 1
    
    # Save updated results
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✓ Updated results file: {results_file}")
    print(f"  - Results updated: {updated_count}")
    print(f"  - Results skipped: {skipped_count}")
    print(f"  - Total results in file: {len(results)}")
    
    print(f"\n✓ Tiles data injection complete!")
    print(f"{'='*80}\n")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
