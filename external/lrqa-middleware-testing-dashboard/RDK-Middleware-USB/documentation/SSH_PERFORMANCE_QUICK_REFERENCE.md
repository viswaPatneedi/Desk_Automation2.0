# SSH Performance Quick Reference Guide

## ⚡ Speed Comparison at a Glance

### Visual Timeline

```
REGULAR SSH (Paramiko):
├─ Connection: 200-500ms
├─ Execution: 100-300ms
├─ Retrieval: 50-150ms
└─ TOTAL: ~500ms - 1 second

LIGHTSPEED SSH:
├─ Auth: 500-1000ms (cached)
├─ Submit: 200-400ms
├─ Poll: 15,000ms+ (15s minimum)
├─ Retrieval: 100-300ms
└─ TOTAL: ~15-60+ seconds
```

### Speed Metrics Table

| Metric | Regular SSH | Lightspeed SSH | Winner |
|--------|-----------|----------------|--------|
| **Best Case** | 500ms | 15s | ✅ Regular |
| **Average** | 630ms | 30s | ✅ Regular |
| **Worst Case** | 950ms | 60s+ | ✅ Regular |
| **Speed Factor** | 1x | 50x slower | ✅ Regular |

---

## 🎯 Decision Tree: Which SSH Method Should I Use?

```
START
  │
  └─ Is direct network access to device available?
     │
     ├─ YES → Is firewall blocking SSH (22, 10022)?
     │         │
     │         ├─ NO → Use REGULAR SSH ✅
     │         │       (Fastest: 500-1000ms)
     │         │
     │         └─ YES → Use LIGHTSPEED SSH ✅
     │                  (Slower but works: 15-60s)
     │
     └─ NO → Device behind firewall/VPN?
             │
             ├─ YES → Use LIGHTSPEED SSH ✅
             │        (No direct access needed)
             │
             └─ NO → Need to execute on multiple devices?
                     │
                     ├─ YES (batch) → Use LIGHTSPEED SSH ✅
                     │                (Parallel: ~15-60s)
                     │
                     └─ NO (single) → Use REGULAR SSH ✅
                                     (Fastest: 500-1000ms)
```

---

## 📊 Performance by Scenario

### Scenario 1: Single Device Command (Real-Time)
```
Task: Execute "cat /version.txt" on one device

REGULAR SSH:           LIGHTSPEED SSH:
0ms ┤                  0ms ┤
    │ ▓ Connection      │
500 ├────────┤          │
    │        ▓ Exec.    │ ░ Auth + Submit
    │        └──┤       │ ░░░░░░░░░
1000├─────────────┤    │
    │             ✓     │ ░░░░░░░░░░░░░░░░ Poll
    │          ~600ms   │ (15s minimum)
                        │
                      15000├──────────────────┤
                        │  ░ Retrieval
                        │  ░┤
                      15200└────── ~15200ms
                        
Regular SSH: 600ms  vs  Lightspeed SSH: 15200ms
Ratio: 25x faster ✅
```

### Scenario 2: Batch Device Commands (10 devices)
```
REGULAR SSH (Serial):          LIGHTSPEED SSH (Parallel):
Device 1: 600ms                Device 1,2,3,4,5,6,7,8,9,10:
Device 2: 600ms                All submit: 400ms
Device 3: 600ms                All poll:   15000ms (once)
...                            All retrieve: 300ms
Device 10: 600ms               
                               Total: ~15300ms
Total: ~6000ms

Ratio: 25x SLOWER ✗
However, parallel advantage means Lightspeed could be used
for very large batches where latency per device matters less.
```

### Scenario 3: Firewall-Protected Device
```
REGULAR SSH:                   LIGHTSPEED SSH:
❌ Connection blocked          ✅ Works via cloud
(Port 22/10022 denied)         (Cloud relay service)

Result: Cannot execute         ~15 seconds execution
                               
Forced Choice: Use Lightspeed SSH 🔒
```

---

## 💡 Key Insights

### Regular SSH Wins When:
```
✅ Speed is critical             → 600ms vs 15s (25x faster)
✅ Real-time interaction needed  → No polling delays
✅ Cost-sensitive               → No API calls/tokens
✅ Direct network access        → Take advantage of it
✅ Single device operations     → Serial execution is fine
✅ Development/testing          → Faster iteration
```

### Lightspeed SSH Wins When:
```
✅ No direct access available    → Firewall blocking
✅ Batch operations needed       → 10+ device parallel execution
✅ Audit trail required          → Compliance logging built-in
✅ Centralized management        → Cloud-based infrastructure
✅ Xfinity infrastructure        → Internal Comcast systems
✅ Enterprise security           → No exposing device IPs
```

---

## 🔍 Detailed Timing Breakdown

### Regular SSH Connection Phases:
```
TCP Connection         ├─ 100-200ms (network latency)
                       ├─ 50-100ms (local system overhead)

SSH Handshake         ├─ 50-150ms (key exchange)
                      ├─ 50-100ms (authentication)

Command Execution     ├─ 50-200ms (command processing)
                      ├─ 20-100ms (output buffering)

Result Retrieval      ├─ 30-80ms (network transfer)
                      └─ 20-70ms (parsing)

TOTAL: 400-900ms      └─ Typical: ~630ms
```

### Lightspeed SSH Phases:
```
OAuth Token           ├─ Reduced to ~1ms (cached)
(First request only)  └─ Expires hourly

Job Submission        ├─ 150-250ms (HTTP POST)
                      └─ 50-150ms (API processing)

Job Polling           ├─ 15,000ms (first 15s wait)
(Hardcoded 15s)       ├─ 100-200ms (HTTP GET)
                      ├─ 50ms per poll overhead
                      └─ Min 1 poll, max 60+ polls

Result Retrieval      ├─ 150-250ms (HTTP POST)
                      └─ 50-100ms (JSON parsing)

TOTAL: 15,300-16,500ms └─ Typical: ~15-60 seconds
```

---

## 📈 Performance Metrics by Use Case

| Use Case | Frequency | Regular SSH | Lightspeed SSH | Recommendation |
|----------|-----------|-----------|---------------|---|
| Quick check | 1x/day | 0.6s | 15s | Regular SSH |
| Automated tests | 100x/day | 60s total | 1500s total | Regular SSH |
| Device status | Every 5min | 3s/hr | 180s/hr | Regular SSH |
| Batch deploy | 1x/week | Varies (serial) | ~20s (parallel) | Lightspeed |
| Remote access | As needed | N/A (blocked) | 15s | Lightspeed |
| Compliance audit | Monthly | N/A | ✓ | Lightspeed |

---

## 🛠️ Implementation Examples

### Quick Test Setup

```bash
# Run performance comparison
python3 performance_comparison_ssh.py

# View results
cat ssh_performance_comparison_[timestamp].json
```

### Configure for Regular SSH
```python
from paramiko import SSHClient

ssh = SSHClient()
ssh.connect('device_ip', port=10022, username='root', password='password')
stdin, stdout, stderr = ssh.exec_command('command')
output = stdout.read().decode()
ssh.close()

# Expected: ~600ms total
```

### Configure for Lightspeed SSH
```python
import requests

# Submit job
response = requests.post('https://axiom-lightspeed.rdkops.comcast.net/revstbssh',
    headers={'Authorization': f'Bearer {token}'},
    data={
        'commands': 'cat /version.txt',
        'mac_array': '1C:2F:A2:30:35:B6',
        'ttls': '15'
    })
trace_id = response.text.replace('"', '')

# Poll for completion (15s minimum)
while True:
    status = requests.get(f'/checkStatus?trace_id={trace_id}')
    if status.json()['status'] == 'done':
        break
    time.sleep(15)

# Get results
results = requests.post(f'/previewMessage?trace_id={trace_id}')

# Expected: ~15-60s total
```

---

## ⚠️ Common Pitfalls

| Pitfall | Impact | Solution |
|---------|--------|----------|
| **Using Lightspeed for real-time ops** | 25x slower | Switch to Regular SSH |
| **Polling Lightspeed too frequently** | Rate limiting | Keep 15s interval minimum |
| **Token expiration** | 401 errors | Implement token refresh |
| **No connection pooling** | ~600ms per command | Reuse SSH connections |
| **Network latency > 200ms** | Impacts regular SSH | Use Lightspeed as backup |
| **Firewall rules not updated** | Regular SSH fails | Test connectivity first |

---

## 📋 Checklist: Choose Your SSH Method

**For Regular SSH:**
- [ ] Device is directly accessible (no NAT/VPN)
- [ ] Port 10022 (or 22) is open on device
- [ ] Network latency < 200ms
- [ ] Real-time operation critical
- [ ] Single or few devices
- [ ] No compliance audit trail needed

**For Lightspeed SSH:**
- [ ] Device is behind firewall
- [ ] Direct access not available
- [ ] Batch operations planned
- [ ] Audit trail required
- [ ] Using Comcast infrastructure
- [ ] Can tolerate 15s+ latency

---

## 🚀 Quick Start

1. **Determine accessibility:**
   ```bash
   # Can you SSH directly?
   ssh -p 10022 root@device_ip
   # If YES → Use Regular SSH
   # If NO → Use Lightspeed SSH
   ```

2. **Run comparison test:**
   ```bash
   python3 performance_comparison_ssh.py
   ```

3. **Review results:**
   - Check `ssh_performance_comparison_*.json`
   - Compare avg times for your environment

4. **Make decision:**
   - If latency matters: Regular SSH
   - If access is blocked: Lightspeed SSH
   - If unsure: Run both tests

---

## 📞 Support & References

- **Performance Test Script**: `performance_comparison_ssh.py`
- **Full Analysis**: `SSH_PERFORMANCE_COMPARISON.md`
- **Lightspeed API**: https://axiom-lightspeed.rdkops.comcast.net
- **Paramiko Docs**: https://www.paramiko.org/

---

*Last Updated: 2026-03-27*
*Quick Reference v1.0*
