"""
Test Controller - Handles test execution requests
"""

from flask import jsonify, request
from flask_login import current_user
from models.device import Device
from models.job import Job
from models.device_lock import DeviceLock
from services.test_execution_service import TestExecutionService
from services.log_service import LogService
from config.config_eta import calculate_eta, format_eta

class TestController:
    """Controller for test execution operations"""
    
    def __init__(self, test_service: TestExecutionService, log_service: LogService):
        self.test_service = test_service
        self.log_service = log_service
    
    def execute_test(self):
        """POST /api/execute - Execute test on device"""
        try:
            # Verify user is authenticated
            if not current_user.is_authenticated:
                return jsonify({'error': 'Authentication required'}), 401
            
            data = request.json
            if not data:
                return jsonify({'error': 'No JSON data provided'}), 400
            
            device_ip = data.get('device_ip')
            execution_queue = data.get('execution_queue')  # New format: array of {method, ir_keys, voice_text}
            iterations = int(data.get('iterations', 1))
            sequence_name = data.get('sequence_name')
            
            # DEBUG: Check if conditions are present in the execution_queue
            if sequence_name:
                has_conditions = any(item.get('condition') for item in (execution_queue or []))
                print(f"🔍 [CONTROLLER] Executing sequence '{sequence_name}': {len(execution_queue or [])} queue items")
                if has_conditions:
                    print(f"  ✓ Conditions DETECTED in execution_queue")
                    for idx, item in enumerate(execution_queue or []):
                        if item.get('condition'):
                            cond = item['condition']
                            print(f"    - Step {idx + 1} ({item.get('method')}): condition with steps={[s['step']+1 for s in cond.get('steps', [])]}, logic={cond.get('logic')}")
                else:
                    print(f"  ⚠️  WARNING: No conditions found in execution_queue for sequence!")
            
            # DEDUPLICATION: Check if an identical job was just created (within last 2 seconds) on the same device
            from datetime import datetime, timedelta
            from models.job import Job
            
            two_secs_ago = (datetime.utcnow() - timedelta(seconds=2)).isoformat()
            recent_jobs = Job.load_all()
            
            for recent_job in recent_jobs:
                if (recent_job.device_ip == device_ip and 
                    recent_job.created_at > two_secs_ago and
                    recent_job.methods == [item['method'] for item in execution_queue]):
                    # Found a duplicate job created within last 2 seconds
                    print(f"🛡️ [DEDUP] Duplicate job detected! Returning existing job {recent_job.job_id}")
                    return jsonify({
                        'message': 'Job already queued (duplicate submission detected)',
                        'job_id': recent_job.job_id,
                        'is_duplicate': True
                    })
            
            # Legacy support for old format
            if not execution_queue:
                method = data.get('method')
                selected_ir_keys = data.get('selected_ir_keys', ['HOME', 'POWER'])
                voice_text = data.get('voice_text', '')
                remote_keys = data.get('remote_keys', '')
                # Convert to new format
                if isinstance(method, list):
                    execution_queue = []
                    for m in method:
                        item = {'method': m, 'ir_keys': selected_ir_keys, 'voice_text': voice_text}
                        if m == 'send_remote_keys':
                            item['remote_keys'] = remote_keys
                        execution_queue.append(item)
                else:
                    item = {'method': method, 'ir_keys': selected_ir_keys, 'voice_text': voice_text}
                    if method == 'send_remote_keys':
                        item['remote_keys'] = remote_keys
                    execution_queue = [item]
            
            # Validate device exists
            device = Device.find_by_ip(device_ip)
            if not device:
                return jsonify({'error': 'Device not found'}), 404
            
            # Check if device is locked
            if DeviceLock.is_device_locked(device_ip):
                # Device is busy, queue the job instead of returning error
                method_names = [item['method'] for item in execution_queue]
                job = Job.create_job(
                    user_id=current_user.ntid,
                    device_ip=device_ip,
                    device_name=device.name,
                    methods=method_names,
                    execution_queue=execution_queue,
                    iterations=iterations,
                    sequence_name=sequence_name
                )
                # Add job to device queue (using queue_service)
                from services.queue_service import QueueService
                queue_service = QueueService(self.test_service, self.log_service)
                if device_ip not in queue_service.device_job_queue:
                    queue_service.device_job_queue[device_ip] = []
                queue_service.device_job_queue[device_ip].append(job.to_dict())
                queue_service._save_device_job_queue()
                return jsonify({
                    'message': 'Device is busy. Job has been queued and will run when the device is free.',
                    'job_id': job.job_id,
                    'queued': True
                })
            
            # Extract method names for job tracking
            method_names = [item['method'] for item in execution_queue]
            
            # Create job record
            job = Job.create_job(
                user_id=current_user.ntid,
                device_ip=device_ip,
                device_name=device.name,
                methods=method_names,
                execution_queue=execution_queue,
                iterations=iterations,
                sequence_name=sequence_name
            )
            
            # Calculate ETA and lock device
            eta_seconds = calculate_eta(execution_queue, iterations)
            lock_acquired = DeviceLock.lock_device(
                device_ip=device_ip,
                device_name=device.name,
                user_id=current_user.ntid,
                job_id=job.job_id,
                estimated_duration_seconds=eta_seconds
            )
            
            if not lock_acquired:
                # Failed to acquire lock
                Job.update_job_status(job.job_id, 'failed')
                return jsonify({'error': 'Could not acquire device lock'}), 409
            
            # Clear log queue and realtime log file
            self.log_service.clear_realtime_log()
            
            # Start execution with job context
            print(f"🔧 [CONTROLLER] About to call execute_test_queue for job {job.job_id}")
            success = self.test_service.execute_test_queue(
                device_ip=device_ip,
                execution_queue=execution_queue,
                iterations=iterations,
                job_id=job.job_id
            )
            print(f"🔧 [CONTROLLER] execute_test_queue returned: {success}")
            
            if success:
                return jsonify({
                    'message': 'Execution started',
                    'job_id': job.job_id,
                    'eta_seconds': eta_seconds,
                    'eta_formatted': format_eta(eta_seconds)
                })
            else:
                # Unlock device and mark job as failed if execution didn't start
                DeviceLock.unlock_device(device_ip)
                Job.update_job_status(job.job_id, 'failed')
                return jsonify({'error': 'Failed to start execution'}), 500
        
        except KeyError as e:
            # Missing required field in JSON
            error_msg = f"Missing required field: {str(e)}"
            print(f"❌ [CONTROLLER ERROR] {error_msg}")
            return jsonify({'error': error_msg}), 400
        
        except ValueError as e:
            # Invalid value (e.g., iterations not an integer)
            error_msg = f"Invalid value: {str(e)}"
            print(f"❌ [CONTROLLER ERROR] {error_msg}")
            return jsonify({'error': error_msg}), 400
        
        except Exception as e:
            # Catch any unexpected errors and return JSON instead of HTML
            import traceback
            error_msg = str(e)
            error_traceback = traceback.format_exc()
            print(f"❌ [CONTROLLER ERROR] {error_msg}")
            print(f"Traceback:\n{error_traceback}")
            return jsonify({
                'error': error_msg,
                'error_type': type(e).__name__,
                'traceback': error_traceback
            }), 500
