"""
Queue Service - Manages test execution queue
Handles job queuing and sequential processing
"""

import queue
import threading
import time
from typing import List, Dict, Optional
from datetime import datetime, timezone

class QueueService:
    def trigger_next_job_for_device(self, device_ip):
        """Move next queued job for device to execution queue if device is free."""
        from models.job import Job
        active_job = Job.get_active_device_job(device_ip)
        if not active_job and device_ip in self.device_job_queue and self.device_job_queue[device_ip]:
            next_job = self.device_job_queue[device_ip].pop(0)
            self._save_device_job_queue()
            with self.queue_lock:
                self.queued_jobs.append(next_job)
            self.execution_queue.put(next_job)
    
    DEVICE_QUEUE_FILE = 'device_job_queue.json'

    def __init__(self, test_execution_service, recovery_service=None):
        self.test_execution_service = test_execution_service
        self.recovery_service = recovery_service
        self.execution_queue = queue.Queue()
        self.queue_lock = threading.Lock()
        self.queued_jobs = []
        self.processor_thread = None
        self.queue_running = False
        self.device_job_queue = self._load_device_job_queue()

    def _load_device_job_queue(self):
        import json, os
        if not os.path.exists(self.DEVICE_QUEUE_FILE):
            return {}
        try:
            with open(self.DEVICE_QUEUE_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_device_job_queue(self):
        import json
        with open(self.DEVICE_QUEUE_FILE, 'w') as f:
            json.dump(self.device_job_queue, f, indent=2)
    
    def add_job(self, device_ip: str, device_name: str, method: str, iterations: int,
                username: str, password: str, port: int = 10022,
                selected_ir_keys: Optional[List[str]] = None, voice_text: str = '', 
                remote_keys: str = '', expected_screen: str = '', execution_queue: Optional[List] = None,
                sequence_name: Optional[str] = None) -> Dict:
        """Add a job to the device queue or start immediately if free"""
        import time
        job_id = f"{device_ip}_{method}_{int(time.time())}"
        job = {
            'id': job_id,
            'job_id': job_id,
            'device_ip': device_ip,
            'device_name': device_name,
            'method': method,
            'iterations': iterations,
            'username': username,
            'password': password,
            'port': port,
            'selected_ir_keys': selected_ir_keys or ['HOME', 'POWER'],
            'voice_text': voice_text,
            'remote_keys': remote_keys,
            'expected_screen': expected_screen,
            'execution_queue': execution_queue or [],
            'sequence_name': sequence_name,
            'queued_at': datetime.now(timezone.utc).isoformat(),
            'status': 'queued'
        }

        # Check if device is busy (has running/pending job)
        from models.job import Job
        active_job = Job.get_active_device_job(device_ip)
        if active_job:
            # Device busy, add to device queue
            if device_ip not in self.device_job_queue:
                self.device_job_queue[device_ip] = []
            self.device_job_queue[device_ip].append(job)
            self._save_device_job_queue()
            position = len(self.device_job_queue[device_ip])
            return {'job_id': job_id, 'position': position, 'queued': True}
        else:
            # Device free, start job immediately
            with self.queue_lock:
                self.queued_jobs.append(job)
            self.execution_queue.put(job)
            if self.recovery_service:
                self.recovery_service.save_queue_state(self.queued_jobs)
            self.start_processor()
            return {'job_id': job_id, 'position': 1, 'queued': False}
    
    def start_processor(self):
        """Start the queue processor thread"""
        if self.processor_thread is None or not self.processor_thread.is_alive():
            self.queue_running = True
            self.processor_thread = threading.Thread(target=self._process_queue, daemon=True)
            self.processor_thread.start()
    
    def _process_queue(self):
        """Background worker to process queued test executions"""
        while self.queue_running:
            try:
                job = self.execution_queue.get(timeout=1)
                job_id = job.get('job_id') or job.get('id')
                with self.queue_lock:
                    self.queued_jobs = [j for j in self.queued_jobs if (j.get('job_id') or j.get('id')) != job_id]
                
                # Use execute_test_queue if execution_queue is provided, otherwise use legacy execute_test
                if job.get('execution_queue'):
                    self.test_execution_service.execute_test_queue(
                        device_ip=job['device_ip'],
                        execution_queue=job['execution_queue'],
                        iterations=job['iterations'],
                        job_id=job_id,
                        sequence_name=job.get('sequence_name')
                    )
                else:
                    # Legacy mode for backward compatibility
                    self.test_execution_service.execute_test(
                        device_ip=job['device_ip'],
                        methods=job['method'],
                        iterations=job['iterations'],
                        selected_ir_keys=job.get('selected_ir_keys'),
                        voice_text=job.get('voice_text', '')
                    )
                self.execution_queue.task_done()

                # After job completes, check device queue for next job
                device_ip = job['device_ip']
                if device_ip in self.device_job_queue and self.device_job_queue[device_ip]:
                    next_job = self.device_job_queue[device_ip].pop(0)
                    self._save_device_job_queue()
                    with self.queue_lock:
                        self.queued_jobs.append(next_job)
                    self.execution_queue.put(next_job)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error processing queue job: {e}")
    
    def get_status(self) -> Dict:
        """Get current queue status"""
        with self.queue_lock:
            jobs_copy = list(self.queued_jobs)
        
        # Combine queued_jobs with device_job_queue (pending jobs waiting for device)
        all_jobs = jobs_copy.copy()
        for device_ip, device_jobs in self.device_job_queue.items():
            all_jobs.extend(device_jobs)
        
        return {
            'queue_size': self.execution_queue.qsize(),
            'processor_running': self.queue_running and self.processor_thread and self.processor_thread.is_alive(),
            'queued_jobs': all_jobs
        }
    
    def clear_queue(self):
        """Clear all queued jobs"""
        with self.execution_queue.queue.mutex:
            self.execution_queue.queue.clear()
        
        with self.queue_lock:
            self.queued_jobs.clear()
