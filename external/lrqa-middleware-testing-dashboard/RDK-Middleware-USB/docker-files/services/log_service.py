"""
Log Service - Manages logging operations
Handles real-time log streaming and file management
"""

import os
import queue
import threading
from datetime import datetime, timezone

class LogService:
    """Service for managing application logs"""
    
    REALTIME_LOG_FILE = os.path.join(os.path.dirname(__file__), '..', 'realtime_logs.txt')
    
    # Class-level variables shared across all instances (thread-safe with threading.local for multiple jobs)
    _thread_local = threading.local()
    
    def __init__(self):
        self.log_queue = queue.Queue()
    
    @property
    def current_log_file(self):
        """Get thread-local current log file"""
        return getattr(self._thread_local, 'current_log_file', None)
    
    @current_log_file.setter
    def current_log_file(self, value):
        """Set thread-local current log file"""
        self._thread_local.current_log_file = value
    
    @property
    def current_log_handle(self):
        """Get thread-local current log handle"""
        return getattr(self._thread_local, 'current_log_handle', None)
    
    @current_log_handle.setter
    def current_log_handle(self, value):
        """Set thread-local current log handle"""
        self._thread_local.current_log_handle = value
    
    @property
    def current_usb_log_file(self):
        """Get thread-local USB log file path"""
        return getattr(self._thread_local, 'current_usb_log_file', None)
    
    @current_usb_log_file.setter
    def current_usb_log_file(self, value):
        """Set thread-local USB log file path"""
        self._thread_local.current_usb_log_file = value
    
    def log(self, message: str, write_to_file: bool = True):
        """Add a log message with UTC timestamp"""
        timestamp = datetime.now(timezone.utc).strftime('[%Y-%m-%d %H:%M:%S UTC]')
        formatted_message = f"{timestamp} {message}"
        self.log_queue.put(formatted_message)
        
        # Write to shared realtime log file
        try:
            with open(self.REALTIME_LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(formatted_message + '\n')
                f.flush()
                os.fsync(f.fileno())
        except Exception:
            pass
        
        # Write to execution-specific file if enabled
        if write_to_file and self.current_log_handle:
            try:
                self.current_log_handle.write(formatted_message + '\n')
                self.current_log_handle.flush()
            except:
                pass
        
        # Write to USB log file if path is set
        if write_to_file and self.current_usb_log_file:
            try:
                with open(self.current_usb_log_file, 'a', encoding='utf-8') as usb_file:
                    usb_file.write(formatted_message + '\n')
                    usb_file.flush()
            except:
                pass
    
    def create_iteration_log(self, device_ip: str, method: str) -> str:
        """Create a new log file for current execution"""
        # Close previous log file if open
        if self.current_log_handle:
            try:
                self.current_log_handle.close()
            except:
                pass
        
        # Create new log file with timestamp
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_UTC')
        filename = f"{device_ip}_{method}_{timestamp}.log"
        
        # Create logs directory if it doesn't exist
        logs_dir = 'iteration_logs'
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
        
        filepath = os.path.join(logs_dir, filename)
        self.current_log_file = filepath
        self.current_log_handle = open(filepath, 'w', encoding='utf-8')
        
        # Write header
        header = f"""{'='*80}
DEVICE OPERATION LOG
{'='*80}
Device IP: {device_ip}
Method: {method}
Start Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
{'='*80}

"""
        self.current_log_handle.write(header)
        self.current_log_handle.flush()
        
        return filepath
    
    def close_iteration_log(self):
        """Close the current iteration log file"""
        if self.current_log_handle:
            try:
                footer = f"""
{'='*80}
End Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
{'='*80}
"""
                self.current_log_handle.write(footer)
                self.current_log_handle.flush()
                self.current_log_handle.close()
                self.current_log_handle = None
            except:
                pass
    
    def clear_realtime_log(self):
        """Clear the realtime log file"""
        try:
            with open(self.REALTIME_LOG_FILE, 'w') as f:
                f.write('')
        except:
            pass
    
    def stream_logs(self):
        """Generator for streaming logs (SSE)"""
        import json
        import time
        last_position = 0
        heartbeat_counter = 0
        
        try:
            while True:
                try:
                    if os.path.exists(self.REALTIME_LOG_FILE):
                        with open(self.REALTIME_LOG_FILE, 'r', encoding='utf-8') as f:
                            f.seek(last_position)
                            new_content = f.read()
                            if new_content:
                                for line in new_content.splitlines():
                                    # Send as JSON-formatted SSE message
                                    yield f"data: {json.dumps({'message': line})}\n\n"
                            last_position = f.tell()
                    
                    # Send heartbeat every 10 iterations (5 seconds) to keep connection alive
                    heartbeat_counter += 1
                    if heartbeat_counter >= 10:
                        yield f": heartbeat\n\n"
                        heartbeat_counter = 0
                        
                except GeneratorExit:
                    # Client disconnected
                    break
                except Exception as e:
                    # Log error but don't break the stream
                    pass
                
                time.sleep(0.5)
        except GeneratorExit:
            # Clean exit when client disconnects
            pass
