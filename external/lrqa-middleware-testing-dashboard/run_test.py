#!/usr/bin/env python3
import requests
import json
import sys
import time

# Flask app URL
BASE_URL = "http://localhost:11079"

# Test execution parameters
DEVICE_IP = "10.0.0.250"
EXECUTION_QUEUE = [
    {
        "method": "netflix_playback",
        "ir_keys": "power",
        "voice_text": "netflix"
    }
]

print("🎬 Starting Netflix Playback Test Execution...")
print(f"📱 Device IP: {DEVICE_IP}")
print(f"🎯 Method: netflix_playback")
print()

try:
    # Make API call to execute test
    payload = {
        "device_ip": DEVICE_IP,
        "execution_queue": EXECUTION_QUEUE
    }
    
    print("📤 Sending execution request...")
    response = requests.post(
        f"{BASE_URL}/api/execute",
        json=payload,
        timeout=30
    )
    
    print(f"✅ Response Status: {response.status_code}")
    
    try:
        response_data = response.json()
        print(f"📋 Response Data:")
        print(json.dumps(response_data, indent=2))
        
        # Extract job_id if available
        if 'job_id' in response_data:
            job_id = response_data['job_id']
            print(f"\n✅ Job created: {job_id}")
            print(f"🔗 Access results at: {BASE_URL}/jobs/{job_id}")
        
    except:
        print(f"📝 Response Text: {response.text[:500]}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

print("\n⏳ Test execution initiated. Monitor the app UI or logs for completion.")
