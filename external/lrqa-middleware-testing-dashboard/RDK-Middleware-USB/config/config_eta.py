"""
Configuration for method execution time estimates (in seconds).
These values are used to calculate ETAs for device availability.
"""

# Base execution times for each method (in seconds)
METHOD_EXECUTION_TIMES = {
    'reboot': 145,  # Reboot with BEFORE/AFTER screenshots + screen validation: 25s BEFORE + 100s reboot + 15s AFTER (fast success) + 5s validation
    'reboot_performance': 280,  # Reboot performance monitoring: 25s BEFORE + 85s wait + 165s monitoring + 5s overhead
    'reboot_performance_v2': 305,  # Enhanced reboot with optional checks: 25s BEFORE + 85s fixed wait + 165s monitoring + 20s AFTER + 10s validation
    'reboot_perf_v2_optimized': 180,  # Optimized reboot (37.9% faster): 10s wait + 40s SSH probe + 110s monitoring + 20s checks
    'soft_hard_boot': 271,  # Soft/Hard boot test: ~79-82s per boot cycle + 3-5s overhead per iteration
    'trail_method': 85,  # Trail method (reboot performance optimized variant): Similar to soft_hard_boot, ~79-82s per boot
    'screenshot': 25,  # Screenshot with full verification: 3s activation + 10s capture + 7s verify + 5s download (fast success)
    'ir_test': 15,  # 15 seconds per IR command test (including waits)
    'voice_command': 35,  # 35 seconds for voice command execution (20s wait + command + validation)
    'deepsleep': 245,  # Deep sleep: 25s BEFORE screenshot + 60s sleep + 100s wake + 20s AFTER screenshot (fast success) + 40s validation
    'maintenance_deepsleep_wakeup': 4500,  # Maintenance + DeepSleep + Wakeup: 50m maintenance (3000s) + 22.5m deepsleep phases (1500s base) = 72.5m (NOTE: Actual varies with sleep_duration_minutes parameter)
    'status': 10,  # 10 seconds for status check
    'log_collection': 30,  # 30 seconds for log collection
    'power_key': 30,  # 30 seconds for power key press
    'send_remote_keys': 20,  # 20 seconds for sending remote keys (base + time per key)
    'screen_validation': 25,  # 25 seconds for screen validation: screenshot capture + verification + OCR + comparison (fast success)
    'navigate_inputs_xumo': 180,  # 3 minutes for XUMO input validation: 5s navigation to inputs + 8s per tile (8 tiles) + 40s screen detection/validation + 20s log collection (if missing)
    'xumo_activation': 180,  # 3 minutes for XUMO activation (fetch code + enter + validation)
    'capture_base_image': 25,  # 25 seconds to capture and save base image with full verification (fast success)
    'validate_results': 20,  # 20 seconds for command execution and output validation
    'wait': 0,  # Wait time is dynamic based on user input
}

# Explicit waits for maintenance and IR key sending
MAINTENANCE_WAIT_AFTER_REBOOT = 900  # 15 minutes (900s) for maintenance tasks after reboot
PRE_IR_WAIT_DEEPSLEEP = 600          # 10 min before IR in deepsleep

# Additional time overhead
OVERHEAD_PER_ITERATION = 10  # 10 seconds overhead per iteration (for logging, status updates)
SETUP_TEARDOWN_TIME = 15  # 15 seconds for setup and teardown

# Wait times between operations
WAIT_AFTER_REBOOT = 0  # Already included in reboot method time
WAIT_BETWEEN_COMMANDS = 3  # 3 seconds between IR/voice commands


def calculate_eta(execution_queue, iterations=1):
    """
    Calculate estimated time for test execution in seconds.
    
    Args:
        execution_queue: List of {method, ir_keys, voice_text, remote_keys, wait_seconds, etc.} objects
        iterations: Number of iterations to run
    
    Returns:
        Estimated time in seconds
    """
    if not execution_queue:
        return 0
    
    total_time = SETUP_TEARDOWN_TIME
    
    # Check if deepsleep is in the execution queue
    has_deepsleep = any(item.get('method') == 'deepsleep' for item in execution_queue)

    for i in range(iterations):
        for queue_item in execution_queue:
            method = queue_item.get('method', '')
            method_time = METHOD_EXECUTION_TIMES.get(method, 20)

            # Adjust for IR keys count (handle both ir_keys and irKeys for backward compatibility)
            ir_keys = queue_item.get('ir_keys') or queue_item.get('irKeys') or []
            if method == 'ir_test' and ir_keys:
                ir_keys_count = len(ir_keys)
                method_time = method_time * ir_keys_count + (WAIT_BETWEEN_COMMANDS * ir_keys_count)
            
            # Adjust for remote keys (count comma-separated keys)
            remote_keys = queue_item.get('remote_keys') or queue_item.get('remoteKeys') or ''
            if method == 'send_remote_keys' and remote_keys:
                keys_count = len(remote_keys.split(','))
                method_time = 5 * keys_count + (WAIT_BETWEEN_COMMANDS * keys_count)  # 5s per key
            
            # Dynamic wait time
            wait_seconds = queue_item.get('wait_seconds') or queue_item.get('waitSeconds')
            if method == 'wait' and wait_seconds:
                method_time = int(wait_seconds)

            # System command duration (TOP sampling or long-running commands)
            if method == 'system_command':
                duration_seconds = queue_item.get('duration_seconds') or queue_item.get('durationSeconds') or 0
                try:
                    duration_seconds = int(duration_seconds)
                except Exception:
                    duration_seconds = 0
                if duration_seconds > 0:
                    method_time = duration_seconds

            # Handle maintenance_deepsleep_wakeup with parameter-based ETA calculation
            if method == 'maintenance_deepsleep_wakeup':
                # Extract parameters from queue_item
                params = queue_item.get('params') or {}
                execute_deepsleep_wakeup = params.get('execute_deepsleep_wakeup') if params else queue_item.get('execute_deepsleep_wakeup')
                if execute_deepsleep_wakeup is None:
                    execute_deepsleep_wakeup = True  # Default is True
                
                sleep_duration_minutes = params.get('sleep_duration_minutes') if params else queue_item.get('sleep_duration_minutes')
                if sleep_duration_minutes is None:
                    sleep_duration_minutes = 13  # Default 13 minutes for maintenance_deepsleep_wakeup
                
                try:
                    sleep_duration_minutes = int(sleep_duration_minutes)
                except (ValueError, TypeError):
                    sleep_duration_minutes = 13
                
                # Calculate ETA based on configuration
                if not execute_deepsleep_wakeup:
                    # Maintenance only (steps 1-7): ~50 minutes
                    method_time = 3000
                else:
                    # Full workflow (steps 1-12):
                    # Calculate based on ACTUAL observed execution times from job runs:
                    # - Maintenance setup & checks: 180s (3 min)
                    # - Device reboot after maintenance: 120s (2 min)
                    # - Sleep duration: user-provided (from parameter)
                    # - Wakeup detection & verification: 180s (3 min)
                    # - Safety buffer: 300s (5 min)
                    maintenance_work = 180  # 3 min for setup
                    reboot_time = 120    # 2 min for reboot
                    sleep_time = sleep_duration_minutes * 60  # User-provided sleep duration in seconds
                    wakeup_time = 180    # 3 min for wakeup detection
                    buffer = 300         # 5 min safety buffer
                    method_time = maintenance_work + reboot_time + sleep_time + wakeup_time + buffer
            
            # Add maintenance wait only if deepsleep is in the execution queue
            if method == 'reboot' and has_deepsleep:
                method_time += MAINTENANCE_WAIT_AFTER_REBOOT
            
            # Add pre-IR wait for deepsleep
            if method == 'deepsleep':
                method_time += PRE_IR_WAIT_DEEPSLEEP

            total_time += method_time
        total_time += OVERHEAD_PER_ITERATION

    return int(total_time)




def format_eta(seconds):
    """
    Format ETA in human-readable format.
    
    Args:
        seconds: Number of seconds
    
    Returns:
        Formatted string like "2m 30s" or "1h 15m"
    """
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        if remaining_seconds > 0:
            return f"{minutes}m {remaining_seconds}s"
        return f"{minutes}m"
    else:
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        if remaining_minutes > 0:
            return f"{hours}h {remaining_minutes}m"
        return f"{hours}h"
