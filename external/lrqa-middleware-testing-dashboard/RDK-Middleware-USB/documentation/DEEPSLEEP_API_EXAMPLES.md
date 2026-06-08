# DeepSleep Method - API Examples and Workflows

## Quick Start API Examples

### 1. Simple DeepSleep Job (Auto-detect Remote, 1 Hour)

**Request:**
```bash
curl -X POST http://localhost:5000/api/jobs/submit \
  -H "Content-Type: application/json" \
  -d '{
    "device_ip": "192.168.1.100",
    "method": "deepsleep"
  }'
```

**Response (202 Accepted):**
```json
{
  "success": true,
  "job_id": "deepsleep_20260327_001",
  "message": "Job deepsleep_20260327_001 submitted for deepsleep"
}
```

**What happens:**
- Remote type: Auto-detect from device name (SKY/XUMO)
- Sleep duration: 60 minutes (default)
- Iteration: 1
- Expected execution time: ~65 minutes

---

### 2. XUMO Device - 120 Minute Test

**Request:**
```bash
curl -X POST http://localhost:5000/api/jobs/submit \
  -H "Content-Type: application/json" \
  -d '{
    "device_ip": "192.168.1.100",
    "method": "deepsleep",
    "remote_type": "XUMO",
    "sleep_duration_minutes": 120
  }'
```

**Response (202 Accepted):**
```json
{
  "success": true,
  "job_id": "deepsleep_20260327_002",
  "message": "Job deepsleep_20260327_002 submitted for deepsleep"
}
```

**What happens:**
- Remote type: XUMO (user-selected, explicit)
- Sleep duration: 120 minutes (2 hours)
- Expected execution time: ~127 minutes
- Uses XUMO_PR3 remote for wake-up command

---

### 3. SKY Device - Quick 10 Minute Validation

**Request:**
```bash
curl -X POST http://localhost:5000/api/jobs/submit \
  -H "Content-Type: application/json" \
  -d '{
    "device_ip": "192.168.1.50",
    "method": "deepsleep",
    "remote_type": "SKY",
    "sleep_duration_minutes": 10
  }'
```

**Response (202 Accepted):**
```json
{
  "success": true,
  "job_id": "deepsleep_20260327_003",
  "message": "Job deepsleep_20260327_003 submitted for deepsleep"
}
```

**What happens:**
- Remote type: SKY (user-selected)
- Sleep duration: 10 minutes (quick validation)
- Expected execution time: ~15 minutes
- Uses SKY_LC103 remote for wake-up command

---

### 4. Extended 5 Hour Stress Test (Multiple Iterations)

**Request:**
```bash
# Job 1 of 3
curl -X POST http://localhost:5000/api/jobs/submit \
  -H "Content-Type: application/json" \
  -d '{
    "device_ip": "192.168.1.100",
    "method": "deepsleep",
    "remote_type": "XUMO",
    "sleep_duration_minutes": 300,
    "iteration": 1
  }'

# Job 2 of 3
curl -X POST http://localhost:5000/api/jobs/submit \
  -H "Content-Type: application/json" \
  -d '{
    "device_ip": "192.168.1.100",
    "method": "deepsleep",
    "remote_type": "XUMO",
    "sleep_duration_minutes": 300,
    "iteration": 2
  }'

# Job 3 of 3
curl -X POST http://localhost:5000/api/jobs/submit \
  -H "Content-Type: application/json" \
  -d '{
    "device_ip": "192.168.1.100",
    "method": "deepsleep",
    "remote_type": "XUMO",
    "sleep_duration_minutes": 300,
    "iteration": 3
  }'
```

**Response for each (202 Accepted):**
```json
{
  "success": true,
  "job_id": "deepsleep_20260327_004",
  "message": "Job deepsleep_20260327_004 submitted for deepsleep"
}
// ... similar for iterations 2 and 3
```

**What happens:**
- 3 sequential DeepSleep jobs queued
- Each: 5 hour duration, XUMO remote
- Total execution time for all: ~15+ hours
- Each iteration can be monitored independently

---

### 5. Invalid Parameters - Error Handling

**Request (Invalid remote type):**
```bash
curl -X POST http://localhost:5000/api/jobs/submit \
  -H "Content-Type: application/json" \
  -d '{
    "device_ip": "192.168.1.100",
    "method": "deepsleep",
    "remote_type": "INVALID_REMOTE"
  }'
```

**Response (400 Bad Request):**
```json
{
  "error": "Invalid remote_type: INVALID_REMOTE"
}
```

---

**Request (Invalid duration):**
```bash
curl -X POST http://localhost:5000/api/jobs/submit \
  -H "Content-Type: application/json" \
  -d '{
    "device_ip": "192.168.1.100",
    "method": "deepsleep",
    "sleep_duration_minutes": 2000
  }'
```

**Response (400 Bad Request):**
```json
{
  "error": "sleep_duration_minutes must be 1-1440"
}
```

---

## Complete Workflow Examples

### Workflow 1: Sequential Multi-Duration Testing

**Goal:** Test device behavior at different DeepSleep durations

**Step 1: Queue Jobs**
```python
import requests

api_url = "http://localhost:5000/api/jobs/submit"
device_ip = "192.168.1.100"

durations = [10, 30, 60, 120]  # Test at 4 different durations
jobs = []

for i, duration in enumerate(durations, 1):
    payload = {
        "device_ip": device_ip,
        "method": "deepsleep",
        "remote_type": "XUMO",
        "sleep_duration_minutes": duration,
        "iteration": i
    }
    
    response = requests.post(api_url, json=payload)
    if response.status_code == 202:
        data = response.json()
        jobs.append({
            'duration': duration,
            'job_id': data['job_id']
        })
        print(f"✓ Queued {duration}m job: {data['job_id']}")
    else:
        print(f"✗ Failed to queue {duration}m job: {response.text}")

print(f"\nTotal jobs queued: {len(jobs)}")
print(f"Expected total time: {sum(d['duration'] for d in jobs) + len(jobs)*5} minutes")
```

**Expected Output:**
```
✓ Queued 10m job: deepsleep_20260327_001
✓ Queued 30m job: deepsleep_20260327_002
✓ Queued 60m job: deepsleep_20260327_003
✓ Queued 120m job: deepsleep_20260327_004

Total jobs queued: 4
Expected total time: 225 minutes (3 hours 45 minutes)
```

**Step 2: Monitor Execution**
```python
import time

def monitor_jobs(jobs):
    """Monitor job execution."""
    completed = []
    
    while len(completed) < len(jobs):
        response = requests.get(f"http://localhost:5000/api/jobs")
        all_jobs = response.json()['jobs']
        
        for submitted_job in jobs:
            if submitted_job['job_id'] in completed:
                continue
            
            # Find job in all_jobs
            job = next((j for j in all_jobs if j['job_id'] == submitted_job['job_id']), None)
            
            if job and job['status'] == 'completed':
                completed.append(submitted_job['job_id'])
                duration = job.get('duration_minutes', 'N/A')
                print(f"✓ Job {submitted_job['job_id']} completed ({submitted_job['duration']}m test took {duration}m)")
            elif job:
                progress = job.get('progress', 'unknown')
                print(f"  Job {submitted_job['job_id']}: {job['status']} ({progress})")
        
        if len(completed) < len(jobs):
            time.sleep(60)  # Check every minute

monitor_jobs(jobs)
```

---

### Workflow 2: Remote Type Testing (XUMO vs SKY)

**Goal:** Verify both remote types work correctly

**Step 1: Create Device Pair**
```python
# Setup
xumo_device = "192.168.1.100"  # XUMO device
sky_device = "192.168.1.50"     # SKY device

# Queue identical tests with different remotes
test_duration = 60  # 1 hour

xumo_config = {
    "device_ip": xumo_device,
    "method": "deepsleep",
    "remote_type": "XUMO",
    "sleep_duration_minutes": test_duration
}

sky_config = {
    "device_ip": sky_device,
    "method": "deepsleep",
    "remote_type": "SKY",
    "sleep_duration_minutes": test_duration
}

# Submit both
r1 = requests.post(api_url, json=xumo_config)
r2 = requests.post(api_url, json=sky_config)

xumo_job_id = r1.json()['job_id']
sky_job_id = r2.json()['job_id']

print(f"XUMO Job: {xumo_job_id}")
print(f"SKY Job: {sky_job_id}")
```

**Step 2: Compare Results**
```python
def compare_results(xumo_job, sky_job):
    """Compare DeepSleep results between remote types."""
    
    xumo_data = requests.get(f"http://localhost:5000/api/jobs/{xumo_job}").json()
    sky_data = requests.get(f"http://localhost:5000/api/jobs/{sky_job}").json()
    
    print("RESULTS COMPARISON:")
    print(f"{'Metric':<25} {'XUMO':<20} {'SKY':<20}")
    print("-" * 65)
    
    metrics = {
        'Status': 'status',
        'Duration (min)': 'duration_minutes',
        'Wakeup Attempts': 'wakeup_attempts',
        'Errors': 'error_count'
    }
    
    for label, key in metrics.items():
        xumo_val = xumo_data.get(key, 'N/A')
        sky_val = sky_data.get(key, 'N/A')
        print(f"{label:<25} {str(xumo_val):<20} {str(sky_val):<20}")
    
    # Determine if both passed
    if xumo_data['status'] == 'completed' and sky_data['status'] == 'completed':
        print("\n✓ Both remote types working correctly!")
    else:
        print("\n✗ One or more remote types failed")

compare_results(xumo_job_id, sky_job_id)
```

---

### Workflow 3: Stress Testing (Extended Duration)

**Goal:** Run extended stress test to verify stability over time

**Configuration:**
```python
# 12-hour stress test with monitoring
stress_config = {
    "device_ip": "192.168.1.100",
    "method": "deepsleep",
    "remote_type": "XUMO",
    "sleep_duration_minutes": 720,  # 12 hours
    "iteration": 1
}

response = requests.post(api_url, json=stress_config)
job_id = response.json()['job_id']

print(f"Stress test job: {job_id}")
print(f"Expected duration: 12+ hours")
print(f"Monitor progress with: curl http://localhost:5000/api/jobs/{job_id}")
```

**Live Monitoring:**
```bash
#!/bin/bash
# Monitor job every 5 minutes for 12+ hours

JOB_ID="deepsleep_20260327_001"
API_URL="http://localhost:5000/api/jobs/${JOB_ID}"

while true; do
    echo "[$(date)] Checking job status..."
    curl -s "$API_URL" | jq '.status, .progress'
    
    if [[ $(curl -s "$API_URL" | jq -r '.status') == "completed" ]]; then
        echo "✓ Job completed!"
        break
    fi
    
    sleep 300  # Check every 5 minutes
done
```

---

### Workflow 4: Automated Test Sequence

**Goal:** Run a comprehensive test sequence across multiple devices

**Python Script:**
```python
import requests
import json
from datetime import datetime

class DeepSleepTestRunner:
    def __init__(self, api_url):
        self.api_url = api_url
        self.jobs = []
    
    def queue_test(self, device_ip, remote_type=None, duration=60, iteration=1):
        """Queue a single DeepSleep test."""
        payload = {
            "device_ip": device_ip,
            "method": "deepsleep",
            "iteration": iteration
        }
        
        if remote_type:
            payload["remote_type"] = remote_type
        if duration != 60:
            payload["sleep_duration_minutes"] = duration
        
        response = requests.post(self.api_url, json=payload)
        if response.status_code == 202:
            job_data = response.json()
            self.jobs.append({
                'device_ip': device_ip,
                'job_id': job_data['job_id'],
                'remote_type': remote_type or 'auto',
                'duration': duration,
                'queued_at': datetime.now().isoformat()
            })
            return job_data['job_id']
        else:
            raise Exception(f"Failed to queue job: {response.text}")
    
    def run_test_suite(self, devices):
        """Run comprehensive test suite across devices."""
        
        print(f"Starting DeepSleep test suite for {len(devices)} devices")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print("=" * 70)
        
        test_cases = [
            {"duration": 10, "label": "Quick (10m)"},
            {"duration": 60, "label": "Standard (60m)"},
            {"duration": 120, "label": "Extended (120m)"}
        ]
        
        for device_config in devices:
            device_ip = device_config['ip']
            device_name = device_config.get('name', 'Unknown')
            
            print(f"\n Device: {device_name} ({device_ip})")
            print("-" * 70)
            
            for test_case in test_cases:
                try:
                    job_id = self.queue_test(
                        device_ip=device_ip,
                        remote_type=device_config.get('remote_type'),
                        duration=test_case['duration']
                    )
                    print(f"  ✓ {test_case['label']:<20} {job_id}")
                except Exception as e:
                    print(f"  ✗ {test_case['label']:<20} Error: {e}")
        
        print("\n" + "=" * 70)
        print(f"Total jobs queued: {len(self.jobs)}")
        print(f"Est. total time: {sum(j['duration'] for j in self.jobs) + len(self.jobs)*5} minutes")
        
        return self.jobs

# Run the test suite
if __name__ == "__main__":
    runner = DeepSleepTestRunner("http://localhost:5000/api/jobs/submit")
    
    devices = [
        {"ip": "192.168.1.100", "name": "XUMO-Device-01", "remote_type": "XUMO"},
        {"ip": "192.168.1.50", "name": "SKY-Device-01", "remote_type": "SKY"},
        {"ip": "192.168.1.75", "name": "XUMO-Device-02", "remote_type": "XUMO"},
    ]
    
    jobs = runner.run_test_suite(devices)
    
    # Save job manifest
    with open('test_manifest.json', 'w') as f:
        json.dump(jobs, f, indent=2)
    
    print("\nJob manifest saved to test_manifest.json")
```

**Expected Output:**
```
Starting DeepSleep test suite for 3 devices
Timestamp: 2026-03-27T14:30:00

 Device: XUMO-Device-01 (192.168.1.100)
----------------------------------------------------------------------
  ✓ Quick (10m)            deepsleep_20260327_001
  ✓ Standard (60m)         deepsleep_20260327_002
  ✓ Extended (120m)        deepsleep_20260327_003

 Device: SKY-Device-01 (192.168.1.50)
----------------------------------------------------------------------
  ✓ Quick (10m)            deepsleep_20260327_004
  ✓ Standard (60m)         deepsleep_20260327_005
  ✓ Extended (120m)        deepsleep_20260327_006

 Device: XUMO-Device-02 (192.168.1.75)
----------------------------------------------------------------------
  ✓ Quick (10m)            deepsleep_20260327_007
  ✓ Standard (60m)         deepsleep_20260327_008
  ✓ Extended (120m)        deepsleep_20260327_009

======================================================================
Total jobs queued: 9
Est. total time: 2430 minutes (40.5 hours)

Job manifest saved to test_manifest.json
```

---

## Command Line Examples

### Direct Python Execution

```python
# Direct method invocation (for testing)
from method_deepsleep import execute_deepsleep_process

# Get device credentials
device = {
    'ip': '192.168.1.100',
    'port': 10022,
    'username': 'root',
    'password': 'password'
}

# Run with XUMO, 120 minute duration
result = execute_deepsleep_process(
    device_ip=device['ip'],
    port=device['port'],
    username=device['username'],
    password=device['password'],
    device_name='XUMO-Device-01',
    remote_type='XUMO',
    sleep_duration_minutes=120,
    iteration=1
)

print(f"Result: {result}")
```

### Using Flask Test Client

```python
# test_deepsleep_api.py
from flask import Flask
from app import create_app
import json

def test_deepsleep_job_submission():
    app = create_app()
    client = app.test_client()
    
    # Test case 1: Basic submission
    response = client.post('/api/jobs/submit', json={
        'device_ip': '192.168.1.100',
        'method': 'deepsleep',
        'remote_type': 'XUMO',
        'sleep_duration_minutes': 60
    })
    
    assert response.status_code == 202
    data = response.get_json()
    assert 'job_id' in data
    print(f"✓ Basic submission: {data['job_id']}")
    
    # Test case 2: Invalid remote type
    response = client.post('/api/jobs/submit', json={
        'device_ip': '192.168.1.100',
        'method': 'deepsleep',
        'remote_type': 'INVALID'
    })
    
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    print(f"✓ Invalid remote type rejected: {data['error']}")
    
    # Test case 3: Auto-detect
    response = client.post('/api/jobs/submit', json={
        'device_ip': '192.168.1.100',
        'method': 'deepsleep'
    })
    
    assert response.status_code == 202
    print(f"✓ Auto-detect works")

if __name__ == '__main__':
    test_deepsleep_job_submission()
    print("\nAll tests passed!")
```

---

## Summary Table: Common Scenarios

| Scenario | API Call | Duration | Remote | Use Case |
|----------|----------|----------|--------|----------|
| Quick test | POST with `sleep_duration_minutes: 10` | ~15 min | Auto | Rapid validation |
| Standard test | POST with defaults | ~65 min | Auto | Daily testing |
| XUMO explicit | POST with `remote_type: XUMO` | ~65 min | XUMO | XUMO-only testing |
| SKY explicit | POST with `remote_type: SKY` | ~65 min | SKY | SKY-only testing |
| Extended test | POST with `sleep_duration_minutes: 120` | ~127 min | Auto | Stress testing |
| Very long test | POST with `sleep_duration_minutes: 300` | ~307 min | Auto | 5+ hour endurance |
| Multi-iteration | POST ×3 with `iteration: 1,2,3` | ~195 min | Auto | Sequential runs |
| Custom duration | POST with `sleep_duration_minutes: 45` | ~50 min | Auto | Specific requirement |

---

**Last Updated:** 2026-03-27  
**Status:** Complete API Examples and Workflows  
**Related Files:** DEEPSLEEP_CONFIGURATION_GUIDE.md, DEEPSLEEP_FLASK_INTEGRATION.md
