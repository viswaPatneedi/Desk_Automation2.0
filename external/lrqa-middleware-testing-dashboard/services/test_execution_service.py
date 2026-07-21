"""
Test Execution Service - Business logic for test execution
Orchestrates test method execution and result management
"""

import threading
import os
import time as time_module
from datetime import datetime, timezone
from typing import List, Optional
from models.device import Device
from models.test_result import TestResult
from models.job import Job
from models.device_lock import DeviceLock
from utils.device_lock_manager import DeviceLockManager
from methods.method_reboot import execute_reboot_process
from methods.method_deepsleep import execute_deepsleep_process
from methods.method_ir_test import execute_ir_test_process
from methods.method_voice_command import execute_voice_command_process
from methods.method_reboot_performance import execute_reboot_performance_process
from methods.method_reboot_performance_v2 import execute_reboot_performance_v2_process
from methods.method_reboot_perf_v2_optimized import execute_reboot_perf_v2_optimized_process
from methods.method_trail import execute_trail_method_process
from methods.method_soft_hard_boot import execute_soft_hard_boot_process
from methods.method_standby_deep_sleep_ir_control import execute_standby_deep_sleep_ir_control_process
from methods.method_validate_results import validate_command_output
from methods.method_system_command import execute_system_command
from methods.method_execute_command import execute_system_command as execute_command
from methods.method_activate_flux import activate_flux_widget
from methods.method_navigate_to_tiles import navigate_to_tiles
from methods.method_collect_device_logs import collect_device_logs
from methods.method_check_logs import execute_check_logs
from methods.method_maintenance_deepsleep_wakeup import execute_maintenance_deepsleep_wakeup_process
from methods.method_maintenance_CURL_deepsleep_wakeup import execute_maintenance_CURL_deepsleep_wakeup_process
from methods.method_deepsleep_maintenance_wakeup import execute_deepsleep_maintenance_wakeup_process

class TestExecutionService:
    """Service for managing test execution"""
    
    def __init__(self, recovery_service=None):
        self.recovery_service = recovery_service
        self.current_html_results = []
        self.last_device_ip = None
        self.last_method = None
        self.last_iterations = 0
        self.device_results_history = {}
        self.last_method_result = {}  # Store last method result for passing data between methods
        self.voice_command_text = {}  # Store voice command text per device
        self.cross_method_data = {}  # Store persistent data across method executions (e.g., flux_server_ip_port)
    
    def execute_test(self, device_ip: str, methods: str | List[str], iterations: int,
                    selected_ir_keys: Optional[List[str]] = None, voice_text: Optional[str] = None) -> bool:
        """
        Execute test method(s) on a device
        
        Args:
            device_ip: IP address of the device
            methods: Single method or list of methods to execute
            iterations: Number of iterations to run
            selected_ir_keys: IR keys to test (for IR test method)
            voice_text: Voice command text (for voice command method)
        
        Returns:
            bool: True if execution started successfully
        """
        # Store voice command text for this device
        if voice_text:
            self.voice_command_text[device_ip] = voice_text
        
        # Get device from model
        device = Device.find_by_ip(device_ip)
        if not device:
            return False
        
        # Convert single method to list
        if isinstance(methods, str):
            methods_list = [methods]
        else:
            methods_list = methods
        
        # Reset execution context
        self.current_html_results = []
        self.last_device_ip = device_ip
        self.last_method = ','.join(methods_list)
        self.last_iterations = iterations
        
        # Execute in background thread
        thread = threading.Thread(
            target=self._execute_method_sequence,
            args=(device, methods_list, iterations, selected_ir_keys, voice_text)
        )
        thread.daemon = True
        thread.start()
        
        return True
    
    def execute_test_queue(self, device_ip: str, execution_queue: List[dict], iterations: int, 
                          job_id: Optional[str] = None, sequence_name: Optional[str] = None) -> bool:
        """
        Execute test queue with individual inputs for each method
        
        Args:
            device_ip: IP address of the device
            execution_queue: List of {method: str, ir_keys: list, voice_text: str}
            iterations: Number of iterations to run
            job_id: Job ID for tracking (optional)
            sequence_name: Name of the sequence being executed (optional)
        
        Returns:
            bool: True if execution started successfully
        """
        # Get device from model
        device = Device.find_by_ip(device_ip)
        if not device:
            return False
        
        # Reset execution context
        self.current_html_results = []
        self.last_device_ip = device_ip
        method_names = [item['method'] for item in execution_queue]
        self.last_method = ','.join(method_names)
        self.last_iterations = iterations
        
        # Execute in background thread
        print(f"🔧 [DEBUG] Creating thread for job {job_id}, device {device_ip}")
        thread = threading.Thread(
            target=self._execute_queue_sequence,
            args=(device, execution_queue, iterations, job_id, sequence_name)
        )
        thread.daemon = True
        thread.start()
        print(f"🔧 [DEBUG] Thread started for job {job_id}")
        
        return True
    
    def _execute_queue_sequence(self, device: Device, execution_queue: List[dict], iterations: int, 
                               job_id: Optional[str] = None, sequence_name: Optional[str] = None):
        """Execute queue sequence with individual inputs (internal)"""
        print(f"🔧 [DEBUG] _execute_queue_sequence started for job {job_id}")
        from services.log_service import LogService
        import threading
        
        log_service = LogService()
        method_names = [item['method'] for item in execution_queue]
        log_file_handle = None
        print(f"🔧 [DEBUG] Executing methods: {method_names} on device {device.ip}")
        
        # Store combined methods and sequence name for this thread (for screenshot folder naming)
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from methods.method_utils import set_execution_methods
        thread_id = threading.get_ident()
        set_execution_methods(thread_id, method_names, sequence_name)
        
        # Use job-specific log directory if job_id provided
        if job_id:
            job_log_dir = f"logs/jobs/{job_id}"
            os.makedirs(job_log_dir, exist_ok=True)
            log_file_path = os.path.join(job_log_dir, 'execution.log')
            
            # Create USB execution session folder for screenshots and device logs
            from utils.session_utils import create_execution_session_folder
            
            # Use sequence name if available, otherwise use truncated method list
            if sequence_name:
                folder_method_name = sequence_name.replace(' ', '_').replace(',', '_')
            else:
                # Use first 3 methods for folder name
                method_list = method_names[:3]
                if len(method_names) > 3:
                    folder_method_name = ','.join(method_list) + f'+{len(method_names)-3}more'
                else:
                    folder_method_name = ','.join(method_list)
            
            usb_session_folder, screenshots_dir, execution_logs_dir, device_logs_dir = create_execution_session_folder(
                folder_method_name, device.name, device.ip, iterations
            )
            session_folder = usb_session_folder
            
            # Set log service to write to job-specific log file
            log_file_handle = open(log_file_path, 'a', encoding='utf-8')
            log_service.current_log_handle = log_file_handle
            log_service.current_log_file = log_file_path
            print(f"🔧 [DEBUG] Job log file created at: {log_file_path}")
            print(f"🔧 [DEBUG] USB session folder: {usb_session_folder}")
            print(f"🔧 [DEBUG] Screenshots folder: {screenshots_dir}")
        else:
            session_folder = log_service.create_iteration_log(device.ip, ','.join(method_names))
            log_file_path = None
        
        # Update job status to running and set log file path
        if job_id:
            print(f"✅ [EXECUTION] Updating job {job_id} status to RUNNING")
            Job.update_job_status(job_id, 'running', log_file_path=log_file_path)
            # Verify the status was updated
            updated_job = Job.get_job(job_id)
            if updated_job:
                print(f"✅ [EXECUTION] Job {job_id} status after update: {updated_job.status}")
            else:
                print(f"❌ [EXECUTION] Failed to retrieve job {job_id} after status update")
        
        try:
            # Determine starting iteration (for job resumption)
            start_iteration = 0
            resume_step = 0
            if job_id:
                # Load job to check if it has a current_iteration set (job resumption)
                job = Job.get_job(job_id)
                if job and job.current_iteration > 0:
                    # Resume from the current_iteration (which is 1-indexed)
                    start_iteration = job.current_iteration - 1  # Convert to 0-indexed
                    resume_step = getattr(job, 'current_step', 0)
                    # If the last recorded step is past the queue length, move to next iteration
                    if resume_step >= len(execution_queue):
                        start_iteration += 1
                        resume_step = 0
                    print(f"🔧 [RESUMING] Job {job_id} will resume from iteration {start_iteration + 1} (0-indexed start: {start_iteration}), step {resume_step}")
                    if start_iteration < iterations:
                        log_service.log(f"\n[RESUMING JOB] Continuing from iteration {start_iteration + 1}/{iterations}")
            
            # Save execution context for recovery
            if self.recovery_service:
                self.recovery_service.save_execution_context(
                    device_ip=device.ip,
                    method=','.join(method_names),
                    iteration=start_iteration,
                    total_iterations=iterations,
                    session_folder=session_folder
                )
            
            for i in range(start_iteration, iterations):
                # Check if job has been cancelled
                if job_id:
                    current_job = Job.get_job(job_id)
                    if current_job and current_job.status == 'cancelled':
                        log_service.log(f"\n{'='*60}")
                        log_service.log(f"⛔ JOB CANCELLED - Stopping execution")
                        log_service.log(f"{'='*60}")
                        print(f"✓ Job {job_id} was cancelled, exiting iteration loop")
                        break
                
                # TIMING: Record iteration start time for ETA calculation
                iteration_start_time = time_module.time()
                
                log_service.log(f"\n{'='*60}")
                log_service.log(f"ITERATION {i+1}/{iterations}")
                log_service.log(f"{'='*60}")
                
                # CRITICAL: Refresh lock at the START of each iteration (including first if needed)
                # This ensures the lock is always valid before starting execution
                if job_id and i >= start_iteration:
                    remaining_iterations = iterations - i
                    if not DeviceLockManager.refresh_lock(device.ip, job_id, execution_queue, remaining_iterations):
                        log_service.log(f"\n❌ CRITICAL: Device lock lost or expired!")
                        log_service.log(f"⚠️  Device {device.ip} is no longer reserved for job {job_id}")
                        log_service.log(f"   Current iteration: {i+1}/{iterations}")
                        log_service.log(f"   Remaining iterations: {remaining_iterations}")
                        if job_id:
                            Job.update_job_status(job_id, 'failed', 
                                end_time=datetime.now(timezone.utc).isoformat(),
                                log_file_path=log_file_path
                            )
                            DeviceLock.unlock_device(device.ip)
                        raise RuntimeError(f"Device lock lost or expired: {device.ip}")
                    
                    time_remaining = DeviceLock.get_time_until_expiration(device.ip)
                    hours = time_remaining // 3600
                    minutes = (time_remaining % 3600) // 60
                    log_service.log(f"🔒 [LOCK-REFRESH] Lock refreshed for remaining {remaining_iterations} iterations")
                    log_service.log(f"   Time remaining: {hours}h {minutes}m")
                
                # Reset cross-method data for this iteration (but preserve flux_server_ip_port across methods within same iteration)
                # self.cross_method_data is NOT reset here - it persists within an iteration to allow cross-method data passing
                
                # Build combined method name for folder structure (e.g., "REBOOT-VOICECOMMAND")
                combined_method_name = '-'.join([item['method'].upper() for item in execution_queue])
                
                # Check if deepsleep is in the execution queue
                has_deepsleep = any(item['method'] == 'deepsleep' for item in execution_queue)
                
                # Update recovery checkpoint
                if self.recovery_service:
                    self.recovery_service.save_execution_context(
                        device_ip=device.ip,
                        method=','.join(method_names),
                        iteration=i + 1,
                        total_iterations=iterations,
                        session_folder=session_folder
                    )
                
                # Track step results for conditional execution
                step_results = {}
                
                # Collect method results for sequence consolidation
                iteration_method_results = []
                is_multi_method_sequence = len(execution_queue) > 1 and sequence_name
                skipped_groups = set()  # Track which condition groups have been skipped
                
                # Debug logging for sequence consolidation
                if sequence_name:
                    log_service.log(f"\n[DEBUG] Sequence detected: {sequence_name}")
                    log_service.log(f"[DEBUG] Execution queue length: {len(execution_queue)}")
                    log_service.log(f"[DEBUG] is_multi_method_sequence: {is_multi_method_sequence}")
                    
                    # CRITICAL: Verify conditions are present in execution_queue
                    has_conditions = any(item.get('condition') for item in execution_queue)
                    log_service.log(f"[DEBUG] Queue items with conditions: {has_conditions}")
                    if has_conditions:
                        for idx, item in enumerate(execution_queue):
                            if item.get('condition'):
                                cond = item['condition']
                                log_service.log(f"  ✓ Step {idx + 1} ({item.get('method')}): HAS condition - steps={cond.get('steps')}, logic={cond.get('logic')}")
                            else:
                                log_service.log(f"  ✗ Step {idx + 1} ({item.get('method')}): NO condition found")
                    else:
                        log_service.log(f"[WARNING] ⚠️  NO conditions found in execution_queue! Conditions may not have been passed from frontend.")
                
                method_start_index = resume_step if i == start_iteration else 0
                for method_index, queue_item in enumerate(execution_queue[method_start_index:], start=method_start_index):
                    # Check if job has been cancelled before processing this method
                    if job_id:
                        current_job = Job.get_job(job_id)
                        if current_job and current_job.status == 'cancelled':
                            log_service.log(f"\n⛔ JOB CANCELLED - Stopping method execution at Step {method_index + 1}")
                            print(f"✓ Job {job_id} was cancelled during method execution, breaking out")
                            break
                    
                    method = queue_item['method']
                    
                    # Check if this step has a condition
                    condition = queue_item.get('condition')
                    if condition:
                        # CONDITION FOUND - Log and execute conditional logic
                        log_service.log(f"[CONDITION-CHECK] Step {method_index + 1} ({method}): Condition found - evaluating...")
                        condition_steps = condition.get('steps', [])
                        depends_on = [f'Step {s["step"]+1}' for s in condition_steps]
                        log_service.log(f"[CONDITION-CHECK]   Depends on: {depends_on}")
                        log_service.log(f"[CONDITION-CHECK]   Logic: {condition.get('logic', 'AND')}")
                        log_service.log(f"[CONDITION-CHECK]   Current step_results: {step_results}")
                        
                        group_id = condition.get('group_id')
                        grouped_steps = condition.get('grouped_steps', [])
                        is_group_leader = condition.get('is_group_leader', False)
                        
                        # Check if this group was already skipped
                        if group_id and group_id in skipped_groups:
                            log_service.log(f"\n⏭️  Skipping Step {method_index + 1}: {method.upper()} - Part of skipped condition block")
                            step_results[method_index] = None  # Mark as skipped (not executed)
                            continue
                        
                        # Support both new format (multiple steps) and old format (single step)
                        should_execute = False
                        condition_summary = ""
                        
                        if condition.get('steps') and len(condition['steps']) > 0:
                            # New format: multiple steps with individual types
                            condition_steps = condition['steps']
                            logic = condition.get('logic', 'AND')
                            
                            results = []
                            summary_parts = []
                            
                            for cond in condition_steps:
                                dep_step = cond['step']
                                cond_type = cond.get('type', 'if_passed')
                                
                                if dep_step in step_results:
                                    dep_passed = step_results[dep_step]
                                    # Evaluate individual condition
                                    cond_result = (cond_type == 'if_passed' and dep_passed) or \
                                                 (cond_type == 'if_failed' and not dep_passed)
                                    results.append(cond_result)
                                    summary_parts.append(f"Step {dep_step + 1} {'PASS' if cond_type == 'if_passed' else 'FAIL'}")
                            
                            # Apply logic operator
                            if len(results) > 0:
                                if logic == 'OR':
                                    should_execute = any(results)
                                else:  # AND (default)
                                    should_execute = all(results)
                                # Build condition summary string
                                cond_parts = []
                                for cond in condition_steps:
                                    step_num = cond['step'] + 1
                                    cond_type = cond.get('type', 'if_passed')
                                    type_str = 'PASS' if cond_type == 'if_passed' else 'FAIL'
                                    cond_parts.append(f'Step {step_num} {type_str}')
                                condition_summary = f" ({f' {logic} '.join(cond_parts)})"
                        else:
                            # Old format: single step (backward compatibility)
                            dependent_step = condition.get('step')
                            condition_type = condition.get('type', 'if_passed')
                            
                            if dependent_step in step_results:
                                dependent_passed = step_results[dependent_step]
                                # Evaluate condition
                                should_execute = (condition_type == 'if_passed' and dependent_passed) or \
                                               (condition_type == 'if_failed' and not dependent_passed)
                                condition_summary = f" (Step {dependent_step + 1} {'PASS' if condition_type == 'if_passed' else 'FAIL'})"
                        
                        if not should_execute and (condition.get('steps') or condition.get('step') is not None):
                            # Mark entire group as skipped
                            if group_id:
                                skipped_groups.add(group_id)
                                if is_group_leader:
                                    log_service.log(f"\n⏭️  Skipping Condition Block (Steps {min(grouped_steps)+1}-{max(grouped_steps)+1}) - Condition not met{condition_summary}")
                                else:
                                    log_service.log(f"\n⏭️  Skipping Step {method_index + 1}: {method.upper()} - Part of skipped condition block")
                            else:
                                log_service.log(f"\n⏭️  Skipping Step {method_index + 1}: {method.upper()} - Condition not met{condition_summary}")
                            step_results[method_index] = None  # Mark as skipped (not executed)
                            continue
                        elif should_execute and (condition.get('steps') or condition.get('step') is not None):
                            if is_group_leader:
                                log_service.log(f"\n✓ Condition met for Block (Steps {min(grouped_steps)+1}-{max(grouped_steps)+1}){condition_summary}")
                            else:
                                log_service.log(f"\n✓ Condition met for Step {method_index + 1}{condition_summary}")
                    else:
                        # NO CONDITION for this step - will execute unconditionally
                        log_service.log(f"[CONDITION-CHECK] Step {method_index + 1} ({method}): NO condition (will execute unconditionally)")

                    
                    # Update job progress (current step and iteration) before execution
                    if job_id:
                        try:
                            Job.update_job_progress(job_id, method_index, i + 1)
                        except Exception as progress_error:
                            print(f"⚠️ Warning: Could not update job progress: {progress_error}")
                            # Continue execution even if progress update fails
                    
                    # Debug: Log only method-relevant parameters to reduce noise
                    filtered = {"method": method}
                    if method == "memcapture_tool":
                        filtered.update({
                            "system_command_name": queue_item.get("system_command_name", ""),
                            "system_command_label": queue_item.get("system_command_label", ""),
                            "duration_seconds": queue_item.get("duration_seconds", 300),
                            "interval_seconds": queue_item.get("interval_seconds", 10),
                            "command": queue_item.get("command", "")
                        })
                    elif method == "execute_command":
                        filtered.update({
                            "command_text": queue_item.get("command_text", "")
                        })
                    elif method == "validate_results":
                        filtered.update({
                            "command": queue_item.get("command", ""),
                            "expected_output": queue_item.get("expected_output", ""),
                            "validation_type": queue_item.get("validation_type", "contains")
                        })
                    elif method == "voice_command":
                        filtered["voice_text"] = queue_item.get("voice_text", "")
                    elif method == "send_remote_keys":
                        filtered["remote_keys"] = queue_item.get("remote_keys", "")
                    elif method == "ir_test":
                        filtered["ir_keys"] = queue_item.get("ir_keys", [])
                        filtered["remote_type"] = queue_item.get("remote_type", "")
                    elif method == "wait":
                        filtered["wait_seconds"] = queue_item.get("wait_seconds", 0)
                    elif method == "screen_validation":
                        filtered["expected_screen"] = queue_item.get("expected_screen", "")
                        filtered["screen_name"] = queue_item.get("screen_name", "")
                    elif method in {"reboot_performance_v2", "reboot_perf_v2_optimized", "soft_hard_boot", "trail_method"}:
                        filtered["home_screen_timeout"] = queue_item.get("home_screen_timeout", 180)
                        if "optional_checks" in queue_item:
                            filtered["optional_checks"] = queue_item.get("optional_checks")
                        if "boot_type" in queue_item:
                            filtered["boot_type"] = queue_item.get("boot_type")
                        # For trail_method, also include log collection parameters
                        if method == "trail_method":
                            filtered["log_search_patterns"] = queue_item.get("log_search_patterns", [])
                            filtered["auto_collect_logs"] = queue_item.get("auto_collect_logs", False)
                    elif method == "deepsleep":
                        filtered["remote_type"] = queue_item.get("remote_type", "auto-detect")
                        filtered["sleep_duration_minutes"] = queue_item.get("sleep_duration_minutes", 60)
                    elif method == "maintenance_deepsleep_wakeup":
                        filtered["remote_type"] = queue_item.get("remote_type", "")
                        filtered["sleep_duration_minutes"] = queue_item.get("sleep_duration_minutes", 60)
                        filtered["execute_deepsleep_wakeup"] = queue_item.get("execute_deepsleep_wakeup", True)
                    elif method == "maintenance_CURL_deepsleep_wakeup":
                        filtered["remote_type"] = queue_item.get("remote_type", "")
                        filtered["sleep_duration_minutes"] = queue_item.get("sleep_duration_minutes", 1)
                        filtered["execute_deepsleep_wakeup"] = queue_item.get("execute_deepsleep_wakeup", True)
                    elif method == "deepsleep_maintenance_wakeup":
                        filtered["remote_type"] = queue_item.get("remote_type", "")
                    elif method == "standby_deep_sleep_ir_control":
                        filtered["remote_type"] = queue_item.get("remote_type", "")
                    log_service.log(f"DEBUG: queue_item keys = {list(filtered.keys())}")
                    log_service.log(f"DEBUG: queue_item = {filtered}")
                    log_service.log(f"DEBUG: actual queue_item (unfiltered) = {queue_item}")
                    
                    ir_keys = queue_item.get('ir_keys', ['HOME', 'POWER'])
                    remote_type = queue_item.get('remote_type')
                    voice_text = queue_item.get('voice_text', '')
                    remote_keys = queue_item.get('remote_keys', None)
                    expected_screen = queue_item.get('expected_screen', None)
                    screen_name = queue_item.get('screen_name', None)
                    wait_seconds = queue_item.get('wait_seconds', 0)
                    
                    # Normalize parameters - handle both camelCase and snake_case from frontend
                    if remote_keys is None:
                        remote_keys = queue_item.get('remoteKeys', None)
                    if voice_text == '':
                        voice_text = queue_item.get('voiceText', '')
                    if not ir_keys or len(ir_keys) == 0:
                        ir_keys = queue_item.get('irKeys', ['HOME', 'POWER'])
                    if not remote_type:
                        remote_type = queue_item.get('remoteType')
                    if expected_screen is None:
                        expected_screen = queue_item.get('expectedScreen', None)
                    if screen_name is None:
                        screen_name = queue_item.get('screenName', None)
                    if wait_seconds == 0:
                        wait_seconds = queue_item.get('waitSeconds', 0)

                    log_service.log(f"\n--- Executing: {method.upper()} (Step {method_index + 1}/{len(execution_queue)}) ---")

                    method_result = None
                    if method == "reboot":
                        # Pass combined method name to create proper folder structure for multi-method execution
                        # Pass has_deepsleep flag to adjust maintenance wait time (15 mins with deepsleep, 2 mins standalone)
                        method_result = execute_reboot_process(
                            device.ip, device.port, device.username, device.password,
                            i + 1, device.name, combined_method_name=combined_method_name if len(execution_queue) > 1 else None,
                            has_deepsleep=has_deepsleep,
                            job_id=job_id
                        )
                        # --- Screenshot capture after navigation step ---
                        if method_result is not None and method in ["reboot", "deepsleep", "status", "ir_test", "voice_command", "send_remote_keys"]:
                            try:
                                from screenshot_utils import take_and_analyze_screenshot
                                screenshot_info = take_and_analyze_screenshot(
                                    device_ip=device.ip,
                                    port=device.port,
                                    username=device.username,
                                    password=device.password,
                                    iteration=i + 1,
                                    method=method,
                                    save_dir="screenshots"
                                )
                                screenshot_path = screenshot_info.get("screenshot_path", "")
                                if screenshot_path:
                                    if "screenshots" in method_result:
                                        method_result["screenshots"].append(screenshot_path)
                                    else:
                                        method_result["screenshots"] = [screenshot_path]
                            except Exception as e:
                                log_service.log(f"⚠️ Screenshot capture failed: {str(e)}")
                    elif method == "reboot_performance":
                        # Reboot performance monitoring with timing and home screen detection
                        method_result = execute_reboot_performance_process(
                            device.ip, device.port, device.username, device.password,
                            i + 1, device.name, combined_method_name=combined_method_name if len(execution_queue) > 1 else None
                        )
                    elif method == "reboot_performance_v2":
                        # Reboot performance V2 - with optional post-reboot checks
                        optional_checks = queue_item.get('optional_checks', {})
                        wait_after_reboot = queue_item.get('wait_after_reboot', 80)  # Default 80 seconds
                        home_screen_timeout = queue_item.get('home_screen_timeout', 150)  # Default 150 seconds
                        
                        # Handle skip_all flag (when user enters -NA-)
                        if optional_checks.get('skip_all'):
                            log_service.log("User selected -NA- to skip all post-reboot checks")
                            optional_checks_resolved = {
                                'skip_all': True,
                                'custom_commands': []
                            }
                        else:
                            # Get all available checks dynamically from config_log_patterns
                            from config.config_log_patterns import get_all_optional_checks
                            available_checks = get_all_optional_checks()
                            
                            # Resolve check_keys to actual commands
                            custom_commands_resolved = []
                            for custom_check in optional_checks.get('custom_commands', []):
                                check_key = custom_check.get('check_key')
                                if check_key and check_key in available_checks:
                                    check_config = available_checks[check_key]
                                    custom_commands_resolved.append({
                                        'command': check_config['command'],
                                        'description': check_config['description'],
                                        'check_key': check_key
                                    })
                            
                            # Build final optional_checks structure
                            optional_checks_resolved = {
                                'custom_commands': custom_commands_resolved
                            }
                            
                            # Log which checks will be executed
                            if custom_commands_resolved:
                                log_service.log(f"Will execute {len(custom_commands_resolved)} post-reboot check(s)")
                            else:
                                log_service.log("No valid post-reboot checks configured")
                        
                        method_result = execute_reboot_performance_v2_process(
                            device.ip, device.port, device.username, device.password,
                            i + 1, device.name, 
                            combined_method_name=combined_method_name if len(execution_queue) > 1 else None,
                            optional_checks=optional_checks_resolved,
                            wait_after_reboot=wait_after_reboot,
                            home_screen_timeout=home_screen_timeout
                        )
                    elif method == "reboot_perf_v2_optimized":
                        # Reboot performance V2 - Optimized (37.9% faster than V2)
                        optional_checks = queue_item.get('optional_checks', {})
                        home_screen_timeout = queue_item.get('home_screen_timeout', 180)  # Default 180 seconds
                        auto_collect_logs = queue_item.get('auto_collect_logs', False)  # Default: don't auto-collect
                        log_search_patterns = queue_item.get('log_search_patterns', [])  # Default: no patterns
                        
                        # Handle skip_all flag (when user enters -NA-)
                        if optional_checks.get('skip_all'):
                            log_service.log("User selected -NA- to skip all post-reboot checks")
                            optional_checks_resolved = {
                                'skip_all': True,
                                'custom_commands': []
                            }
                        else:
                            # Get all available checks dynamically from config_log_patterns
                            from config.config_log_patterns import get_all_optional_checks
                            available_checks = get_all_optional_checks()
                            
                            # Resolve check_keys to actual commands
                            custom_commands_resolved = []
                            for custom_check in optional_checks.get('custom_commands', []):
                                check_key = custom_check.get('check_key')
                                if check_key and check_key in available_checks:
                                    check_config = available_checks[check_key]
                                    custom_commands_resolved.append({
                                        'command': check_config['command'],
                                        'description': check_config['description'],
                                        'check_key': check_key
                                    })
                            
                            # Build final optional_checks structure
                            optional_checks_resolved = {
                                'custom_commands': custom_commands_resolved
                            }
                            
                            # Log which checks will be executed
                            if custom_commands_resolved:
                                log_service.log(f"Will execute {len(custom_commands_resolved)} post-reboot check(s)")
                            else:
                                log_service.log("No valid post-reboot checks configured")
                        
                        # Log auto-collect-logs and pattern-search configuration
                        if log_search_patterns and len(log_search_patterns) > 0:
                            log_service.log(f"Pattern-based log collection: ENABLED - Will search for {len(log_search_patterns)} pattern(s)")
                            for pattern in log_search_patterns:
                                log_service.log(f"  - Pattern: '{pattern}'")
                        elif auto_collect_logs:
                            log_service.log("Auto-collect logs: ENABLED - Logs will be collected to /media/apps when HOME is found")
                        else:
                            log_service.log("Log collection: DISABLED")
                        
                        method_result = execute_reboot_perf_v2_optimized_process(
                            device.ip, device.port, device.username, device.password,
                            i + 1, device.name, 
                            combined_method_name=combined_method_name if len(execution_queue) > 1 else None,
                            optional_checks=optional_checks_resolved,
                            home_screen_timeout=home_screen_timeout,
                            auto_collect_logs=auto_collect_logs,
                            log_search_patterns=log_search_patterns,
                            job_id=job_id
                        )
                    elif method == "trail_method":
                        # Trail Method - Cloned from Reboot Performance V2 Optimized
                        optional_checks = queue_item.get('optional_checks', {})
                        home_screen_timeout = queue_item.get('home_screen_timeout', 180)  # Default 180 seconds
                        auto_collect_logs = queue_item.get('auto_collect_logs', False)  # Default: don't auto-collect
                        log_search_patterns = queue_item.get('log_search_patterns', [])  # Default: no patterns
                        
                        # Handle skip_all flag (when user enters -NA-)
                        if optional_checks.get('skip_all'):
                            log_service.log("User selected -NA- to skip all post-reboot checks")
                            optional_checks_resolved = {
                                'skip_all': True,
                                'custom_commands': []
                            }
                        else:
                            # Get all available checks dynamically from config_log_patterns
                            from config.config_log_patterns import get_all_optional_checks
                            available_checks = get_all_optional_checks()
                            
                            # Resolve check_keys to actual commands
                            custom_commands_resolved = []
                            for custom_check in optional_checks.get('custom_commands', []):
                                check_key = custom_check.get('check_key')
                                if check_key and check_key in available_checks:
                                    check_config = available_checks[check_key]
                                    custom_commands_resolved.append({
                                        'command': check_config['command'],
                                        'description': check_config['description'],
                                        'check_key': check_key
                                    })
                            
                            # Build final optional_checks structure
                            optional_checks_resolved = {
                                'custom_commands': custom_commands_resolved
                            }
                            
                            # Log which checks will be executed
                            if custom_commands_resolved:
                                log_service.log(f"Will execute {len(custom_commands_resolved)} post-reboot check(s)")
                            else:
                                log_service.log("No valid post-reboot checks configured")
                        
                        # Log auto-collect-logs and pattern-search configuration
                        if log_search_patterns and len(log_search_patterns) > 0:
                            log_service.log(f"Pattern-based log collection: ENABLED - Will search for {len(log_search_patterns)} pattern(s)")
                            for pattern in log_search_patterns:
                                log_service.log(f"  - Pattern: '{pattern}'")
                        elif auto_collect_logs:
                            log_service.log("Auto-collect logs: ENABLED - Logs will be collected to /media/apps when HOME is found")
                        else:
                            log_service.log("Log collection: DISABLED")
                        
                        method_result = execute_trail_method_process(
                            device.ip, device.port, device.username, device.password,
                            i + 1, device.name, 
                            combined_method_name=combined_method_name if len(execution_queue) > 1 else None,
                            optional_checks=optional_checks_resolved,
                            home_screen_timeout=home_screen_timeout,
                            auto_collect_logs=auto_collect_logs,
                            log_search_patterns=log_search_patterns,
                            job_id=job_id
                        )
                    elif method == "soft_hard_boot":
                        # Soft Boot / Hard Boot Performance Monitoring
                        boot_type = queue_item.get('boot_type', 'HARD')  # Default: HARD boot
                        home_screen_timeout = queue_item.get('home_screen_timeout', 180)  #Default 180 seconds
                        optional_checks = queue_item.get('optional_checks', {})
                        
                        log_service.log(f"Boot Type: {boot_type}")
                        if boot_type == 'HARD':
                            log_service.log(f"  Command: systemctl reboot")
                            log_service.log(f"  Performance: From command sent to HOME screen detection")
                        else:
                            log_service.log(f"  Method: Settings GUI navigation")
                            log_service.log(f"  Path: Settings > System Management > Reset & Updates > Restart device")
                            log_service.log(f"  Navigation keys: DOWN(2x), ENTER, DOWN(2x), ENTER, ENTER (5s per key)")
                            log_service.log(f"  Performance: From last key press to HOME screen detection")
                        
                        log_service.log(f"HOME Screen Timeout: {home_screen_timeout}s")
                        log_service.log(f"Data Collection: rdk_milestones.log will be captured")
                        
                        method_result = execute_soft_hard_boot_process(
                            device.ip, device.port, device.username, device.password,
                            i + 1, device.name,
                            combined_method_name=combined_method_name if len(execution_queue) > 1 else None,
                            boot_type=boot_type,
                            optional_checks=optional_checks_resolved if optional_checks else None,
                            home_screen_timeout=home_screen_timeout,
                            job_id=job_id
                        )
                    elif method == "deepsleep":
                        skip_pre = method_index > 0
                        # Extract DeepSleep-specific parameters from queue item
                        remote_type_ds = queue_item.get('remote_type', None)  # XUMO, SKY, or None (auto-detect)
                        sleep_duration = queue_item.get('sleep_duration_minutes', 60)  # Default 60 minutes
                        perform_reboot = queue_item.get('perform_reboot', False)  # Default False (no reboot)
                        
                        # Log the parameters being used
                        log_service.log(f"DeepSleep remote_type: {remote_type_ds or 'auto-detect'}")
                        log_service.log(f"DeepSleep duration: {sleep_duration} minutes")
                        log_service.log(f"DeepSleep perform_reboot: {perform_reboot}")
                        
                        method_result = execute_deepsleep_process(
                            device.ip, device.port, device.username, device.password,
                            i + 1, skip_pre, device.name, combined_method_name=combined_method_name if len(execution_queue) > 1 else None,
                            remote_type=remote_type_ds,
                            sleep_duration_minutes=sleep_duration,
                            job_id=job_id,
                            perform_reboot=perform_reboot
                        )
                    elif method == "maintenance_deepsleep_wakeup":
                        # Extract Maintenance > DeepSleep > Wakeup specific parameters
                        remote_type_mdw = queue_item.get('remote_type', None)  # XUMO, SKY, or None (auto-detect)
                        sleep_duration = queue_item.get('sleep_duration_minutes', 60)  # Default 60 minutes
                        execute_ds_wakeup = queue_item.get('execute_deepsleep_wakeup', True)  # Default True (full workflow)
                        
                        log_service.log(f"Maintenance > DeepSleep > Wakeup remote_type: {remote_type_mdw or 'auto-detect'}")
                        log_service.log(f"DeepSleep duration: {sleep_duration} minutes")
                        log_service.log(f"Execute DeepSleep & Wakeup phases: {execute_ds_wakeup}")
                        
                        method_result = execute_maintenance_deepsleep_wakeup_process(
                            device.ip, device.port, device.username, device.password,
                            i + 1, device.name, combined_method_name=combined_method_name if len(execution_queue) > 1 else None,
                            remote_type=remote_type_mdw,
                            sleep_duration_minutes=sleep_duration,
                            job_id=job_id,
                            execute_deepsleep_wakeup=execute_ds_wakeup,
                            remaining_iterations=remaining_iterations,
                            execution_queue=execution_queue
                        )
                    elif method == "maintenance_CURL_deepsleep_wakeup":
                        # Extract Maintenance > CURL DeepSleep > Wakeup specific parameters (optimized version)
                        remote_type_mdw = queue_item.get('remote_type', None)  # XUMO, SKY, or None (auto-detect)
                        sleep_duration = queue_item.get('sleep_duration_minutes', 1)  # Default 1 minute (vs 60 for standard)
                        execute_ds_wakeup = queue_item.get('execute_deepsleep_wakeup', True)  # Default True (full workflow)
                        
                        log_service.log(f"Maintenance > CURL DeepSleep > Wakeup remote_type: {remote_type_mdw or 'auto-detect'}")
                        log_service.log(f"DeepSleep CURL wait duration: {sleep_duration} minute(s) (OPTIMIZED)")
                        log_service.log(f"Execute DeepSleep & Wakeup phases: {execute_ds_wakeup}")
                        
                        method_result = execute_maintenance_CURL_deepsleep_wakeup_process(
                            device.ip, device.port, device.username, device.password,
                            i + 1, device.name, combined_method_name=combined_method_name if len(execution_queue) > 1 else None,
                            remote_type=remote_type_mdw,
                            sleep_duration_minutes=sleep_duration,
                            job_id=job_id,
                            execute_deepsleep_wakeup=execute_ds_wakeup
                        )
                    elif method == "deepsleep_maintenance_wakeup":
                        # Extract DeepSleep Maintenance Wakeup specific parameters
                        # Following step specification: wake -> EPG check -> deep sleep config -> sleep -> wake -> reboot -> verify
                        remote_type_dmw = queue_item.get('remote_type', None)  # IR remote type (auto-detect if None)
                        
                        log_service.log(f"DeepSleep Maintenance Wakeup remote_type: {remote_type_dmw or 'auto-detect'}")
                        log_service.log("This method will execute all 6 steps: wake, EPG check, configure deep sleep, enter sleep, wake from deep sleep, and reboot")
                        
                        method_result = execute_deepsleep_maintenance_wakeup_process(
                            device.ip, device.port, device.username, device.password,
                            i + 1, device.name, remote_type=remote_type_dmw,
                            job_id=job_id
                        )
                    elif method == "standby_deep_sleep_ir_control":
                        # Extract Standby Deep Sleep IR Control parameters
                        remote_type_standby = queue_item.get('remote_type', None)  # IR remote type (XUMO_PR3, SKY_LC103, etc)
                        
                        # Log the parameters being used
                        log_service.log(f"Standby Deep Sleep IR Control remote_type: {remote_type_standby or 'default'}")
                        
                        method_result = execute_standby_deep_sleep_ir_control_process(
                            device.ip, device.port, device.username, device.password,
                            i + 1, device.name, combined_method_name=combined_method_name if len(execution_queue) > 1 else None,
                            remote_type=remote_type_standby,
                            job_id=job_id
                        )
                    elif method == "status":
                        import paramiko
                        import time
                        try:
                            log_service.log("Checking device status...")
                            client = paramiko.SSHClient()
                            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                            client.connect(device.ip, port=device.port, username=device.username, password=device.password, timeout=10)
                            stdin, stdout, stderr = client.exec_command('uptime')
                            uptime_output = stdout.read().decode().strip()
                            log_service.log(f"✓ Device is online and responsive")
                            log_service.log(f"  Uptime: {uptime_output}")
                            client.close()
                            method_result = {"iteration": i + 1, "screenshots": [], "logs": [], "success": True}
                            log_service.log("✓ Status check completed successfully")
                        except Exception as e:
                            log_service.log(f"❌ Status check failed: {str(e)}")
                            method_result = {"iteration": i + 1, "screenshots": [], "logs": [], "success": False}
                        time_module.sleep(2)
                    elif method == "ir_test":
                        log_service.log(f"IR Keys for this instance: {', '.join(ir_keys)}")
                        ir_key_delay = step.get('params', {}).get('ir_key_delay', 0.5)
                        log_service.log(f"IR Key Delay: {ir_key_delay} seconds")
                        if remote_type:
                            log_service.log(f"IR Remote Type for this instance: {remote_type}")
                        method_result = execute_ir_test_process(
                            device.ip, device.port, device.username, device.password,
                            i + 1, device.name, ir_keys, combined_method_name=combined_method_name if len(execution_queue) > 1 else None,
                            remote_type_override=remote_type, key_delay=ir_key_delay
                        )
                    elif method == "voice_command":
                        if not voice_text:
                            log_service.log("⚠️  No voice command text provided for this instance, skipping...")
                            continue
                        log_service.log(f"Voice command for this instance: \"{voice_text}\"")
                        method_result = execute_voice_command_process(
                            device.ip, device.port, device.username, device.password,
                            i + 1, device.name, voice_text, combined_method_name=combined_method_name if len(execution_queue) > 1 else None
                        )
                    elif method == "send_remote_keys":
                        log_service.log(f"Remote Keys for this instance: {remote_keys}")
                        key_delay = step.get('params', {}).get('key_delay', 2.0)
                        log_service.log(f"Key Delay: {key_delay} seconds")
                        try:
                            import sys, os as os_mod
                            if os_mod.path.dirname(os_mod.path.dirname(os_mod.path.abspath(__file__))) not in sys.path:
                                sys.path.insert(0, os_mod.path.dirname(os_mod.path.dirname(os_mod.path.abspath(__file__))))
                            from methods.method_remote_keys import send_remote_keys as send_keys_func
                            # Use the new unified function signature
                            if remote_keys:
                                log_service.log(f"[SENDKEYS-START] Beginning remote key execution")
                                result = send_keys_func(
                                    device_ip=device.ip,
                                    key_sequence=remote_keys,  # Pass as string (will be parsed in function)
                                    port=device.port,
                                    username=device.username,
                                    password=device.password,
                                    key_delay=key_delay
                                )
                                log_service.log(f"[SENDKEYS-RESULT] Got result: {result}")
                                method_result = {
                                    "iteration": i + 1, 
                                    "screenshots": [], 
                                    "logs": [], 
                                    "success": result.get("success", False), 
                                    "details": result.get("message", "")
                                }
                                log_service.log(f"{'✓' if result.get('success') else '✗'} {result.get('message', '')}")
                            else:
                                method_result = {"iteration": i + 1, "screenshots": [], "logs": [], "success": False, "details": "No remote keys provided."}
                                log_service.log("⚠ No remote keys provided for this send_remote_keys call")
                        except Exception as e:
                            import traceback
                            error_trace = traceback.format_exc()
                            log_service.log(f"❌ Remote keys execution failed: {str(e)}")
                            log_service.log(f"[ERROR-TRACE] {error_trace}")
                            method_result = {"iteration": i + 1, "screenshots": [], "logs": [], "success": False, "details": f"Error: {str(e)}"}
                    
                    elif method == "screen_validation":
                        log_service.log(f"🎯 Screen Validation: Checking for '{expected_screen}' screen")
                        try:
                            import sys, os as os_mod
                            if os_mod.path.dirname(os_mod.path.dirname(os_mod.path.abspath(__file__))) not in sys.path:
                                sys.path.insert(0, os_mod.path.dirname(os_mod.path.dirname(os_mod.path.abspath(__file__))))
                            from methods.method_screen_validation import validate_screen as validate_screen_func
                            # Use device credentials and expected_screen parameter
                            if expected_screen:
                                result = validate_screen_func(
                                    device_ip=device.ip,
                                    expected_screen=expected_screen,
                                    port=device.port,
                                    username=device.username,
                                    password=device.password
                                )
                                # Store screenshot path for display
                                screenshot_path = result.get('screenshot_path', '')
                                screenshots_list = [screenshot_path] if screenshot_path else []
                                
                                method_result = {
                                    "iteration": i + 1, 
                                    "screenshots": screenshots_list, 
                                    "logs": [], 
                                    "success": result.get("success", False), 
                                    "details": result.get("message", ""),
                                    "validation_result": result.get("validation_result", {})
                                }
                                log_service.log(f"{'✓' if result.get('success') else '✗'} {result.get('message', '')}")
                            else:
                                method_result = {"iteration": i + 1, "screenshots": [], "logs": [], "success": False, "details": "No expected screen provided."}
                                log_service.log("⚠ No expected screen provided for screen_validation call")
                        except Exception as e:
                            log_service.log(f"❌ Screen validation failed: {str(e)}")
                            method_result = {"iteration": i + 1, "screenshots": [], "logs": [], "success": False, "details": str(e)}
                    
                    elif method == "xumo_activation":
                        log_service.log(f"XUMO activation for device: {device.ip}")
                        try:
                            import sys, os as os_mod
                            if os_mod.path.dirname(os_mod.path.dirname(os_mod.path.abspath(__file__))) not in sys.path:
                                sys.path.insert(0, os_mod.path.dirname(os_mod.path.dirname(os_mod.path.abspath(__file__))))
                            from methods.method_xumo_activation import activate_xumo
                            # Use device credentials
                            result = activate_xumo(
                                device_ip=device.ip,
                                port=device.port,
                                username=device.username,
                                password=device.password
                            )
                            
                            method_result = {
                                "iteration": i + 1, 
                                "screenshots": [], 
                                "logs": [], 
                                "success": result.get("success", False), 
                                "details": result.get("message", ""),
                                "activation_code": result.get("activation_code", ""),
                                "script_output": result.get("script_output", "")
                            }
                            log_service.log(f"{'✓' if result.get('success') else '✗'} {result.get('message', '')}")
                            
                            # Log script output for debugging
                            if result.get("script_output"):
                                log_service.log(f"Script output:\n{result['script_output']}")
                        except Exception as e:
                            log_service.log(f"❌ XUMO activation failed: {str(e)}")
                            method_result = {"iteration": i + 1, "screenshots": [], "logs": [], "success": False, "details": str(e)}
                    
                    elif method == "capture_base_image":
                        # Get screen name from queue_item
                        capture_screen_name = screen_name or f"screen_{i+1}"
                        log_service.log(f"Base image capture for device: {device.ip}, Screen: {capture_screen_name}")
                        try:
                            import sys, os as os_mod
                            if os_mod.path.dirname(os_mod.path.dirname(os_mod.path.abspath(__file__))) not in sys.path:
                                sys.path.insert(0, os_mod.path.dirname(os_mod.path.dirname(os_mod.path.abspath(__file__))))
                            from methods.method_capture_base_image import capture_base_image
                            # Use device credentials
                            result = capture_base_image(
                                device_ip=device.ip,
                                screen_name=capture_screen_name,
                                port=device.port,
                                username=device.username,
                                password=device.password,
                                log_callback=log_service.log
                            )
                            
                            method_result = {
                                "iteration": i + 1,
                                "screenshots": [result.get("image_path", "")] if result.get("image_path") else [],
                                "logs": [],
                                "success": result.get("success", False),
                                "details": result.get("message", ""),
                                "screen_name": result.get("screen_name", ""),
                                "image_path": result.get("image_path", "")
                            }
                            log_service.log(f"{'✓' if result.get('success') else '✗'} {result.get('message', '')}")
                        except Exception as e:
                            log_service.log(f"❌ Base image capture failed: {str(e)}")
                            method_result = {"iteration": i + 1, "screenshots": [], "logs": [], "success": False, "details": str(e)}
                    elif method == "capture_current_screen":
                        # Get image name from queue_item
                        image_name = queue_item.get('image_name', f"current_screen_{i+1}")
                        log_service.log(f"Capture Current Screen for device: {device.ip}, Image Name: {image_name}")
                        try:
                            import sys, os as os_mod
                            if os_mod.path.dirname(os_mod.path.dirname(os_mod.path.abspath(__file__))) not in sys.path:
                                sys.path.insert(0, os_mod.path.dirname(os_mod.path.dirname(os_mod.path.abspath(__file__))))
                            from methods.method_capture_current_screen import capture_current_screen
                            # Use the same screenshots_dir/session_folder as the rest of the job
                            result = capture_current_screen(
                                device_ip=device.ip,
                                port=device.port,
                                username=device.username,
                                password=device.password,
                                image_name=image_name,
                                screenshots_dir=screenshots_dir,
                                iteration=i+1,
                                device_name=device.name,
                                log_callback=log_service.log
                            )
                            # Convert screenshot path to comma-separated string for storage
                            screenshot_path = result.get("screenshot_path", "")
                            screenshots_str = screenshot_path if screenshot_path else ""
                            
                            method_result = {
                                "iteration": i + 1,
                                "screenshots": screenshots_str,
                                "logs": [],
                                "success": result.get("success", False),
                                "details": result.get("details", ""),
                                "image_name": image_name,
                                "usb_folder": result.get("usb_folder", "")
                            }
                            log_service.log(f"{'✓' if result.get('success') else '✗'} {result.get('details', '')}")
                            if screenshot_path:
                                log_service.log(f"   Screenshot saved to: {screenshot_path}")
                        except Exception as e:
                            log_service.log(f"❌ Capture Current Screen failed: {str(e)}")
                            method_result = {"iteration": i + 1, "screenshots": "", "logs": [], "success": False, "details": str(e)}
                    
                    elif method == "navigate_inputs_xumo":
                        # Navigate to Inputs on XUMO-TV and validate available input tiles
                        log_service.log(f"Navigate to Inputs - XUMO-TV Device")
                        try:
                            import sys, os as os_mod
                            if os_mod.path.dirname(os_mod.path.dirname(os_mod.path.abspath(__file__))) not in sys.path:
                                sys.path.insert(0, os_mod.path.dirname(os_mod.path.dirname(os_mod.path.abspath(__file__))))
                            from methods.method_navigate_inputs_xumo import navigate_inputs_xumo
                            result = navigate_inputs_xumo(
                                device_ip=device.ip,
                                port=device.port,
                                username=device.username,
                                password=device.password,
                                screenshots_dir=screenshots_dir,
                                iteration=i+1,
                                device_name=device.name,
                                log_callback=log_service.log
                            )
                            
                            found_inputs = result.get('found_inputs', [])
                            missing_inputs = result.get('missing_inputs', [])
                            initial_screenshot = result.get('initial_screenshot', '')
                            tiles_summary = result.get('tiles_summary', {})
                            
                            method_result = {
                                "iteration": i + 1,
                                "screenshots": initial_screenshot if initial_screenshot else "",
                                "logs": [],
                                "success": result.get("success", False),
                                "details": result.get("details", ""),
                                "found_inputs": found_inputs,
                                "missing_inputs": missing_inputs,
                                "tiles_summary": tiles_summary
                            }
                            log_service.log(f"{'✓' if result.get('success') else '✗'} {result.get('details', '')}")
                        except Exception as e:
                            log_service.log(f"❌ Navigate Inputs XUMO failed: {str(e)}")
                            method_result = {
                                "iteration": i + 1,
                                "screenshots": "",
                                "logs": [],
                                "success": False,
                                "details": str(e),
                                "found_inputs": [],
                                "missing_inputs": []
                            }
                    
                    elif method == "activate_flux":
                        # Activate Flux Server on EPG widget and extract IP:port
                        log_service.log(f"Activating Flux Server on EPG Widget...")
                        try:
                            result = activate_flux_widget(
                                device_ip=device.ip,
                                port=device.port,
                                username=device.username,
                                password=device.password,
                                iteration=i + 1,
                                device_name=device.name,
                                combined_method_name=combined_method_name if len(execution_queue) > 1 else None
                            )
                            
                            method_result = {
                                "iteration": i + 1,
                                "screenshots": [],
                                "logs": result.get('logs', []),
                                "success": result.get('success', False),
                                "details": result.get('details', ''),
                                "flux_server_ip_port": result.get('flux_server_ip_port', None),
                                "timestamp": result.get('timestamp', '')
                            }
                            
                            # Store flux_server_ip_port in persistent cross-method data so Navigate_to_Tiles can access it
                            if result.get('flux_server_ip_port'):
                                self.cross_method_data['flux_server_ip_port'] = result.get('flux_server_ip_port')
                                log_service.log(f"[CROSS-METHOD] Persisted flux_server_ip_port: {result.get('flux_server_ip_port')}")
                            
                            log_service.log(f"{'✓' if result.get('success') else '✗'} {result.get('details', '')}")
                            if result.get('flux_server_ip_port'):
                                log_service.log(f"   Flux Server IP:port: {result.get('flux_server_ip_port')}")
                        
                        except Exception as e:
                            log_service.log(f"❌ Activate Flux failed: {str(e)}")
                            method_result = {
                                "iteration": i + 1,
                                "screenshots": [],
                                "logs": [],
                                "success": False,
                                "details": f"Flux activation failed: {str(e)}",
                                "flux_server_ip_port": None
                            }
                    
                    elif method == "navigate_to_tiles":
                        # Navigate to specific section and tile on EPG widget
                        section = queue_item.get('section', '').strip()
                        tile_to_navigate = queue_item.get('tile_to_navigate', '').strip()
                        
                        # Try to get flux_server_ip_port from multiple sources:
                        # 1. Queue item (can be manually provided)
                        # 2. Persistent cross-method data (stored by Activate_Flux)
                        # 3. Last method result (fallback, immediate previous method)
                        flux_server_ip_port = queue_item.get('flux_server_ip_port')
                        
                        # Check persistent cross-method storage first
                        if not flux_server_ip_port and self.cross_method_data.get('flux_server_ip_port'):
                            flux_server_ip_port = self.cross_method_data.get('flux_server_ip_port')
                            log_service.log(f"[CROSS-METHOD] Retrieved persisted flux_server_ip_port: {flux_server_ip_port}")
                        
                        # If not found, try to get from previous method results
                        if not flux_server_ip_port and self.last_method_result:
                            flux_server_ip_port = self.last_method_result.get('flux_server_ip_port')
                        
                        if not section or not tile_to_navigate:
                            log_service.log("❌ Navigate to Tiles requires both 'section' and 'tile_to_navigate' parameters")
                            log_service.log("  Example: section='Apps', tile_to_navigate='prime video'")
                            method_result = {
                                "iteration": i + 1,
                                "screenshots": [],
                                "logs": [],
                                "success": False,
                                "details": "Missing section or tile_to_navigate parameter"
                            }
                        elif not flux_server_ip_port:
                            log_service.log("❌ Flux Server IP:port not available")
                            log_service.log("  Tip: Run 'Activate_Flux' method first to initialize Flux Server")
                            method_result = {
                                "iteration": i + 1,
                                "screenshots": [],
                                "logs": [],
                                "success": False,
                                "details": "Flux Server IP:port not available. Run Activate_Flux method first."
                            }
                        else:
                            log_service.log(f"Navigating to section '{section}' and tile '{tile_to_navigate}'...")
                            try:
                                result = navigate_to_tiles(
                                    device_ip=device.ip,
                                    port=device.port,
                                    username=device.username,
                                    password=device.password,
                                    flux_server_ip_port=flux_server_ip_port,
                                    section=section,
                                    tile_to_navigate=tile_to_navigate,
                                    iteration=i + 1,
                                    device_name=device.name,
                                    combined_method_name=combined_method_name if len(execution_queue) > 1 else None
                                )
                                
                                method_result = {
                                    "iteration": i + 1,
                                    "screenshots": [],
                                    "logs": result.get('logs', []),
                                    "success": result.get('success', False),
                                    "details": result.get('details', ''),
                                    "final_focused_tile": result.get('final_focused_tile', None),
                                    "section_attempts": result.get('section_attempts', 0),
                                    "tile_attempts": result.get('tile_attempts', 0)
                                }
                                
                                log_service.log(f"{'✓' if result.get('success') else '✗'} {result.get('details', '')}")
                                if result.get('final_focused_tile'):
                                    log_service.log(f"   Final Focused Tile: {result.get('final_focused_tile')}")
                                log_service.log(f"   Section attempts: {result.get('section_attempts', 0)}")
                                log_service.log(f"   Tile attempts: {result.get('tile_attempts', 0)}")
                            
                            except Exception as e:
                                log_service.log(f"❌ Navigate to Tiles failed: {str(e)}")
                                method_result = {
                                    "iteration": i + 1,
                                    "screenshots": [],
                                    "logs": [],
                                    "success": False,
                                    "details": f"Navigation failed: {str(e)}",
                                    "final_focused_tile": None
                                }
                    
                    elif method == "memcapture_tool":
                        # Memcapture tool - Execute approved system commands and capture TOP metrics to Excel
                        system_command_name = queue_item.get('system_command_name', '').strip()
                        
                        log_service.log(f"Executing Memcapture Tool - Command: {system_command_name}")
                        try:
                            result = execute_system_command(
                                device_ip=device.ip,
                                port=device.port,
                                username=device.username,
                                password=device.password,
                                iteration=i + 1,
                                device_name=device.name,
                                combined_method_name=combined_method_name if len(execution_queue) > 1 else None,
                                log_callback=log_service.log
                            )
                            
                            method_result = {
                                "iteration": i + 1,
                                "screenshots": result.get('screenshots', []),
                                "logs": result.get('logs', []),
                                "success": result.get('success', False),
                                "details": result.get('details', ''),
                                "performance_seconds": result.get('performance_seconds')
                            }
                            
                            log_service.log(f"{'✓' if result.get('success') else '✗'} {result.get('details', '')}")
                        
                        except Exception as e:
                            log_service.log(f"❌ Memcapture Tool failed: {str(e)}")
                            method_result = {
                                "iteration": i + 1,
                                "screenshots": [],
                                "logs": [],
                                "success": False,
                                "details": f"Memcapture Tool failed: {str(e)}"
                            }
                    
                    elif method == "execute_command":
                        # Execute System Command - Run arbitrary system commands via SSH
                        # Support both 'command_text' and 'command' field names for backwards compatibility
                        command_text = queue_item.get('command_text', '').strip()
                        if not command_text:
                            command_text = queue_item.get('command', '').strip()
                        expected_output = queue_item.get('expected_output', '').strip()
                        validation_type = queue_item.get('validation_type', 'contains')
                        
                        if not command_text:
                            log_service.log("❌ No command provided")
                            method_result = {
                                "iteration": i + 1,
                                "screenshots": [],
                                "logs": [],
                                "success": False,
                                "details": "No command provided (e.g., 'systemctl restart ermgr')"
                            }
                        else:
                            if expected_output:
                                log_service.log(f"Executing system command: {command_text}")
                                log_service.log(f"Expected output: '{expected_output}'")
                                log_service.log(f"Validation type: {validation_type}")
                            else:
                                log_service.log(f"Executing system command: {command_text}")
                            
                            try:
                                result = execute_command(
                                    device_ip=device.ip,
                                    port=device.port,
                                    username=device.username,
                                    password=device.password,
                                    command_text=command_text,
                                    iteration=i + 1,
                                    device_name=device.name,
                                    combined_method_name=combined_method_name if len(execution_queue) > 1 else None,
                                    log_callback=log_service.log,
                                    expected_output=expected_output if expected_output else None,
                                    validation_type=validation_type
                                )
                                
                                method_result = {
                                    "iteration": i + 1,
                                    "screenshots": [],
                                    "logs": result.get('logs', []),
                                    "success": result.get('success', False),
                                    "details": result.get('details', ''),
                                    "command_output": result.get('output', ''),
                                    "exit_code": result.get('exit_code', -1)
                                }
                                
                                log_service.log(f"{'✓' if result.get('success') else '✗'} {result.get('details', '')}")
                            
                            except Exception as e:
                                log_service.log(f"❌ Command execution failed: {str(e)}")
                                method_result = {
                                    "iteration": i + 1,
                                    "screenshots": [],
                                    "logs": [],
                                    "success": False,
                                    "details": f"Command execution failed: {str(e)}"
                                }
                    
                    elif method == "collect_device_logs":
                        # Collect Device Logs - Gather all logs from /opt/logs/ and store as archive in /media/apps/
                        log_service.log(f"Collecting device logs...")
                        try:
                            result = collect_device_logs(
                                device_ip=device.ip,
                                port=device.port,
                                username=device.username,
                                password=device.password,
                                iteration=i + 1,
                                device_name=device.name,
                                combined_method_name=combined_method_name if len(execution_queue) > 1 else None,
                                log_callback=log_service.log
                            )
                            
                            method_result = {
                                "iteration": i + 1,
                                "screenshots": [],
                                "logs": result.get('logs', []),
                                "success": result.get('success', False),
                                "details": result.get('details', ''),
                                "archive_name": result.get('archive_name', ''),
                                "archive_path": result.get('archive_path', ''),
                                "file_size": result.get('file_size', '')
                            }
                            
                            log_service.log(f"{'✓' if result.get('success') else '✗'} {result.get('details', '')}")
                            if result.get('archive_name'):
                                log_service.log(f"   Archive: {result.get('archive_name')}")
                                log_service.log(f"   Size: {result.get('file_size', 'N/A')}")
                        
                        except Exception as e:
                            log_service.log(f"❌ Log collection failed: {str(e)}")
                            method_result = {
                                "iteration": i + 1,
                                "screenshots": [],
                                "logs": [],
                                "success": False,
                                "details": f"Log collection failed: {str(e)}"
                            }
                    
                    elif method == "check_logs":
                        # Check Available Logs - Validate logs based on log patterns from log_patterns.json
                        log_service.log(f"Checking available logs with selected patterns...")
                        try:
                            # Get selected patterns from queue_item
                            selected_patterns = queue_item.get('selected_patterns', [])
                            
                            if not selected_patterns:
                                log_service.log("⚠️  No log patterns selected for validation")
                                method_result = {
                                    "iteration": i + 1,
                                    "screenshots": [],
                                    "logs": [],
                                    "success": False,
                                    "details": "No log patterns selected"
                                }
                            else:
                                result = execute_check_logs(
                                    device_ip=device.ip,
                                    port=device.port,
                                    username=device.username,
                                    password=device.password,
                                    iteration=i + 1,
                                    device_name=device.name,
                                    selected_patterns=selected_patterns,
                                    log_callback=log_service.log,
                                    job_id=job_id
                                )
                                
                                method_result = {
                                    "iteration": i + 1,
                                    "screenshots": [],
                                    "logs": result.get('logs', []),
                                    "success": result.get('success', False),
                                    "details": result.get('details', ''),
                                    "log_results": result.get('log_results', {}),
                                    "matched_patterns": result.get('matched_patterns', []),
                                    "archive_path": result.get('archive_path', '')
                                }
                                
                                log_service.log(f"{'✓' if result.get('success') else '✗'} {result.get('details', '')}")
                                if result.get('matched_patterns'):
                                    log_service.log(f"   Patterns matched: {len(result.get('matched_patterns', []))}")
                                if result.get('archive_path'):
                                    log_service.log(f"   Logs collected: {result.get('archive_path', '')}")
                        
                        except Exception as e:
                            log_service.log(f"❌ Log validation failed: {str(e)}")
                            method_result = {
                                "iteration": i + 1,
                                "screenshots": [],
                                "logs": [],
                                "success": False,
                                "details": f"Log validation failed: {str(e)}"
                            }
                    
                    elif method == "wait":
                        # Get wait duration from queue_item
                        wait_seconds = queue_item.get('wait_seconds', 5)
                        # Normalize camelCase
                        if not wait_seconds or wait_seconds == 5:
                            wait_seconds = queue_item.get('waitSeconds', 5)
                        
                        log_service.log(f"Wait duration: {wait_seconds} seconds")
                        try:
                            import sys, os as os_mod
                            if os_mod.path.dirname(os_mod.path.dirname(os_mod.path.abspath(__file__))) not in sys.path:
                                sys.path.insert(0, os_mod.path.dirname(os_mod.path.dirname(os_mod.path.abspath(__file__))))
                            from methods.method_wait import wait_duration
                            result = wait_duration(
                                wait_seconds=wait_seconds,
                                log_callback=log_service.log
                            )
                            
                            method_result = {
                                "iteration": i + 1,
                                "screenshots": [],
                                "logs": [],
                                "success": result.get("success", False),
                                "details": result.get("message", ""),
                                "waited_seconds": result.get("waited_seconds", 0)
                            }
                            log_service.log(f"{'✓' if result.get('success') else '✗'} {result.get('message', '')}")
                        except Exception as e:
                            log_service.log(f"❌ Wait failed: {str(e)}")
                            method_result = {"iteration": i + 1, "screenshots": [], "logs": [], "success": False, "details": str(e)}
                    
                    elif method == "validate_results":
                        # Get command and expected output from queue_item
                        command = queue_item.get('command', '')
                        expected_output = queue_item.get('expected_output', '')
                        validation_type = queue_item.get('validation_type', 'contains')
                        
                        # Normalize camelCase from frontend
                        if not command:
                            command = queue_item.get('commandText', '')
                        if not expected_output:
                            expected_output = queue_item.get('expectedOutput', '')
                        if not validation_type or validation_type == 'contains':
                            validation_type = queue_item.get('validationType', 'contains')
                        
                        log_service.log(f"Command: {command if command else '(empty)'}")
                        log_service.log(f"Expected Output: {expected_output if expected_output else '(empty)'}")
                        log_service.log(f"Validation Type: {validation_type}")
                        
                        if not command or not expected_output:
                            log_service.log("⚠️  No command or expected output provided, skipping...")
                            log_service.log("💡 HINT: When adding 'Validate_Results' to the queue, you must provide:")
                            log_service.log("   1. Command to execute (e.g., 'ls -ltr /lib/teetz/')")
                            log_service.log("   2. Expected output text to validate (or regex pattern)")
                            log_service.log("   3. Validation type (contains/exact/not_contains/regex)")
                            log_service.log("📝 Please edit this step in the queue or remove it and re-add with proper values.")
                            method_result = {"iteration": i + 1, "screenshots": [], "logs": [], "success": False, "details": "Missing command or expected output"}



                    # Track step result for conditional execution
                    if method_result and isinstance(method_result, dict):
                        step_success = method_result.get('success', False)
                        step_results[method_index] = step_success
                        # Store result for passing between methods (e.g., activate_flux → navigate_to_tiles)
                        self.last_method_result = method_result
                        log_service.log(f"📊 Step {method_index + 1} result: {'PASSED' if step_success else 'FAILED'}")

                        # ATOMIC STEP-WISE RESULT SAVE: Save after every step
                        log_service.log(f"[RESULT-SAVE-1] Saving individual step result for job_id={job_id}, method={method}, iteration={i+1}")
                        self.add_result(
                            iteration=i + 1,
                            phase=f"{method} Execution",
                            status="PASSED" if step_success else "FAILED",
                            details=method_result.get('details', ''),
                            screenshots=method_result.get('screenshots', ''),
                            logs=method_result.get('logs', ''),
                            device_ip=device.ip,
                            device_name=device.name,  # ← NEW: Pass device name
                            method=method,
                            job_id=job_id,
                            username=None,  # Will be looked up from Job object
                            sequence_name=sequence_name,  # ← NEW: Pass sequence name
                            performance_seconds=method_result.get('performance_seconds', None),
                            optional_checks=method_result.get('optional_checks', None),
                            build_info=method_result.get('build_info', None),
                            tiles_summary=method_result.get('tiles_summary', None),
                            rdk_milestones_log=method_result.get('rdk_milestones_log', None),
                            boot_type=method_result.get('boot_type', None)
                        )
                        log_service.log(f"[RESULT-SAVE-1-DONE] Individual result saved")

                        # Check if method returned stop_iterations flag (e.g., from reboot_performance /lib/teetz/ validation)
                        if method_result.get('stop_iterations', False):
                            log_service.log(f"\n🛑 CRITICAL: Method {method} signaled to STOP iterations")
                            log_service.log(f"⚠️  Reason: {method_result.get('details', 'Pre-reboot validation failed')}")
                            log_service.log(f"⚠️  Halting execution - Developer intervention required!")
                            # Mark remaining iterations as skipped in job
                            if job_id:
                                for remaining_iter in range(i + 2, iterations + 1):
                                    Job.update_iteration_result(job_id, remaining_iter, 'skipped')
                            # Break out of iteration loop
                            iterations = i + 1  # Set iterations to current iteration to exit loop
                            log_service.log(f"⏹️  Stopping at iteration {i + 1} of originally planned {iterations}")
                    else:
                        # If no explicit result, assume success
                        if method_result is None:
                            log_service.log(f"[WARNING] Method '{method}' returned None (will not save result)")
                        elif not isinstance(method_result, dict):
                            log_service.log(f"[WARNING] Method '{method}' returned non-dict type: {type(method_result)} (will not save result)")
                        step_results[method_index] = True

                    # Update job progress after step completion (next step index)
                    if job_id:
                        try:
                            Job.update_job_progress(job_id, method_index + 1, i + 1)
                        except Exception as progress_error:
                            print(f"⚠️ Warning: Could not update job progress after step: {progress_error}")

                    # Save method results if available
                    if method_result and isinstance(method_result, dict):
                        screenshots = method_result.get('screenshots', [])
                        logs_data = method_result.get('logs', [])
                        success = method_result.get('success', True)
                        details = method_result.get('details', f"{method.capitalize()} execution {'completed successfully' if success else 'failed'}")
                        
                        # For multi-method sequences, collect results instead of saving individually

                        if is_multi_method_sequence:
                            log_service.log(f"[DEBUG] Collecting result for method '{method}' (will consolidate later)")
                            iteration_method_results.append({
                                'method': method,
                                'screenshots': screenshots,
                                'logs': logs_data,
                                'success': success,
                                'details': details,
                                'performance_seconds': method_result.get('performance_seconds'),
                                'optional_checks': method_result.get('optional_checks'),
                                'build_info': method_result.get('build_info'),
                                'tiles_summary': method_result.get('tiles_summary')
                            })
                        else:
                            pass

                
                # After all steps in iteration complete, determine if iteration passed or failed
                # Only check executed steps (not skipped ones) - skipped steps are marked as None
                executed_steps = {k: v for k, v in step_results.items() if v is not None}
                iteration_passed = all(executed_steps.values()) if executed_steps else True
                iteration_result = 'passed' if iteration_passed else 'failed'
                
                # For multi-method sequences, save a consolidated result after each step
                if is_multi_method_sequence and iteration_method_results:
                    log_service.log(f"\n[RESULT-SAVE-2] Consolidating {len(iteration_method_results)} method results for job_id={job_id}, sequence={sequence_name}, iteration={i+1}")
                    all_screenshots = []
                    all_logs = []
                    all_details = []
                    all_passed = True
                    for res in iteration_method_results:
                        if res['screenshots']:
                            all_screenshots.extend(res['screenshots'] if isinstance(res['screenshots'], list) else [res['screenshots']])
                        if res['logs']:
                            all_logs.extend(res['logs'] if isinstance(res['logs'], list) else [res['logs']])
                        if res['details']:
                            all_details.append(f"{res['method'].upper()}: {res['details']}")
                        if not res['success']:
                            all_passed = False
                    screenshot_str = ', '.join(all_screenshots) if all_screenshots else ''
                    logs_str = ', '.join(all_logs) if all_logs else ''
                    details_str = '\n'.join(all_details) if all_details else f"Sequence execution {'completed successfully' if all_passed else 'failed'}"
                    status = "PASSED" if all_passed else "FAILED"
                    # Save consolidated result for the sequence after each step
                    try:
                        # Extract performance_seconds from reboot method if present
                        # Extract tiles_summary from navigate_inputs_xumo if present
                        perf_seconds = None
                        optional_checks = None
                        build_info = None
                        tiles_summary = None
                        for res in iteration_method_results:
                            if res.get('method') and 'reboot' in res.get('method', '').lower():
                                # This is a reboot method, extract performance data
                                perf_seconds = res.get('performance_seconds')
                                optional_checks = res.get('optional_checks')
                                build_info = res.get('build_info')
                            if res.get('method') and 'navigate' in res.get('method', '').lower():
                                # This is a navigate method, extract tiles data
                                tiles_summary = res.get('tiles_summary')
                        
                        self.add_result(
                            iteration=i + 1,
                            phase=f"Sequence: {sequence_name}",
                            status=status,
                            details=details_str,
                            screenshots=screenshot_str,
                            logs=logs_str,
                            device_ip=device.ip,
                            device_name=device.name,  # ← NEW: Pass device name
                            method=','.join([item['method'] for item in execution_queue]),
                            job_id=job_id,
                            username=None,  # Will be looked up from Job object
                            sequence_name=sequence_name,  # ← NEW: Pass sequence name
                            performance_seconds=perf_seconds,
                            optional_checks=optional_checks,
                            build_info=build_info,
                            tiles_summary=tiles_summary
                        )
                        log_service.log(f"[RESULT-SAVE-2-DONE] Consolidated sequence result saved")
                    except Exception as save_error:
                        log_service.log(f"[RESULT-SAVE-2-ERROR] Failed to save consolidated result: {save_error}")
                        import traceback
                        log_service.log(f"[SAVE-ERROR-TRACE] {traceback.format_exc()}")
                elif is_multi_method_sequence and not iteration_method_results:
                    log_service.log(f"[WARNING] Multi-method sequence detected but iteration_method_results is empty for job_id={job_id}")
                
                # Update iteration result in job
                if job_id:
                    Job.update_iteration_result(job_id, i + 1, iteration_result)
                    log_service.log(f"\n{'✅' if iteration_passed else '❌'} Iteration {i+1}/{iterations} {iteration_result.upper()}")
                    
                    # TIMING: Calculate iteration duration and ETA (excluding artificial sleeps)
                    iteration_end_time = time_module.time()
                    iteration_duration_sec = iteration_end_time - iteration_start_time
                    iteration_duration_min = iteration_duration_sec / 60
                    
                    # Extract sleep duration from execution queue to subtract from iteration time
                    # (The sleep duration is an artificial test delay, not real execution)
                    deepsleep_wait_seconds = 0
                    for queue_item in execution_queue:
                        if queue_item.get('method') in ['deepsleep', 'maintenance_deepsleep_wakeup', 'maintenance_CURL_deepsleep_wakeup']:
                            sleep_minutes = queue_item.get('sleep_duration_minutes', 0)
                            if sleep_minutes > 0:
                                deepsleep_wait_seconds += sleep_minutes * 60
                    
                    # Calculate actual execution time (excluding deepsleep wait)
                    actual_execution_sec = iteration_duration_sec - deepsleep_wait_seconds
                    actual_execution_min = actual_execution_sec / 60
                    
                    # Store actual execution timing for ETA calculation (NOT including sleep)
                    if not hasattr(self, 'iteration_times'):
                        self.iteration_times = []
                    self.iteration_times.append(actual_execution_sec)
                    
                    # Calculate average time per iteration (excluding sleep)
                    avg_iteration_time = sum(self.iteration_times) / len(self.iteration_times)
                    
                    # Calculate remaining time and ETA
                    remaining_iterations = iterations - (i + 1)
                    estimated_remaining_sec = avg_iteration_time * remaining_iterations
                    estimated_remaining_min = estimated_remaining_sec / 60
                    estimated_remaining_hours = estimated_remaining_sec / 3600
                    
                    # Log timing information with full breakdown
                    log_service.log(f"\n⏱️  ITERATION TIMING BREAKDOWN:")
                    log_service.log(f"   • Total iteration time: {iteration_duration_min:.1f} minutes ({int(iteration_duration_sec)}s)")
                    if deepsleep_wait_seconds > 0:
                        log_service.log(f"   • DeepSleep wait time: {deepsleep_wait_seconds / 60:.1f} minutes ({int(deepsleep_wait_seconds)}s)")
                    log_service.log(f"   • ✓ Actual execution time: {actual_execution_min:.1f} minutes ({int(actual_execution_sec)}s)")
                    log_service.log(f"   • Average per iteration (excl. sleep): {avg_iteration_time/60:.1f} minutes")
                    if remaining_iterations > 0:
                        if estimated_remaining_hours >= 1:
                            log_service.log(f"   • Remaining iterations: {remaining_iterations}")
                            log_service.log(f"   • 📊 Estimated remaining time: {estimated_remaining_hours:.1f} hours ({estimated_remaining_min:.0f} min)")
                        else:
                            log_service.log(f"   • Remaining iterations: {remaining_iterations}")
                            log_service.log(f"   • 📊 Estimated remaining time: {estimated_remaining_min:.1f} minutes")
                    else:
                        log_service.log(f"   • ✓ All iterations complete!")

                    # Advance to next iteration for recovery, unless this was the last iteration
                    if i + 1 < iterations:
                        try:
                            Job.update_job_progress(job_id, 0, i + 2)
                        except Exception as progress_error:
                            print(f"⚠️ Warning: Could not update job progress for next iteration: {progress_error}")
            
            # Mark job as completed or failed based on iteration results
            if job_id:
                # datetime and timezone are already imported at module level
                # Reload job to get latest iteration_results
                job = Job.get_job(job_id)
                final_status = 'completed'
                
                # Check if any iteration failed
                if job and job.iteration_results:
                    if any(result == 'failed' for result in job.iteration_results.values()):
                        final_status = 'failed'
                
                Job.update_job_status(
                    job_id, 
                    final_status, 
                    end_time=datetime.now(timezone.utc).isoformat(),
                    log_file_path=log_file_path
                )
                DeviceLock.unlock_device(device.ip)
                log_service.log(f"\n✅ Job {job_id} completed successfully" if final_status == 'completed' else f"\n❌ Job {job_id} completed with failures")
                
                # Send email notification to user who triggered the execution
                self._send_completion_email(job_id, final_status, log_file_path)

            
        except Exception as e:
            # Log the error with explicit flushing
            import traceback
            error_msg = f"\n❌ Error during execution: {str(e)}\n{traceback.format_exc()}"
            print(f"🔧 [DEBUG] Exception in _execute_queue_sequence: {error_msg}")
            log_service.log(error_msg)
            
            # CRITICAL: Flush logs immediately after error to ensure they're written
            if log_file_handle:
                try:
                    log_file_handle.flush()
                    import os
                    os.fsync(log_file_handle.fileno())  # Force write to disk
                except:
                    pass
            
            # Mark job as failed on error
            if job_id:
                # datetime and timezone are already imported at module level
                Job.update_job_status(
                    job_id, 
                    'failed', 
                    end_time=datetime.now(timezone.utc).isoformat(),
                    log_file_path=log_file_path
                )
                log_service.log(f"\n✓ Job status marked as failed in database")
                
                # Unlock device BEFORE attempting any other operations
                try:
                    DeviceLock.unlock_device(device.ip)
                    log_service.log(f"✓ Device lock released: {device.ip}")
                except Exception as unlock_error:
                    log_service.log(f"⚠️  Error releasing device lock: {unlock_error}")
                
                # Flush logs again
                if log_file_handle:
                    try:
                        log_file_handle.flush()
                        import os
                        os.fsync(log_file_handle.fileno())
                    except:
                        pass
                
                log_service.log(f"\n❌ Job {job_id} failed: {str(e)}")
                
                # If this is a lock-related error, force cleanup orphaned locks
                if "lock" in str(e).lower():
                    log_service.log(f"\n🧹 [LOCK-CLEANUP] Forcing cleanup of orphaned locks due to lock error...")
                    try:
                        DeviceLockManager.force_cleanup_orphaned_locks()
                        log_service.log(f"✓ Orphaned lock cleanup completed")
                    except Exception as cleanup_error:
                        log_service.log(f"⚠️  Could not cleanup orphaned locks: {cleanup_error}")
                
                # Send email notification about failure
                self._send_completion_email(job_id, 'failed', log_file_path)
        finally:
            # FINAL flush before closing logs
            if log_file_handle:
                try:
                    log_service.log(f"\n[FINALLY] Finalizing job logs and releasing resources...")
                    log_file_handle.flush()
                    import os
                    os.fsync(log_file_handle.fileno())
                except:
                    pass
            
            # Close the job-specific log handle
            if log_file_handle:
                try:
                    log_file_handle.close()
                except:
                    pass
            log_service.close_iteration_log()
            
            # CRITICAL: Ensure device is unlocked, but verify ownership first (Change 4 implementation)
            if job_id and device:
                try:
                    if DeviceLock.is_lock_owned_by_job(device.ip, job_id):
                        DeviceLock.unlock_device(device.ip)
                        log_service.log(f"\n🔓 Device unlocked: {device.ip}")
                    else:
                        current_lock = DeviceLock.get_device_lock(device.ip)
                        if current_lock:
                            log_service.log(f"\n⚠️ Device locked by job {current_lock.get('job_id', 'unknown')}, not unlocking")
                        else:
                            log_service.log(f"\n⚠️ Device already unlocked")
                except Exception as unlock_error:
                    log_service.log(f"\n❌ Error checking lock ownership: {unlock_error}")
            
            # Clear crash marker after successful job completion
            if self.recovery_service and job_id:
                try:
                    job = Job.get_job(job_id)
                    # Clear crash marker if job completed successfully
                    if job and job.status == 'completed':
                        self.recovery_service.clear_crash_marker()
                        print("[RECOVERY] Crash marker cleared after successful execution")
                except:
                    pass  # Don't let recovery operations interrupt main flow
    
    def _execute_method_sequence(self, device: Device, methods: List[str], 
                                iterations: int, selected_ir_keys: Optional[List[str]], 
                                voice_text: Optional[str]):
        """Execute method sequence (internal)"""
        from services.log_service import LogService
        
        log_service = LogService()
        session_folder = log_service.create_iteration_log(device.ip, ','.join(methods))
        
        # Save execution context for recovery
        if self.recovery_service:
            self.recovery_service.save_execution_context(
                device_ip=device.ip,
                method=','.join(methods),
                iteration=0,
                total_iterations=iterations,
                session_folder=session_folder
            )
        
        for i in range(iterations):
            log_service.log(f"\n{'='*60}")
            log_service.log(f"ITERATION {i+1}/{iterations}")
            log_service.log(f"{'='*60}")
            
            # Update recovery checkpoint
            if self.recovery_service:
                self.recovery_service.save_execution_context(
                    device_ip=device.ip,
                    method=','.join(methods),
                    iteration=i + 1,
                    total_iterations=iterations,
                    session_folder=session_folder
                )
            
            for method_index, method in enumerate(methods):
                if method == "reboot":
                    execute_reboot_process(
                        device.ip, device.port, device.username, device.password,
                        i + 1, device.name
                    )
                elif method == "deepsleep":
                    skip_pre = method_index > 0
                    execute_deepsleep_process(
                        device.ip, device.port, device.username, device.password,
                        i + 1, skip_pre, device.name
                    )
                elif method == "status":
                    # Status check - basic device connectivity and state verification
                    import paramiko
                    import time
                    try:
                        log_service.log("Checking device status...")
                        client = paramiko.SSHClient()
                        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                        client.connect(device.ip, port=device.port, username=device.username, password=device.password, timeout=10)
                        
                        # Check if device is responsive
                        stdin, stdout, stderr = client.exec_command('uptime')
                        uptime_output = stdout.read().decode().strip()
                        log_service.log(f"✓ Device is online and responsive")
                        log_service.log(f"  Uptime: {uptime_output}")
                        
                        client.close()
                        log_service.log("✓ Status check completed successfully")
                    except Exception as e:
                        log_service.log(f"❌ Status check failed: {str(e)}")
                    
                    time_module.sleep(2)  # Small delay between operations
                elif method == "ir_test":
                    execute_ir_test_process(
                        device.ip, device.port, device.username, device.password,
                        i + 1, device.name, selected_ir_keys
                    )
                elif method == "voice_command":
                    # Use stored voice text or provided voice text
                    command_text = voice_text or self.voice_command_text.get(device.ip, "")
                    if not command_text:
                        log_service.log("⚠️  No voice command text provided, skipping...")
                        continue
                    execute_voice_command_process(
                        device.ip, device.port, device.username, device.password,
                        i + 1, device.name, command_text
                    )
        
        log_service.close_iteration_log()
    
    def add_result(self, iteration: int, phase: str, status: str, details: str,
                  screenshots: str = "", logs: str = "", device_ip: Optional[str] = None,
                  method: Optional[str] = None, job_id: Optional[str] = None,
                  performance_seconds: Optional[float] = None, optional_checks: Optional[dict] = None,
                  build_info: Optional[str] = None, tiles_summary: Optional[dict] = None,
                  rdk_milestones_log: Optional[str] = None, boot_type: Optional[str] = None,
                  device_name: Optional[str] = None, username: Optional[str] = None,
                  sequence_name: Optional[str] = None):
        """Add a test result with full metadata preservation"""
        result_device_ip = device_ip or self.last_device_ip or 'N/A'
        result_method = method or self.last_method or 'unknown'
        result_device_name = device_name
        result_username = username
        result_sequence_name = sequence_name
        
        # If job_id provided and metadata not explicitly passed, try to get from Job
        if job_id and not (device_name or username or sequence_name):
            try:
                from models.job import Job
                job = Job.get_job(job_id)  # ← Use get_job() to look up by ID
                if job:
                    result_device_name = result_device_name or job.device_name
                    result_sequence_name = result_sequence_name or job.sequence_name
                    result_username = result_username or job.user_id
            except:
                pass  # Job not found - continue with what we have
        
        # Create and save result
        result = TestResult(
            iteration=iteration,
            phase=phase,
            status=status,
            details=details,
            screenshots=screenshots,
            logs=logs,
            device_ip=result_device_ip,
            device_name=result_device_name,  # ← NEW: Include device name
            method=result_method,
            job_id=job_id,
            username=result_username,  # ← NEW: Include username
            sequence_name=result_sequence_name,  # ← NEW: Include sequence name
            performance_seconds=performance_seconds,
            optional_checks=optional_checks,
            build_info=build_info,
            tiles_summary=tiles_summary,
            rdk_milestones_log=rdk_milestones_log,
            boot_type=boot_type
        )
        print(f"[DEBUG] Saving result for job_id={job_id}, device_ip={result_device_ip}, device_name={result_device_name}, iteration={iteration}, phase={phase}, status={status}")
        # Add to current execution results
        self.current_html_results.append(result.to_dict())
        # Add to device history
        if result_device_ip != 'N/A':
            if result_device_ip not in self.device_results_history:
                self.device_results_history[result_device_ip] = []
            self.device_results_history[result_device_ip].append(result.to_dict())
        # Save to persistent storage
        try:
            TestResult.add(result)
            print(f"[DEBUG] Result persisted for job_id={job_id}, iteration={iteration}, device_name={result_device_name}")
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"[ERROR] Failed to persist result for job_id={job_id}, iteration={iteration}: {e}")
            print(f"[ERROR] Traceback: {error_trace}")
    
    def get_all_results(self) -> List[dict]:
        """Get all test results"""
        results = TestResult.load_all()
        return [r.to_dict() for r in results]
    
    def _send_completion_email(self, job_id: str, status: str, log_file_path: Optional[str] = None):
        """Send email notification when job completes or fails"""
        from datetime import datetime, timezone
        from services.email_service import EmailService
        from models.user import User
        import glob
        
        # Use a dedicated log file for email operations (works in background threads)
        email_log_file = 'email_operations.log'
        
        def log_email(msg):
            """Log to both stdout and file"""
            timestamp = datetime.now(timezone.utc).isoformat()
            formatted_msg = f"[{timestamp}] {msg}"
            print(formatted_msg)
            try:
                with open(email_log_file, 'a') as f:
                    f.write(formatted_msg + '\n')
            except:
                pass
        
        try:
            log_email(f"📧 [EMAIL] Attempting to send completion email for job {job_id} (status: {status})")
            
            # Get job data
            job = Job.get_job(job_id)
            if not job:
                log_email(f"⚠️ [EMAIL] Could not find job {job_id} for email notification")
                return
            
            # Get user email
            user = User.get_user_by_id(job.user_id)
            if not user:
                log_email(f"⚠️ [EMAIL] Could not find user {job.user_id} for email notification")
                return
            
            recipient_email = user.email
            log_email(f"📧 [EMAIL] Recipient: {recipient_email}")
            
            # Prepare job data for email
            job_data = {
                'job_id': job.job_id,
                'device_name': job.device_name,
                'device_ip': job.device_ip,
                'methods': job.methods,
                'status': status,
                'start_time': job.start_time,
                'end_time': job.end_time,
                'iterations': job.iterations,
                'iterations_completed': job.current_iteration if hasattr(job, 'current_iteration') else job.iterations,
                'sequence_name': job.sequence_name,
                'iteration_results': getattr(job, 'iteration_results', {})
            }
            
            # Collect log files to attach
            log_files = []
            if log_file_path and os.path.exists(log_file_path):
                log_files.append(log_file_path)
            
            # Find iteration logs for this job
            job_log_dir = os.path.dirname(log_file_path) if log_file_path else f"logs/jobs/{job_id}"
            if os.path.exists(job_log_dir):
                # Get all log files in job directory
                for log_file in glob.glob(os.path.join(job_log_dir, "*.log")):
                    if log_file not in log_files:
                        log_files.append(log_file)
            
            # Also include iteration logs from iteration_logs directory
            device_folder = job.device_ip.replace('.', '_')
            iteration_logs_base = f"iteration_logs/{device_folder}"
            if os.path.exists(iteration_logs_base):
                # Find recent iteration logs for this job (match by timestamp proximity)
                for iteration_folder in sorted(os.listdir(iteration_logs_base), reverse=True)[:5]:  # Last 5 iterations
                    iteration_log_path = os.path.join(iteration_logs_base, iteration_folder)
                    if os.path.isdir(iteration_log_path):
                        for log_file in glob.glob(os.path.join(iteration_log_path, "*.log")):
                            log_files.append(log_file)
            
            # Limit attachments to avoid email size issues (max 5MB total)
            max_size = 5 * 1024 * 1024  # 5MB
            total_size = 0
            filtered_log_files = []
            
            for log_file in log_files:
                try:
                    file_size = os.path.getsize(log_file)
                    if total_size + file_size <= max_size:
                        filtered_log_files.append(log_file)
                        total_size += file_size
                    else:
                        break
                except:
                    pass
            
            # Send email
            email_service = EmailService()
            log_email(f"📧 [EMAIL] Email service enabled: {email_service.enabled}")
            log_email(f"📧 [EMAIL] Sending to: {recipient_email} with {len(filtered_log_files)} attachments")
            
            success, message = email_service.send_execution_results_email(
                recipient_email, 
                job_data, 
                filtered_log_files
            )
            
            if success:
                log_email(f"✅ [EMAIL] Execution results email sent to {recipient_email}")
            else:
                log_email(f"⚠️ [EMAIL] Failed to send email to {recipient_email}: {message}")
        
        except Exception as e:
            log_email(f"⚠️ [EMAIL] Error sending completion email: {e}")
            import traceback
            log_email(traceback.format_exc())
    
    def get_results_by_device(self, device_ip: str) -> List[dict]:
        """Get results for specific device"""
        results = TestResult.get_by_device(device_ip)
        return [r.to_dict() for r in results]
