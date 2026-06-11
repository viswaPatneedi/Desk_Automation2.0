"""
Agent-ETA-DeviceLock: Device Lock and Expected Time of Arrival (ETA) Management
Manages device locks, calculates ETAs, and prevents conflicts during execution
"""

import logging
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json

logger = logging.getLogger(__name__)

# ============================================================
# DATA CLASSES & ENUMS
# ============================================================

class LockStatus(Enum):
    """Device lock status"""
    AVAILABLE = "available"
    LOCKED = "locked"
    EXPIRING_SOON = "expiring_soon"
    EXPIRED = "expired"
    ERROR = "error"


class LockPriority(Enum):
    """Lock request priority levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class DeviceLockInfo:
    """Information about a device lock"""
    device_id: str
    job_id: str
    acquired_at: str
    ttl_seconds: int
    estimated_release: str
    priority: int
    user_id: str
    reason: str
    
    def to_dict(self):
        return asdict(self)


@dataclass
class ETA:
    """Expected Time of Arrival for a test"""
    job_id: str
    device_id: str
    method: str
    estimated_seconds: int
    estimated_completion: str
    confidence: float  # 0.0 - 1.0
    status: str
    
    def to_dict(self):
        return asdict(self)


# ============================================================
# DEVICE LOCK MANAGER
# ============================================================

class DeviceLockManager:
    """Manage device locks to prevent concurrent execution conflicts"""
    
    def __init__(self, db_session_provider=None):
        """
        Initialize lock manager
        
        Args:
            db_session_provider: Callable that returns SQLAlchemy session
        """
        self.db_session_provider = db_session_provider
        self.locks: Dict[str, DeviceLockInfo] = {}
        self.lock = threading.Lock()
    
    def acquire_lock(
        self,
        device_id: str,
        job_id: str,
        ttl_seconds: int,
        priority: LockPriority = LockPriority.MEDIUM,
        user_id: str = None,
        reason: str = None
    ) -> Tuple[bool, str]:
        """
        Attempt to acquire a device lock
        
        Args:
            device_id: Device identifier
            job_id: Job requesting the lock
            ttl_seconds: Time to live for the lock
            priority: Lock priority level
            user_id: User requesting the lock
            reason: Reason for lock request
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            with self.lock:
                # Check if device already locked
                if device_id in self.locks:
                    existing = self.locks[device_id]
                    
                    # Check if we can override with higher priority
                    if priority.value > existing.priority:
                        logger.warning(
                            f"🔄 Device {device_id} - Higher priority job {job_id} "
                            f"overriding existing lock from job {existing.job_id}"
                        )
                        self.locks[device_id] = DeviceLockInfo(
                            device_id=device_id,
                            job_id=job_id,
                            acquired_at=datetime.now(timezone.utc).isoformat(),
                            ttl_seconds=ttl_seconds,
                            estimated_release=(
                                datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
                            ).isoformat(),
                            priority=priority.value,
                            user_id=user_id or "system",
                            reason=reason or "No reason provided"
                        )
                        return True, f"Lock acquired (overrode lower priority lock)"
                    else:
                        return False, f"Device {device_id} is locked by job {existing.job_id}"
                
                # Create new lock
                self.locks[device_id] = DeviceLockInfo(
                    device_id=device_id,
                    job_id=job_id,
                    acquired_at=datetime.now(timezone.utc).isoformat(),
                    ttl_seconds=ttl_seconds,
                    estimated_release=(
                        datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
                    ).isoformat(),
                    priority=priority.value,
                    user_id=user_id or "system",
                    reason=reason or "No reason provided"
                )
                
                logger.info(f"✅ Lock acquired for device {device_id} (job: {job_id}, TTL: {ttl_seconds}s)")
                return True, "Lock acquired successfully"
        
        except Exception as e:
            logger.error(f"❌ Error acquiring lock: {e}")
            return False, str(e)
    
    def release_lock(self, device_id: str, job_id: str = None) -> Tuple[bool, str]:
        """
        Release a device lock
        
        Args:
            device_id: Device identifier
            job_id: Job releasing the lock (for verification)
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            with self.lock:
                if device_id not in self.locks:
                    return False, f"No lock found for device {device_id}"
                
                lock_info = self.locks[device_id]
                
                # Verify job_id if provided
                if job_id and lock_info.job_id != job_id:
                    logger.warning(
                        f"⚠️  Job {job_id} attempted to release lock held by job {lock_info.job_id}"
                    )
                    return False, f"Lock is held by different job {lock_info.job_id}"
                
                del self.locks[device_id]
                logger.info(f"✅ Lock released for device {device_id}")
                return True, "Lock released successfully"
        
        except Exception as e:
            logger.error(f"❌ Error releasing lock: {e}")
            return False, str(e)
    
    def get_lock_status(self, device_id: str) -> Dict[str, Any]:
        """Get current lock status for a device"""
        try:
            with self.lock:
                if device_id not in self.locks:
                    return {
                        'device_id': device_id,
                        'status': LockStatus.AVAILABLE.value,
                        'locked': False
                    }
                
                lock_info = self.locks[device_id]
                
                # Check if lock is expired
                release_time = datetime.fromisoformat(lock_info.estimated_release)
                now = datetime.now(timezone.utc)
                
                if now > release_time:
                    # Lock has expired - clean it up
                    del self.locks[device_id]
                    return {
                        'device_id': device_id,
                        'status': LockStatus.AVAILABLE.value,
                        'locked': False
                    }
                
                # Check if expiring soon (within 10%)
                ttl = lock_info.ttl_seconds
                elapsed = (now - datetime.fromisoformat(lock_info.acquired_at)).total_seconds()
                remaining = ttl - elapsed
                
                status = LockStatus.LOCKED
                if remaining < ttl * 0.1:
                    status = LockStatus.EXPIRING_SOON
                
                return {
                    'device_id': device_id,
                    'status': status.value,
                    'locked': True,
                    'job_id': lock_info.job_id,
                    'acquired_at': lock_info.acquired_at,
                    'estimated_release': lock_info.estimated_release,
                    'ttl_seconds': lock_info.ttl_seconds,
                    'seconds_remaining': max(0, int(remaining)),
                    'priority': lock_info.priority,
                    'reason': lock_info.reason
                }
        
        except Exception as e:
            logger.error(f"❌ Error getting lock status: {e}")
            return {'device_id': device_id, 'status': LockStatus.ERROR.value, 'error': str(e)}
    
    def renew_lock(self, device_id: str, job_id: str, additional_seconds: int) -> Tuple[bool, str]:
        """
        Renew (extend) an existing device lock
        
        Args:
            device_id: Device identifier
            job_id: Job holding the lock
            additional_seconds: Additional time to add to lock TTL
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            with self.lock:
                if device_id not in self.locks:
                    return False, f"No lock found for device {device_id}"
                
                lock_info = self.locks[device_id]
                
                if lock_info.job_id != job_id:
                    return False, f"Lock is held by job {lock_info.job_id}, not {job_id}"
                
                # Extend the lock
                new_release = datetime.now(timezone.utc) + timedelta(seconds=additional_seconds)
                lock_info.ttl_seconds += additional_seconds
                lock_info.estimated_release = new_release.isoformat()
                
                logger.info(
                    f"✅ Lock renewed for device {device_id} (+{additional_seconds}s, "
                    f"new TTL: {lock_info.ttl_seconds}s)"
                )
                return True, f"Lock renewed with additional {additional_seconds} seconds"
        
        except Exception as e:
            logger.error(f"❌ Error renewing lock: {e}")
            return False, str(e)
    
    def get_all_locks(self) -> List[Dict[str, Any]]:
        """Get all active locks"""
        with self.lock:
            return [lock.to_dict() for lock in self.locks.values()]
    
    def cleanup_expired_locks(self) -> int:
        """Remove all expired locks and return count"""
        cleaned = 0
        now = datetime.now(timezone.utc)
        
        with self.lock:
            expired = []
            for device_id, lock_info in self.locks.items():
                release_time = datetime.fromisoformat(lock_info.estimated_release)
                if now > release_time:
                    expired.append(device_id)
            
            for device_id in expired:
                del self.locks[device_id]
                cleaned += 1
        
        if cleaned > 0:
            logger.info(f"🧹 Cleaned up {cleaned} expired locks")
        
        return cleaned


# ============================================================
# ETA CALCULATOR
# ============================================================

class ETACalculator:
    """Calculate and manage Expected Time of Arrival for tests"""
    
    def __init__(self, config_eta_module=None):
        """
        Initialize ETA calculator
        
        Args:
            config_eta_module: config_eta module with calculate_eta function
        """
        self.config_eta = config_eta_module
        self.etas: Dict[str, ETA] = {}
        self.history: List[Tuple[str, int, int]] = []  # (job_id, estimated, actual)
        self.lock = threading.Lock()
    
    def calculate_eta(
        self,
        job_id: str,
        device_id: str,
        method: str,
        iterations: int = 1,
        historical_data: Dict[str, Any] = None
    ) -> Optional[ETA]:
        """
        Calculate ETA for a test job
        
        Args:
            job_id: Job identifier
            device_id: Device identifier
            method: Method name
            iterations: Number of iterations for the test
            historical_data: Historical execution data for accuracy
        
        Returns:
            ETA object or None if calculation fails
        """
        try:
            # Use config_eta if available, otherwise use default calculation
            if self.config_eta and hasattr(self.config_eta, 'calculate_eta'):
                base_seconds = self.config_eta.calculate_eta(method, iterations)
            else:
                # Default: 60 seconds per iteration
                base_seconds = 60 * iterations
            
            # Adjust based on historical data
            confidence = 0.7  # Default confidence
            
            if historical_data:
                avg_actual = historical_data.get('average_time', base_seconds)
                variance = historical_data.get('variance', 0)
                confidence = min(1.0, 0.5 + (1.0 / (1.0 + variance)))
                base_seconds = int(avg_actual)
            
            # Add buffer (20% for system overhead)
            estimated_seconds = int(base_seconds * 1.2)
            
            eta = ETA(
                job_id=job_id,
                device_id=device_id,
                method=method,
                estimated_seconds=estimated_seconds,
                estimated_completion=(
                    datetime.now(timezone.utc) + timedelta(seconds=estimated_seconds)
                ).isoformat(),
                confidence=confidence,
                status="active"
            )
            
            with self.lock:
                self.etas[job_id] = eta
            
            logger.info(
                f"📊 ETA calculated: job={job_id}, method={method}, "
                f"estimated={estimated_seconds}s, confidence={confidence:.0%}"
            )
            
            return eta
        
        except Exception as e:
            logger.error(f"❌ Error calculating ETA: {e}")
            return None
    
    def update_eta_progress(self, job_id: str, elapsed_seconds: int) -> Dict[str, Any]:
        """
        Update ETA based on elapsed time
        
        Args:
            job_id: Job identifier
            elapsed_seconds: Seconds elapsed so far
        
        Returns:
            Updated ETA info or error dict
        """
        try:
            with self.lock:
                if job_id not in self.etas:
                    return {'error': f'No ETA found for job {job_id}'}
                
                eta = self.etas[job_id]
                
                # Calculate remaining time
                remaining = max(0, eta.estimated_seconds - elapsed_seconds)
                
                # Estimate completion time
                completion = (datetime.now(timezone.utc) + timedelta(seconds=remaining)).isoformat()
                
                return {
                    'job_id': job_id,
                    'elapsed_seconds': elapsed_seconds,
                    'estimated_total': eta.estimated_seconds,
                    'remaining_seconds': remaining,
                    'progress_percent': min(100, int((elapsed_seconds / eta.estimated_seconds) * 100)),
                    'estimated_completion': completion,
                    'confidence': eta.confidence
                }
        
        except Exception as e:
            logger.error(f"❌ Error updating ETA: {e}")
            return {'error': str(e)}
    
    def complete_eta(self, job_id: str, actual_seconds: int) -> Dict[str, Any]:
        """
        Mark ETA as complete and record actual time
        
        Args:
            job_id: Job identifier
            actual_seconds: Actual execution time
        
        Returns:
            Completion info with accuracy metrics
        """
        try:
            with self.lock:
                if job_id not in self.etas:
                    return {'error': f'No ETA found for job {job_id}'}
                
                eta = self.etas[job_id]
                estimated = eta.estimated_seconds
                
                # Calculate accuracy
                error_seconds = abs(estimated - actual_seconds)
                error_percent = (error_seconds / estimated) * 100
                accuracy = max(0, 100 - error_percent)
                
                # Store in history
                self.history.append((job_id, estimated, actual_seconds))
                
                # Remove from active ETAs
                del self.etas[job_id]
                
                logger.info(
                    f"📊 ETA completed: job={job_id}, "
                    f"estimated={estimated}s, actual={actual_seconds}s, "
                    f"accuracy={accuracy:.0f}%"
                )
                
                return {
                    'job_id': job_id,
                    'estimated_seconds': estimated,
                    'actual_seconds': actual_seconds,
                    'error_seconds': error_seconds,
                    'accuracy_percent': accuracy,
                    'overestimated': estimated > actual_seconds
                }
        
        except Exception as e:
            logger.error(f"❌ Error completing ETA: {e}")
            return {'error': str(e)}
    
    def get_etas_by_device(self, device_id: str) -> List[Dict[str, Any]]:
        """Get all active ETAs for a device"""
        with self.lock:
            return [
                eta.to_dict() 
                for eta in self.etas.values() 
                if eta.device_id == device_id
            ]
    
    def get_accuracy_metrics(self) -> Dict[str, float]:
        """Get historical accuracy metrics"""
        if not self.history:
            return {'total_jobs': 0, 'average_accuracy': 0}
        
        accuracies = []
        for _, estimated, actual in self.history:
            error = abs(estimated - actual)
            accuracy = max(0, 100 - (error / estimated) * 100)
            accuracies.append(accuracy)
        
        return {
            'total_jobs': len(self.history),
            'average_accuracy': sum(accuracies) / len(accuracies),
            'min_accuracy': min(accuracies),
            'max_accuracy': max(accuracies)
        }


# ============================================================
# AGENT-ETA-DEVICE-LOCK
# ============================================================

class AgentETADeviceLock:
    """
    AI Agent for device lock management and ETA prediction
    
    Responsibilities:
    - Acquire and release device locks to prevent conflicts
    - Calculate and predict job completion times (ETAs)
    - Manage lock expiration and renewal
    - Optimize device allocation based on ETAs
    - Prevent "device already locked" errors
    """
    
    def __init__(self, config_eta_module=None):
        self.name = "Agent-ETA-DeviceLock"
        self.is_running = False
        self.lock_manager = DeviceLockManager()
        self.eta_calculator = ETACalculator(config_eta_module)
        self.monitor_thread = None
        self.queue: List[Dict[str, Any]] = []
        
        logger.info(f"✅ {self.name} initialized")
    
    def start(self):
        """Start the agent"""
        if self.is_running:
            logger.warning(f"⚠️  {self.name} is already running")
            return
        
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info(f"🚀 {self.name} started")
    
    def stop(self):
        """Stop the agent"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info(f"⛔ {self.name} stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                # Clean up expired locks
                self.lock_manager.cleanup_expired_locks()
                
                # Check for ETAs that need updates
                self._check_eta_progress()
                
                time.sleep(30)  # Monitor every 30 seconds
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                time.sleep(60)
    
    def _check_eta_progress(self):
        """Check and update ETA progress"""
        try:
            # Monitor active ETAs
            pass
        except Exception as e:
            logger.error(f"Error checking ETA progress: {e}")
    
    def request_lock(
        self,
        device_id: str,
        job_id: str,
        method: str,
        iterations: int = 1,
        priority: LockPriority = LockPriority.MEDIUM,
        user_id: str = None
    ) -> Dict[str, Any]:
        """
        Request a device lock and calculate ETA
        
        Args:
            device_id: Device to lock
            job_id: Job requesting the lock
            method: Test method to execute
            iterations: Number of iterations
            priority: Request priority
            user_id: User making the request
        
        Returns:
            Lock and ETA information
        """
        try:
            # Calculate ETA first
            eta = self.eta_calculator.calculate_eta(
                job_id, device_id, method, iterations
            )
            
            if not eta:
                return {'success': False, 'error': 'ETA calculation failed'}
            
            # Try to acquire lock with TTL matching ETA (+ buffer)
            lock_ttl = eta.estimated_seconds + 60  # Add 60s buffer
            
            success, message = self.lock_manager.acquire_lock(
                device_id=device_id,
                job_id=job_id,
                ttl_seconds=lock_ttl,
                priority=priority,
                user_id=user_id,
                reason=f"Method: {method}, Iterations: {iterations}"
            )
            
            if not success:
                return {'success': False, 'error': message}
            
            return {
                'success': True,
                'lock': {
                    'device_id': device_id,
                    'job_id': job_id,
                    'ttl_seconds': lock_ttl,
                    'acquired_at': datetime.now(timezone.utc).isoformat()
                },
                'eta': eta.to_dict()
            }
        
        except Exception as e:
            logger.error(f"❌ Error requesting lock: {e}")
            return {'success': False, 'error': str(e)}
    
    def release_lock_with_completion(
        self,
        device_id: str,
        job_id: str,
        actual_seconds: int
    ) -> Dict[str, Any]:
        """
        Release a lock and record actual completion time
        
        Args:
            device_id: Device to unlock
            job_id: Job completing
            actual_seconds: Actual execution time
        
        Returns:
            Release and accuracy information
        """
        try:
            # Record completion and accuracy
            accuracy = self.eta_calculator.complete_eta(job_id, actual_seconds)
            
            # Release the lock
            success, message = self.lock_manager.release_lock(device_id, job_id)
            
            return {
                'success': success,
                'message': message,
                'accuracy': accuracy,
                'device_id': device_id,
                'job_id': job_id
            }
        
        except Exception as e:
            logger.error(f"❌ Error releasing lock: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """Get current status of a device"""
        lock_status = self.lock_manager.get_lock_status(device_id)
        etas = self.eta_calculator.get_etas_by_device(device_id)
        
        return {
            'device_id': device_id,
            'lock_status': lock_status,
            'active_etas': etas,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get agent status"""
        return {
            'agent_name': self.name,
            'is_running': self.is_running,
            'active_locks': len(self.lock_manager.locks),
            'active_etas': len(self.eta_calculator.etas),
            'accuracy_metrics': self.eta_calculator.get_accuracy_metrics(),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }


# ============================================================
# GLOBAL AGENT INSTANCE
# ============================================================

_ETA_DEVICE_LOCK_AGENT = None

def get_eta_device_lock_agent() -> AgentETADeviceLock:
    """Get or create the global ETA-DeviceLock agent"""
    global _ETA_DEVICE_LOCK_AGENT
    if _ETA_DEVICE_LOCK_AGENT is None:
        _ETA_DEVICE_LOCK_AGENT = AgentETADeviceLock()
    return _ETA_DEVICE_LOCK_AGENT


def start_eta_device_lock_agent():
    """Start the ETA-DeviceLock agent"""
    agent = get_eta_device_lock_agent()
    agent.start()
    return agent


def stop_eta_device_lock_agent():
    """Stop the ETA-DeviceLock agent"""
    if _ETA_DEVICE_LOCK_AGENT:
        _ETA_DEVICE_LOCK_AGENT.stop()


# ============================================================
# CLI INTERFACE
# ============================================================

def main():
    """CLI interface for agent"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Agent-ETA-DeviceLock')
    parser.add_argument('--start', action='store_true', help='Start the agent')
    parser.add_argument('--status', action='store_true', help='Get agent status')
    parser.add_argument('--device-status', metavar='DEVICE_ID', help='Get device status')
    
    args = parser.parse_args()
    
    agent = get_eta_device_lock_agent()
    
    if args.start:
        print("🚀 Starting Agent-ETA-DeviceLock...")
        agent.start()
        print("✅ Agent started. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n⛔ Stopping agent...")
            agent.stop()
    
    elif args.status:
        import json
        agent.start()
        print(json.dumps(agent.get_agent_status(), indent=2))
        agent.stop()
    
    elif args.device_status:
        import json
        agent.start()
        print(json.dumps(agent.get_device_status(args.device_status), indent=2))
        agent.stop()
    
    else:
        parser.print_help()


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    main()
