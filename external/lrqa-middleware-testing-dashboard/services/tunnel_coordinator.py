"""
Global Tunnel Coordinator - Manages concurrent SSH tunnel requests to shared R-Pi backends
Prevents tunnel conflicts when multiple jobs try to establish tunnels simultaneously
"""

import threading
import time
from typing import Dict, Tuple, Optional
from datetime import datetime, timedelta


class TunnelCoordinator:
    """
    Global singleton for coordinating SSH tunnel access to R-Pi backends
    
    Problem:
    - Multiple jobs (Device A, Device B) execute concurrently
    - Both share same R-Pi backend
    - R-Pi SSH can only handle ONE tunnel at a time
    - Result: Second job fails with "tunnel connection failed"
    
    Solution:
    - Per-R-Pi locks to serialize tunnel requests
    - Wait/retry logic with timeout
    - Queuing for fair access
    """
    
    _instance = None
    _lock = threading.Lock()
    
    # Per-R-Pi locks (keyed by R-Pi IP)
    _rpi_locks: Dict[str, threading.RLock] = {}
    
    # Track tunnel usage (for timeout/cleanup)
    _tunnel_usage: Dict[str, dict] = {}
    
    # Configuration
    TUNNEL_TIMEOUT = 300  # 5 minutes max per tunnel
    RETRY_TIMEOUT = 60    # Max 60 seconds to wait for tunnel availability
    RETRY_INTERVAL = 0.5  # Check every 500ms
    
    def __new__(cls):
        """Singleton pattern - only one instance"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize if not already done"""
        if self._initialized:
            return
        
        self._initialized = True
        print("[TUNNEL-COORD] Global Tunnel Coordinator initialized")
    
    @classmethod
    def get_instance(cls) -> 'TunnelCoordinator':
        """Get singleton instance"""
        return cls()
    
    def acquire_tunnel(self, rpi_ip: str, job_id: str, device_name: str, timeout: int = RETRY_TIMEOUT) -> Tuple[bool, str]:
        """
        Acquire exclusive access to R-Pi tunnel
        
        Args:
            rpi_ip: R-Pi backend IP address
            job_id: Job ID requesting tunnel
            device_name: Device name (for logging)
            timeout: Max seconds to wait for tunnel availability (default: 60)
        
        Returns:
            Tuple of (success, message)
        
        Example:
            success, msg = coordinator.acquire_tunnel('10.138.17.42', 'job-123', 'Device-A')
            if success:
                # Now exclusive tunnel access to this R-Pi
                # Do tunnel work...
            else:
                # Failed to acquire - another job has it
                # Fail gracefully
        """
        # Ensure lock exists for this R-Pi
        if rpi_ip not in self._rpi_locks:
            with self._lock:
                if rpi_ip not in self._rpi_locks:
                    self._rpi_locks[rpi_ip] = threading.RLock()
        
        rpi_lock = self._rpi_locks[rpi_ip]
        
        # Try to acquire lock with timeout
        acquired = False
        start_time = datetime.now()
        attempt = 0
        
        while not acquired and (datetime.now() - start_time).total_seconds() < timeout:
            attempt += 1
            
            # Non-blocking try to acquire lock
            acquired = rpi_lock.acquire(blocking=True, timeout=0.5)
            
            if acquired:
                # Record acquisition
                self._tunnel_usage[rpi_ip] = {
                    'job_id': job_id,
                    'device_name': device_name,
                    'acquired_at': datetime.now(),
                    'attempt': attempt
                }
                
                elapsed = (datetime.now() - start_time).total_seconds()
                msg = f"[TUNNEL-COORD] ✅ Tunnel acquired for {device_name} (R-Pi: {rpi_ip}, attempts: {attempt}, waited: {elapsed:.1f}s)"
                print(msg)
                return True, msg
            
            # Wait before retry
            time.sleep(self.RETRY_INTERVAL)
        
        # Timeout occurred
        if rpi_ip in self._tunnel_usage:
            current = self._tunnel_usage[rpi_ip]
            msg = f"[TUNNEL-COORD] ❌ Timeout acquiring tunnel for {device_name} (R-Pi: {rpi_ip}). Currently held by job {current['job_id']} ({current['device_name']})"
        else:
            msg = f"[TUNNEL-COORD] ❌ Timeout acquiring tunnel for {device_name} (R-Pi: {rpi_ip})"
        
        print(msg)
        return False, msg
    
    def release_tunnel(self, rpi_ip: str, job_id: str, device_name: str = None):
        """
        Release exclusive access to R-Pi tunnel
        
        Args:
            rpi_ip: R-Pi backend IP address
            job_id: Job ID releasing tunnel
            device_name: Device name (for logging)
        """
        if rpi_ip not in self._rpi_locks:
            return
        
        rpi_lock = self._rpi_locks[rpi_ip]
        
        try:
            rpi_lock.release()
            
            if rpi_ip in self._tunnel_usage:
                usage = self._tunnel_usage[rpi_ip]
                duration = (datetime.now() - usage['acquired_at']).total_seconds()
                del self._tunnel_usage[rpi_ip]
                
                msg = f"[TUNNEL-COORD] ✅ Tunnel released for job {job_id} ({device_name}), held for {duration:.1f}s"
            else:
                msg = f"[TUNNEL-COORD] ✅ Tunnel released for job {job_id}"
            
            print(msg)
        except RuntimeError:
            # Lock wasn't held
            msg = f"[TUNNEL-COORD] ⚠️  Attempted to release lock not held by this thread (job: {job_id})"
            print(msg)
    
    def get_tunnel_status(self, rpi_ip: str) -> Dict:
        """
        Get current status of R-Pi tunnel
        
        Returns:
            Dict with keys:
                - in_use: bool
                - job_id: str (if in_use)
                - device_name: str (if in_use)
                - duration: float (seconds held)
        """
        if rpi_ip in self._tunnel_usage:
            usage = self._tunnel_usage[rpi_ip]
            return {
                'in_use': True,
                'job_id': usage.get('job_id'),
                'device_name': usage.get('device_name'),
                'duration': (datetime.now() - usage.get('acquired_at', datetime.now())).total_seconds()
            }
        else:
            return {
                'in_use': False,
                'job_id': None,
                'device_name': None,
                'duration': 0
            }
    
    def reset(self):
        """Reset all locks and usage tracking (for testing/cleanup)"""
        with self._lock:
            self._rpi_locks = {}
            self._tunnel_usage = {}
            print("[TUNNEL-COORD] Coordinator reset")


# Global singleton instance
_tunnel_coordinator = TunnelCoordinator.get_instance()


def get_tunnel_coordinator() -> TunnelCoordinator:
    """Get global tunnel coordinator instance"""
    return _tunnel_coordinator
