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
    
    def __init__(self, test_service: TestExecutionService, log_service: LogService, queue_service=None):
        self.test_service = test_service
        self.log_service = log_service
        self.queue_service = queue_service
    
    def execute_test(self):
        """POST /api/execute - Execute test on device with R-Pi grouping"""
        try:
            # Debug: Check authentication status
            import sys
            print(f"\n{'='*60}", file=sys.stderr)
            print(f"🔍 [DEBUG /api/execute] Request headers:", file=sys.stderr)
            print(f"   Cookie: {request.headers.get('Cookie', 'NO COOKIE')}", file=sys.stderr)
            print(f"   User-Agent: {request.headers.get('User-Agent', 'N/A')[:50]}", file=sys.stderr)
            print(f"   Host: {request.host}", file=sys.stderr)
            print(f"   Request path: {request.path}", file=sys.stderr)
            print(f"🔍 [DEBUG] current_user object: {current_user}", file=sys.stderr)
            print(f"🔍 [DEBUG] is_authenticated: {current_user.is_authenticated}", file=sys.stderr)
            if hasattr(current_user, 'ntid'):
                print(f"🔍 [DEBUG] User NTID: {current_user.ntid}", file=sys.stderr)
            print(f"{'='*60}\n", file=sys.stderr)
            
            # Verify user is authenticated
            if not current_user.is_authenticated:
                print(f"❌ [DEBUG] User not authenticated - returning 401", file=sys.stderr)
                # Still try to get more info
                user_id = request.cookies.get('session')
                print(f"   Session cookie value (partial): {user_id[:20] if user_id else 'NO SESSION COOKIE'}...", file=sys.stderr)
                return jsonify({'error': 'Authentication required', 'debug': 'Not authenticated. Check session cookie.'}), 401
            
            print(f"✅ [DEBUG] User authenticated: {current_user.ntid if hasattr(current_user, 'ntid') else 'UNKNOWN'}", file=sys.stderr)
            
            # ✨ NEW: Import R-Pi Connection Group Manager
            from services.rpi_connection_group_manager import get_rpi_connection_manager
            
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
            
            # ✨ MANDATORY: Validate R-Pi configuration BEFORE creating job
            # This ensures immediate feedback if device lacks R-Pi config
            if not device.rpi_config or not device.rpi_config.get('rpi_ip'):
                error_msg = (
                    f"Device '{device.name}' ({device_ip}) does NOT have R-Pi configuration. "
                    f"All execution REQUIRES R-Pi tunnel. "
                    f"Please configure R-Pi settings (IP, port, username, password) for this device in the Device Management panel."
                )
                print(f"❌ [CONTROLLER] R-Pi Config Validation FAILED: {error_msg}")
                return jsonify({
                    'error': error_msg,
                    'error_code': 'RPI_CONFIG_MISSING',
                    'device_name': device.name,
                    'device_ip': device_ip
                }), 400
            
            print(f"✅ [CONTROLLER] R-Pi config validated for device {device.name}: R-Pi={device.rpi_config.get('rpi_ip')}")
            
            # ✨ NEW: R-Pi Connection Grouping
            # Get R-Pi connection manager and prepare R-Pi connection
            rpi_manager = get_rpi_connection_manager()
            
            # For single device, still use grouping manager for consistency
            rpi_prep_result = rpi_manager.prepare_execution_with_rpi_grouping([device])
            
            if not rpi_prep_result.get('success'):
                print(f"⚠️  [R-Pi Grouping] Warning: {rpi_prep_result.get('message')}", file=sys.stderr)
                # Don't fail - device execution can continue without R-Pi if available
            
            print(f"✅ [R-Pi Grouping] Preparation result: {rpi_prep_result.get('message')}", file=sys.stderr)
            
            # ✨ YOUR APPROACH: Simplified execution flow
            # Don't wait for companion jobs in request handler
            # Let execution service detect and share tunnels during execution
            print(f"\n[EXECUTE] Creating job for {device.name} ({device_ip})", file=sys.stderr)
            
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
                    sequence_name=sequence_name,
                    team_name=getattr(current_user, 'team_name', '')
                )
                # Add job to device queue (using global queue_service)
                if self.queue_service:
                    if device_ip not in self.queue_service.device_job_queue:
                        self.queue_service.device_job_queue[device_ip] = []
                    self.queue_service.device_job_queue[device_ip].append(job.to_dict())
                    self.queue_service._save_device_job_queue()
                    print(f"✅ [CONTROLLER] Job {job.job_id} added to queue for device {device_ip}")
                else:
                    print(f"⚠️  [CONTROLLER] No queue_service available, job may not execute!")
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
                sequence_name=sequence_name,
                team_name=getattr(current_user, 'team_name', '')
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
            
            # Start execution with job context and R-Pi connection
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

    def execute_test_multiple(self):
        """POST /api/execute-multiple - Execute test on multiple devices with R-Pi grouping"""
        try:
            data = request.json
            if not data:
                return jsonify({'error': 'No JSON data provided'}), 400
            
            device_ips = data.get('device_ips')  # Array of device IPs
            execution_queue = data.get('execution_queue')
            iterations = int(data.get('iterations', 1))
            sequence_name = data.get('sequence_name')
            
            if not device_ips or not isinstance(device_ips, list) or len(device_ips) == 0:
                return jsonify({'error': 'device_ips must be a non-empty array'}), 400
            
            if len(device_ips) == 1:
                # Single device - fallback to single-device execution
                data['device_ip'] = device_ips[0]
                return self.execute_test()
            
            print(f"\n🔵 [MULTI-DEVICE] Executing on {len(device_ips)} devices: {device_ips}")
            
            # Load all devices
            devices = []
            for device_ip in device_ips:
                device = Device.find_by_ip(device_ip)
                if not device:
                    return jsonify({'error': f'Device not found: {device_ip}'}), 404
                devices.append(device)
            
            # ✨ MANDATORY: Validate R-Pi configuration for ALL devices BEFORE creating jobs
            # This ensures immediate feedback if any device lacks R-Pi config
            devices_missing_rpi = []
            for device in devices:
                if not device.rpi_config or not device.rpi_config.get('rpi_ip'):
                    devices_missing_rpi.append({
                        'name': device.name,
                        'ip': device.ip
                    })
            
            if devices_missing_rpi:
                error_msg = (
                    f"The following {len(devices_missing_rpi)} device(s) do NOT have R-Pi configuration: "
                    f"{', '.join([d['name'] for d in devices_missing_rpi])}. "
                    f"All execution REQUIRES R-Pi tunnel. "
                    f"Please configure R-Pi settings for these devices in the Device Management panel."
                )
                print(f"❌ [MULTI-DEVICE] R-Pi Config Validation FAILED: {error_msg}")
                return jsonify({
                    'error': error_msg,
                    'error_code': 'RPI_CONFIG_MISSING',
                    'devices_missing_rpi': devices_missing_rpi
                }), 400
            
            print(f"✅ [MULTI-DEVICE] R-Pi config validated for all {len(devices)} devices")
            
            # Check device locks
            locked_devices = [ip for ip in device_ips if DeviceLock.is_device_locked(ip)]
            if locked_devices:
                return jsonify({
                    'error': f'Some devices are busy: {", ".join(locked_devices)}',
                    'locked_devices': locked_devices
                }), 409
            
            # ✨ NEW: R-Pi CONNECTION GROUPING
            # Collect R-Pi configs, deduplicate, and establish connections BEFORE execution
            from services.rpi_connection_group_manager import get_rpi_connection_manager
            
            print(f"🔵 [MULTI-DEVICE] Starting R-Pi grouping preparation...")
            rpi_manager = get_rpi_connection_manager()
            
            try:
                rpi_prep_result = rpi_manager.prepare_execution_with_rpi_grouping(devices)
            except Exception as rpi_error:
                print(f"❌ [R-Pi Grouping] Exception during preparation: {str(rpi_error)}")
                import traceback
                print(f"   Traceback: {traceback.format_exc()}")
                raise
            
            if not rpi_prep_result.get('success'):
                print(f"❌ [R-Pi Grouping] Failed: {rpi_prep_result.get('message')}")
                return jsonify({
                    'error': f"R-Pi connection preparation failed: {rpi_prep_result.get('message')}",
                    'rpi_failures': rpi_prep_result.get('failed_rpi_keys', [])
                }), 500
            
            print(f"✅ [R-Pi Grouping] {rpi_prep_result.get('unique_rpi_count')} unique R-Pi connection(s) established")
            print(f"📊 R-Pi Device Mapping:")
            for rpi_key, devices_on_rpi in rpi_prep_result.get('rpi_to_devices_mapping', {}).items():
                print(f"   • R-Pi [{rpi_key}]: {len(devices_on_rpi)} device(s)")
                for dev_info in devices_on_rpi:
                    print(f"     - {dev_info['name']} ({dev_info['ip']})")
            
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
            
            # Extract method names for job tracking
            method_names = [item['method'] for item in execution_queue]
            
            # Create job records for each device and acquire locks
            job_ids = []
            for device in devices:
                job = Job.create_job(
                    user_id=current_user.ntid,
                    device_ip=device.ip,
                    device_name=device.name,
                    methods=method_names,
                    execution_queue=execution_queue,
                    iterations=iterations,
                    sequence_name=sequence_name,
                    team_name=getattr(current_user, 'team_name', '')
                )
                job_ids.append(job.job_id)
                
                # Calculate ETA and lock device
                from config.config_eta import calculate_eta
                eta_seconds = calculate_eta(execution_queue, iterations)
                lock_acquired = DeviceLock.lock_device(
                    device_ip=device.ip,
                    device_name=device.name,
                    user_id=current_user.ntid,
                    job_id=job.job_id,
                    estimated_duration_seconds=eta_seconds
                )
                
                if not lock_acquired:
                    # Failed to acquire lock - rollback all previous locks and mark jobs as failed
                    for prev_job_id in job_ids[:-1]:  # All except current (current hasn't started yet)
                        prev_job = Job.find_by_id(prev_job_id)
                        if prev_job:
                            DeviceLock.unlock_device(prev_job.device_ip)
                            Job.update_job_status(prev_job_id, 'failed')
                    Job.update_job_status(job.job_id, 'failed')
                    return jsonify({
                        'error': f'Could not acquire lock for device {device.name}'
                    }), 409
            
            # All locks acquired successfully - now execute with R-Pi grouping
            print(f"✅ [MULTI-DEVICE] All locks acquired. Executing on {len(devices)} devices via {rpi_prep_result.get('unique_rpi_count')} R-Pi(s)")
            print(f"   Job IDs: {job_ids}")
            
            # ✨ IMPORTANT: Execute in BACKGROUND THREAD to avoid blocking the response
            # This allows the frontend to immediately close the modal and show job status
            # while execution happens asynchronously in the backend
            import threading
            
            def execute_async():
                """Run multi-device execution in background thread"""
                print(f"🔷 [ASYNC-EXEC] Background thread started for {len(devices)} devices")
                try:
                    results = self.test_service.execute_tests_for_multiple_devices(
                        devices=devices,
                        execution_queue=execution_queue,
                        iterations=iterations,
                        job_id=job_ids
                    )
                    print(f"🔷 [ASYNC-EXEC] Background execution completed! Results: {type(results)}")
                except Exception as async_error:
                    print(f"❌ [ASYNC-EXEC] Background execution error: {str(async_error)}")
                    import traceback
                    print(f"Traceback: {traceback.format_exc()}")
            
            # Start execution in background thread (non-blocking)
            execution_thread = threading.Thread(
                target=execute_async,
                daemon=False,
                name=f"MultiDeviceExec-{len(devices)}devices"
            )
            execution_thread.start()
            
            # Immediately return success without waiting for execution to complete
            # Jobs are already created and locked, execution happens in background
            print(f"✅ [MULTI-DEVICE] Background execution thread started (non-blocking)")
            return jsonify({
                'message': 'Multi-device execution started with R-Pi grouping',
                'job_ids': job_ids,
                'device_count': len(devices),
                'unique_rpi_count': rpi_prep_result.get('unique_rpi_count'),
                'eta_seconds': eta_seconds,
                'status': 'BACKGROUND_EXECUTION_STARTED'
            })
        
        except KeyError as e:
            error_msg = f"Missing required field: {str(e)}"
            print(f"❌ [MULTI-DEVICE ERROR] {error_msg}")
            return jsonify({'error': error_msg}), 400
        
        except ValueError as e:
            error_msg = f"Invalid value: {str(e)}"
            print(f"❌ [MULTI-DEVICE ERROR] {error_msg}")
            return jsonify({'error': error_msg}), 400
        
        except Exception as e:
            import traceback
            error_msg = str(e)
            error_traceback = traceback.format_exc()
            print(f"\n❌ [MULTI-DEVICE ERROR] Exception occurred!")
            print(f"   Error Message: {error_msg}")
            print(f"   Error Type: {type(e).__name__}")
            print(f"   Traceback:\n{error_traceback}")
            return jsonify({
                'error': error_msg,
                'error_type': type(e).__name__,
                'traceback': error_traceback
            }), 500
