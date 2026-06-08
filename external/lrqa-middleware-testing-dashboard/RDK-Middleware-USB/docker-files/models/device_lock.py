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
                now = datetime.utcnow()
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
        """Load all device locks from JSON file."""
        if not os.path.exists(DEVICE_LOCKS_FILE):
            return {}
        
        try:
            with open(DEVICE_LOCKS_FILE, 'r') as f:
                locks_data = json.load(f)
                return {ip: DeviceLock.from_dict(data) for ip, data in locks_data.items()}
        except (json.JSONDecodeError, IOError):
            return {}
    
    @staticmethod
    def save_all(locks):
        """Save all device locks to JSON file."""
        locks_data = {ip: lock.to_dict() for ip, lock in locks.items()}
        with open(DEVICE_LOCKS_FILE, 'w') as f:
            json.dump(locks_data, f, indent=2)
    
    @staticmethod
    def lock_device(device_ip, device_name, user_id, job_id, estimated_duration_seconds):
        """Lock a device for a specific job."""
        locks = DeviceLock.load_all()
        
        now = datetime.utcnow()
        estimated_completion = (now + timedelta(seconds=estimated_duration_seconds)).isoformat()
        
        lock = DeviceLock(
            device_ip=device_ip,
            user_id=user_id,
            job_id=job_id,
            locked_at=now.isoformat(),
            estimated_completion=estimated_completion,
            device_name=device_name
        )
        
        locks[device_ip] = lock
        DeviceLock.save_all(locks)
        return lock
    
    @staticmethod
    def unlock_device(device_ip):
        """Unlock a device."""
        locks = DeviceLock.load_all()
        if device_ip in locks:
            del locks[device_ip]
            DeviceLock.save_all(locks)
            return True
        return False
    
    @staticmethod
    def is_device_locked(device_ip):
        """Check if a device is currently locked."""
        locks = DeviceLock.load_all()
        if device_ip not in locks:
            return False
        
        lock = locks[device_ip]
        # Check if lock has expired
        estimated_time = datetime.fromisoformat(lock.estimated_completion)
        if datetime.utcnow() > estimated_time:
            # Lock expired, remove it
            DeviceLock.unlock_device(device_ip)
            return False
        
        return True
    
    @staticmethod
    def get_device_lock(device_ip):
        """Get lock information for a device."""
        locks = DeviceLock.load_all()
        if device_ip in locks:
            lock = locks[device_ip]
            # Check if expired
            estimated_time = datetime.fromisoformat(lock.estimated_completion)
            if datetime.utcnow() > estimated_time:
                DeviceLock.unlock_device(device_ip)
                return None
            return lock
        return None
    
    @staticmethod
    def get_user_locks(user_id):
        """Get all locks for a specific user."""
        locks = DeviceLock.load_all()
        user_locks = []
        for lock in locks.values():
            if lock.user_id == user_id:
                # Check if expired
                estimated_time = datetime.fromisoformat(lock.estimated_completion)
                if datetime.utcnow() <= estimated_time:
                    user_locks.append(lock)
        return user_locks
    
    @staticmethod
    def cleanup_expired_locks():
        """Remove all expired locks."""
        locks = DeviceLock.load_all()
        now = datetime.utcnow()
        expired_ips = []
        
        for ip, lock in locks.items():
            estimated_time = datetime.fromisoformat(lock.estimated_completion)
            if now > estimated_time:
                expired_ips.append(ip)
        
        for ip in expired_ips:
            del locks[ip]
        
        if expired_ips:
            DeviceLock.save_all(locks)
        
        return len(expired_ips)
    
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
            old_completion = datetime.fromisoformat(lock.estimated_completion.replace('Z', '+00:00'))
            new_completion = old_completion + timedelta(seconds=additional_seconds)
            lock.estimated_completion = new_completion.isoformat()
            locks[device_ip] = lock
            DeviceLock.save_all(locks)
            return True
        except Exception:
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
            completion_time = datetime.fromisoformat(lock.estimated_completion.replace('Z', '+00:00'))
            now = datetime.utcnow().replace(tzinfo=timezone.utc)
            remaining = int((completion_time - now).total_seconds())
            return max(0, remaining)
        except:
            return -1
