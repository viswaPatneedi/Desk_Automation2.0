#!/usr/bin/env python3
"""
Extract tiles data from execution log and prepare results
"""

import json
import re
from pathlib import Path

job_id = "e2a9a09c-7871-46eb-bd4c-ca33989f3af2"
log_file = f"logs/jobs/{job_id}/execution.log"

tiles_data = []

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
                        found_tiles = [t.strip() for t in tiles_str.split(',') if t.strip()]
                        if missing_str and missing_str != 'None.':
                            missing_tiles = [t.strip() for t in missing_str.split(',') if t.strip()]
                
                tiles_data.append({
                    'iteration': iteration,
                    'found_count': found_count,
                    'total_count': total_count,
                    'found_tiles': found_tiles,
                    'missing_tiles': missing_tiles,
                    'tiles_status': f"{found_count}/{total_count}"
                })
    
    print(f"\n{'='*80}")
    print(f"TILES EXTRACTION SUMMARY - Job {job_id}")
    print(f"{'='*80}\n")
    print(f"Total iterations processed: {len(tiles_data)}")
    print(f"Sample data (first 5 iterations):")
    print(json.dumps(tiles_data[:5], indent=2))
    
    # Summary statistics
    all_found = all(t['found_count'] == t['total_count'] for t in tiles_data)
    missing_count = sum(1 for t in tiles_data if t['found_count'] < t['total_count'])
    
    print(f"\nAll tiles found for all iterations: {all_found}")
    print(f"Iterations with missing tiles: {missing_count}")
    
    if tiles_data:
        avg_found = sum(t['found_count'] for t in tiles_data) / len(tiles_data)
        print(f"Average tiles found: {avg_found:.1f}/{tiles_data[0]['total_count']}")
    
    # Save to file for use in results table
    output_file = 'tiles_results_data.json'
    with open(output_file, 'w') as f:
        json.dump({
            'job_id': job_id,
            'device': 'SHARP-DEVICE-DESK_10.0.0.232',
            'total_iterations': len(tiles_data),
            'tiles_data': tiles_data,
            'summary': {
                'all_perfect': all_found,
                'iterations_with_missing': missing_count,
                'average_found': avg_found if tiles_data else 0
            }
        }, f, indent=2)
    
    print(f"\n✓ Data saved to {output_file}")
    print(f"{'='*80}\n")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
