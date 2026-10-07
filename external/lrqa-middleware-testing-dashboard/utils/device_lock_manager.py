"""
Device Lock Management Utilities - Enhanced with Lock Refresh and Validation

This module provides improved device locking mechanisms to prevent:
- Lock expiration during long-running jobs
- Concurrent access to devices by multiple jobs
- Race conditions in device acquisition
"""

from datetime import datetime, timedelta, timezone
from models.device_lock import DeviceLock
import time

class DeviceLockManager:
    """Enhanced device lock management with refresh and validation"""
    
    @staticmethod
    def _estimate_leaf_seconds(queue_item):
        """Estimate execution time (seconds) for a single leaf (non-control-flow) step."""
        method = queue_item.get('method', '')

        if method == 'deepsleep':
            sleep_duration_minutes = queue_item.get('sleep_duration_minutes', 60)
            # deepsleep: 60s pre-check + (duration * 60) + 300s post-processing + 600s PRE_IR_WAIT (10 min wait before IR wakeup)
            return 60 + (sleep_duration_minutes * 60) + 300 + 600

        if method == 'maintenance_deepsleep_wakeup':
            sleep_duration_minutes = queue_item.get('sleep_duration_minutes', 13)
            # Conservative estimate: 180s (pre/setup) + (sleep_mins * 60) + 600s (post/verification/buffer)
            return 180 + (sleep_duration_minutes * 60) + 600

        if method == 'maintenance_CURL_deepsleep_wakeup':
            # Conservative estimate of 3000s (50 min) to ensure sufficient lock time
            return 3000

        if method == 'wait':
            wait_seconds = queue_item.get('wait_seconds', 0) or 0
            return wait_seconds + 10  # 10s overhead

        if method == 'reboot' or 'reboot' in method:
            return 300  # Reboot methods typically take 3-5 minutes

        if method == 'ir_test':
            return 120  # 1-2 minutes

        if method == 'voice_command':
            return 90  # 30-60 seconds

        if method == 'screenshot' or 'screen' in method:
            return 60  # 20-30 seconds

        return 60  # Default: 60 seconds per method

    @staticmethod
    def _estimate_queue_span_seconds(execution_queue, start, end):
        """
        Estimate total seconds for execution_queue[start:end] (an absolute-index sub-range
        of the flat marker-based queue - see services/test_execution_service.py's control-
        flow engine), correctly handling nested LOOP and IF/ELSEIF/ELSE control-flow markers:
        - LOOP: multiplies its body's cost by `loop_iterations`, or - for a day-based loop -
          uses `loop_days * 86400` directly (the loop re-runs its body for that whole
          duration regardless of how fast the body itself completes).
        - IF/ELSEIF/ELSE: takes the MAX cost across all branches, since we can't know at
          lock-acquisition time which branch will actually run - this is a deliberately
          conservative (longer) estimate so the lock doesn't expire mid-job.
        """
        total = 0.0
        i = start
        while i < end:
            item = execution_queue[i]
            method = item.get('method', '')

            if method == 'loop_start':
                depth = 1
                j = i + 1
                while j < end and depth > 0:
                    m = execution_queue[j].get('method')
                    if m == 'loop_start':
                        depth += 1
                    elif m == 'loop_end':
                        depth -= 1
                        if depth == 0:
                            break
                    j += 1
                loop_end_idx = j
                body_seconds = DeviceLockManager._estimate_queue_span_seconds(execution_queue, i + 1, loop_end_idx)

                if item.get('loop_mode') == 'days':
                    try:
                        loop_days = float(item.get('loop_days') or 0)
                    except (TypeError, ValueError):
                        loop_days = 0
                    total += loop_days * 86400
                else:
                    try:
                        loop_iterations = int(item.get('loop_iterations') or 1)
                    except (TypeError, ValueError):
                        loop_iterations = 1
                    total += body_seconds * max(1, loop_iterations)

                i = loop_end_idx + 1
                continue

            if method == 'if_start':
                depth = 1
                j = i + 1
                branch_starts = [i]
                endif_idx = end
                while j < end:
                    m = execution_queue[j].get('method')
                    if m == 'if_start':
                        depth += 1
                    elif m == 'endif_block':
                        depth -= 1
                        if depth == 0:
                            endif_idx = j
                            break
                    elif depth == 1 and m in ('elseif_start', 'else_start'):
                        branch_starts.append(j)
                    j += 1
                branch_starts.append(endif_idx)
                branch_costs = [
                    DeviceLockManager._estimate_queue_span_seconds(execution_queue, branch_starts[bi] + 1, branch_starts[bi + 1])
                    for bi in range(len(branch_starts) - 1)
                ]
                total += max(branch_costs) if branch_costs else 0
                i = endif_idx + 1
                continue

            if method in ('loop_end', 'elseif_start', 'else_start', 'endif_block', 'exit_loop'):
                # Only reached for malformed/unbalanced markers - skip safely
                i += 1
                continue

            total += DeviceLockManager._estimate_leaf_seconds(item)
            i += 1

        return total

    @staticmethod
    def calculate_job_duration(execution_queue, iterations):
        """
        Calculate realistic lock duration based on job parameters.
        
        Args:
            execution_queue: List of methods to execute with parameters
            iterations: Number of iterations
        
        Returns:
            int: Estimated duration in seconds with 50% safety buffer
        """
        total_seconds = DeviceLockManager._estimate_queue_span_seconds(execution_queue, 0, len(execution_queue))
        
        # Multiply by iterations and add 75% buffer for safety (increased from 50% for long-running methods)
        # 75% buffer accommodates lock refresh overhead and timing variations
        total_with_buffer = int((total_seconds * iterations) * 1.75)
        
        # Minimum duration: 10 minutes; Maximum: 30 days (a day-based LOOP step can
        # legitimately need to hold the lock for several days - previously this was
        # capped at 72h, silently truncating the lock for any multi-day loop)
        min_duration = 600
        max_duration = 30 * 86400  # 30 days
        
        final_duration = max(min_duration, min(max_duration, total_with_buffer))
        
        return final_duration
    
    @staticmethod
    def acquire_lock_with_duration(device_ip, device_name, user_id, job_id, 
                                   execution_queue, iterations):
        """
        Acquire device lock with duration calculated from job parameters.
        
        Args:
            device_ip: Device IP address
            device_name: Device name
            user_id: User ID requesting the lock
            job_id: Job ID for tracking
            execution_queue: Job execution queue
            iterations: Number of iterations
        
        Returns:
            DeviceLock object or None if lock cannot be acquired
        """
        # Check if already locked
        if DeviceLock.is_device_locked(device_ip):
            existing_lock = DeviceLock.get_device_lock(device_ip)
            return None  # Device is locked
        
        # Calculate duration
        duration_seconds = DeviceLockManager.calculate_job_duration(
            execution_queue, 
            iterations
        )
        
        # Acquire lock
        lock = DeviceLock.lock_device(
            device_ip=device_ip,
            device_name=device_name,
            user_id=user_id,
            job_id=job_id,
            estimated_duration_seconds=duration_seconds
        )
        
        return lock
    
    @staticmethod
    def refresh_lock(device_ip, job_id, execution_queue, remaining_iterations):
        """
        Refresh device lock for remaining iterations (ATOMIC - solves concurrent execution race condition).
        
        Call this at the START of each iteration to ensure lock doesn't expire.
        
        Uses atomic lock duration update to prevent race conditions when multiple jobs
        execute concurrently and try to refresh their locks simultaneously.
        
        Args:
            device_ip: Device IP address
            job_id: Job ID (current owner)
            execution_queue: Job execution queue
            remaining_iterations: How many iterations are left to do
        
        Returns:
            bool: True if lock was refreshed, False if cannot refresh (lock lost)
        """
        try:
            from datetime import datetime, timezone
            import json
            import os
            now = datetime.now(timezone.utc)
            
            # Check if device is still locked by THIS job
            current_lock = DeviceLock.get_device_lock(device_ip)
            
            if not current_lock:
                # Lock is lost - get debug information about file state
                print(f"❌ REFRESH FAILED: No lock found for {device_ip} at {now.isoformat()}")
                print(f"   Job ID: {job_id[:8]}...")
                try:
                    locks_file = getattr(DeviceLock, 'DEVICE_LOCKS_FILE', 'Json/device_locks.json')
                    with open(locks_file, 'r') as f:
                        data = json.load(f)
                    print(f"   File content ({len(data)} devices): {list(data.keys())}")
                except Exception as fe:
                    print(f"   Could not read file: {fe}")
                return False
            
            if current_lock.job_id != job_id:
                # Lock is owned by another job!
                print(f"❌ REFRESH FAILED: Device {device_ip} locked by job {current_lock.job_id}, not {job_id}")
                return False
            
            # Parse expiration to see how much time is left
            exp_str = current_lock.estimated_completion
            if 'Z' in exp_str:
                exp_str = exp_str.replace('Z', '+00:00')
            exp_time = datetime.fromisoformat(exp_str)
            time_remaining = (exp_time - now).total_seconds()
            
            print(f"📊 REFRESH CHECK: Device {device_ip}, Job {job_id[:8]}...")
            print(f"   Current time: {now.isoformat()}")
            print(f"   Lock expires: {exp_time.isoformat()}")
            print(f"   Time remaining: {time_remaining:.1f}s")
            
            # Calculate new duration
            new_duration = DeviceLockManager.calculate_job_duration(
                execution_queue,
                remaining_iterations
            )
            
            print(f"   New duration: {new_duration}s")
            
            # USE ATOMIC UPDATE - This prevents race condition when multiple jobs refresh concurrently
            # Instead of: unlock(), then lock()  (2 separate writes with window for collision)
            # We do: single atomic update of estimated_completion (1 write only)
            if not DeviceLock.update_lock_duration(device_ip, job_id, new_duration):
                print(f"❌ UPDATE FAILED: Could not update lock duration for {device_ip}")
                return False
            
            print(f"✓ REFRESH SUCCESS: Device {device_ip}, New duration: {new_duration}s for {remaining_iterations} iterations")
            return True
        except Exception as e:
            # If any error occurs during re-lock, return False
            print(f"❌ REFRESH ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def is_lock_valid_for_job(device_ip, job_id):
        """
        Check if device lock is valid for THIS specific job.
        
        Args:
            device_ip: Device IP address
            job_id: Job ID to verify
        
        Returns:
            bool: True if device is locked by this job, False otherwise
        """
        lock = DeviceLock.get_device_lock(device_ip)
        
        if not lock:
            return False  # Not locked
        
        if lock.job_id != job_id:
            return False  # Locked by another job
        
        return True
    
    @staticmethod
    def wait_with_lock_validation(duration_seconds, device_ip, job_id, log_callback=None):
        """
        Wait for specified duration while periodically validating lock.
        
        Use this instead of time.sleep() during long waits (deepsleep, etc.)
        to ensure lock is still valid.
        
        Args:
            duration_seconds: How long to wait
            device_ip: Device IP to validate
            job_id: Job ID that should own the lock
            log_callback: Optional logging function
        
        Returns:
            bool: True if wait completed successfully, False if lock was lost
        
        Raises:
            RuntimeError: If lock was lost during wait
        """
        CHECK_INTERVAL = 60  # Check every 60 seconds
        elapsed = 0
        
        def log(msg):
            if log_callback:
                log_callback(msg)
            else:
                print(msg)
        
        while elapsed < duration_seconds:
            # Calculate how long to sleep
            remaining_wait = duration_seconds - elapsed
            sleep_duration = min(CHECK_INTERVAL, remaining_wait)
            
            # Sleep in chunks
            time.sleep(sleep_duration)
            elapsed += sleep_duration
            
            # Validate lock
            if not DeviceLockManager.is_lock_valid_for_job(device_ip, job_id):
                msg = f"❌ CRITICAL: Device lock lost during wait! Device {device_ip} no longer reserved for job {job_id}"
                log(msg)
                raise RuntimeError(msg)
            
            # Log progress
            if elapsed < duration_seconds:
                remaining = duration_seconds - elapsed
                log(f"  ⏱ Elapsed: {elapsed}s / {duration_seconds}s | Remaining: {remaining}s (lock valid ✓)")
        
        return True
    
    @staticmethod
    def force_cleanup_orphaned_locks():
        """
        Force cleanup of orphaned locks that have expired for several minutes.
        Call this when a job fails to ensure orphaned locks don't block future jobs.
        
        Returns:
            List of device IPs that were unlocked
        """
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        try:
            cleaned_devices = []
            expired_count = DeviceLock.cleanup_expired_locks()
            if expired_count > 0:
                print(f"🧹 [CLEANUP] Removed {expired_count} expired device locks")
            return cleaned_devices
        except Exception as e:
            print(f"⚠️  [CLEANUP ERROR] Could not cleanup orphaned locks: {str(e)}")
            return []
