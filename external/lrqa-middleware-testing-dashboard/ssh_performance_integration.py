#!/usr/bin/env python3
"""
Integration Examples: Measuring SSH Performance in Existing Code
Shows how to integrate performance metrics into the existing Flask application
"""

import time
import json
import logging
from datetime import datetime, timezone
from functools import wraps
from typing import Callable, Any, Dict

# ============================================================================
# 1. DECORATOR FOR MEASURING EXECUTION TIME
# ============================================================================

def measure_execution_time(ssh_method: str = "unknown"):
    """
    Decorator to measure and log SSH command execution time
    
    Usage:
        @measure_execution_time("Regular SSH - execute_command")
        def my_ssh_function():
            # code here
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            method_start_breakdown = {
                'func_name': func.__name__,
                'ssh_method': ssh_method,
                'start_time': datetime.now(timezone.utc).isoformat(),
                'start_timestamp': start_time
            }
            
            try:
                result = func(*args, **kwargs)
                elapsed_time = time.time() - start_time
                
                # Log performance metric
                logging.info(
                    f"[PERF] {ssh_method} - {func.__name__}: {elapsed_time:.3f}s",
                    extra={
                        'ssh_method': ssh_method,
                        'function': func.__name__,
                        'execution_time': elapsed_time,
                        'status': 'success'
                    }
                )
                
                return result
                
            except Exception as e:
                elapsed_time = time.time() - start_time
                logging.error(
                    f"[PERF] {ssh_method} - {func.__name__}: {elapsed_time:.3f}s (FAILED)",
                    extra={
                        'ssh_method': ssh_method,
                        'function': func.__name__,
                        'execution_time': elapsed_time,
                        'status': 'failed',
                        'error': str(e)
                    }
                )
                raise
        
        return wrapper
    return decorator


# ============================================================================
# 2. CONTEXT MANAGER FOR TIMING CODE BLOCKS
# ============================================================================

class SSHTimer:
    """Context manager for timing SSH operations"""
    
    def __init__(self, operation_name: str, ssh_method: str = "unknown", verbose: bool = True):
        self.operation_name = operation_name
        self.ssh_method = ssh_method
        self.verbose = verbose
        self.start_time = None
        self.elapsed_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        if self.verbose:
            logging.debug(f"[TIMER] Starting: {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed_time = time.time() - self.start_time
        status = "FAILED" if exc_type else "SUCCESS"
        
        if self.verbose:
            logging.info(
                f"[TIMER] {self.operation_name}: {self.elapsed_time:.3f}s ({status})",
                extra={
                    'operation': self.operation_name,
                    'ssh_method': self.ssh_method,
                    'execution_time': self.elapsed_time,
                    'status': status
                }
            )
        
        return False  # Don't suppress exceptions


# ============================================================================
# 3. INTEGRATION WITH EXISTING method_utils.py
# ============================================================================

def execute_ssh_command_with_timing(
    device_ip: str,
    command: str,
    port: int = 10022,
    username: str = "root",
    password: str = None,
    timeout: int = 30,
    log_callback: Callable = None,
    measure_time: bool = True
) -> Dict[str, Any]:
    """
    Enhanced SSH command execution with performance metrics
    
    Returns dict with:
        {
            'output': str,
            'error': str,
            'returncode': int,
            'timing': {
                'connection_time': float,
                'execution_time': float,
                'retrieval_time': float,
                'total_time': float
            }
        }
    """
    import paramiko
    
    result = {
        'output': '',
        'error': '',
        'returncode': -1,
        'timing': {
            'connection_time': 0,
            'execution_time': 0,
            'retrieval_time': 0,
            'total_time': 0
        }
    }
    
    total_start = time.time()
    
    try:
        # Measure connection time
        if measure_time:
            conn_start = time.time()
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(device_ip, port=port, username=username, password=password, timeout=timeout)
        
        if measure_time:
            result['timing']['connection_time'] = time.time() - conn_start
        
        # Measure command execution time
        if measure_time:
            exec_start = time.time()
        
        stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
        
        if measure_time:
            result['timing']['execution_time'] = time.time() - exec_start
        
        # Measure result retrieval time
        if measure_time:
            retr_start = time.time()
        
        result['output'] = stdout.read().decode('utf-8', errors='ignore').strip()
        result['error'] = stderr.read().decode('utf-8', errors='ignore').strip()
        result['returncode'] = stdout.channel.recv_exit_status()
        
        if measure_time:
            result['timing']['retrieval_time'] = time.time() - retr_start
        
        ssh.close()
        
        result['timing']['total_time'] = time.time() - total_start
        
        if log_callback and measure_time:
            log_callback(
                f"✓ SSH Command completed in {result['timing']['total_time']:.3f}s "
                f"(conn: {result['timing']['connection_time']:.3f}s, "
                f"exec: {result['timing']['execution_time']:.3f}s, "
                f"retr: {result['timing']['retrieval_time']:.3f}s)"
            )
        
        return result
        
    except Exception as e:
        result['timing']['total_time'] = time.time() - total_start
        result['error'] = str(e)
        
        if log_callback:
            log_callback(f"❌ SSH Command failed after {result['timing']['total_time']:.3f}s: {e}")
        
        raise


# ============================================================================
# 4. LIGHTSPEED SSH WITH TIMING
# ============================================================================

def execute_lightspeed_ssh_with_timing(
    command: str,
    mac_address: str,
    client_id: str,
    client_secret: str,
    log_callback: Callable = None,
    measure_time: bool = True
) -> Dict[str, Any]:
    """
    Enhanced Lightspeed SSH execution with performance metrics
    
    Returns dict with:
        {
            'output': str,
            'trace_id': str,
            'timing': {
                'auth_time': float,
                'submission_time': float,
                'polling_time': float,
                'retrieval_time': float,
                'total_time': float
            }
        }
    """
    import requests
    
    result = {
        'output': '',
        'trace_id': '',
        'timing': {
            'auth_time': 0,
            'submission_time': 0,
            'polling_time': 0,
            'retrieval_time': 0,
            'total_time': 0
        }
    }
    
    total_start = time.time()
    
    try:
        # Get OAuth token
        if measure_time:
            auth_start = time.time()
        
        token_headers = {
            'Content-Type': 'application/json',
            'X-Client-Id': client_id,
            'X-Client-Secret': client_secret
        }
        
        token_response = requests.post(
            "https://sat-stg.codebig2.net/v2/oauth/token",
            headers=token_headers,
            timeout=10
        )
        token = token_response.json()['access_token']
        
        if measure_time:
            result['timing']['auth_time'] = time.time() - auth_start
        
        # Submit job
        if measure_time:
            submit_start = time.time()
        
        headers = {'Authorization': f'Bearer {token}'}
        data = {
            "ttls": "15",
            "commands": command,
            "mac_array": mac_address,
            "region": "NA",
            "webpatimeout": 60,
            "criteria": "(?s)(.+)",
            "max_macs": 1,
            "slack": "automate-deploy-ops",
            "justification": "Performance Testing"
        }
        
        response = requests.post(
            "https://axiom-lightspeed.rdkops.comcast.net/revstbssh",
            headers=headers,
            data=data,
            timeout=60
        )
        
        result['trace_id'] = response.text.replace('"', '')
        
        if measure_time:
            result['timing']['submission_time'] = time.time() - submit_start
        
        # Poll for completion
        if measure_time:
            poll_start = time.time()
        
        import datetime as dt
        timeout_time = dt.datetime.now() + dt.timedelta(minutes=15)
        
        while dt.datetime.now() < timeout_time:
            status_response = requests.get(
                f"https://axiom-lightspeed.rdkops.comcast.net/checkStatus?trace_id={result['trace_id']}",
                headers=headers,
                timeout=30
            )
            
            if status_response.status_code == 200:
                status = status_response.json()
                if isinstance(status, dict) and status.get('status') == 'done':
                    break
            
            time.sleep(15)
        
        if measure_time:
            result['timing']['polling_time'] = time.time() - poll_start
        
        # Retrieve results
        if measure_time:
            retr_start = time.time()
        
        result_response = requests.post(
            f"https://axiom-lightspeed.rdkops.comcast.net/previewMessage?trace_id={result['trace_id']}",
            headers=headers,
            timeout=30
        )
        
        result['output'] = json.dumps(result_response.json(), indent=2)
        
        if measure_time:
            result['timing']['retrieval_time'] = time.time() - retr_start
        
        result['timing']['total_time'] = time.time() - total_start
        
        if log_callback and measure_time:
            log_callback(
                f"✓ Lightspeed SSH completed in {result['timing']['total_time']:.3f}s "
                f"(auth: {result['timing']['auth_time']:.3f}s, "
                f"submit: {result['timing']['submission_time']:.3f}s, "
                f"poll: {result['timing']['polling_time']:.3f}s, "
                f"retr: {result['timing']['retrieval_time']:.3f}s)"
            )
        
        return result
        
    except Exception as e:
        result['timing']['total_time'] = time.time() - total_start
        if log_callback:
            log_callback(f"❌ Lightspeed SSH failed after {result['timing']['total_time']:.3f}s: {e}")
        raise


# ============================================================================
# 5. COMPARISON IN CONTROLLER
# ============================================================================

def compare_ssh_methods_for_device(device_ip: str, command: str = "cat /version.txt"):
    """
    Compare both SSH methods for a single device
    Can be called from device controller
    """
    comparison_result = {
        'device_ip': device_ip,
        'command': command,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'regular_ssh': None,
        'lightspeed_ssh': None,
        'comparison': None
    }
    
    # Test Regular SSH
    try:
        result = execute_ssh_command_with_timing(
            device_ip,
            command,
            measure_time=True
        )
        comparison_result['regular_ssh'] = {
            'status': 'success',
            'timing': result['timing'],
            'output_length': len(result['output'])
        }
    except Exception as e:
        comparison_result['regular_ssh'] = {
            'status': 'failed',
            'error': str(e)
        }
    
    # Generate comparison summary
    regular_time = comparison_result['regular_ssh'].get('timing', {}).get('total_time')
    
    if regular_time:
        comparison_result['comparison'] = {
            'faster_method': 'Regular SSH',
            'notes': f'Regular SSH: {regular_time:.3f}s (direct connection)',
            'recommendation': 'Use Regular SSH for real-time operations' if regular_time < 1.0 else 'Check network latency'
        }
    
    return comparison_result


# ============================================================================
# 6. PERFORMANCE LOGGING SETUP
# ============================================================================

def setup_performance_logging():
    """
    Configure logging for SSH performance metrics
    Add to app.py initialization
    """
    import logging.handlers
    
    # Create performance logger
    perf_logger = logging.getLogger('ssh_performance')
    perf_logger.setLevel(logging.DEBUG)
    
    # File handler for performance metrics
    handler = logging.handlers.RotatingFileHandler(
        'logs/ssh_performance.log',
        maxBytes=10_000_000,  # 10MB
        backupCount=5
    )
    
    formatter = logging.Formatter(
        '%(asctime)s - %(ssh_method)s - %(function)s - %(execution_time).3fs - %(status)s'
    )
    
    handler.setFormatter(formatter)
    perf_logger.addHandler(handler)
    
    return perf_logger


# ============================================================================
# 7. USAGE EXAMPLES IN EXISTING CODE
# ============================================================================

# EXAMPLE 1: Using decorator in method_utils.py
"""
@measure_execution_time("Regular SSH - execute_command")
def execute_device_command(device_ip, command):
    # existing code
    ssh = paramiko.SSHClient()
    # ... rest of implementation
"""

# EXAMPLE 2: Using context manager in controller
"""
def reboot_device(device_ip):
    with SSHTimer("Device Reboot", "Regular SSH", verbose=True):
        result = execute_ssh_command_with_timing(
            device_ip,
            "reboot"
        )
    return result
"""

# EXAMPLE 3: Using both methods for comparison
"""
def diagnose_device_connection(device_ip):
    metrics = {
        'regular_ssh': None,
        'device_ip': device_ip,
        'timestamp': datetime.now().isoformat()
    }
    
    with SSHTimer("SSH Connectivity Test", "Regular SSH"):
        metrics['regular_ssh'] = execute_ssh_command_with_timing(
            device_ip,
            "echo 'OK'",
            measure_time=True
        )
    
    return metrics
"""


# ============================================================================
# 8. EXAMPLE: INTEGRATION IN log_service.py
# ============================================================================

def stream_logs_with_performance_metrics(device_ip: str, log_callback: Callable):
    """
    Example of how to integrate timing into existing log_service.py
    """
    
    with SSHTimer("Log Stream Collection", "Regular SSH") as timer:
        result = execute_ssh_command_with_timing(
            device_ip,
            "tail -n 100 /var/log/messages",
            log_callback=log_callback,
            measure_time=True
        )
    
    # Log the performance metrics
    log_callback(f"Log retrieval metrics: {json.dumps(result['timing'], indent=2)}")
    
    return result['output']


# ============================================================================
# 9. MIGRATION GUIDE
# ============================================================================

"""
TO INTEGRATE INTO EXISTING CODEBASE:

1. Add to method_utils.py:
   - Import the timer classes/decorators from this file
   - Wrap existing SSH functions with @measure_execution_time decorator
   - Or use SSHTimer context manager around SSH blocks

2. Update device_controller.py:
   - Replace raw paramiko calls with execute_ssh_command_with_timing()
   - This maintains backward compatibility while adding metrics

3. Add performance logging:
   - Setup performance logger in app.py: setup_performance_logging()
   - Logs automatically captured in logs/ssh_performance.log

4. Example minimal change:
   BEFORE:
       stdin, stdout, stderr = ssh.exec_command(command)
       output = stdout.read()
   
   AFTER:
       result = execute_ssh_command_with_timing(device_ip, command, measure_time=True)
       output = result['output']
       logging.info(f"Execution took {result['timing']['total_time']:.3f}s")

5. Monitor performance:
   - Check logs/ssh_performance.log for per-command metrics
   - Look for commands taking > 5 seconds
   - Identify bottlenecks and optimize
"""


if __name__ == "__main__":
    # Example usage
    print("SSH Performance Integration Examples")
    print("=" * 80)
    print("""
This module provides ready-to-use timing functions for SSH operations.

Key functions:
1. measure_execution_time() - Decorator for automatic timing
2. SSHTimer - Context manager for manual timing
3. execute_ssh_command_with_timing() - Enhanced regular SSH with metrics
4. execute_lightspeed_ssh_with_timing() - Enhanced Lightspeed SSH with metrics

Integration examples are provided in the comments above.

For full integration guide, see SSH_PERFORMANCE_COMPARISON.md
    """)
