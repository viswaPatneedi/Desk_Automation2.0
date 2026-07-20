"""
Execution Monitor Service - Monitors stuck executions

This service continuously monitors running executions and:
1. Detects when executions get stuck (device unreachable, errors, etc.)
2. Checks device reachability
3. Generates reports and sends email when execution completes with device unreachable
"""

import threading
import time
import os
import json
import paramiko
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List


class ExecutionMonitorService:
    """Service for monitoring stuck executions"""
    
    MONITOR_INTERVAL = 30  # Check every 30 seconds
    STUCK_THRESHOLD = 180  # Consider stuck if no progress for 3 minutes
    DEVICE_UNREACHABLE_TIMEOUT = 10  # Device unreachable timeout in seconds
    
    def __init__(self, email_service=None, test_execution_service=None, queue_service=None):
        """Initialize the execution monitor service"""
        self.email_service = email_service
        self.test_execution_service = test_execution_service
        self.queue_service = queue_service
        self.monitor_thread = None
        self.monitor_running = False
        self.lock = threading.Lock()
        
        # Track execution state for each job
        self.execution_state = {}  # {job_id: {last_update, retry_count, device_check_count}}
    
    def start_monitoring(self):
        """Start the monitoring thread"""
        if self.monitor_running:
            print("[EXECUTION MONITOR] Already running")
            return
        
        self.monitor_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print("[EXECUTION MONITOR] Started - checking every", self.MONITOR_INTERVAL, "seconds")
    
    def stop_monitoring(self):
        """Stop the monitoring thread"""
        self.monitor_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        print("[EXECUTION MONITOR] Stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitor_running:
            try:
                self._check_executions()
            except Exception as e:
                print(f"[EXECUTION MONITOR] Error in monitor loop: {e}")
                import traceback
                traceback.print_exc()
            
            # Sleep in small increments to allow quick shutdown
            for _ in range(self.MONITOR_INTERVAL):
                if not self.monitor_running:
                    break
                time.sleep(1)
    
    def _check_executions(self):
        """Check all running executions for stuck state"""
        from models.job import Job
        
        # Load all jobs
        jobs = Job.load_all()
        running_jobs = [j for j in jobs if j.status in ['running', 'pending']]
        
        if not running_jobs:
            # Clear stale execution state
            with self.lock:
                self.execution_state.clear()
            return
        
        print(f"[EXECUTION MONITOR] Checking {len(running_jobs)} running/pending jobs")
        
        for job in running_jobs:
            job_id = job.job_id
            
            # Initialize execution state if not exists
            if job_id not in self.execution_state:
                with self.lock:
                    self.execution_state[job_id] = {
                        'last_update': datetime.now(timezone.utc),
                        'last_iteration': getattr(job, 'current_iteration', 1),
                        'last_step': getattr(job, 'current_step', 0),
                        'device_check_count': 0,
                        'last_check': None
                    }
                continue
            
            # Check if execution is making progress
            current_iteration = getattr(job, 'current_iteration', 1)
            current_step = getattr(job, 'current_step', 0)
            state = self.execution_state[job_id]
            
            # Check if progress was made
            if current_iteration > state['last_iteration'] or current_step > state['last_step']:
                # Progress detected - update state
                with self.lock:
                    state['last_update'] = datetime.now(timezone.utc)
                    state['last_iteration'] = current_iteration
                    state['last_step'] = current_step
                print(f"[EXECUTION MONITOR] Job {job_id} progressing: iteration {current_iteration}, step {current_step}")
                continue
            
            # Check if execution is stuck
            time_since_update = datetime.now(timezone.utc) - state['last_update']
            
            if time_since_update.total_seconds() > self.STUCK_THRESHOLD:
                print(f"[EXECUTION MONITOR] ⚠️  Job {job_id} appears stuck - no progress for {int(time_since_update.total_seconds())} seconds")
                
                # Get device credentials from Device model
                from models.device import Device
                device = Device.find_by_ip(job.device_ip)
                
                if not device:
                    print(f"[EXECUTION MONITOR] ✗ Device {job.device_ip} not found in devices.json")
                    self._mark_job_failed(job, "Device configuration not found")
                    continue
                
                # Check device reachability
                is_reachable = self._check_device_reachability(
                    job.device_ip, 
                    device.username, 
                    device.password, 
                    device.port
                )
                
                if is_reachable:
                    print(f"[EXECUTION MONITOR] ✓ Device {job.device_ip} is reachable")
                    print(f"[EXECUTION MONITOR] ⚠️  Job {job_id} is stuck but device is reachable - no automatic recovery")
                else:
                    print(f"[EXECUTION MONITOR] ✗ Device {job.device_ip} is NOT reachable")
                    
                    # Check if all iterations might be completed based on log file
                    if self._check_if_completed(job):
                        print(f"[EXECUTION MONITOR] Job {job_id} appears completed - generating report")
                        self._finalize_completed_job(job)
                    else:
                        # Increment device check count
                        with self.lock:
                            state['device_check_count'] += 1
                        
                        # If device unreachable for too long, mark as failed
                        if state['device_check_count'] > 10:  # ~5 minutes
                            print(f"[EXECUTION MONITOR] ❌ Device unreachable for too long, marking job as failed")
                            self._mark_job_failed(job, "Device unreachable - execution could not continue")
    
    def _check_device_reachability(self, device_ip: str, username: str, password: str, port: int = 10022) -> bool:
        """Check if device is reachable via SSH"""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            ssh.connect(
                hostname=device_ip,
                port=port,
                username=username,
                password=password,
                timeout=self.DEVICE_UNREACHABLE_TIMEOUT,
                banner_timeout=self.DEVICE_UNREACHABLE_TIMEOUT,
                auth_timeout=self.DEVICE_UNREACHABLE_TIMEOUT
            )
            
            # Try a simple command
            stdin, stdout, stderr = ssh.exec_command('echo "test"', timeout=5)
            result = stdout.read().decode().strip()
            ssh.close()
            
            return result == "test"
        except Exception as e:
            print(f"[EXECUTION MONITOR] Device {device_ip} check failed: {e}")
            return False
    
    def _check_if_completed(self, job) -> bool:
        """Check if job is actually completed based on log file analysis"""
        log_file = getattr(job, 'log_file_path', None)
        
        if not log_file or not os.path.exists(log_file):
            return False
        
        try:
            with open(log_file, 'r') as f:
                log_content = f.read()
            
            # Check for completion indicators
            completed_indicators = [
                'completed successfully',
                'All iterations completed',
                '✓ Test execution completed',
                f'{job.iterations}/{job.iterations} iterations'
            ]
            
            for indicator in completed_indicators:
                if indicator in log_content:
                    return True
            
            # Check iteration results
            iteration_results = getattr(job, 'iteration_results', {})
            if len(iteration_results) >= job.iterations:
                return True
            
            return False
        except Exception as e:
            print(f"[EXECUTION MONITOR] Error checking completion for job {job.job_id}: {e}")
            return False
    
    def _finalize_completed_job(self, job):
        """Finalize a completed job and send notification"""
        try:
            from models.job import Job
            
            # Mark job as completed
            job.status = 'completed'
            job.end_time = datetime.now(timezone.utc).isoformat()
            
            # Save job
            all_jobs = Job.load_all()
            for i, j in enumerate(all_jobs):
                if j.job_id == job.job_id:
                    all_jobs[i] = job
                    break
            Job.save_all(all_jobs)
            
            print(f"[EXECUTION MONITOR] ✓ Marked job {job.job_id} as completed")
            
            # Generate and send report
            self._send_completion_report(job)
            
            # Clean up execution state
            with self.lock:
                if job.job_id in self.execution_state:
                    del self.execution_state[job.job_id]
            
            # Trigger next job for device if any
            if self.queue_service:
                self.queue_service.trigger_next_job_for_device(job.device_ip)
        except Exception as e:
            print(f"[EXECUTION MONITOR] Error finalizing job {job.job_id}: {e}")
            import traceback
            traceback.print_exc()
    
    def _mark_job_failed(self, job, reason: str):
        """Mark job as failed with reason"""
        try:
            from models.job import Job
            
            job.status = 'failed'
            job.end_time = datetime.now(timezone.utc).isoformat()
            
            # Log failure reason to job's log file
            self._log_to_job_file(job, f"[FAILURE] {reason}")
            
            # Save job
            all_jobs = Job.load_all()
            for i, j in enumerate(all_jobs):
                if j.job_id == job.job_id:
                    all_jobs[i] = job
                    break
            Job.save_all(all_jobs)
            
            print(f"[EXECUTION MONITOR] ❌ Marked job {job.job_id} as failed: {reason}")
            
            # Send failure notification
            self._send_failure_notification(job, reason)
            
            # Clean up execution state
            with self.lock:
                if job.job_id in self.execution_state:
                    del self.execution_state[job.job_id]
            
            # Trigger next job for device if any
            if self.queue_service:
                self.queue_service.trigger_next_job_for_device(job.device_ip)
        except Exception as e:
            print(f"[EXECUTION MONITOR] Error marking job as failed {job.job_id}: {e}")
            import traceback
            traceback.print_exc()
    
    def _send_completion_report(self, job):
        """Send completion report email to user"""
        if not self.email_service or not self.email_service.enabled:
            print("[EXECUTION MONITOR] Email service not available - skipping notification")
            return
        
        try:
            # Get user email
            from models.user import User
            user = User.get_user_by_id(job.user_id)
            
            if not user or not user.email:
                print(f"[EXECUTION MONITOR] No email found for user {job.user_id}")
                return
            
            # Prepare job data for email
            job_data = job.to_dict()
            job_data['iterations_completed'] = len(getattr(job, 'iteration_results', {}))
            iteration_results = getattr(job, 'iteration_results', {})
            job_data['passed_count'] = sum(1 for r in iteration_results.values() if r == 'passed')
            job_data['failed_count'] = sum(1 for r in iteration_results.values() if r == 'failed')
            
            # ✅ ENHANCEMENT 2: Validate execution before sending
            validation_result = self.email_service.validate_execution_before_email(job_data)
            if not validation_result['is_valid']:
                print(f"[EXECUTION MONITOR] ⚠️  Execution data validation failed: {validation_result['warnings']}")
            else:
                print(f"[EXECUTION MONITOR] ✓ Execution data validation passed")
            
            # ✅ ENHANCEMENT 4: Smart notification filtering
            should_send, send_reason = self.email_service.should_send_notification(job_data)
            print(f"[EXECUTION MONITOR] {send_reason}")
            
            if not should_send:
                print(f"[EXECUTION MONITOR] Notification suppressed based on rules")
                return
            
            # ✅ ENHANCEMENT 1: AI analysis for failures
            ai_analysis = {}
            if job_data.get('status') == 'failed':
                print(f"[EXECUTION MONITOR] Running AI analysis on failed execution...")
                log_content = ""
                if job.log_file_path and os.path.exists(job.log_file_path):
                    try:
                        with open(job.log_file_path, 'r') as f:
                            log_content = f.read()[-2000:]  # Last 2000 chars
                    except:
                        pass
                job_data['error_message'] = getattr(job, 'error_message', 'Execution failed')
                ai_analysis = self.email_service.analyze_execution_failure_with_ai(job_data, log_content)
                if 'error' not in ai_analysis:
                    print(f"[EXECUTION MONITOR] AI Analysis: Root Cause = {ai_analysis.get('root_cause', 'Unknown')}")
                    job_data['ai_analysis'] = ai_analysis
            
            # ✅ ENHANCEMENT 3 & 5: Add performance metrics and progress tracking
            job_data['performance_metrics'] = True  # Flag to include in email
            progress_info = self.email_service.track_execution_progress(job_data)
            if 'error' not in progress_info:
                job_data['progress_info'] = progress_info
                print(f"[EXECUTION MONITOR] Progress tracked: {progress_info['current_progress']['iteration']}")
            
            # Get log files
            log_files = []
            if job.log_file_path and os.path.exists(job.log_file_path):
                log_files.append(job.log_file_path)
            
            # Send email with all enhancements
            success, message = self.email_service.send_execution_results_email(
                recipient_email=user.email,
                job_data=job_data,
                log_file_paths=log_files
            )
            
            if success:
                print(f"[EXECUTION MONITOR] ✓ Sent completion report to {user.email}")
                if ai_analysis and 'error' not in ai_analysis:
                    print(f"[EXECUTION MONITOR] ✓ Included AI analysis and recommendations")
                if progress_info and 'error' not in progress_info:
                    print(f"[EXECUTION MONITOR] ✓ Included performance metrics")
            else:
                print(f"[EXECUTION MONITOR] ✗ Failed to send email: {message}")
        except Exception as e:
            print(f"[EXECUTION MONITOR] Error sending completion report: {e}")
            import traceback
            traceback.print_exc()
    
    def _send_failure_notification(self, job, reason: str):
        """Send failure notification email to user"""
        if not self.email_service or not self.email_service.enabled:
            print("[EXECUTION MONITOR] Email service not available - skipping notification")
            return
        
        try:
            # Get user email
            from models.user import User
            user = User.get_user_by_id(job.user_id)
            
            if not user or not user.email:
                print(f"[EXECUTION MONITOR] No email found for user {job.user_id}")
                return
            
            # Prepare job data
            job_data = job.to_dict()
            job_data['failure_reason'] = reason
            job_data['iterations_completed'] = len(getattr(job, 'iteration_results', {}))
            
            # Get log files
            log_files = []
            if job.log_file_path and os.path.exists(job.log_file_path):
                log_files.append(job.log_file_path)
            
            # Send email (will use execution results email with failed status)
            success, message = self.email_service.send_execution_results_email(
                recipient_email=user.email,
                job_data=job_data,
                log_file_paths=log_files
            )
            
            if success:
                print(f"[EXECUTION MONITOR] ✓ Sent failure notification to {user.email}")
            else:
                print(f"[EXECUTION MONITOR] ✗ Failed to send email: {message}")
        except Exception as e:
            print(f"[EXECUTION MONITOR] Error sending failure notification: {e}")
            import traceback
            traceback.print_exc()
    
    def _log_to_job_file(self, job, message: str):
        """Log a message to the job's log file"""
        log_file = getattr(job, 'log_file_path', None)
        
        if not log_file:
            return
        
        try:
            timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
            log_entry = f"\n[{timestamp}] {message}\n"
            
            with open(log_file, 'a') as f:
                f.write(log_entry)
        except Exception as e:
            print(f"[EXECUTION MONITOR] Error writing to log file: {e}")
