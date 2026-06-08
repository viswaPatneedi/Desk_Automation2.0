# Quick Reference - Interactive Log Collection

## Feature Overview
When HOME screen is detected during reboot test, system prompts: "Collect device logs for this iteration? (yes/no)"

## Quick Start

### For Interactive Sessions
```
🔍 Log Line Found! Collect device logs for this iteration? (yes/no): yes
✓ Device logs successfully collected in /media/app
  File: /media/app/10.0.0.250_ELEMENT-A4K-DESK_ITR-42_logs_20260201_143025.tar.gz
```

### For Automated Sessions
- System automatically skips if no interactive terminal
- Test continues without delay
- No configuration needed

## Command Reference

### View collected logs on device
```bash
ssh root@[device_ip]
ls -lh /media/app/*.tar.gz
```

### Extract and view logs
```bash
cd /media/app
tar -tzf 10.0.0.250_ELEMENT-A4K-DESK_ITR-42_logs_20260201_143025.tar.gz | head -20
tar -xzf 10.0.0.250_ELEMENT-A4K-DESK_ITR-42_logs_20260201_143025.tar.gz
```

### Download logs to local machine
```bash
sftp root@[device_ip]
cd /media/app
get *.tar.gz
```

## File Naming Convention
```
/media/app/{ip}_{device_name}_ITR-{iteration}_logs_{timestamp}.tar.gz
```

Example:
- IP: `10.0.0.250`
- Device: `ELEMENT-A4K-DESK`
- Iteration: `42`
- Timestamp: `20260201_143025`

**Result**: `/media/app/10.0.0.250_ELEMENT-A4K-DESK_ITR-42_logs_20260201_143025.tar.gz`

## Response Options

| Input | Action |
|-------|--------|
| `yes` or `y` | Collect logs to /media/app |
| `no` or `n` | Skip log collection |
| Other | Re-prompt with error message |
| Timeout/No input | Skip (automated mode) |

## Log Contents
Archive includes all files from `/opt/logs/`:
- System logs
- Application logs  
- Crash dumps
- Performance data
- Device messages

## Typical Usage Flow

```
1. Test execution starts
2. Device reboots
3. HOME screen detected ✓
4. Prompt appears: "Collect device logs? (yes/no)"
5a. If YES:
    → Logs collected
    → Archive created in /media/app
    → File path displayed
    → Test continues
5b. If NO:
    → Test continues immediately
    → No additional storage used
6. Test continues to next steps
```

## Integration Point
- **Step**: 4.5 (after HOME detection, before performance calculation)
- **Method**: Reboot Performance V2 - Optimized
- **File**: `method_reboot_perf_v2_optimized.py`

## Features
✓ Interactive decision making  
✓ Selective log capture  
✓ Organized file naming  
✓ Automatic directory creation  
✓ File verification  
✓ Non-blocking operation  
✓ Graceful error handling  

## Storage Location
- **Device**: `/media/app/`
- **Archive Format**: `.tar.gz` (compressed)
- **Typical Size**: 50-200 MB per iteration
- **Access Method**: SSH/SFTP

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Prompt not showing | Running in automated mode - normal behavior |
| Archive creation fails | Check `/media/app` permissions and disk space |
| Input not recognized | Use 'yes', 'no', 'y', or 'n' (case-insensitive) |
| SSH connection lost | Test will continue without log collection |

## Related Documentation
- Full details: `INTERACTIVE_LOG_COLLECTION_FEATURE.md`
- Method guide: `REBOOT_PERF_V2_OPTIMIZED_GUIDE.md`
- Device logs: `DEVICE_LOGS_ORGANIZATION.md`

