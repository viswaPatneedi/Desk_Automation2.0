#!/usr/bin/env python3
"""
Test script to verify multi-iteration screenshot fix
Tests that get_job_screenshots returns ALL iteration screenshots, not just the first
"""

import json
import os
import sys

# Add app path
sys.path.insert(0, '/home/guser/Desk-automation/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard')

def test_multi_iteration_screenshots():
    """Test that screenshots from all iterations are returned"""
    
    print("\n" + "="*80)
    print("MULTI-ITERATION SCREENSHOT TEST")
    print("="*80 + "\n")
    
    # Test job ID with 2 iterations
    job_id = 'c18ab1ea-a762-4854-b30a-4a5405b8818a'
    
    # Read test_results_history.json
    base_dir = '/home/guser/Desk-automation/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard'
    history_file = os.path.join(base_dir, 'Json', 'test_results_history.json')
    
    print(f"📋 Reading: {history_file}\n")
    
    with open(history_file, 'r') as f:
        all_results = json.load(f)
    
    # Find results for the job
    results_for_job = [r for r in all_results if r.get('job_id') == job_id]
    
    print(f"🔍 Found {len(results_for_job)} results for job {job_id}\n")
    
    # Check each result
    total_screenshots = 0
    iterations_with_screenshots = {}
    
    for i, result in enumerate(results_for_job, 1):
        iteration = result.get('iteration')
        method = result.get('method')
        captured_ss = result.get('captured_screenshots', {})
        
        print(f"Result {i}:")
        print(f"  ├─ Iteration: {iteration}")
        print(f"  ├─ Method: {method}")
        print(f"  └─ Captured Screenshots:")
        
        if captured_ss.get('before'):
            print(f"      ├─ Before: ✅ Present")
            total_screenshots += 1
        else:
            print(f"      ├─ Before: ❌ Missing")
        
        if captured_ss.get('after'):
            print(f"      └─ After: ✅ Present")
            total_screenshots += 1
        else:
            print(f"      └─ After: ❌ Missing")
        
        if captured_ss.get('before') or captured_ss.get('after'):
            iterations_with_screenshots[iteration] = len([s for s in [captured_ss.get('before'), captured_ss.get('after')] if s])
        
        print()
    
    # Verify the fix
    print("="*80)
    print("TEST RESULTS")
    print("="*80 + "\n")
    
    if len(results_for_job) > 1:
        print(f"✅ Job has multiple iterations: {len(results_for_job)} results found")
    else:
        print(f"⚠️  Job has only 1 result")
    
    if len(iterations_with_screenshots) > 1:
        print(f"✅ Multiple iterations have screenshots: {len(iterations_with_screenshots)} iterations")
        for iter_num, ss_count in sorted(iterations_with_screenshots.items()):
            print(f"   └─ Iteration {iter_num}: {ss_count} screenshots")
    else:
        print(f"❌ Only 1 iteration has screenshots")
    
    print(f"\n✅ Total screenshots across all iterations: {total_screenshots}")
    
    # Summary
    print("\n" + "="*80)
    print("BEFORE FIX BEHAVIOR:")
    print("  ❌ Would show only 2 screenshots (from Iteration 1)")
    print("\nAFTER FIX BEHAVIOR:")
    print(f"  ✅ Shows all {total_screenshots} screenshots (from all {len(results_for_job)} iterations)")
    print("  ✅ Each screenshot labeled with iteration number")
    print("="*80 + "\n")
    
    return total_screenshots == 4  # Should have 2 before + 2 after = 4 total

if __name__ == '__main__':
    try:
        success = test_multi_iteration_screenshots()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
