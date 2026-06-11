"""Job model for tracking test executions and their status."""
import json
import os
import uuid
from datetime import datetime, timezone, timedelta
from utils.file_lock import FileLockManager
from config.config_eta import calculate_eta, format_eta
from config.config_paths import JOBS_FILE


class Job:
    """Job model for storing job execution information."""
    
    def __init__(self, job_id, user_id, device_ip, device_name, methods, iterations, 
                 status='pending', start_time=None, end_time=None, log_file_path=None,
                 execution_queue=None, sequence_name=None, current_step=0, current_iteration=0,
                 iteration_results=None, created_at=None, execution_type=None):
        self.job_id = job_id
        self.user_id = user_id
        self.device_ip = device_ip
        self.device_name = device_name
        self.methods = methods  # List of method names (legacy)
        self.execution_queue = execution_queue or []  # New format: [{method, irKeys, voiceText}]
        self.iterations = iterations
        self.status = status  # pending, running, completed, failed, cancelled
        self.start_time = start_time or datetime.utcnow().isoformat()
        self.end_time = end_time
        self.log_file_path = log_file_path
        self.sequence_name = sequence_name
        # execution_type: 'direct_method' (user selected methods) or 'saved_sequence' (user selected sequence)
        self.execution_type = execution_type or ('saved_sequence' if sequence_name else 'direct_method')
        self.current_step = current_step  # Track current executing step (0-based index)
        self.current_iteration = current_iteration  # Track current iteration number
        self.iteration_results = iteration_results or {}  # {iteration_num: 'passed'|'failed'}
        # FIX: Preserve created_at from JSON when loading existing jobs (don't reset to current time)
        self.created_at = created_at or datetime.utcnow().isoformat()
        
        # Log job creation for diagnostics
        print(f"✅ [JOB] Job created: {self.job_id} on device {self.device_ip}")
        print(f"✅ [JOB]   status: {self.status}")
        print(f"✅ [JOB]   start_time: {self.start_time}")
        print(f"✅ [JOB]   created_at: {self.created_at}")
        print(f"✅ [JOB]   methods: {self.methods}")
    
    def to_dict(self):
        """Convert job object to dictionary."""
        # Calculate ETA information
        eta_data = self._calculate_eta()
        
        return {
            'job_id': self.job_id,
            'user_id': self.user_id,
            'device_ip': self.device_ip,
            'device_name': self.device_name,
            'methods': self.methods,
            'execution_queue': self.execution_queue,
            'iterations': self.iterations,
            'status': self.status,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'log_file_path': self.log_file_path,
            'sequence_name': self.sequence_name,
            'execution_type': self.execution_type,
            'current_step': getattr(self, 'current_step', 0),
            'current_iteration': getattr(self, 'current_iteration', 1),
            'iteration_results': getattr(self, 'iteration_results', {}),
            'created_at': self.created_at,
            'eta_seconds': eta_data['eta_seconds'],
            'eta_formatted': eta_data['eta_formatted'],
            'time_per_iteration': eta_data['time_per_iteration'],
            'remaining_iterations': eta_data['remaining_iterations']
        }
    
    def _calculate_eta(self):
        """Calculate ETA information based on execution queue and iterations."""
        try:
            # Calculate total time for one complete iteration (INCLUDING sleep durations)
            total_time_per_iteration = calculate_eta(self.execution_queue, iterations=1)
            
            # Calculate remaining iterations (accounting for current iteration)
            current_iter = getattr(self, 'current_iteration', 1)
            remaining_iterations = self.iterations - current_iter + 1
            remaining_iterations = max(0, remaining_iterations)
            
            # If job is completed/failed/cancelled, ETA is 0
            if self.status in ['completed', 'failed', 'cancelled']:
                eta_seconds = 0
                eta_formatted = 'Done'
            elif self.status == 'pending' or self.status == 'queued':
                # Total time for all iterations (including sleep durations)
                total_eta_seconds = calculate_eta(self.execution_queue, iterations=self.iterations)
                eta_seconds = total_eta_seconds
                eta_formatted = format_eta(total_eta_seconds)
            elif self.status == 'running':
                # Calculate remaining time based on remaining iterations (including sleep)
                remaining_time_seconds = total_time_per_iteration * remaining_iterations
                eta_seconds = remaining_time_seconds
                eta_formatted = format_eta(remaining_time_seconds)
            else:
                eta_seconds = 0
                eta_formatted = 'Unknown'
            
            return {
                'eta_seconds': eta_seconds,
                'eta_formatted': eta_formatted,
                'time_per_iteration': total_time_per_iteration,
                'remaining_iterations': remaining_iterations
            }
        except Exception as e:
            print(f"Error calculating ETA for job {self.job_id}: {e}")
            return {
                'eta_seconds': 0,
                'eta_formatted': 'Error calculating ETA',
                'time_per_iteration': 0,
                'remaining_iterations': 0
            }
    
    
    @staticmethod
    def from_dict(data):
        """Create Job object from dictionary."""
        # Determine execution_type if not explicitly set (backward compatibility)
        execution_type = data.get('execution_type')
        if not execution_type:
            # For older jobs, infer from sequence_name
            execution_type = 'saved_sequence' if data.get('sequence_name') else 'direct_method'
        
        return Job(
            job_id=data['job_id'],
            user_id=data['user_id'],
            device_ip=data['device_ip'],
            device_name=data['device_name'],
            methods=data.get('methods', []),
            iterations=data['iterations'],
            status=data.get('status', 'pending'),
            start_time=data.get('start_time'),
            end_time=data.get('end_time'),
            log_file_path=data.get('log_file_path'),
            execution_queue=data.get('execution_queue', []),
            sequence_name=data.get('sequence_name'),
            current_step=data.get('current_step', 0),
            current_iteration=data.get('current_iteration', 1),
            iteration_results=data.get('iteration_results', {}),
            created_at=data.get('created_at'),  # FIX: Preserve original created_at from JSON
            execution_type=execution_type
        )
    
    @staticmethod
    def load_all():
        """Load all jobs from JSON file."""
        if not os.path.exists(JOBS_FILE):
            return []
        
        try:
            jobs_data = FileLockManager.safe_json_read(JOBS_FILE, default=[])
            if not isinstance(jobs_data, list):
                return []
            return [Job.from_dict(data) for data in jobs_data]
        except (json.JSONDecodeError, IOError):
            return []
    
    @staticmethod
    def save_all(jobs):
        """Save all jobs to JSON file with atomic write and error handling."""
        jobs_data = [job.to_dict() for job in jobs]
        try:
            FileLockManager.safe_json_write(JOBS_FILE, jobs_data, indent=2)
        except Exception as e:
            print(f"❌ Error saving jobs: {e}")
            raise
    
    @staticmethod
    def create_job(user_id, device_ip, device_name, methods, iterations, 
                   execution_queue=None, sequence_name=None):
        """Create a new job."""
        job_id = str(uuid.uuid4())
        job = Job(
            job_id=job_id,
            user_id=user_id,
            device_ip=device_ip,
            device_name=device_name,
            methods=methods,
            iterations=iterations,
            execution_queue=execution_queue,
            sequence_name=sequence_name
        )
        
        def _append_job(data):
            data_list = data if isinstance(data, list) else []
            data_list.append(job.to_dict())
            return data_list
        FileLockManager.atomic_json_update(JOBS_FILE, _append_job)
        
        # Create job log directory
        job_log_dir = os.path.join('logs', 'jobs', job_id)
        os.makedirs(job_log_dir, exist_ok=True)
        
        return job
    
    @staticmethod
    def get_job(job_id):
        """Get job by ID."""
        jobs = Job.load_all()
        for job in jobs:
            if job.job_id == job_id:
                return job
        return None
    
    @staticmethod
    def update_job_status(job_id, status, end_time=None, log_file_path=None):
        """Update job status with error handling and logging."""
        try:
            job_found = {'value': False}

            def _update(data):
                data_list = data if isinstance(data, list) else []
                for job in data_list:
                    if job.get('job_id') == job_id:
                        job_found['value'] = True
                        old_status = job.get('status')
                        job['status'] = status
                        if end_time:
                            job['end_time'] = end_time
                        if log_file_path:
                            job['log_file_path'] = log_file_path
                        print(f"[JOB] Updating job {job_id}: {old_status} -> {status}")
                        break
                return data_list

            FileLockManager.atomic_json_update(JOBS_FILE, _update)

            if job_found['value']:
                print(f"[JOB] ✅ Successfully updated job {job_id} to {status}")
                return True

            print(f"[JOB] ⚠️  Job {job_id} not found in jobs list")
            return False
            
        except Exception as e:
            print(f"[JOB] ❌ Critical error in update_job_status: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def update_job_progress(job_id, current_step, current_iteration=None):
        """Update job progress (current step and iteration)."""
        def _update(data):
            data_list = data if isinstance(data, list) else []
            updated = False
            for job in data_list:
                if job.get('job_id') == job_id:
                    job['current_step'] = current_step
                    if current_iteration is not None:
                        job['current_iteration'] = current_iteration
                    updated = True
                    break
            return data_list if updated else data_list

        FileLockManager.atomic_json_update(JOBS_FILE, _update)
        return True
    
    @staticmethod
    def update_iteration_result(job_id, iteration_num, result):
        """Update result for a specific iteration (passed/failed)."""
        def _update(data):
            data_list = data if isinstance(data, list) else []
            for job in data_list:
                if job.get('job_id') == job_id:
                    iteration_results = job.get('iteration_results') or {}
                    iteration_results[str(iteration_num)] = result
                    job['iteration_results'] = iteration_results
                    break
            return data_list

        FileLockManager.atomic_json_update(JOBS_FILE, _update)
        return True
    
    @staticmethod
    def get_running_jobs():
        """Get all running jobs."""
        jobs = Job.load_all()
        return [job for job in jobs if job.status in ['pending', 'running']]
    
    @staticmethod
    def get_user_jobs(user_id):
        """Get all jobs for a specific user."""
        jobs = Job.load_all()
        return [job for job in jobs if job.user_id == user_id]
    
    @staticmethod
    def get_device_jobs(device_ip):
        """Get all jobs for a specific device."""
        jobs = Job.load_all()
        return [job for job in jobs if job.device_ip == device_ip]
    
    @staticmethod
    def get_active_device_job(device_ip):
        """Get currently active (running/pending) job for a device."""
        jobs = Job.load_all()
        for job in jobs:
            if job.device_ip == device_ip and job.status in ['pending', 'running']:
                return job
        return None
    
    @staticmethod
    def cancel_job(job_id):
        """Cancel a pending or running job and release device lock."""
        cancelled = {
            'value': False, 
            'device_ip': None,
            'device_name': None,
            'username': None,
            'password': None,
            'port': 10022,
            'use_jump_host': False,
            'jump_host_config': None
        }

        def _update(data):
            data_list = data if isinstance(data, list) else []
            for job in data_list:
                if job.get('job_id') == job_id:
                    if job.get('status') in ['pending', 'running']:
                        job['status'] = 'cancelled'
                        job['end_time'] = datetime.utcnow().isoformat()
                        cancelled['value'] = True
                        cancelled['device_ip'] = job.get('device_ip')
                        cancelled['device_name'] = job.get('device_name')
                    break
            return data_list

        FileLockManager.atomic_json_update(JOBS_FILE, _update)

        if cancelled['value']:
            # Get device credentials to kill the running process
            from models.device import Device
            from models.device_lock import DeviceLock
            
            device_ip = cancelled['device_ip']
            
            # Get device details
            try:
                device = Device.get_by_ip(device_ip)
                if device:
                    cancelled['username'] = device.username
                    cancelled['password'] = device.password
                    cancelled['port'] = device.port if device.port else 10022
                    cancelled['use_jump_host'] = device.use_jump_host
                    cancelled['jump_host_config'] = device.jump_host_config
            except Exception as e:
                print(f"⚠ Error retrieving device details: {e}")
            
            # Kill the running process on the device
            try:
                from services.job_cancellation_service import JobCancellationService
                
                if cancelled['username'] and cancelled['password']:
                    success, message = JobCancellationService.kill_job_process_on_device(
                        device_ip=cancelled['device_ip'],
                        device_name=cancelled['device_name'] or device_ip,
                        username=cancelled['username'],
                        password=cancelled['password'],
                        port=cancelled['port'],
                        use_jump_host=cancelled['use_jump_host'],
                        jump_host_config=cancelled['jump_host_config']
                    )
                    
                    if success:
                        print(f"✓ {message}")
                    else:
                        print(f"⚠ Could not kill process: {message}")
                else:
                    print(f"⚠ Could not retrieve device credentials for {device_ip}")
                    
            except Exception as e:
                print(f"⚠ Error killing job process: {e}")
            
            # Release device lock
            if device_ip:
                DeviceLock.unlock_device(device_ip)
                print(f"🔓 Released lock for device {device_ip} after cancelling job {job_id}")
            
            return True

        return False
    
    @staticmethod
    def execute_pending_job(job_id):
        """Move a pending job to running status to trigger execution."""
        executed = {'value': False}
        
        def _update(data):
            data_list = data if isinstance(data, list) else []
            for job in data_list:
                if job.get('job_id') == job_id:
                    if job.get('status') == 'pending':
                        job['status'] = 'running'
                        job['start_time'] = datetime.utcnow().isoformat()
                        executed['value'] = True
                    break
            return data_list
        
        FileLockManager.atomic_json_update(JOBS_FILE, _update)
        return executed['value']
    
    @staticmethod
    def delete_pending_job(job_id):
        """Delete a pending job from the queue."""
        deleted = {'value': False}
        
        def _update(data):
            data_list = data if isinstance(data, list) else []
            original_length = len(data_list)
            # Filter out the job with matching job_id and pending status
            data_list = [job for job in data_list if not (job.get('job_id') == job_id and job.get('status') == 'pending')]
            if len(data_list) < original_length:
                deleted['value'] = True
            return data_list
        
        FileLockManager.atomic_json_update(JOBS_FILE, _update)
        return deleted['value']
    
    @staticmethod
    def cleanup_old_pending_jobs(days=2):
        """Auto-cancel pending jobs older than specified days and release locks."""
        jobs = Job.load_all()
        cutoff_time = datetime.now() - timedelta(days=days)
        cancelled_count = 0
        cancelled_ips = []
        
        for job in jobs:
            if job.status == 'pending':
                try:
                    created_at = datetime.fromisoformat(job.created_at)
                    if created_at < cutoff_time:
                        job.status = 'cancelled'
                        job.end_time = datetime.utcnow().isoformat()
                        cancelled_count += 1
                        cancelled_ips.append(job.device_ip)
                except (ValueError, AttributeError):
                    pass
        
        if cancelled_count > 0:
            Job.save_all(jobs)
            
            # Release device locks for cancelled jobs
            from models.device_lock import DeviceLock
            for device_ip in set(cancelled_ips):
                DeviceLock.unlock_device(device_ip)
            
            print(f"Auto-cancelled {cancelled_count} old pending jobs (>{days} days)")
        
        return cancelled_count
    
    @staticmethod
    def cleanup_old_completed_jobs(keep_days=20):
        """Remove completed/failed/cancelled jobs older than keep_days and clean up related data.
        Default keep_days=20 means keep last 20 days of job history for date filtering.
        Also removes associated log files, iteration logs, and screenshots."""
        import os
        import shutil
        
        jobs = Job.load_all()
        removed_count = 0
        kept_jobs = []
        removed_job_ids = []
        
        # Calculate cutoff time
        cutoff_time = datetime.now() - timedelta(days=keep_days)
        
        for job in jobs:
            # Always keep running/pending jobs
            if job.status in ['running', 'pending']:
                kept_jobs.append(job)
                continue
            
            # For completed/failed/cancelled, check date
            try:
                # Use start_time or created_at for date check
                job_time_str = job.start_time or job.created_at
                job_time = datetime.fromisoformat(job_time_str.split('+')[0])  # Remove timezone if present
                
                # Keep jobs newer than cutoff
                if job_time >= cutoff_time:
                    kept_jobs.append(job)
                else:
                    removed_count += 1
                    removed_job_ids.append(job.job_id)
            except (ValueError, AttributeError, IndexError):
                # If we can't parse the date, keep the job to be safe
                kept_jobs.append(job)
        
        if removed_count > 0:
            # Save updated jobs list
            Job.save_all(kept_jobs)
            print(f"Removed {removed_count} old completed jobs (older than {keep_days} days)")
            
            # Clean up related data for removed jobs
            cleanup_count = {'logs': 0, 'iteration_logs': 0, 'screenshots': 0}
            
            for job_id in removed_job_ids:
                # Remove job log directory
                job_log_dir = f"logs/jobs/{job_id}"
                if os.path.exists(job_log_dir):
                    try:
                        shutil.rmtree(job_log_dir)
                        cleanup_count['logs'] += 1
                    except Exception as e:
                        print(f"Warning: Could not remove job logs for {job_id}: {e}")
            
            # Clean up old iteration logs (older than keep_days)
            if os.path.exists('iteration_logs'):
                try:
                    for filename in os.listdir('iteration_logs'):
                        filepath = os.path.join('iteration_logs', filename)
                        if os.path.isfile(filepath):
                            file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                            if file_mtime < cutoff_time:
                                os.remove(filepath)
                                cleanup_count['iteration_logs'] += 1
                except Exception as e:
                    print(f"Warning: Error cleaning iteration_logs: {e}")
            
            # Clean up old screenshots (older than keep_days)
            if os.path.exists('screenshots'):
                try:
                    for device_folder in os.listdir('screenshots'):
                        device_path = os.path.join('screenshots', device_folder)
                        if os.path.isdir(device_path):
                            for itr_folder in os.listdir(device_path):
                                itr_path = os.path.join(device_path, itr_folder)
                                if os.path.isdir(itr_path):
                                    dir_mtime = datetime.fromtimestamp(os.path.getmtime(itr_path))
                                    if dir_mtime < cutoff_time:
                                        shutil.rmtree(itr_path)
                                        cleanup_count['screenshots'] += 1
                except Exception as e:
                    print(f"Warning: Error cleaning screenshots: {e}")
            
            # Clean up external storage (USB drive) for old execution logs and screenshots
            external_base = "/media/pi/Lexar/Enhancement_output"
            if os.path.exists(external_base):
                try:
                    # Clean up EXECUTION_LOGS by date folder
                    exec_logs_path = os.path.join(external_base, "EXECUTION_LOGS")
                    if os.path.exists(exec_logs_path):
                        for date_folder in os.listdir(exec_logs_path):
                            date_path = os.path.join(exec_logs_path, date_folder)
                            if os.path.isdir(date_path):
                                try:
                                    # Parse date folder name (YYYY-MM-DD)
                                    folder_date = datetime.strptime(date_folder, '%Y-%m-%d')
                                    if folder_date < cutoff_time:
                                        shutil.rmtree(date_path)
                                        cleanup_count['logs'] += 1
                                except (ValueError, OSError) as e:
                                    # Skip folders that don't match date format or can't be removed
                                    pass
                    
                    # Clean up root level date folders (YYYY-MM-DD format)
                    for item in os.listdir(external_base):
                        item_path = os.path.join(external_base, item)
                        if os.path.isdir(item_path) and len(item) == 10 and item.count('-') == 2:
                            try:
                                # Parse date folder name (YYYY-MM-DD)
                                folder_date = datetime.strptime(item, '%Y-%m-%d')
                                if folder_date < cutoff_time:
                                    shutil.rmtree(item_path)
                                    cleanup_count['screenshots'] += 1
                            except (ValueError, OSError) as e:
                                # Skip folders that don't match date format or can't be removed
                                pass
                except Exception as e:
                    print(f"Warning: Error cleaning external storage: {e}")
            
            print(f"Cleaned up related data - Logs: {cleanup_count['logs']}, "
                  f"Iteration Logs: {cleanup_count['iteration_logs']}, "
                  f"Screenshots: {cleanup_count['screenshots']}")
        
        return removed_count
    
    @staticmethod
    def get_pending_jobs():
        """Get all pending jobs with details."""
        # Cleanup is now done only at app startup, not on every call
        jobs = Job.load_all()
        pending = []
        
        for job in jobs:
            if job.status == 'pending':
                job_data = job.to_dict()
                try:
                    created_at = datetime.fromisoformat(job.created_at)
                    job_data['pending_duration'] = str(datetime.now() - created_at)
                    job_data['created_at_formatted'] = created_at.strftime('%Y-%m-%d %H:%M:%S')
                except (ValueError, AttributeError):
                    job_data['pending_duration'] = 'Unknown'
                    job_data['created_at_formatted'] = job.created_at
                pending.append(job_data)
        
        return sorted(pending, key=lambda x: x['created_at'], reverse=True)
    
    @staticmethod
    def get_pending_jobs_no_cleanup():
        """Get all pending jobs without triggering cleanup (for startup)."""
        jobs = Job.load_all()
        pending = []
        
        for job in jobs:
            if job.status == 'pending':
                job_data = job.to_dict()
                try:
                    created_at = datetime.fromisoformat(job.created_at)
                    job_data['pending_duration'] = str(datetime.now() - created_at)
                    job_data['created_at_formatted'] = created_at.strftime('%Y-%m-%d %H:%M:%S')
                except (ValueError, AttributeError):
                    job_data['pending_duration'] = 'Unknown'
                    job_data['created_at_formatted'] = job.created_at
                pending.append(job_data)
        
        return sorted(pending, key=lambda x: x['created_at'], reverse=True)
