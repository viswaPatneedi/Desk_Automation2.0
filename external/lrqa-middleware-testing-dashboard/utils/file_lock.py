"""
File Lock Utility - Provides distributed file locking for JSON files
Ensures data integrity across multiple worker processes
"""
import fcntl
import json
import os
import time
from contextlib import contextmanager
from typing import Any, Dict

class FileLockManager:
    """Manager for file-based locking to prevent race conditions"""
    
    @staticmethod
    @contextmanager
    def locked_json_file(file_path: str, mode: str = 'r'):
        """
        Context manager for reading/writing JSON files with exclusive locks.
        
        Args:
            file_path: Path to the JSON file
            mode: File mode ('r' for read, 'w' for write, 'r+' for read-write)
        
        Yields:
            Tuple of (file_handle, data) for 'r' mode
            file_handle for 'w' mode
        
        Example:
            # Reading
            with FileLockManager.locked_json_file('devices.json', 'r') as (f, data):
                devices = data
            
            # Writing
            with FileLockManager.locked_json_file('devices.json', 'w') as f:
                json.dump(new_data, f, indent=2)
        """
        # Ensure file exists
        if not os.path.exists(file_path) and 'r' in mode:
            with open(file_path, 'w') as f:
                json.dump({} if file_path.endswith('.json') else [], f)
        
        # Open file
        file_handle = open(file_path, mode)
        
        try:
            # Acquire exclusive lock (blocks until available)
            fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX)
            
            if mode == 'r':
                # Read-only: parse and return tuple (file_handle, data) for backward compatibility
                try:
                    file_handle.seek(0)
                    data = json.load(file_handle)
                    yield file_handle, data
                except json.JSONDecodeError:
                    # Return empty structure on parse error
                    yield file_handle, {} if file_path.endswith('devices.json') else []
            elif mode == 'r+':
                # Read-write: return tuple (file_handle, data) for atomic read-modify-write
                try:
                    file_handle.seek(0)
                    data = json.load(file_handle)
                except (json.JSONDecodeError, IOError):
                    data = {} if file_path.endswith('.json') else []
                yield file_handle, data
            else:
                # Write-only: just yield file handle for writing
                yield file_handle
        
        finally:
            # Release lock and close file
            fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)
            file_handle.close()
    
    @staticmethod
    def safe_json_read(file_path: str, default: Any = None) -> Any:
        """
        Safely read JSON file with locking.
        
        Args:
            file_path: Path to JSON file
            default: Default value if file doesn't exist or is invalid
        
        Returns:
            Parsed JSON data or default value
        """
        if not os.path.exists(file_path):
            return default if default is not None else {}
        
        try:
            with FileLockManager.locked_json_file(file_path, 'r') as (f, data):
                return data
        except Exception:
            return default if default is not None else {}
    
    @staticmethod
    def safe_json_write(file_path: str, data: Any, indent: int = 2) -> bool:
        """
        Safely write JSON file with locking.
        
        Args:
            file_path: Path to JSON file
            data: Data to write
            indent: JSON indentation level
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with FileLockManager.locked_json_file(file_path, 'w') as f:
                json.dump(data, f, indent=indent)
            return True
        except Exception as e:
            print(f"Error writing to {file_path}: {e}")
            return False
    
    @staticmethod
    def atomic_json_update(file_path: str, update_func: callable) -> bool:
        """
        Atomically update JSON file using a callback function.
        
        Args:
            file_path: Path to JSON file
            update_func: Function that takes current data and returns updated data
        
        Returns:
            True if successful, False otherwise
        
        Example:
            def add_device(data):
                data['devices'].append(new_device)
                return data
            
            FileLockManager.atomic_json_update('devices.json', add_device)
        """
        try:
            with FileLockManager.locked_json_file(file_path, 'r+') as (f, data):
                # Apply update function
                updated_data = update_func(data)
                
                # Write back to file
                f.seek(0)
                f.truncate()
                json.dump(updated_data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error updating {file_path}: {e}")
            return False


# Optional: Redis-based distributed locking for multi-container setups
class RedisLockManager:
    """Redis-based distributed locking (requires Redis connection)"""
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
    
    @contextmanager
    def lock(self, key: str, timeout: int = 10, retry_interval: float = 0.1):
        """
        Acquire a distributed lock using Redis.
        
        Args:
            key: Lock key name
            timeout: Lock timeout in seconds
            retry_interval: Time to wait between retry attempts
        """
        if not self.redis:
            # Fallback to no-op if Redis not available
            yield
            return
        
        lock_key = f"lock:{key}"
        acquired = False
        
        try:
            # Try to acquire lock
            start_time = time.time()
            while time.time() - start_time < timeout:
                if self.redis.setnx(lock_key, 1):
                    self.redis.expire(lock_key, timeout)
                    acquired = True
                    break
                time.sleep(retry_interval)
            
            if not acquired:
                raise TimeoutError(f"Could not acquire lock for {key}")
            
            yield
        
        finally:
            if acquired:
                self.redis.delete(lock_key)
