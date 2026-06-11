"""
Recovery Service - Auto-recovery mechanism for application crashes
Handles state persistence and automatic recovery
"""

import json
import os
import pickle
import threading
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from config.config_paths import APP_STATE_FILE, CHECKPOINT_FILE

class RecoveryService:
    """Service for handling application state recovery"""
    
    # Use absolute paths to avoid working directory issues
    _BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    CHECKPOINT_INTERVAL = 30  # Save state every 30 seconds
    
    def __init__(self):
        self.checkpoint_thread = None
        self.checkpoint_running = False
        self.state = {
            'last_checkpoint': None,
            'execution_context': {},
            'queue_state': {},
            'active_sessions': {},
            'crash_count': 0,
            'last_crash': None
        }
        self.lock = threading.Lock()
    
    def initialize(self):
        """Initialize recovery system and restore previous state"""
        try:
            self._load_state()
            if self.state.get('last_crash'):
                print(f"[RECOVERY] Detected previous crash at {self.state['last_crash']}")
                print(f"[RECOVERY] Crash count: {self.state.get('crash_count', 0)}")
                self._restore_execution_state()
            else:
                print("[RECOVERY] Clean startup - no previous crash detected")
            
            # Start checkpoint thread
            self.start_checkpointing()
            return True
        except Exception as e:
            print(f"[RECOVERY] Error during initialization: {e}")
            return False
    
    def _load_state(self):
        """Load saved state from disk"""
        if os.path.exists(APP_STATE_FILE):
            try:
                with open(APP_STATE_FILE, 'r') as f:
                    saved_state = json.load(f)
                    self.state.update(saved_state)
                print(f"[RECOVERY] Loaded state from {APP_STATE_FILE}")
            except Exception as e:
                print(f"[RECOVERY] Error loading state: {e}")
        
        # Load binary checkpoint if available
        if os.path.exists(CHECKPOINT_FILE):
            try:
                with open(CHECKPOINT_FILE, 'rb') as f:
                    checkpoint_data = pickle.load(f)
                    self.state['checkpoint_data'] = checkpoint_data
                print(f"[RECOVERY] Loaded checkpoint from {CHECKPOINT_FILE}")
            except Exception as e:
                print(f"[RECOVERY] Error loading checkpoint: {e}")
    
    def _save_state(self):
        """Save current state to disk with robust error handling"""
        try:
            with self.lock:
                state_to_save = {
                    'last_checkpoint': datetime.now(timezone.utc).isoformat(),
                    'execution_context': self.state.get('execution_context', {}),
                    'queue_state': self.state.get('queue_state', {}),
                    'active_sessions': self.state.get('active_sessions', {}),
                    'crash_count': self.state.get('crash_count', 0),
                    'last_crash': self.state.get('last_crash')
                }
                
                # Ensure directory exists
                state_dir = os.path.dirname(APP_STATE_FILE)
                if state_dir and not os.path.exists(state_dir):
                    try:
                        os.makedirs(state_dir, exist_ok=True)
                    except Exception as dir_err:
                        print(f"[RECOVERY] Warning: Could not create directory {state_dir}: {dir_err}")
                
                # Write to temp file first, then rename (atomic operation)
                temp_file = f"{APP_STATE_FILE}.tmp"
                try:
                    with open(temp_file, 'w') as f:
                        json.dump(state_to_save, f, indent=2)
                    # Try atomic rename first
                    try:
                        os.replace(temp_file, APP_STATE_FILE)
                    except (OSError, FileNotFoundError) as replace_err:
                        # Fallback: try direct write if atomic operation fails
                        print(f"[RECOVERY] Atomic rename failed ({replace_err}), using direct write")
                        with open(APP_STATE_FILE, 'w') as f:
                            json.dump(state_to_save, f, indent=2)
                        # Clean up temp file if it exists
                        if os.path.exists(temp_file):
                            try:
                                os.remove(temp_file)
                            except:
                                pass
                except IOError as io_err:
                    print(f"[RECOVERY] Error writing state file: {io_err}")
                    # Try to clean up temp file
                    if os.path.exists(temp_file):
                        try:
                            os.remove(temp_file)
                        except:
                            pass
        except Exception as e:
            print(f"[RECOVERY] Error saving state: {e}")
    
    def save_execution_context(self, device_ip: str, method: str, iteration: int, 
                              total_iterations: int, session_folder: str):
        """Save current execution context"""
        with self.lock:
            self.state['execution_context'] = {
                'device_ip': device_ip,
                'method': method,
                'current_iteration': iteration,
                'total_iterations': total_iterations,
                'session_folder': session_folder,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def save_queue_state(self, queued_jobs: list, queue_size: int):
        """Save current queue state"""
        with self.lock:
            self.state['queue_state'] = {
                'queued_jobs': queued_jobs,
                'queue_size': queue_size,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def save_session_info(self, session_id: str, session_data: Dict):
        """Save active session information"""
        with self.lock:
            if 'active_sessions' not in self.state:
                self.state['active_sessions'] = {}
            self.state['active_sessions'][session_id] = {
                **session_data,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def _restore_execution_state(self):
        """Restore execution state after crash"""
        exec_context = self.state.get('execution_context', {})
        if exec_context:
            print(f"[RECOVERY] Restoring execution context:")
            print(f"  - Device: {exec_context.get('device_ip')}")
            print(f"  - Method: {exec_context.get('method')}")
            print(f"  - Iteration: {exec_context.get('current_iteration')}/{exec_context.get('total_iterations')}")
            print(f"  - Session: {exec_context.get('session_folder')}")
        
        queue_state = self.state.get('queue_state', {})
        if queue_state and queue_state.get('queue_size', 0) > 0:
            print(f"[RECOVERY] Restoring queue state:")
            print(f"  - Queued jobs: {queue_state.get('queue_size')}")
            # Queue will be restored by QueueService
    
    def mark_crash(self, is_actual_crash: bool = False):
        """Mark application crash or just save state
        
        Args:
            is_actual_crash: If True, increment crash counter. If False, just save state.
        """
        with self.lock:
            if is_actual_crash:
                self.state['crash_count'] = self.state.get('crash_count', 0) + 1
                self.state['last_crash'] = datetime.now(timezone.utc).isoformat()
            # Always save state regardless
        self._save_state()
    
    def clear_crash_marker(self):
        """Clear crash marker after successful recovery"""
        with self.lock:
            self.state['last_crash'] = None
            self.state['crash_count'] = 0  # Reset crash count on successful recovery
        self._save_state()
        print("[RECOVERY] Crash marker cleared and crash count reset")
    
    def start_checkpointing(self):
        """Start automatic checkpoint thread"""
        if not self.checkpoint_running:
            self.checkpoint_running = True
            self.checkpoint_thread = threading.Thread(target=self._checkpoint_loop, daemon=True)
            self.checkpoint_thread.start()
            print("[RECOVERY] Checkpoint thread started")
    
    def _checkpoint_loop(self):
        """Background thread for periodic checkpointing"""
        while self.checkpoint_running:
            try:
                self._save_state()
                time.sleep(self.CHECKPOINT_INTERVAL)
            except Exception as e:
                print(f"[RECOVERY] Checkpoint error: {e}")
    
    def stop_checkpointing(self):
        """Stop checkpoint thread"""
        self.checkpoint_running = False
        if self.checkpoint_thread:
            self.checkpoint_thread.join(timeout=5)
        # Final save
        self._save_state()
        print("[RECOVERY] Checkpoint thread stopped")
    
    def get_recovery_info(self) -> Dict[str, Any]:
        """Get recovery information"""
        with self.lock:
            return {
                'last_checkpoint': self.state.get('last_checkpoint'),
                'crash_count': self.state.get('crash_count', 0),
                'last_crash': self.state.get('last_crash'),
                'has_active_execution': bool(self.state.get('execution_context')),
                'has_queued_jobs': bool(self.state.get('queue_state', {}).get('queue_size', 0) > 0),
                'active_sessions': len(self.state.get('active_sessions', {}))
            }
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Clean up old session data"""
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        
        with self.lock:
            active_sessions = self.state.get('active_sessions', {})
            cleaned_sessions = {}
            
            for session_id, session_data in active_sessions.items():
                try:
                    timestamp = datetime.fromisoformat(session_data['timestamp'].replace('Z', '+00:00'))
                    if timestamp >= cutoff:
                        cleaned_sessions[session_id] = session_data
                except:
                    pass
            
            removed = len(active_sessions) - len(cleaned_sessions)
            if removed > 0:
                self.state['active_sessions'] = cleaned_sessions
                print(f"[RECOVERY] Cleaned up {removed} old sessions")
