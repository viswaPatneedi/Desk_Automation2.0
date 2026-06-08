"""Device lock model for managing device availability."""
import json
import os
from datetime import datetime, timezone, timedelta
from config_eta import format_eta
import logging
from config_paths import DEVICE_LOCKS_FILE

logger = logging.getLogger(__name__)


class DeviceLock:
    """Device lock model for tracking device usage."""
    
    def __init__(self, device_ip, user_id, job_id, locked_at, estimated_completion, 
                 device_name=None):
        self.device_ip = device_ip
        self.device_name = device_name
        self.user_id = user_id
        self.job_id = job_id
        self.locked_at = locked_at
        self.estimated_completion = estimated_completion
    
    def to_dict(self):
        """Convert lock object to dictionary."""
        # Calculate remaining time
        eta_formatted = 'Unknown'
        if self.estimated_completion:
            try:
                completion_time = datetime.fromisoformat(self.estimated_completion.replace('Z', '+00:00'))
                # Ensure completion_time is timezone-aware
                if completion_time.tzinfo is None:
                    completion_time = completion_time.replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                remaining_seconds = int((completion_time - now).total_seconds())
                if remaining_seconds > 0:
                    eta_formatted = format_eta(remaining_seconds)
                else:
                    eta_formatted = 'Completing...'
            except (ValueError, AttributeError):
                eta_formatted = 'Unknown'
        
        return {
            'device_ip': self.device_ip,
            'device_name': self.device_name,
            'user_id': self.user_id,
            'job_id': self.job_id,
            'locked_at': self.locked_at,
            'estimated_completion': self.estimated_completion,
            'eta_formatted': eta_formatted
        }
    
    @staticmethod
    def from_dict(data):
        """Create DeviceLock object from dictionary."""
        return DeviceLock(
            device_ip=data['device_ip'],
            user_id=data['user_id'],
            job_id=data['job_id'],
            locked_at=data['locked_at'],
            estimated_completion=data['estimated_completion'],
            device_name=data.get('device_name')
        )
    
    @staticmethod
    def load_all():
        """Load all device locks from JSON file with file locking for thread safety."""
        from utils.file_lock import FileLockManager
        
        if not os.path.exists(DEVICE_LOCKS_FILE):
            return {}
        
        try:
            # Use FileLockManager for thread-safe file access
            with FileLockManager.locked_json_file(DEVICE_LOCKS_FILE, 'r') as (f, locks_data):
                return {ip: DeviceLock.from_dict(data) for ip, data in locks_data.items()}
        except (json.JSONDecodeError, IOError, Exception) as e:
            logger.warning(f"Error reading device locks file: {e}")
            return {}
    
    @staticmethod
    def save_all(locks):
        """Save all device locks to JSON file with file locking for thread safety."""
        from utils.file_lock import FileLockManager
        
        locks_data = {ip: lock.to_dict() for ip, lock in locks.items()}
        try:
            # Use FileLockManager for thread-safe file access
            with FileLockManager.locked_json_file(DEVICE_LOCKS_FILE, 'w') as f:
                json.dump(locks_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error writing device locks file: {e}")
    
    @staticmethod
    def lock_device(device_ip, device_name, user_id, job_id, estimated_duration_seconds):
        """Lock a device for a specific job (ATOMIC operation - prevents race conditions)."""
        from utils.file_lock import FileLockManager
        import json
        
        # ATOMIC: Load, modify, and save all in one locked operation
        locks_file = DEVICE_LOCKS_FILE
        
        try:
            # Use SINGLE atomic operation: acquire lock, read, modify, write, release lock
            with FileLockManager.locked_json_file(locks_file, 'r+') as (f, locks_data):
                # Use timezone-aware UTC datetime consistently
                now = datetime.now(timezone.utc)
                estimated_completion = (now + timedelta(seconds=estimated_duration_seconds)).isoformat()
                
                # Create new lock
                lock_dict = {
                    'device_ip': device_ip,
                    'user_id': user_id,
                    'job_id': job_id,
                    'locked_at': now.isoformat(),
                    'estimated_completion': estimated_completion,
                    'device_name': device_name
                }
                
                # Add lock to dict
                locks_data[device_ip] = lock_dict
                
                # Write back atomically (file lock still held)
                f.seek(0)
                f.truncate()
                json.dump(locks_data, f, indent=2)
                f.flush()
                
                logger.info(f"🔒[LOCK-ACQUIRED] Device {device_ip} ({device_name}) locked for job {job_id} - Expires: {estimated_completion} ({estimated_duration_seconds}s from now)")
                return True
        except Exception as e:
            logger.error(f"❌[LOCK-FAILED] Error locking device {device_ip}: {str(e)}")
            return False
    
    @staticmethod
    def unlock_device(device_ip):
        """Unlock a device (ATOMIC operation)."""
        from utils.file_lock import FileLockManager
        import json
        
        try:
            locks_file = DEVICE_LOCKS_FILE
            
            # ATOMIC: Read, modify, write in ONE locked operation
            with FileLockManager.locked_json_file(locks_file, 'r+') as (f, locks_data):
                if device_ip in locks_data:
                    del locks_data[device_ip]
                    
                    # Write back atomically (lock still held)
                    f.seek(0)
                    f.truncate()
                    json.dump(locks_data, f, indent=2)
                    f.flush()
                    
                    logger.info(f"🔓[LOCK-RELEASED] Device {device_ip} unlocked")
                    return True
            return False
        except Exception as e:
            logger.error(f"Error unlocking device {device_ip}: {str(e)}")
            return False
    
    @staticmethod
    def is_device_locked(device_ip):
        """Check if a device is currently locked."""
        locks = DeviceLock.load_all()
        if device_ip not in locks:
            return False
        
        lock = locks[device_ip]
        # Check if lock has expired
        try:
            completion_string = lock.estimated_completion
            if 'Z' in completion_string:
                completion_string = completion_string.replace('Z', '+00:00')
                estimated_time = datetime.fromisoformat(completion_string)
            else:
                # Naive format
                estimated_time = datetime.fromisoformat(completion_string)
            
            if datetime.now(timezone.utc) > estimated_time:
                # Lock expired, remove it
                DeviceLock.unlock_device(device_ip)
                return False
            
            return True
        except Exception as e:
            logger.warning(f"Error checking lock status for {device_ip}: {str(e)}")
            # If we can't parse, consider it invalid and remove it
            DeviceLock.unlock_device(device_ip)
            return False
    
    @staticmethod
    def get_device_lock(device_ip):
        """Get lock information for a device."""
        locks = DeviceLock.load_all()
        if device_ip in locks:
            lock = locks[device_ip]
            # Check if expired (SAFE timezone handling)
            try:
                completion_string = lock.estimated_completion
                
                # Normalize timezone string
                if 'Z' in completion_string:
                    completion_string = completion_string.replace('Z', '+00:00')
                
                # Parse and ensure timezone awareness
                estimated_time = datetime.fromisoformat(completion_string)
                
                # If naive, make it aware (UTC)
                if estimated_time.tzinfo is None:
                    estimated_time = estimated_time.replace(tzinfo=timezone.utc)
                
                # Get current time as timezone-aware UTC
                current_time = datetime.now(timezone.utc)
                
                # DETAILED DEBUG LOGGING
                time_remaining = (estimated_time - current_time).total_seconds()
                logger.debug(f"🔍[LOCK-CHECK] Device {device_ip}: Current={current_time.isoformat()} Expires={estimated_time.isoformat()} Remaining={time_remaining:.1f}s Job={lock.job_id}")
                
                # Safe comparison (both are timezone-aware)
                if current_time > estimated_time:
                    logger.warning(f"⚠️ [LOCK-EXPIRED] Device {device_ip} lock expired! (Remaining: {time_remaining:.1f}s) Unlocking...")
                    DeviceLock.unlock_device(device_ip)
                    return None
            except Exception as e:
                logger.warning(f"❌ Error checking lock expiration for {device_ip}: {str(e)}")
                # On any error, fail SAFE - remove bad lock to prevent hangs
                try:
                    DeviceLock.unlock_device(device_ip)
                except:
                    pass
                return None
            logger.debug(f"✅[LOCK-VALID] Device {device_ip} lock is valid for job {lock.job_id}")
            return lock
        # ENHANCED DEBUG: Log when lock not found with full details about what IS locked
        logger.warning(f"❌[LOCK-NOT-FOUND] Device {device_ip} NOT in locks. Available: {list(locks.keys())}")
        return None
    
    @staticmethod
    def get_user_locks(user_id):
        """Get all locks for a specific user."""
        locks = DeviceLock.load_all()
        user_locks = []
        for lock in locks.values():
            if lock.user_id == user_id:
                try:
                    # Check if expired
                    completion_string = lock.estimated_completion
                    if 'Z' in completion_string:
                        completion_string = completion_string.replace('Z', '+00:00')
                        estimated_time = datetime.fromisoformat(completion_string)
                    else:
                        # Naive format
                        estimated_time = datetime.fromisoformat(completion_string)
                    
                    # Compare naive datetimes (both are UTC)
                    if datetime.now(timezone.utc) <= estimated_time:
                        user_locks.append(lock)
                except Exception:
                    # Skip this lock if parsing fails
                    continue
        return user_locks
    
    @staticmethod
    def cleanup_expired_locks():
        """Remove all expired locks (ATOMIC operation)."""
        from utils.file_lock import FileLockManager
        import json
        
        try:
            locks_file = DEVICE_LOCKS_FILE
            now = datetime.now(timezone.utc)
            expired_ips = []
            
            # ATOMIC: Read, check, modify, write in ONE locked operation
            with FileLockManager.locked_json_file(locks_file, 'r+') as (f, locks_data):
                # Check which locks are expired
                for ip, lock_data in locks_data.items():
                    try:
                        completion_string = lock_data.get('estimated_completion', '')
                        if 'Z' in completion_string:
                            completion_string = completion_string.replace('Z', '+00:00')
                        estimated_time = datetime.fromisoformat(completion_string)
                        
                        if now > estimated_time:
                            expired_ips.append(ip)
                    except Exception as e:
                        logger.warning(f"Error checking expiration for lock {ip}: {str(e)}")
                        expired_ips.append(ip)  # Remove invalid locks
                
                # Remove expired locks
                for ip in expired_ips:
                    del locks_data[ip]
                
                # Write back if any were removed (file lock still held - atomic!)
                if expired_ips:
                    f.seek(0)
                    f.truncate()
                    json.dump(locks_data, f, indent=2)
                    f.flush()
                    logger.info(f"🧹[CLEANUP] Removed {len(expired_ips)} expired locks: {expired_ips}")
            
            return len(expired_ips)
        except Exception as e:
            logger.error(f"Error in cleanup_expired_locks: {str(e)}")
            return 0
    
    @staticmethod
    def is_lock_owned_by_job(device_ip, job_id):
        """
        Check if device lock is owned by a specific job.
        
        Args:
            device_ip: Device IP address
            job_id: Job ID to check
        
        Returns:
            bool: True if lock exists and is owned by job_id
        """
        lock = DeviceLock.get_device_lock(device_ip)
        if not lock:
            return False
        return lock.job_id == job_id
    
    @staticmethod
    def extend_lock(device_ip, additional_seconds):
        """
        Extend existing lock by adding more time.
        
        Args:
            device_ip: Device IP address
            additional_seconds: Seconds to add to lock duration
        
        Returns:
            bool: True if lock was extended, False if lock not found or error
        """
        try:
            locks = DeviceLock.load_all()
            if device_ip not in locks:
                return False
            
            lock = locks[device_ip]
            # Parse current completion time and extend it
            # Handle both timezone-aware and naive datetime formats
            completion_string = lock.estimated_completion
            if 'Z' in completion_string:
                completion_string = completion_string.replace('Z', '+00:00')
                old_completion = datetime.fromisoformat(completion_string)
            else:
                # Naive format - parse as naive UTC
                old_completion = datetime.fromisoformat(completion_string)
            
            new_completion = old_completion + timedelta(seconds=additional_seconds)
            lock.estimated_completion = new_completion.isoformat()
            locks[device_ip] = lock
            DeviceLock.save_all(locks)
            return True
        except Exception as e:
            logger.warning(f"Error extending lock for {device_ip}: {str(e)}")
            return False
    
    @staticmethod
    def get_time_until_expiration(device_ip):
        """
        Get seconds remaining until lock expires.
        
        Args:
            device_ip: Device IP address
        
        Returns:
            int: Seconds remaining, or -1 if not locked
        """
        lock = DeviceLock.get_device_lock(device_ip)
        if not lock:
            return -1
        
        try:
            # Handle both timezone-aware and naive datetime formats
            completion_string = lock.estimated_completion
            
            # If string contains 'Z', it's UTC (e.g., "2026-05-12T03:05:48.439341Z")
            if 'Z' in completion_string:
                completion_string = completion_string.replace('Z', '+00:00')
                completion_time = datetime.fromisoformat(completion_string)
            else:
                # Format is naive (e.g., "2026-05-12T03:05:48.439341")
                # Parse as naive UTC then make aware
                completion_time = datetime.fromisoformat(completion_string)
                completion_time = completion_time.replace(tzinfo=timezone.utc)
            
            # Get current time as aware UTC
            now = datetime.now(timezone.utc).replace(tzinfo=timezone.utc)
            
            # Calculate remaining seconds
            remaining = int((completion_time - now).total_seconds())
            return max(0, remaining)
        except Exception as e:
            logger.warning(f"Error calculating time until expiration for {device_ip}: {str(e)}")
            return -1
    
    @staticmethod
    def update_lock_duration(device_ip, job_id, new_duration_seconds):
        """
        Atomically update lock duration for a device (ATOMIC - solves race condition in concurrent executions).
        
        This method performs a true atomic read-modify-write operation within a single file lock,
        preventing any interleaving of concurrent lock updates.
        
        Args:
            device_ip: Device IP address
            job_id: Job ID (must match current owner)
            new_duration_seconds: New duration in seconds from now
        
        Returns:
            bool: True if lock was updated, False if lock not found, job mismatch, or error
        """
        from utils.file_lock import FileLockManager
        import json
        
        try:
            locks_file = DEVICE_LOCKS_FILE
            
            # ATOMIC: Read, check, modify, write all in ONE locked operation
            with FileLockManager.locked_json_file(locks_file, 'r+') as (f, locks_data):
                # Verify lock exists and matches job
                if device_ip not in locks_data:
                    logger.warning(f"❌ Lock update failed: No lock found for {device_ip}")
                    return False
                
                lock_data = locks_data[device_ip]
                
                if lock_data.get('job_id') != job_id:
                    logger.warning(f"❌ Lock update failed: Device {device_ip} owned by job {lock_data.get('job_id')}, not {job_id}")
                    return False
                
                # Calculate new expiration
                now = datetime.now(timezone.utc)
                new_completion = (now + timedelta(seconds=new_duration_seconds)).isoformat()
                
                # Update the lock (file lock still held - atomic!)
                lock_data['estimated_completion'] = new_completion
                locks_data[device_ip] = lock_data
                
                # Write back atomically (lock still held)
                f.seek(0)
                f.truncate()
                json.dump(locks_data, f, indent=2)
                f.flush()
                
                logger.info(f"✓[LOCK-UPDATED] Device {device_ip}: new duration {new_duration_seconds}s ({new_duration_seconds//3600}h {(new_duration_seconds%3600)//60}m) - Expires: {new_completion}")
                return True
            
        except Exception as e:
            logger.error(f"❌[LOCK-UPDATE-ERROR] Error updating lock duration for {device_ip}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
            import traceback
            logger.error(traceback.format_exc())
            return False
