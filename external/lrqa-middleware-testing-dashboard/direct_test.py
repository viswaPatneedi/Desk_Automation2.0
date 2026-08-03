#!/usr/bin/env python3
"""
Direct Netflix Playback Test Execution
Bypasses Flask API authentication by calling method directly
"""
import sys
import os
import time

# Add methods directory to path
sys.path.insert(0, '/home/lrqa/Desktop/viswa/Desk-automation2.0/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard')
sys.path.insert(0, '/home/lrqa/Desktop/viswa/Desk-automation2.0/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard/methods')

# Change to project directory
os.chdir('/home/lrqa/Desktop/viswa/Desk-automation2.0/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard')

print("="*80)
print("🎬 NETFLIX PLAYBACK TEST EXECUTION (Direct Method Call)")
print("="*80)
print()

try:
    # Import the Netflix playback method
    print("📦 Loading Netflix playback method...")
    from method_netflix_playback import netflix_playback
    
    # Execute the test on device 10.0.0.250
    device_ip = "10.0.0.250"
    port = 10022
    username = "root"
    password = ""  # Empty password
    
    print(f"📱 Device: {device_ip}")
    print(f"🔌 Port: {port}")
    print(f"👤 User: {username}")
    print(f"🎯 Method: netflix_playback")
    print()
    
    print("⏳ Executing... (this may take 2-5 minutes)")
    print("-" * 80)
    print()
    
    # Call the method with all parameters
    result = netflix_playback(device_ip, port, username, password)
    
    print()
    print("-" * 80)
    print()
    print("✅ EXECUTION COMPLETED")
    print()
    print(f"🎯 Result: {result.get('status', 'unknown')}")
    
    # Print result summary
    if isinstance(result, dict):
        for key, value in result.items():
            if key not in ['logs', 'execution_logs_path']:
                if isinstance(value, bool) or isinstance(value, str) or isinstance(value, int):
                    print(f"   {key}: {value}")
    
    if result.get('execution_logs_path'):
        print(f"\n📊 Full logs: {result['execution_logs_path']}")
    
except Exception as e:
    import traceback
    print(f"\n❌ ERROR: {e}")
    print("\n📋 Traceback:")
    traceback.print_exc()
    sys.exit(1)

print("\n✅ Test execution completed successfully!")
print("\n📌 To validate stale log detection:")
print("   1. Check if Layer 2 & 3 show '⚠ No NEW logs (stale)' when playback stops")
print("   2. Verify logs contain both 'NEW' and 'stale' indicators")
print("   3. Compare Step 8 output with previous execution ffac17dd-b609-440b-9d91-ca50aa22263e")
