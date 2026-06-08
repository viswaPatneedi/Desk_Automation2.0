# Log Pattern Management - Integration Guide

## For Developers

### How to Use Log Patterns in Your Code

#### 1. Basic Pattern Lookup

```python
from config_log_patterns import get_log_pattern, get_log_file_path

# Get pattern and file
pattern = get_log_pattern('HOME')
file_path = get_log_file_path('HOME')

if pattern and file_path:
    # Build your command
    command = f"grep -E \"{pattern}\" {file_path}"
```

#### 2. Build Log Check Commands

```python
from config_log_patterns import build_log_check_command

# Get complete grep command
command = build_log_check_command('HOME')
# Returns: "grep -E 'QMS Bookmark.*HOME_TILES.*load.*complete' /opt/logs/sky-messages.log"

# Execute it
result = execute_ssh_command(device_ip, command)
if result:
    log_data['home_screen'] = 'FOUND'
```

#### 3. Get All Available Patterns

```python
from config_log_patterns import get_all_approved_pattern_names

# List all pattern names
patterns = get_all_approved_pattern_names()
# Returns: ['HOME', 'Network_Error', 'Process_Crash']

for pattern_name in patterns:
    print(f"- {pattern_name}")
```

#### 4. Get Patterns with Full Details

```python
from config_log_patterns import get_all_patterns_with_commands

# Get all patterns with their commands
all_patterns = get_all_patterns_with_commands()

for name, details in all_patterns.items():
    print(f"\n{name}:")
    print(f"  Command: {details['command']}")
    print(f"  Description: {details['description']}")
    print(f"  File: {details['file_path']}")
```

#### 5. Use with Legacy Patterns (Backward Compatibility)

```python
from config_log_patterns import merge_approved_with_legacy_checks

# Get all checks (old + new)
all_checks = merge_approved_with_legacy_checks()

# Now you have both:
# - Legacy hardcoded patterns (HOME, Network_Error, etc.)
# - New user-submitted patterns
# - New patterns take precedence if names conflict
```

---

## Integration with Device Methods

### Example: Reboot Performance Check

```python
# method_reboot_performance_v2.py
from config_log_patterns import build_log_check_command, get_all_patterns_with_commands

def check_post_reboot_logs(device_ip, pattern_names):
    """
    Check logs for specific patterns after reboot
    
    Args:
        device_ip: Target device
        pattern_names: List of pattern names to check (e.g., ['HOME', 'Network_Error'])
    
    Returns:
        dict: Results for each pattern
    """
    results = {}
    
    for pattern_name in pattern_names:
        command = build_log_check_command(pattern_name)
        
        if not command:
            results[pattern_name] = 'NOT_FOUND'
            continue
        
        # Execute the check command
        output = execute_ssh_command(device_ip, command)
        
        # Store result
        results[pattern_name] = 'FOUND' if output else 'NOT_FOUND'
    
    return results
```

### Example: Dynamic Test Selection

```python
# Get available patterns for UI dropdown
from config_log_patterns import get_all_patterns_with_commands

def get_available_checks():
    """Get all available log checks for UI selection"""
    patterns = get_all_patterns_with_commands()
    
    checks = []
    for name, details in patterns.items():
        checks.append({
            'id': name,
            'label': name.replace('_', ' ').title(),
            'description': details['description'],
            'file': details['file_path']
        })
    
    return sorted(checks, key=lambda x: x['label'])
```

---

## Integration with Test Execution Service

### In test_execution_service.py

```python
from config_log_patterns import merge_approved_with_legacy_checks

class TestExecutionService:
    @staticmethod
    def get_available_post_reboot_checks():
        """
        Get all available optional post-reboot checks
        Automatically includes both legacy and new user-submitted patterns
        """
        # Merge legacy and new patterns
        all_checks = merge_approved_with_legacy_checks()
        
        # Format for UI
        formatted = {}
        for name, details in all_checks.items():
            formatted[name] = {
                'command': details['command'],
                'description': details['description']
            }
        
        return formatted
    
    @staticmethod
    def execute_post_reboot_check(device, check_name):
        """Execute a specific post-reboot check"""
        from config_log_patterns import build_log_check_command
        
        command = build_log_check_command(check_name)
        if not command:
            return {'status': 'NOT_FOUND', 'check': check_name}
        
        # Execute and return result
        try:
            output = device.execute_command(command)
            return {
                'status': 'SUCCESS',
                'check': check_name,
                'output': output,
                'found': bool(output)
            }
        except Exception as e:
            return {
                'status': 'ERROR',
                'check': check_name,
                'error': str(e)
            }
```

---

## Integration with Web UI

### In templates/test_selection.html

```html
<!-- Dynamic Pattern Dropdown -->
<div class="form-group">
    <label for="patternCheck">Post-Reboot Check:</label>
    <select id="patternCheck" multiple>
        <!-- Options populated by JavaScript -->
    </select>
</div>

<script>
// Load available patterns when page loads
fetch('/api/log-patterns/approved')
    .then(r => r.json())
    .then(data => {
        const select = document.getElementById('patternCheck');
        const patterns = data.data;
        
        for (const [name, details] of Object.entries(patterns)) {
            const option = document.createElement('option');
            option.value = name;
            option.textContent = `${name}: ${details.description}`;
            option.title = `Pattern: ${details.log_pattern}`;
            select.appendChild(option);
        }
    });

// Execute selected checks
async function executeSelectedChecks() {
    const select = document.getElementById('patternCheck');
    const selectedPatterns = Array.from(select.selectedOptions).map(o => o.value);
    
    for (const pattern of selectedPatterns) {
        const response = await fetch('/api/execute-pattern-check', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                device_ip: currentDevice,
                pattern_name: pattern
            })
        });
        
        const result = await response.json();
        displayResult(pattern, result);
    }
}
</script>
```

---

## Database/Storage Integration (Future)

If migrating to database, patterns are stored as:

```python
class LogPattern(Base):
    __tablename__ = 'log_patterns'
    
    id = Column(String, primary_key=True)
    pattern_name = Column(String, unique=True, nullable=False)
    log_pattern = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    description = Column(String)
    submitted_by = Column(String, ForeignKey('user.user_id'))
    submitted_at = Column(DateTime, default=datetime.utcnow)
    is_admin_submission = Column(Boolean, default=False)
    status = Column(Enum(PatternStatus), default=PatternStatus.APPROVED)  # APPROVED, PENDING, REJECTED
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
```

---

## Performance Optimization

### Caching Patterns

```python
from functools import lru_cache
import time

class PatternCache:
    _cache = None
    _cache_time = None
    _cache_ttl = 300  # 5 minutes
    
    @classmethod
    def get_patterns(cls, force_refresh=False):
        """Get patterns with caching"""
        now = time.time()
        
        if force_refresh or not cls._cache or (now - cls._cache_time) > cls._cache_ttl:
            # Reload from disk
            from config_log_patterns import load_approved_patterns
            cls._cache = load_approved_patterns()
            cls._cache_time = now
        
        return cls._cache

# Usage
patterns = PatternCache.get_patterns()
# Reload: patterns = PatternCache.get_patterns(force_refresh=True)
```

### Batch Operations

```python
def execute_multiple_checks(device_ip, pattern_names):
    """Execute multiple pattern checks efficiently"""
    from config_log_patterns import build_log_check_command
    
    results = {}
    
    # Build all commands first
    commands = {}
    for name in pattern_names:
        cmd = build_log_check_command(name)
        if cmd:
            commands[name] = cmd
    
    # Execute all at once
    combined_command = ' && '.join(
        f'echo "CHECK:{name}:" && {cmd}'
        for name, cmd in commands.items()
    )
    
    output = execute_ssh_command(device_ip, combined_command)
    
    # Parse results
    return parse_batch_output(output)
```

---

## Monitoring and Logging

### Pattern Usage Analytics

```python
class PatternAnalytics:
    @staticmethod
    def log_pattern_use(pattern_name, device_ip, result, execution_time):
        """Log pattern usage for analytics"""
        import json
        from datetime import datetime
        
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'pattern': pattern_name,
            'device': device_ip,
            'result': result,
            'execution_time_ms': execution_time
        }
        
        # Append to analytics log
        with open('logs/pattern_analytics.log', 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    @staticmethod
    def get_pattern_stats(pattern_name, days=7):
        """Get usage stats for a pattern"""
        import json
        from datetime import datetime, timedelta
        
        stats = {
            'total_uses': 0,
            'successful': 0,
            'failed': 0,
            'avg_execution_time': 0
        }
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        with open('logs/pattern_analytics.log', 'r') as f:
            for line in f:
                entry = json.loads(line)
                if entry['pattern'] != pattern_name:
                    continue
                if datetime.fromisoformat(entry['timestamp']) < cutoff:
                    continue
                
                stats['total_uses'] += 1
                if entry['result'] == 'FOUND':
                    stats['successful'] += 1
                else:
                    stats['failed'] += 1
        
        return stats
```

---

## Error Handling

### Graceful Fallback

```python
def execute_pattern_check_safe(device_ip, pattern_name):
    """Execute pattern check with fallback"""
    try:
        from config_log_patterns import build_log_check_command
        
        command = build_log_check_command(pattern_name)
        if not command:
            # Pattern not found, try legacy pattern
            if pattern_name == 'HOME':
                from config_log_patterns import log_check_command_HOME
                command = log_check_command_HOME
        
        if not command:
            return {'error': 'Pattern not found', 'pattern': pattern_name}
        
        output = execute_ssh_command(device_ip, command)
        return {'success': True, 'found': bool(output)}
        
    except FileNotFoundError as e:
        return {'error': 'Log file not found', 'details': str(e)}
    except Exception as e:
        return {'error': 'Execution failed', 'details': str(e)}
```

---

## Testing Patterns

### Unit Tests

```python
import pytest
from config_log_patterns import (
    load_approved_patterns,
    build_log_check_command,
    validate_log_pattern
)

def test_load_approved_patterns():
    patterns = load_approved_patterns()
    assert isinstance(patterns, dict)
    assert 'HOME' in patterns

def test_build_log_check_command():
    cmd = build_log_check_command('HOME')
    assert cmd is not None
    assert 'grep' in cmd
    assert '/opt/logs/sky-messages.log' in cmd

def test_build_nonexistent_pattern():
    cmd = build_log_check_command('NONEXISTENT')
    assert cmd is None
```

### Integration Tests

```python
def test_end_to_end_pattern_workflow(client, admin_user):
    # Submit pattern (as user)
    response = client.post('/api/log-patterns/submit', json={
        'pattern_name': 'TEST_PATTERN',
        'log_pattern': 'test.*',
        'file_path': '/opt/logs/sky-messages.log',
        'description': 'Test'
    })
    assert response.status_code == 200
    
    # Approve pattern (as admin)
    submission_id = response.json['submission_id']
    response = client.post(f'/api/log-patterns/{submission_id}/approve')
    assert response.status_code == 200
    
    # Use pattern
    from config_log_patterns import build_log_check_command
    cmd = build_log_check_command('TEST_PATTERN')
    assert cmd is not None
    assert 'test.*' in cmd
```

---

## Migration Checklist

When integrating into existing code:

- [ ] Import `build_log_check_command` instead of hardcoding patterns
- [ ] Replace hardcoded file paths with `get_log_file_path()`
- [ ] Update UI to use `/api/log-patterns/approved` endpoint
- [ ] Test backward compatibility with legacy patterns
- [ ] Update documentation with pattern names
- [ ] Create pre-approved patterns for common checks
- [ ] Set up admin user to manage patterns
- [ ] Monitor log file paths for changes
- [ ] Back up `log_pattern_submissions.json` before updates
- [ ] Test pattern validation on target device

---

## Troubleshooting Integration

### Pattern Not Found at Runtime

```python
from config_log_patterns import build_log_check_command

cmd = build_log_check_command('HOME')
if cmd is None:
    print(f"Pattern 'HOME' not in approved patterns")
    print("Check if pattern name is correct")
    print("Check if log_pattern_submissions.json exists")
```

### Command Execution Fails

```python
# Verify pattern format
from config_log_patterns import get_log_pattern, get_log_file_path

pattern = get_log_pattern('HOME')
file = get_log_file_path('HOME')

# Test locally first
import subprocess
cmd = f"grep -E '{pattern}' {file}"
result = subprocess.run(cmd, shell=True, capture_output=True)
```

---

## Support and Resources

- **Controller**: `controllers/log_pattern_controller.py`
- **Config**: `config_log_patterns.py`
- **UI**: `templates/log_patterns.html`
- **Docs**: `LOG_PATTERN_MANAGEMENT.md`
- **API**: `LOG_PATTERN_API.md`

---

Last Updated: January 21, 2026
