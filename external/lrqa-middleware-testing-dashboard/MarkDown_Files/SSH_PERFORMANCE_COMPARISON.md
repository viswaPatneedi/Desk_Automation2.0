# SSH Performance Comparison: Regular SSH vs Lightspeed SSH

## Executive Summary

This document provides a comprehensive analysis of execution time differences between:
- **Regular SSH (Paramiko)**: Direct device SSH connection via Paramiko library
- **Lightspeed SSH**: Cloud-based SSH service (RDK Lightspeed/RevSTB SSH)

## Key Performance Metrics

### Expected Execution Times

#### Regular SSH (Paramiko - Direct Connection)
| Metric | Typical Time | Notes |
|--------|-------------|-------|
| **Connection Time** | 200-500ms | Paramiko handshake + authentication |
| **Command Execution** | 100-300ms | Command runs directly on device |
| **Result Retrieval** | 50-150ms | Reading stdout/stderr |
| **TOTAL** | 350-950ms | ~0.5-1.0 seconds typical |

#### Lightspeed SSH (Cloud-Based)
| Metric | Typical Time | Notes |
|--------|-------------|-------|
| **OAuth Token Retrieval** | 500-1000ms | First request only, cached after |
| **Job Submission** | 200-400ms | HTTP request to Lightspeed API |
| **Job Polling** | 15-60+ seconds | Waits in 15s intervals for completion |
| **Result Retrieval** | 100-300ms | HTTP request to fetch results |
| **TOTAL** | 15-60+ seconds | Dominated by job polling |

### Performance Comparison

```
Regular SSH:      ~0.5-1.0 seconds
Lightspeed SSH:   ~15-60+ seconds

Speed Ratio:      Lightspeed is ~15-100x SLOWER
```

## Detailed Breakdown

### 1. Regular SSH (Paramiko) - How It Works

```
User Request
    ↓
Establish TCP Connection to Device (200-500ms)
    ↓
SSH Handshake & Authentication (100-300ms)
    ↓
Execute Command (100-300ms)
    ↓
Retrieve Results (50-150ms)
    ↓
Close Connection
    ↓
TOTAL: ~500ms - 1 second
```

**Advantages:**
- ✅ Direct connection = minimal latency
- ✅ Synchronous execution = simple, predictable timing
- ✅ No polling overhead
- ✅ Works anywhere with network access
- ✅ Low infrastructure cost

**Disadvantages:**
- ❌ Requires direct network access to device
- ❌ Firewall restrictions may block SSH (port 22, 10022)
- ❌ No centralized logging/monitoring
- ❌ Single device at a time

### 2. Lightspeed SSH - How It Works

```
User Request
    ↓
Get OAuth Token (~500-1000ms on first request)
    ↓
Submit Job to Lightspeed API (~200-400ms)
    ↓
Poll for Job Status Every 15 Seconds (~15-60+ seconds)
    ├─ Request 1: Still pending (15s delay)
    ├─ Request 2: Still pending (15s delay)
    ├─ Request 3: Still pending (15s delay)
    └─ Request N: Complete
    ↓
Retrieve Results (~100-300ms)
    ↓
TOTAL: ~15-60+ seconds (dominated by polling delays)
```

**Advantages:**
- ✅ No direct device connectivity required
- ✅ Works through firewalls/proxies
- ✅ Centralized cloud service
- ✅ Batch execution (multiple devices)
- ✅ Audit trail & compliance logging
- ✅ Xfinity/Comcast infrastructure

**Disadvantages:**
- ❌ Asynchronous polling = high latency (~15s minimum per job)
- ❌ Network round trips every 15 seconds
- ❌ OAuth token overhead
- ❌ Service availability dependency
- ❌ Rate limiting on API calls
- ❌ 15-minute job timeout window

## Execution Time Analysis

### Scenario 1: Simple Command (cat /version.txt)

**Regular SSH:**
```
Connection:    350ms (establish SSH to device)
Execution:     150ms (run command and capture output)
Retrieval:      80ms (read result)
─────────────────────
Total:         ~580ms
```

**Lightspeed SSH:**
```
Auth token:    750ms (OAuth token request - cached after)
Job submit:    250ms (POST to /revstbssh)
Job polling:  15000ms (1 poll cycle minimum - 15s default)
Retrieval:     200ms (GET /previewMessage)
─────────────────────
Total:         ~16,200ms (16.2 seconds)
```

**Performance Ratio: 16.2s ÷ 0.58s = ~28x slower**

### Scenario 2: Multiple Polling Cycles

If the job doesn't complete in first 15-second interval:

```
Cycle 1 (15s):  Submitted, checking status...
Cycle 2 (30s):  Still processing...
Cycle 3 (45s):  Still processing...
Cycle 4 (60s):  Complete!

Total: ~60+ seconds
```

**Performance Ratio: 60s ÷ 0.58s = ~103x slower**

## Real-World Impact

| Use Case | Regular SSH | Lightspeed SSH | When to Use |
|----------|-------------|----------------|------------|
| **Quick Device Check** | ~1s | ~15s | ✓ Regular SSH |
| **Batch Device Commands** | N×1s | ~15s (parallel) | ✓ Lightspeed |
| **Interactive Testing** | ~1s | ~15s | ✓ Regular SSH |
| **Remote Access (Firewall)** | ❌ Blocked | ✓ Works | ✓ Lightspeed |
| **Automated Test Suite** | ~1s per test | Cumulative latency | ✓ Regular SSH |
| **Compliance Audit Trail** | None | ✓ Built-in | ✓ Lightspeed |

## Why Lightspeed is Slower

1. **Asynchronous Polling Model**: Jobs are queued and polled, not executed immediately
2. **15-Second Polling Interval**: Hardcoded wait between status checks (minimum 15s latency)
3. **Network Round Trips**: Each poll requires HTTP request/response cycle
4. **Job Queue Processing**: Jobs may wait in queue before execution
5. **OAuth Overhead**: Token retrieval adds 500-1000ms (first request)
6. **No Persistent Connection**: Each operation requires new HTTP request

## When to Use Each Method

### Use Regular SSH When:
- ✅ Low latency is critical
- ✅ Real-time command execution needed
- ✅ Direct network access available
- ✅ Device firewalls allow SSH traffic
- ✅ Single or small batch of devices
- ✅ Testing/development environment
- ✅ Cost is primary concern

### Use Lightspeed SSH When:
- ✅ Devices are behind restrictive firewalls
- ✅ Batch/parallel execution needed (multiple devices simultaneously)
- ✅ Audit trail & compliance logging required
- ✅ No direct network access to devices
- ✅ Cloud-based infrastructure preferred
- ✅ Centralized management needed
- ✅ Xfinity/Comcast internal use
- ✅ High availability/failover required

## Performance Tuning Recommendations

### For Regular SSH:
```python
# Optimize connection pooling
ssh.get_transport().set_keepalive(30)  # Keep connection alive
# Batch commands to reduce connection overhead
ssh_connection.exec_command("cmd1 && cmd2 && cmd3")
# Increase timeout for slow networks
ssh.connect(host, timeout=15)
```

### For Lightspeed SSH:
```python
# Token caching (already done in implementation)
# reduces first request overhead

# Batch multiple devices in single job
data = {
    "mac_array": "MAC1,MAC2,MAC3",  # Multiple MACs
    "max_macs": 20
}

# Reduce polling frequency (if service allows)
# Currently hardcoded to 15s, consider service limits

# Use bulk API if available for better pricing
```

## Benchmark Results Template

Run `performance_comparison_ssh.py` to generate actual metrics:

```
Regular SSH (Paramiko) - Direct Connection
─────────────────────────────────────────
Success Rate: 5/5 (100%)
Min Time:     0.521s
Max Time:     0.847s
Average Time: 0.634s
Std Dev:      0.123s
Total Time:   3.172s

Lightspeed SSH - Cloud-Based SSH
─────────────────────────────────
Success Rate: 5/5 (100%)
Min Time:     15.234s
Max Time:     60.156s
Average Time: 31.245s
Std Dev:      18.456s
Total Time:   156.229s

Comparison
──────────
Faster Method:          Regular SSH
Time Difference:        30.611s
Performance Ratio:      49.27x (Lightspeed is 49x slower)
Lightspeed Overhead:    +4827% slower
```

## Conclusion

**Regular SSH is 15-100x faster than Lightspeed SSH**, primarily due to:
1. Direct connection vs. asynchronous polling
2. No 15-second polling delay
3. Synchronous execution model
4. No job queue processing

**Choose based on requirements:**
- **Performance-critical**: Use Regular SSH
- **Firewall/Security**: Use Lightspeed SSH
- **Both needed**: Implement dual-path with fallback

## References

- [Lightspeed SSH API Documentation](https://axiom-lightspeed.rdkops.comcast.net)
- [Paramiko Documentation](https://www.paramiko.org/)
- [SSH Performance Best Practices](https://linux.die.net/man/5/ssh_config)

---

*Last Updated: 2026-03-27*
*Test Script: `performance_comparison_ssh.py`*
