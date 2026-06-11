# Example: VNC Screenshot Integration into method_deepsleep.py
# This file shows the exact changes needed to use VNC screenshots

## BEFORE (Current Implementation - 60-90 seconds for screenshots)
CODE_BEFORE = """
# In execute_deepsleep_process() function

# PRE-DEEPSLEEP VALIDATION
if not skip_pre_validation:
    # ... other validation code ...
    
    # Take BEFORE screenshot
    method_for_folder = get_folder_method_name() or combined_method_name or "deepsleep"
    screenshot_folder = create_screenshot_folder(device_ip, safe_device_name, iteration, "Before", method_for_folder)
    screenshot_name = f"{device_ip}_{safe_device_name}_Iteration-{iteration}_Before-DeepSleep_{timestamp}"
    
    # THIS TAKES 20-30 SECONDS
    screenshot_result = take_and_analyze_screenshot(
        ssh, screenshot_name, device_ip, log_message, screenshot_folder
    )
    
    if screenshot_result and screenshot_result.get('success'):
        screenshots_list.append(screenshot_result.get('local_path', ''))


# POST-DEEPSLEEP VALIDATION
log_message("Checking if device is on HOME screen after DeepSleep...")

# ... check HOME screen ...

# Take AFTER screenshot
screenshot_folder = create_screenshot_folder(device_ip, safe_device_name, iteration, "After", method_for_folder)
screenshot_name = f"{device_ip}_{safe_device_name}_Iteration-{iteration}_After-DeepSleep_{timestamp}"

# THIS TAKES ANOTHER 20-30 SECONDS
screenshot_result = take_and_analyze_screenshot(
    ssh, screenshot_name, device_ip, log_message, screenshot_folder
)

# TOTAL TIME: 40-60 seconds just for screenshots!
"""


## AFTER (New Implementation with VNC - 10-20 seconds for screenshots)
CODE_AFTER = """
# In execute_deepsleep_process() function

# ADD IMPORT AT TOP
from tools.screen.screenshot_utils_vnc import take_vnc_screenshot_with_fallback

# PRE-DEEPSLEEP VALIDATION
if not skip_pre_validation:
    # ... other validation code ...
    
    # Take BEFORE screenshot
    method_for_folder = get_folder_method_name() or combined_method_name or "deepsleep"
    screenshot_folder = create_screenshot_folder(device_ip, safe_device_name, iteration, "Before", method_for_folder)
    screenshot_name = f"{device_ip}_{safe_device_name}_Iteration-{iteration}_Before-DeepSleep"
    
    # NOW TAKES ONLY 5-10 SECONDS (with fallback if needed)
    screenshot_result = take_vnc_screenshot_with_fallback(
        ssh=ssh,
        device_ip=device_ip,
        device_name=safe_device_name,
        iteration=iteration,
        screenshot_folder=screenshot_folder,
        vnc_port=5800,
        log_callback=log_message,
        fallback_to_plugin=True  # Falls back to plugin if VNC fails
    )
    
    if screenshot_result and screenshot_result.get('success'):
        screenshots_list.append(screenshot_result.get('local_path', ''))
        time_saved = screenshot_result.get('capture_time', 0)
        log_message(f"📈 Screenshot captured in {time_saved:.2f}s (VNC method)")


# POST-DEEPSLEEP VALIDATION
log_message("Checking if device is on HOME screen after DeepSleep...")

# ... check HOME screen ...

# Take AFTER screenshot
screenshot_folder = create_screenshot_folder(device_ip, safe_device_name, iteration, "After", method_for_folder)
screenshot_name = f"{device_ip}_{safe_device_name}_Iteration-{iteration}_After-DeepSleep"

# NOW TAKES ONLY 5-10 SECONDS
screenshot_result = take_vnc_screenshot_with_fallback(
    ssh=ssh,
    device_ip=device_ip,
    device_name=safe_device_name,
    iteration=iteration,
    screenshot_folder=screenshot_folder,
    vnc_port=5800,
    log_callback=log_message,
    fallback_to_plugin=True
)

# TOTAL TIME: 10-20 seconds for screenshots (3-4x faster!)
"""


## STEP-BY-STEP CHANGES

print("=" * 80)
print("STEP-BY-STEP INTEGRATION GUIDE")
print("=" * 80)

print("""
STEP 1: Add Import at Top of method_deepsleep.py
-------------------------------------------------
Location: Near other imports (around line 10-20)

Add this line:
    from tools.screen.screenshot_utils_vnc import take_vnc_screenshot_with_fallback


STEP 2: Find All take_and_analyze_screenshot Calls
---------------------------------------------------
Search for: "take_and_analyze_screenshot"

In method_deepsleep.py, you'll find 3 occurrences:
    1. Line ~260: PRE-DEEPSLEEP screenshot (Before)
    2. Line ~380: POST-DEEPSLEEP screenshot (After) 
    3. Line ~420: POST-DEEPSLEEP error diagnosis screenshot


STEP 3: Replace Each Call
--------------------------

REPLACEMENT 1 (Before DeepSleep):
    
    FROM:
        screenshot_result = take_and_analyze_screenshot(
            ssh, screenshot_name, device_ip, log_message, screenshot_folder
        )
    
    TO:
        screenshot_result = take_vnc_screenshot_with_fallback(
            ssh=ssh,
            device_ip=device_ip,
            device_name=safe_device_name,
            iteration=iteration,
            screenshot_folder=screenshot_folder,
            log_callback=log_message,
            fallback_to_plugin=True
        )


REPLACEMENT 2 (After DeepSleep - Success Case):
    
    FROM:
        screenshot_result = take_and_analyze_screenshot(
            ssh, screenshot_name, device_ip, log_message, screenshot_folder
        )
    
    TO:
        screenshot_result = take_vnc_screenshot_with_fallback(
            ssh=ssh,
            device_ip=device_ip,
            device_name=safe_device_name,
            iteration=iteration,
            screenshot_folder=screenshot_folder,
            log_callback=log_message,
            fallback_to_plugin=True
        )


REPLACEMENT 3 (After DeepSleep - Error Case):

    FROM:
        screenshot_result = take_and_analyze_screenshot(
            ssh, screenshot_name, device_ip, log_message, screenshot_folder
        )
    
    TO:
        screenshot_result = take_vnc_screenshot_with_fallback(
            ssh=ssh,
            device_ip=device_ip,
            device_name=safe_device_name,
            iteration=iteration,
            screenshot_folder=screenshot_folder,
            log_callback=log_message,
            fallback_to_plugin=True
        )


STEP 4: Test the Changes
------------------------
1. Run a test iteration with one device
2. Check logs for capture times - should see "5-10 seconds" for VNC
3. Verify screenshots are saved correctly
4. Check if fallback to plugin works if VNC fails


STEP 5: Monitor Performance
----------------------------
Before:  ~60-90 seconds per iteration (3 screenshots @ 20-30s each)
After:   ~15-30 seconds per iteration (3 screenshots @ 5-10s each)
Savings: ~45-60 seconds per iteration!


OPTIONAL ENHANCEMENTS:
-----------------------

Add logging for better visibility:

    screenshot_result = take_vnc_screenshot_with_fallback(
        ssh=ssh,
        device_ip=device_ip,
        device_name=safe_device_name,
        iteration=iteration,
        screenshot_folder=screenshot_folder,
        log_callback=log_message,
        fallback_to_plugin=True
    )
    
    # Add this after the call:
    if screenshot_result.get('success'):
        capture_time = screenshot_result.get('capture_time', 0)
        method = screenshot_result.get('method', 'VNC')
        log_message(f"✓ Screenshot: {capture_time:.2f}s using {method}")
        
        # Extract screen state
        screen_state = screenshot_result.get('screen_state', {})
        if screen_state:
            screen_detected = screen_state.get('screen_detected', 'Unknown')
            confidence = screen_state.get('confidence', 0.0)
            log_message(f"  Screen: {screen_detected} ({confidence:.0%})")
""")


## EXACT LINE NUMBERS FOR method_deepsleep.py

print("\n" + "=" * 80)
print("EXACT LOCATIONS IN method_deepsleep.py")
print("=" * 80)

locations = """
Location 1 - Before DeepSleep Screenshot
-----------------------------------------
Current Line ~260:
    screenshot_result = take_and_analyze_screenshot(ssh, screenshot_name, device_ip, log_message, screenshot_folder)

Replace with:
    screenshot_result = take_vnc_screenshot_with_fallback(
        ssh=ssh, device_ip=device_ip, device_name=safe_device_name,
        iteration=iteration, screenshot_folder=screenshot_folder,
        log_callback=log_message, fallback_to_plugin=True
    )


Location 2 - After DeepSleep Screenshot (Success)
--------------------------------------------------
Current Line ~380:
    screenshot_result = take_and_analyze_screenshot(ssh, screenshot_name, device_ip, log_message, screenshot_folder)

Replace with:
    screenshot_result = take_vnc_screenshot_with_fallback(
        ssh=ssh, device_ip=device_ip, device_name=safe_device_name,
        iteration=iteration, screenshot_folder=screenshot_folder,
        log_callback=log_message, fallback_to_plugin=True
    )


Location 3 - After DeepSleep Screenshot (Error)
-----------------------------------------------
Current Line ~420:
    screenshot_result = take_and_analyze_screenshot(ssh, screenshot_name, device_ip, log_message, screenshot_folder)

Replace with:
    screenshot_result = take_vnc_screenshot_with_fallback(
        ssh=ssh, device_ip=device_ip, device_name=safe_device_name,
        iteration=iteration, screenshot_folder=screenshot_folder,
        log_callback=log_message, fallback_to_plugin=True
    )


Location 4 - Recovery Screenshot (IR HOME retry)
------------------------------------------------
Current Line ~450:
    screenshot_result = take_and_analyze_screenshot(ssh, screenshot_name, device_ip, log_message, screenshot_folder)

Replace with:
    screenshot_result = take_vnc_screenshot_with_fallback(
        ssh=ssh, device_ip=device_ip, device_name=safe_device_name,
        iteration=iteration, screenshot_folder=screenshot_folder,
        log_callback=log_message, fallback_to_plugin=True
    )
"""

print(locations)


## EXPECTED RESULTS

print("\n" + "=" * 80)
print("EXPECTED RESULTS AFTER INTEGRATION")
print("=" * 80)

results = """
TIMING IMPROVEMENTS:
-------------------
Metric                      Before          After          Improvement
DeepSleep test (1 iter)    60-90 sec       20-30 sec      65-70% faster
Screenshots only           40-60 sec       10-15 sec      75% faster
5 iterations              5-7.5 min       1.5-2.5 min    65% faster


QUALITY ASSURANCE:
------------------
✓ Screenshot resolution maintained
✓ Screen validation accuracy maintained (using same validator)
✓ Fallback to plugin ensures no test failures
✓ OCR quality not affected


LOGS/MONITORING:
----------------
Before:
    ⏱ Waiting 20 seconds for screenshot upload to complete...
    ✓ Screenshot downloaded successfully
    Total time: 28.3s

After:
    📸 VNC Screenshot: Generating capture from http://10.0.0.195:5800/...
    ✓ Screenshot downloaded: 156.23 KB
    Total time: 8.2s


ERROR HANDLING:
---------------
Scenario 1: VNC succeeds
    → Uses fast VNC method (5-10s) ✓

Scenario 2: VNC fails but plugin available
    → Falls back to ScreenCapture plugin (20-30s) ✓
    → Test continues successfully

Scenario 3: Both fail
    → Test fails gracefully with error message
    → SSH connection still active for other operations
"""

print(results)


## VALIDATION CHECKLIST

print("\n" + "=" * 80)
print("POST-INTEGRATION VALIDATION CHECKLIST")
print("=" * 80)

checklist = """
After making the changes, verify:

□ 1. Application starts without errors
    grep "Error" app.log | head -5

□ 2. Screenshot utility imports correctly
    python -c "from tools.screen.screenshot_utils_vnc import take_vnc_screenshot_with_fallback; print('✓ Import OK')"

□ 3. First test captures screenshots
    Console should show: "✓ Screenshot captured in X.XXs using VNC"

□ 4. Screenshots are saved to correct folder
    ls -la screenshots/ | grep -E "10\.0\.0\.[0-9]+.*\.png"

□ 5. Screen validation works
    Console should show: "✓ Screen detected: HOME_SCREEN_XUMO (XX% confidence)"

□ 6. Timing shows improvement
    Compare: Old runs had "20-30s" to-each screenshot
            New runs have "5-10s" per screenshot

□ 7. Fallback works (test by blocking VNC port)
    Should see message: "⚠ VNC failed, falling back to ScreenCapture plugin"

□ 8. Test results are consistent
    Run 5 iterations and verify same success rate as before

□ 9. Check for any new errors in logs
    tail -n 50 app.log | grep -i "error\\|exception"

□ 10. Performance metrics documented
    Record: Old time (60-90s), New time (15-30s), Time saved
"""

print(checklist)


## QUICK TESTING SCRIPT

print("\n" + "=" * 80)
print("QUICK TESTING SCRIPT")
print("=" * 80)

test_script = """
# test_vnc_screenshot.py - Test VNC screenshot on your device

#!/usr/bin/env python3

from tools.screen.screenshot_utils_vnc import take_vnc_screenshot_with_fallback, take_vnc_screenshot
import paramiko
import time

# Configuration
device_ip = "10.0.0.195"  # Change to your device
device_name = "SKY-GLASS-G1"
iteration = 1

print("\\n" + "="*80)
print("VNC SCREENSHOT TEST")
print("="*80)

# Test 1: VNC only (fastest)
print("\\nTest 1: VNC-only screenshot (no fallback)...")
start = time.time()
result = take_vnc_screenshot(device_ip, device_name, iteration)
vnc_time = time.time() - start

if result['success']:
    print(f"✓ VNC Success: {vnc_time:.2f}s")
    print(f"  File: {result['local_path']}")
    print(f"  Size: {result['file_size']/1024:.2f}KB")
    print(f"  Dimensions: {result['dimensions']}")
else:
    print(f"✗ VNC Failed: {result['error']}")

# Test 2: With fallback (more reliable)
print("\\nTest 2: VNC with ScreenCapture fallback...")
try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(device_ip, port=10022, username="root", password="")
    
    start = time.time()
    result = take_vnc_screenshot_with_fallback(
        ssh, device_ip, device_name, iteration+1,
        fallback_to_plugin=True
    )
    fallback_time = time.time() - start
    
    if result['success']:
        print(f"✓ Fallback Success: {fallback_time:.2f}s")
        print(f"  File: {result['local_path']}")
    else:
        print(f"✗ Fallback Failed: {result['error']}")
    
    ssh.close()
except Exception as e:
    print(f"✗ Test failed: {e}")

# Summary
print("\\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"VNC-only time:     {vnc_time:.2f}s")
if 'fallback_time' in locals():
    print(f"With fallback:     {fallback_time:.2f}s")
    if fallback_time > vnc_time:
        print(f"Fallback overhead: {fallback_time - vnc_time:.2f}s")
print("="*80)
"""

print(test_script)
