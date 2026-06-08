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
    def calculate_job_duration(execution_queue, iterations):
        """
        Calculate realistic lock duration based on job parameters.
        
        Args:
            execution_queue: List of methods to execute with parameters
            iterations: Number of iterations
        
        Returns:
            int: Estimated duration in seconds with 50% safety buffer
        """
        total_seconds = 0
        
        for queue_item in execution_queue:
            method = queue_item.get('method', '')
            
            if method == 'deepsleep':
                sleep_duration_minutes = queue_item.get('sleep_duration_minutes', 60)
                # deepsleep: 60s pre-check + (duration * 60) + 300s post-processing + 600s PRE_IR_WAIT (10 min wait before IR wakeup)
                # Total: accounts for full deepsleep+wakeup cycle including pre-sleep IR scheduling
                total_seconds += 60 + (sleep_duration_minutes * 60) + 300 + 600
            
            elif method == 'maintenance_deepsleep_wakeup':
                # maintenance_deepsleep_wakeup: Long-running method with built-in sleep
                # Includes: maintenance start, reboot, 13-minute deepsleep, wakeup, verification
                sleep_duration_minutes = queue_item.get('sleep_duration_minutes', 13)
                # Time breakdown: ~2-3 min setup + device reboot (2 min) + sleep + ~5-6 min wakeup & verification
                # INCREASED from (60 + sleep*60 + 360) to (180 + sleep*60 + 600) for better margin
                # Conservative estimate: 180s (pre/setup) + (sleep_mins * 60) + 600s (post/verification/buffer)
                total_seconds += 180 + (sleep_duration_minutes * 60) + 600
            
            elif method == 'maintenance_CURL_deepsleep_wakeup':
                # maintenance_CURL_deepsleep_wakeup: Optimized maintenance with CURL-based deepsleep injection
                # ACTUAL OBSERVED: This method takes approximately 43-45 minutes per iteration (2616-2700 seconds)
                # Using conservative estimate of 3000 seconds (50 minutes) to ensure sufficient lock time
                # Time breakdown: ~2-3 min setup + 38-40 min maintenance polling + 2-3 min deepsleep + 1-2 min wakeup/verification
                # Note: Uses slightly higher estimate than raw average to accommodate device variations
                total_seconds += 3000
            
            elif method == 'wait':
                wait_seconds = queue_item.get('wait_seconds', 0)
                total_seconds += wait_seconds + 10  # 10s overhead
            
            elif method == 'reboot' or 'reboot' in method:
                # Reboot methods typically take 3-5 minutes
                total_seconds += 300
            
            elif method == 'ir_test':
                # IR test: 1-2 minutes
                total_seconds += 120
            
            elif method == 'voice_command':
                # Voice command: 30-60 seconds
                total_seconds += 90
            
            elif method == 'screenshot' or 'screen' in method:
                # Screenshot operations: 20-30 seconds
                total_seconds += 60
            
            else:
                # Default: 60 seconds per method
                total_seconds += 60
        
        # Multiply by iterations and add 75% buffer for safety (increased from 50% for long-running methods)
        # 75% buffer accommodates lock refresh overhead and timing variations
        total_with_buffer = int((total_seconds * iterations) * 1.75)
        
        # Minimum duration: 10 minutes; Maximum: 72 hours (supports 50-iteration multi-device runs)
        min_duration = 600
        max_duration = 259200  # 72 hours = 259200 seconds
        
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
