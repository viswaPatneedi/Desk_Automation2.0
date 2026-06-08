"""
Results Controller - Handles test results and reporting
"""

from flask import jsonify, render_template, Response, request
from models.device import Device
from models.test_result import TestResult
from models.job import Job
from services.test_execution_service import TestExecutionService
from services.log_service import LogService
from datetime import datetime, timezone
from urllib.parse import quote

class ResultsController:
    """Controller for test results operations"""
    
    def __init__(self, test_service: TestExecutionService, log_service: LogService):
        self.test_service = test_service
        self.log_service = log_service
    
    def get_results(self):
        """GET /api/results - Get test results with sequence consolidation and pagination by day"""
        try:
            from datetime import timedelta
            
            # Parse pagination parameters
            offset_days = int(request.args.get('offset_days', 0))
            limit_days = int(request.args.get('limit_days', 1))
            filter_date = request.args.get('filter_date', None)  # Support date filtering
            
            all_results = self.test_service.get_all_results()

            # Build device name map once
            devices = Device.load_all()
            device_name_map = {d.ip: d.name for d in devices}

            # Build job -> sequence name / execution queue maps for saved sequences
            jobs = Job.load_all()
            job_sequence_map = {j.job_id: j.sequence_name for j in jobs if j.sequence_name}
            job_queue_map = {j.job_id: (j.execution_queue or []) for j in jobs}
            job_iterations_map = {j.job_id: j.iterations for j in jobs}
            
            # Enrich all results with display fields
            enriched_results = []
            sequence_groups = {}  # Track sequences: (device_ip, iteration, date) -> list of methods
            
            for r in all_results:
                timestamp = r.get('timestamp', '')
                try:
                    if timestamp:
                        if ' UTC' in timestamp:
                            dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S UTC')
                        else:
                            dt = datetime.strptime(timestamp[:19], '%Y-%m-%d %H:%M:%S')
                        r['display_datetime'] = dt.strftime('%Y-%m-%d %H:%M')
                    else:
                        r['display_datetime'] = r.get('date', '')
                except Exception:
                    r['display_datetime'] = timestamp[:16] if timestamp and len(timestamp) >= 16 else r.get('date', '')

                device_ip = r.get('device_ip', 'N/A')
                r['device_name'] = device_name_map.get(device_ip) or r.get('device_name') or 'Unknown Device'

                method = r.get('method') or r.get('method_name') or ''
                phase = r.get('phase', '')
                r['method_name'] = method if method else (phase.replace(' Execution', '') if phase else 'N/A')

                status = str(r.get('status', '')).upper()
                r['success'] = status in {'PASSED', 'PASS', 'SUCCESS', 'OK'}

                screenshots = r.get('screenshots', [])
                if isinstance(screenshots, str):
                    screenshots_list = [s.strip() for s in screenshots.split(',') if s.strip()]
                elif isinstance(screenshots, list):
                    screenshots_list = [s for s in screenshots if s]
                else:
                    screenshots_list = []

                normalized_urls = []
                for shot in screenshots_list:
                    if isinstance(shot, str) and shot.startswith('/screenshots/'):
                        normalized_urls.append(shot)
                    elif isinstance(shot, str) and shot.startswith('http'):
                        normalized_urls.append(shot)
                    elif isinstance(shot, str):
                        normalized_urls.append(f"/screenshots/{quote(shot.lstrip('/'), safe='/')}")
                r['screenshots'] = normalized_urls
                
                enriched_results.append(r)
                
                # Track for sequence consolidation
                group_id = r.get('job_id') or r.get('timestamp') or r.get('date')
                seq_key = (device_ip, r.get('iteration'), r.get('date'), group_id)
                if seq_key not in sequence_groups:
                    sequence_groups[seq_key] = []
                sequence_groups[seq_key].append(r)
            
            # Consolidate ALL methods by iteration: every iteration gets ONE consolidated card
            consolidated_results = []
            processed_keys = set()
            
            for r in enriched_results:
                group_id = r.get('job_id') or r.get('timestamp') or r.get('date')
                iteration_key = (r.get('device_ip'), r.get('iteration'), r.get('date'), group_id)
                
                # Skip if already processed as part of an iteration group
                if iteration_key in processed_keys:
                    continue
                
                methods_in_iteration = sequence_groups.get(iteration_key, [])
                processed_keys.add(iteration_key)
                
                # ALWAYS consolidate - create ONE card per iteration with ALL methods
                if len(methods_in_iteration) >= 1:
                    # Build ordered method results, preserving duplicates
                    methods_in_iteration_sorted = sorted(methods_in_iteration, key=lambda m: m.get('timestamp', ''))

                    # Prefer full execution queue for sequences to show all steps
                    job_queue = job_queue_map.get(r.get('job_id')) or []
                    if job_queue:
                        buckets = {}
                        for method_result in methods_in_iteration_sorted:
                            method_name = method_result.get('method') or method_result.get('method_name') or 'N/A'
                            buckets.setdefault(method_name, []).append(method_result)

                        methods_list = []
                        for queue_item in job_queue:
                            queue_method = queue_item.get('method') or 'N/A'
                            bucket = buckets.get(queue_method, [])
                            if bucket:
                                matched = bucket.pop(0)
                                methods_list.append({
                                    'method_name': queue_method,
                                    'success': matched.get('success'),
                                    'timestamp': matched.get('timestamp'),
                                    'details': matched.get('details')
                                })
                            else:
                                methods_list.append({
                                    'method_name': queue_method,
                                    'success': None,
                                    'status': 'SKIPPED' if queue_item.get('condition') else 'NOT_RECORDED'
                                })
                    else:
                        methods_list = [
                            {
                                'method_name': (m.get('method') or m.get('method_name') or 'N/A'),
                                'success': m.get('success'),
                                'timestamp': m.get('timestamp'),
                                'details': m.get('details')
                            }
                            for m in methods_in_iteration_sorted
                        ]

                    num_methods = len(methods_list)
                    if num_methods == 1:
                        method_label = f"Method ({methods_list[0].get('method_name', 'N/A')})"
                    else:
                        method_label = f"Sequence ({num_methods} methods)"
                    
                    # Prefer saved sequence name from job when available
                    job_sequence_name = job_sequence_map.get(r.get('job_id'))
                    display_sequence_name = job_sequence_name or method_label

                    # Collect screenshots, details, and performance metrics from all methods in the iteration
                    all_screenshots = []
                    all_details = []
                    method_screenshots = {}  # Map method_name -> [screenshots]
                    performance_secs = None  # Extract from reboot/perf method if available
                    
                    for method_result in methods_in_iteration_sorted:
                        method_name = method_result.get('method') or method_result.get('method_name') or 'N/A'
                        shots = method_result.get('screenshots', [])
                        if shots:
                            method_screenshots[method_name] = shots if isinstance(shots, list) else [shots]
                            all_screenshots.extend(method_screenshots[method_name])
                        
                        # Collect details from each method
                        details = method_result.get('details', '')
                        if details:
                            all_details.append(f"{method_name.upper()}: {details}")
                        
                        # Extract performance_seconds from any reboot/perf method
                        if performance_secs is None and method_result.get('performance_seconds'):
                            performance_secs = method_result.get('performance_seconds')

                    # Determine overall status: PASSED if all methods succeeded, FAILED otherwise
                    iteration_success = all(m.get('success') for m in methods_in_iteration)
                    overall_status = "PASSED" if iteration_success else "FAILED"
                    combined_details = '\n'.join(all_details) if all_details else f"Iteration execution {'completed successfully' if iteration_success else 'failed'}"
                    
                    # Create consolidated card for this iteration
                    summary_card = {
                        'device_ip': r.get('device_ip'),
                        'device_name': r.get('device_name'),
                        'iteration': r.get('iteration'),
                        'total_iterations': job_iterations_map.get(r.get('job_id'), 'Unknown'),
                        'date': r.get('date'),
                        'timestamp': max(m.get('timestamp', '') for m in methods_in_iteration),
                        'display_datetime': r.get('display_datetime'),
                        'is_sequence': num_methods > 1,
                        'num_methods': num_methods,
                        'sequence_name': display_sequence_name,
                        'method_name': display_sequence_name,
                        'job_id': r.get('job_id'),
                        'success': iteration_success,  # All must pass
                        'status': overall_status,  # Status field for results display (PASSED/FAILED)
                        'details': combined_details,  # Combined details from all methods
                        'methods': methods_list,  # Keep as array for frontend rendering
                        'screenshots': all_screenshots,  # All screenshots from all methods
                        'method_screenshots': method_screenshots,  # Map for carousel display
                        'performance_seconds': performance_secs
                    }
                    consolidated_results.append(summary_card)

            # Ensure all screenshots are arrays of URLs for consistent API response
            for result in consolidated_results:
                shots = result.get('screenshots', [])
                if isinstance(shots, str):
                    # Convert single screenshot string to array and filter blanks
                    result['screenshots'] = [s.strip() for s in shots.split(',') if s.strip()] if shots else []
                elif isinstance(shots, list):
                    # Filter out blank/empty strings from list
                    result['screenshots'] = [s for s in shots if s and (isinstance(s, str) and s.strip())]
                else:
                    result['screenshots'] = []
            
            # Deduplicate any accidental duplicate cards by job/iteration
            deduped_results = {}
            for result in consolidated_results:
                job_id = result.get('job_id')
                device_ip = result.get('device_ip')
                iteration = result.get('iteration')
                date = result.get('date')
                name_key = result.get('sequence_name') or result.get('method_name') or ''
                dedupe_key = (device_ip, iteration, job_id or 'NO_JOB', date, name_key)

                if dedupe_key not in deduped_results:
                    deduped_results[dedupe_key] = result
                    continue

                existing = deduped_results[dedupe_key]

                # Preserve full method list (including duplicates) from the richer card
                existing_methods = existing.get('methods') or []
                new_methods = result.get('methods') or []
                if len(new_methods) > len(existing_methods):
                    existing['methods'] = new_methods
                existing['num_methods'] = len(existing.get('methods') or [])
                existing['is_sequence'] = existing['num_methods'] > 1

                if existing['num_methods'] == 1:
                    only_method = (existing.get('methods') or [{}])[0].get('method_name', 'N/A')
                    method_label = f"Method ({only_method})"
                else:
                    method_label = f"Sequence ({existing['num_methods']} methods)"
                existing['sequence_name'] = method_label
                existing['method_name'] = method_label

                # Merge screenshots and timestamps
                existing_screens = existing.get('screenshots') or []
                new_screens = result.get('screenshots') or []
                merged_screens = list(dict.fromkeys([*existing_screens, *new_screens]))
                existing['screenshots'] = merged_screens
                existing['timestamp'] = max(existing.get('timestamp', ''), result.get('timestamp', ''))
                existing['success'] = existing.get('success', True) and result.get('success', True)
                
                # Preserve or merge status and details
                existing['status'] = "FAILED" if not existing['success'] else "PASSED"
                existing_details = existing.get('details', '')
                new_details = result.get('details', '')
                merged_details = '\n'.join([d for d in [existing_details, new_details] if d])
                existing['details'] = merged_details or f"Iteration execution {'completed successfully' if existing['success'] else 'failed'}"

            consolidated_results = list(deduped_results.values())
            
            # Sort by timestamp descending
            consolidated_results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            # Extract unique dates and calculate date range for pagination
            unique_dates = {}
            for result in consolidated_results:
                date_str = result.get('date', result.get('display_datetime', '')[:10] if result.get('display_datetime') else '')
                if date_str and date_str not in unique_dates:
                    unique_dates[date_str] = True
            
            sorted_dates = sorted(unique_dates.keys(), reverse=True)  # Most recent first
            
            # Handle date-specific filtering if provided
            selected_dates = []
            if filter_date:
                # User selected a specific date
                if filter_date in unique_dates:
                    selected_dates = [filter_date]
                else:
                    selected_dates = []
            else:
                # Calculate start and end indices for the date range based on offset
                start_date_idx = min(offset_days, len(sorted_dates) - 1) if sorted_dates else 0
                end_date_idx = min(offset_days + limit_days, len(sorted_dates))
                selected_dates = sorted_dates[start_date_idx:end_date_idx] if sorted_dates else []
            
            # Filter results for selected date range
            filtered_results = [
                r for r in consolidated_results 
                if r.get('date', r.get('display_datetime', '')[:10] if r.get('display_datetime') else '') in selected_dates
            ]
            
            # Group by device
            results_by_device = {}
            for result in filtered_results:
                device_ip = result.get('device_ip', 'N/A')
                if device_ip not in results_by_device:
                    results_by_device[device_ip] = []
                results_by_device[device_ip].append(result)
            
            # Calculate pagination metadata
            has_more_days = (offset_days + limit_days) < len(sorted_dates) if not filter_date else False
            total_days = len(sorted_dates)
            
            # Collect all unique sequences, methods, and devices from ALL consolidated results
            all_sequences = set()
            all_methods = set()
            all_devices = set()
            
            for result in consolidated_results:
                if result.get('is_sequence'):
                    all_sequences.add(result.get('sequence_name', 'Unknown Sequence'))
                else:
                    all_methods.add(result.get('method_name', 'Unknown Method'))
                
                device_name = result.get('device_name', 'Unknown Device')
                if device_name:
                    all_devices.add(device_name)
            
            return jsonify({
                'results': filtered_results,
                'by_device': results_by_device,
                'total': len(filtered_results),
                'pagination': {
                    'offset_days': offset_days,
                    'limit_days': limit_days,
                    'total_days': total_days,
                    'has_more_days': has_more_days,
                    'current_dates': selected_dates,
                    'all_dates': sorted_dates,
                    'all_sequences': sorted(list(all_sequences)),
                    'all_methods': sorted(list(all_methods)),
                    'all_devices': sorted(list(all_devices))
                }
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    def results_page(self):
        """Render results page"""
        # Load all results
        all_results = self.test_service.get_all_results()
        
        # Sort by timestamp descending
        all_results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Load devices to get MAC addresses
        from models.device import Device
        devices = Device.load_all()
        device_mac_map = {d.ip: d.mac_address for d in devices}
        
        # Group results intelligently:
        # - Consolidate sequence jobs (with job_id and sequence_name) into single card per iteration
        # - Otherwise, keep individual result cards
        grouped_results = {}
        for r in all_results:
            timestamp = r.get('timestamp', '')
            phase = r.get('phase', '')
            device_ip = r.get('device_ip', '')
            iteration = r.get('iteration', 1)
            job_id = r.get('job_id', '')
            sequence_name = r.get('sequence_name', '') if 'sequence_name' in r else ''
            device_name = r.get('device_name', '')
            is_sequence = phase.startswith('Sequence:') or (job_id and sequence_name) or (job_id and (phase.lower().startswith('reboot_perf_v2_optimized') or phase.lower().startswith('trail_method')))
            group_id = job_id or timestamp
            # Always include device_name for grouping
            if is_sequence:
                key = (r.get('date', ''), device_ip, device_name, iteration, 'SEQUENCE', sequence_name or phase.replace('Sequence: ', ''), group_id)
            else:
                key = (r.get('date', ''), device_ip, device_name, iteration, group_id)
            if key not in grouped_results:
                display_datetime = ''
                if timestamp:
                    try:
                        if ' UTC' in timestamp:
                            dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S UTC')
                        else:
                            dt = datetime.strptime(timestamp[:19], '%Y-%m-%d %H:%M:%S')
                        display_datetime = dt.strftime('%Y-%m-%d %H:%M')
                    except:
                        display_datetime = timestamp[:16] if len(timestamp) >= 16 else timestamp
                grouped_results[key] = {
                    'date': r.get('date', ''),
                    'device_ip': device_ip,
                    'device_name': device_name,
                    'mac_address': device_mac_map.get(device_ip, ''),
                    'iteration': iteration,
                    'timestamp': timestamp,
                    'display_datetime': display_datetime,
                    'methods_list': [],
                    'phases': [],
                    'is_sequence': is_sequence,
                    'sequence_name': sequence_name or phase.replace('Sequence: ', '') if is_sequence else ''
                }
            grouped_results[key]['phases'].append(r)
            method = r.get('method', 'UNKNOWN')
            if method not in grouped_results[key]['methods_list']:
                grouped_results[key]['methods_list'].append(method)
        grouped_list = []
        for group in grouped_results.values():
            group['methods'] = ' → '.join(reversed(group['methods_list']))
            del group['methods_list']
            grouped_list.append(group)
        grouped_list.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        iteration_status = {}
        for r in all_results:
            itr = r['iteration']
            if itr not in iteration_status:
                iteration_status[itr] = 'PASSED'
            if r['status'] == 'FAILED':
                iteration_status[itr] = 'FAILED'
            elif r['status'] == 'WARNING' and iteration_status[itr] != 'FAILED':
                iteration_status[itr] = 'WARNING'
        iteration_status_by_device = {}
        for result in all_results:
            device_ip = result.get('device_ip', 'N/A')
            if device_ip not in iteration_status_by_device:
                iteration_status_by_device[device_ip] = {}
            itr = result['iteration']
            if itr not in iteration_status_by_device[device_ip]:
                iteration_status_by_device[device_ip][itr] = 'PASSED'
            if result['status'] == 'FAILED':
                iteration_status_by_device[device_ip][itr] = 'FAILED'
            elif result['status'] == 'WARNING' and iteration_status_by_device[device_ip][itr] != 'FAILED':
                iteration_status_by_device[device_ip][itr] = 'WARNING'
        distinct_devices = list(set(r.get('device_ip', 'N/A') for r in all_results))
        devices = Device.load_all()
        generated_ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        reboot_perf_executions = self._build_reboot_perf_executions()
        
        return render_template(
            'results.html',
            devices=[d.to_dict() for d in devices],
            results=all_results,
            grouped_results=grouped_list,
            iteration_status=iteration_status,
            device_ip=self.test_service.last_device_ip,
            method=self.test_service.last_method,
            total_iterations=len(all_results),
            aggregated_results=all_results,
            iteration_status_by_device=iteration_status_by_device,
            distinct_devices=distinct_devices,
            generated=generated_ts,
            reboot_perf_executions=reboot_perf_executions
        )

    def _build_reboot_perf_executions(self):
        """Build Reboot Performance V2 Optimized and Trail Method execution summaries"""
        jobs = Job.load_all()

        def is_reboot_perf_job(job_item):
            if job_item.methods and ('reboot_perf_v2_optimized' in job_item.methods or 'trail_method' in job_item.methods):
                return True
            if job_item.execution_queue:
                for item in job_item.execution_queue:
                    if item.get('method') in ('reboot_perf_v2_optimized', 'trail_method'):
                        return True
            return False

        reboot_jobs = [job for job in jobs if is_reboot_perf_job(job)]

        all_results = self.test_service.get_all_results()
        results_by_job = {}
        for result in all_results:
            job_id = result.get('job_id')
            if not job_id:
                continue
            results_by_job.setdefault(job_id, []).append(result)

        executions = {}
        for job in reboot_jobs:
            job_id = job.job_id
            method_label = ', '.join(job.methods) if job.methods else 'reboot_perf_v2_optimized'
            executions[job_id] = {
                'job_id': job_id,
                'device_name': job.device_name,
                'device_ip': job.device_ip,
                'method': method_label,
                'iterations': job.iterations,
                'start_time': job.start_time,
                'build_info': None,
                'per_iteration': [],
                'performance_values': [],
                'crashes_found': False,
                'logs_collected': False
            }

        for job_id, entry in executions.items():
            job_results = results_by_job.get(job_id, [])

            for result in job_results:
                perf_value = result.get('performance_seconds')
                if isinstance(perf_value, (int, float)):
                    entry['performance_values'].append(float(perf_value))

                optional_checks = result.get('optional_checks') or {}
                custom_checks = optional_checks.get('custom_checks', []) or []
                crash_checks = []
                for check in custom_checks:
                    if not check.get('pattern_found'):
                        continue
                    description = str(check.get('description', '')).lower()
                    command = str(check.get('command', '')).lower()
                    if 'crash' in description or 'crash' in command or 'segfault' in description or 'segfault' in command:
                        crash_checks.append(check)

                crash_found = len(crash_checks) > 0
                crash_details = []
                for c in crash_checks:
                    output = c.get('output', '').strip()
                    description = c.get('description', '').strip()
                    # Create detailed crash info with actual log lines if available
                    if output:
                        # Format output for display - show up to 5 lines
                        output_lines = output.split('\n')[:5]
                        crash_details.append({
                            'description': description or 'Crash pattern detected',
                            'output': output,
                            'output_lines': output_lines,
                            'line_count': len(output.split('\n'))
                        })
                    else:
                        crash_details.append({
                            'description': description or 'Crash pattern detected',
                            'output': '',
                            'output_lines': [],
                            'line_count': 0
                        })

                logs_list = []
                logs_field = result.get('logs')
                if isinstance(logs_field, list):
                    logs_list.extend([s for s in logs_field if s])
                elif isinstance(logs_field, str) and logs_field.strip():
                    logs_list.extend([s.strip() for s in logs_field.split(',') if s.strip()])

                collected_logs = optional_checks.get('collected_logs') or []
                if isinstance(collected_logs, list):
                    logs_list.extend([s for s in collected_logs if s])

                logs_collected = len(logs_list) > 0

                entry['per_iteration'].append({
                    'iteration': result.get('iteration'),
                    'performance_seconds': perf_value,
                    'crash_found': crash_found,
                    'crash_details': crash_details,
                    'logs_collected': logs_collected
                })

                if crash_found:
                    entry['crashes_found'] = True
                if logs_collected:
                    entry['logs_collected'] = True

                if not entry.get('build_info') and result.get('build_info'):
                    entry['build_info'] = result.get('build_info')

        execution_list = []
        for job_id, entry in executions.items():
            perf_values = entry.pop('performance_values', [])
            if perf_values:
                entry['average_performance'] = sum(perf_values) / len(perf_values)
            else:
                entry['average_performance'] = None

            entry['per_iteration'].sort(key=lambda x: x.get('iteration') or 0)
            execution_list.append(entry)

        execution_list.sort(key=lambda x: x.get('start_time') or '', reverse=True)
        return execution_list
    
    def stream_logs(self):
        """Stream real-time logs via SSE"""
        def generate():
            try:
                for log_data in self.log_service.stream_logs():
                    yield log_data
            except GeneratorExit:
                pass
        
        response = Response(generate(), mimetype='text/event-stream')
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['X-Accel-Buffering'] = 'no'
        return response

    def reboot_perf_results_page(self, current_user):
        """Render reboot performance results page"""
        return render_template('reboot_perf_results.html', current_user=current_user)

    def get_reboot_perf_results(self):
        """GET /api/reboot-perf-results - Get reboot perf results grouped by device and job"""
        try:
            import re
            import os
            job_ids_param = request.args.get('job_ids', '')
            device_ips_param = request.args.get('device_ips', '')
            selected_job_ids = [j.strip() for j in job_ids_param.split(',') if j.strip()]
            selected_device_ips = [d.strip() for d in device_ips_param.split(',') if d.strip()]

            jobs = Job.load_all()

            def is_reboot_perf_job(job_item):
                if job_item.methods and ('reboot_perf_v2_optimized' in job_item.methods or 'trail_method' in job_item.methods):
                    return True
                if job_item.execution_queue:
                    for item in job_item.execution_queue:
                        if item.get('method') in ('reboot_perf_v2_optimized', 'trail_method'):
                            return True
                return False

            reboot_jobs = [job for job in jobs if is_reboot_perf_job(job)]
            reboot_job_ids = {job.job_id for job in reboot_jobs}

            all_results = self.test_service.get_all_results()
            results_for_reboot = [
                r for r in all_results
                if r.get('job_id') and r.get('method') in ('reboot_perf_v2_optimized', 'trail_method')
            ]
            jobs_with_results = {r.get('job_id') for r in results_for_reboot}

            if selected_job_ids:
                job_filter = set(selected_job_ids)
            else:
                job_filter = jobs_with_results

            filtered_results = [
                r for r in all_results
                if r.get('job_id') in job_filter and r.get('method') in ('reboot_perf_v2_optimized', 'trail_method')
            ]

            if selected_device_ips:
                device_filter = set(selected_device_ips)
                filtered_results = [r for r in filtered_results if r.get('device_ip') in device_filter]
            results_by_job = {}
            for r in results_for_reboot:
                job_id = r.get('job_id')
                if not job_id:
                    continue
                results_by_job.setdefault(job_id, r)

            image_name_cache = {}

            def _extract_image_name(job_id, log_path=None):
                if job_id in image_name_cache:
                    return image_name_cache[job_id]
                candidates = []
                if log_path:
                    candidates.append(log_path)
                candidates.append(f"logs/jobs/{job_id}/execution.log")
                pattern = re.compile(r"imagename:([^\s]+)")
                for path in candidates:
                    if not path or not os.path.exists(path):
                        continue
                    try:
                        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                            for line in f:
                                match = pattern.search(line)
                                if match:
                                    image_name_cache[job_id] = match.group(1).strip()
                                    return image_name_cache[job_id]
                    except Exception:
                        continue
                image_name_cache[job_id] = None
                return None

            available_jobs = []
            for job in reboot_jobs:
                if job.job_id not in jobs_with_results:
                    continue
                sample = results_by_job.get(job.job_id, {})
                image_name = sample.get('build_info') or job.sequence_name
                if not image_name:
                    image_name = _extract_image_name(job.job_id, job.log_file_path)
                available_jobs.append({
                    'job_id': job.job_id,
                    'device_ip': job.device_ip,
                    'device_name': job.device_name,
                    'iterations': job.iterations,
                    'status': job.status,
                    'start_time': job.start_time,
                    'end_time': job.end_time,
                    'image_name': image_name
                })

            # Fallback for jobs present in results but missing from jobs.json
            missing_jobs = jobs_with_results.difference({j['job_id'] for j in available_jobs})
            for job_id in missing_jobs:
                sample = results_by_job.get(job_id, {})
                image_name = sample.get('build_info')
                if not image_name:
                    image_name = _extract_image_name(job_id)
                available_jobs.append({
                    'job_id': job_id,
                    'device_ip': sample.get('device_ip') or 'N/A',
                    'device_name': sample.get('device_name') or 'Unknown Device',
                    'iterations': None,
                    'status': 'unknown',
                    'start_time': None,
                    'end_time': None,
                    'image_name': image_name
                })

            results_by_device = {}
            for result in filtered_results:
                job_id = result.get('job_id')
                device_ip = result.get('device_ip') or 'N/A'
                job = next((j for j in reboot_jobs if j.job_id == job_id), None)

                optional_checks = result.get('optional_checks') or {}
                custom_checks = optional_checks.get('custom_checks', []) or []
                crash_checks = []
                for check in custom_checks:
                    if not check.get('pattern_found'):
                        continue
                    description = str(check.get('description', '')).lower()
                    command = str(check.get('command', '')).lower()
                    if 'crash' in description or 'crash' in command or 'segfault' in description or 'segfault' in command:
                        crash_checks.append(check)

                crash_found = len(crash_checks) > 0
                crash_details = []
                for c in crash_checks:
                    output = c.get('output', '').strip()
                    description = c.get('description', '').strip()
                    # Create detailed crash info with actual log lines if available
                    if output:
                        # Format output for display - show up to 5 lines
                        output_lines = output.split('\n')[:5]
                        crash_details.append({
                            'description': description or 'Crash pattern detected',
                            'output': output,
                            'output_lines': output_lines,
                            'line_count': len(output.split('\n'))
                        })
                    else:
                        crash_details.append({
                            'description': description or 'Crash pattern detected',
                            'output': '',
                            'output_lines': [],
                            'line_count': 0
                        })

                logs_list = []
                logs_field = result.get('logs')
                if isinstance(logs_field, list):
                    logs_list.extend([s for s in logs_field if s])
                elif isinstance(logs_field, str) and logs_field.strip():
                    logs_list.extend([s.strip() for s in logs_field.split(',') if s.strip()])

                collected_logs = optional_checks.get('collected_logs') or []
                if isinstance(collected_logs, list):
                    logs_list.extend([s for s in collected_logs if s])

                logs_collected = len(logs_list) > 0

                screenshots_field = result.get('screenshots')
                screenshots = []
                if isinstance(screenshots_field, list):
                    screenshots = [s for s in screenshots_field if s]
                elif isinstance(screenshots_field, str) and screenshots_field.strip():
                    screenshots = [s.strip() for s in screenshots_field.split(',') if s.strip()]

                device_entry = results_by_device.setdefault(device_ip, {
                    'device_ip': device_ip,
                    'device_name': (job.device_name if job else result.get('device_name')) or 'Unknown Device',
                    'jobs': {}
                })

                image_name = result.get('build_info') or (job.sequence_name if job else None)
                if not image_name:
                    image_name = _extract_image_name(job_id, job.log_file_path if job else None)

                job_entry = device_entry['jobs'].setdefault(job_id, {
                    'job_id': job_id,
                    'device_ip': device_ip,
                    'device_name': (job.device_name if job else result.get('device_name')) or 'Unknown Device',
                    'iterations': job.iterations if job else None,
                    'status': job.status if job else 'unknown',
                    'start_time': job.start_time if job else None,
                    'end_time': job.end_time if job else None,
                    'image_name': image_name,
                    'per_iteration': []
                })

                job_entry['per_iteration'].append({
                    'iteration': result.get('iteration'),
                    'performance_seconds': result.get('performance_seconds'),
                    'crash_found': crash_found,
                    'crash_details': crash_details,
                    'logs_collected': logs_collected,
                    'screenshots': screenshots
                })

            for device_entry in results_by_device.values():
                for job_entry in device_entry['jobs'].values():
                    job_entry['per_iteration'].sort(key=lambda x: x.get('iteration') or 0)
                    # Calculate crash summary
                    total_iterations = len(job_entry['per_iteration'])
                    crashes_found = sum(1 for x in job_entry['per_iteration'] if x.get('crash_found'))
                    job_entry['crash_summary'] = {
                        'crashes_found': crashes_found,
                        'total_iterations': total_iterations,
                        'summary_text': f"Crashes found {crashes_found} / {total_iterations}"
                    }

            return jsonify({
                'available_jobs': available_jobs,
                'selected_job_ids': selected_job_ids,
                'selected_device_ips': selected_device_ips,
                'results_by_device': results_by_device
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    def soft_hard_boot_results_page(self, current_user):
        """Render soft_hard_boot results page"""
        return render_template('soft_hard_boot_results.html', current_user=current_user)

    def get_soft_hard_boot_results(self):
        """GET /api/soft-hard-boot-results - Get soft_hard_boot results with milestones"""
        try:
            all_results = self.test_service.get_all_results()
            
            # Filter for soft_hard_boot results only
            soft_hard_boot_results = [
                r for r in all_results
                if r.get('method') == 'soft_hard_boot'
            ]
            
            if not soft_hard_boot_results:
                return jsonify({'results_by_device': {}})
            
            # Group by device and job
            results_by_device = {}
            for result in soft_hard_boot_results:
                device_ip = result.get('device_ip', 'N/A')
                device_name = result.get('device_name', 'Unknown')
                job_id = result.get('job_id', 'no-job')
                
                if device_ip not in results_by_device:
                    results_by_device[device_ip] = {
                        'device_name': device_name,
                        'device_ip': device_ip,
                        'jobs': {}
                    }
                
                if job_id not in results_by_device[device_ip]['jobs']:
                    # Extract image name and timestamp from first result for this job
                    build_info = result.get('build_info', '')
                    image_name = build_info.split('\n')[0] if build_info else 'Unknown Build'
                    start_time = result.get('timestamp', '')
                    
                    results_by_device[device_ip]['jobs'][job_id] = {
                        'job_id': job_id,
                        'device_ip': device_ip,
                        'device_name': device_name,
                        'per_iteration': [],
                        'status': 'completed',
                        'image_name': image_name,
                        'start_time': start_time
                    }
                
                # Extract image name from build_info (first line)
                build_info = result.get('build_info', '')
                image_name = build_info.split('\n')[0] if build_info else 'Unknown Build'
                
                # Add iteration data
                iteration_data = {
                    'iteration': result.get('iteration', 1),
                    'boot_type': result.get('boot_type', 'N/A'),
                    'performance_seconds': result.get('performance_seconds'),
                    'crash_found': 'crash' in str(result.get('details', '')).lower(),
                    'crash_details': [],
                    'logs_collected': bool(result.get('logs')),
                    'rdk_milestones_log': result.get('rdk_milestones_log', ''),
                    'build_info': result.get('build_info', ''),
                    'screenshots': result.get('screenshots', []),
                    'status': result.get('status', 'PASSED'),
                    'start_time': result.get('timestamp', ''),
                    'image_name': image_name
                }
                
                results_by_device[device_ip]['jobs'][job_id]['per_iteration'].append(iteration_data)
            
            # Get device names from Device model
            from models.device import Device
            devices = Device.load_all()
            device_map = {d.ip: d.name for d in devices}
            
            for device_ip, device_data in results_by_device.items():
                if device_ip in device_map:
                    device_data['device_name'] = device_map[device_ip]
            
            return jsonify({
                'results_by_device': results_by_device,
                'total_results': len(soft_hard_boot_results)
            })
        except Exception as e:
            return jsonify({'error': str(e), 'results_by_device': {}}), 500

    def tiles_results_page(self, current_user):
        """Render tiles detection results page"""
        return render_template('tiles_results.html', current_user=current_user)

    def get_tiles_results(self):
        """GET /api/tiles-results - Get tiles detection results grouped by device and job"""
        try:
            import re
            import os
            job_ids_param = request.args.get('job_ids', '')
            device_ips_param = request.args.get('device_ips', '')
            selected_job_ids = [j.strip() for j in job_ids_param.split(',') if j.strip()]
            selected_device_ips = [d.strip() for d in device_ips_param.split(',') if d.strip()]

            jobs = Job.load_all()

            def is_tiles_job(job_item):
                if job_item.methods and 'navigate_inputs_xumo' in job_item.methods:
                    return True
                if job_item.execution_queue:
                    for item in job_item.execution_queue:
                        if item.get('method') == 'navigate_inputs_xumo':
                            return True
                return False

            tiles_jobs = [job for job in jobs if is_tiles_job(job)]
            tiles_job_ids = {job.job_id for job in tiles_jobs}

            all_results = self.test_service.get_all_results()
            results_for_tiles = [
                r for r in all_results
                if r.get('job_id') and r.get('method') == 'navigate_inputs_xumo' and r.get('tiles_summary')
            ]
            jobs_with_results = {r.get('job_id') for r in results_for_tiles}

            if selected_job_ids:
                job_filter = set(selected_job_ids)
            else:
                job_filter = jobs_with_results

            results_by_device = {}
            for result in results_for_tiles:
                job_id = result.get('job_id')
                device_ip = result.get('device_ip') or 'N/A'
                job = next((j for j in tiles_jobs if j.job_id == job_id), None)

                tiles_summary = result.get('tiles_summary') or {}
                found_count = tiles_summary.get('found_count', 0)
                total_count = tiles_summary.get('total_count', 0)
                found_tiles = tiles_summary.get('tiles_found', [])
                missing_tiles = tiles_summary.get('tiles_missing', [])

                device_entry = results_by_device.setdefault(device_ip, {
                    'device_ip': device_ip,
                    'device_name': (job.device_name if job else result.get('device_name')) or 'Unknown Device',
                    'jobs': {}
                })

                job_entry = device_entry['jobs'].setdefault(job_id, {
                    'job_id': job_id,
                    'device_ip': device_ip,
                    'device_name': (job.device_name if job else result.get('device_name')) or 'Unknown Device',
                    'iterations': job.iterations if job else None,
                    'status': job.status if job else 'unknown',
                    'start_time': job.start_time if job else None,
                    'end_time': job.end_time if job else None,
                    'per_iteration': []
                })

                job_entry['per_iteration'].append({
                    'iteration': result.get('iteration'),
                    'tiles_status': f"{found_count}/{total_count}",
                    'found_count': found_count,
                    'total_count': total_count,
                    'found_tiles': found_tiles,
                    'missing_tiles': missing_tiles,
                    'all_found': found_count == total_count,
                    'logs_collected': result.get('logs_collected', False)
                })

            for device_entry in results_by_device.values():
                for job_entry in device_entry['jobs'].values():
                    job_entry['per_iteration'].sort(key=lambda x: x.get('iteration') or 0)

            available_jobs = []
            for job in tiles_jobs:
                if job.job_id not in jobs_with_results:
                    continue
                available_jobs.append({
                    'job_id': job.job_id,
                    'device_ip': job.device_ip,
                    'device_name': job.device_name,
                    'iterations': job.iterations,
                    'status': job.status,
                    'start_time': job.start_time,
                    'end_time': job.end_time
                })

            return jsonify({
                'available_jobs': available_jobs,
                'selected_job_ids': selected_job_ids,
                'selected_device_ips': selected_device_ips,
                'results_by_device': results_by_device
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    def download_reboot_perf_excel(self):
        """Download reboot performance results as Excel file"""
        from datetime import datetime
        from flask import send_file
        from services.excel_export import create_reboot_perf_excel
        
        try:
            job_ids_param = request.args.get('job_ids', '')
            device_ips_param = request.args.get('device_ips', '')
            selected_job_ids = [j.strip() for j in job_ids_param.split(',') if j.strip()]
            selected_device_ips = [d.strip() for d in device_ips_param.split(',') if d.strip()]
            
            # Get reboot perf results
            results_data = self.get_reboot_perf_results()
            if isinstance(results_data, tuple):
                data = results_data[0].get_json() if hasattr(results_data[0], 'get_json') else {}
            else:
                data = results_data.get_json() if hasattr(results_data, 'get_json') else {}
            
            results_by_device = data.get('results_by_device', {})
            
            # Filter if needed
            if selected_job_ids or selected_device_ips:
                filtered_results = {}
                for device_ip, device_data in results_by_device.items():
                    if selected_device_ips and device_ip not in selected_device_ips:
                        continue
                    filtered_jobs = {}
                    for job_id, job_data in device_data.get('jobs', {}).items():
                        if selected_job_ids and job_id not in selected_job_ids:
                            continue
                        filtered_jobs[job_id] = job_data
                    
                    if filtered_jobs:
                        filtered_results[device_ip] = device_data.copy()
                        filtered_results[device_ip]['jobs'] = filtered_jobs
                
                results_by_device = filtered_results
            
            # Create Excel file
            excel_buffer = create_reboot_perf_excel(results_by_device)
            
            # Generate filename - format: Device-ImageName_Version_ITR-Count.xls
            filename = 'reboot_perf_results.xlsx'
            
            try:
                # Extract device name, image name, and iteration count from first device if available
                if results_by_device:
                    first_device = next(iter(results_by_device.values()))
                    device_name = first_device.get('device_name', 'Device')
                    image_name = first_device.get('image_name', '')
                    
                    # Extract device model (e.g., Element-A4K from "Element-A4K-DESK")
                    try:
                        parts = device_name.split('-')
                        if len(parts) >= 2:
                            device_model = f"{parts[0]}-{parts[1]}"
                        else:
                            device_model = device_name
                    except:
                        device_model = device_name
                    
                    # Extract image version from image_name (e.g., XUSPTC11MWR_8.3.4.9B1 from full path)
                    if image_name:
                        # Extract just the image name and version parts
                        image_parts = image_name.split('_')
                        if len(image_parts) >= 2:
                            # Extract XUSPTC11MWR_8.3.4.9B1 format
                            image_short = f"{image_parts[0]}_{image_parts[-1]}"
                        else:
                            image_short = image_name.split('/')[-1]  # Get last part if path
                    else:
                        image_short = 'Unknown'
                    
                    # Count total iterations
                    total_iterations = 0
                    for device_data in results_by_device.values():
                        for job_data in device_data.get('jobs', {}).values():
                            total_iterations += len(job_data.get('per_iteration', []))
                    
                    # Build filename: Device-ImageShort_ITR-Count.xls
                    filename = f'{device_model}-{image_short}_ITR-{total_iterations}.xls'
            except Exception as e:
                # Fallback to timestamp-based filename if error
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'reboot_perf_results_{timestamp}.xlsx'
            
            return send_file(
                excel_buffer,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=filename
            )
        except Exception as e:
            return jsonify({'error': f'Failed to generate Excel: {str(e)}'}), 500

    def download_tiles_excel(self):
        """Download tiles detection results as Excel file"""
        from datetime import datetime
        from flask import send_file
        from services.excel_export import create_tiles_excel
        
        try:
            job_ids_param = request.args.get('job_ids', '')
            device_ips_param = request.args.get('device_ips', '')
            selected_job_ids = [j.strip() for j in job_ids_param.split(',') if j.strip()]
            selected_device_ips = [d.strip() for d in device_ips_param.split(',') if d.strip()]
            
            # Get tiles results
            results_data = self.get_tiles_results()
            if isinstance(results_data, tuple):
                data = results_data[0].get_json() if hasattr(results_data[0], 'get_json') else {}
            else:
                data = results_data.get_json() if hasattr(results_data, 'get_json') else {}
            
            results_by_device = data.get('results_by_device', {})
            
            # Filter if needed
            if selected_job_ids or selected_device_ips:
                filtered_results = {}
                for device_ip, device_data in results_by_device.items():
                    if selected_device_ips and device_ip not in selected_device_ips:
                        continue
                    filtered_jobs = {}
                    for job_id, job_data in device_data.get('jobs', {}).items():
                        if selected_job_ids and job_id not in selected_job_ids:
                            continue
                        filtered_jobs[job_id] = job_data
                    
                    if filtered_jobs:
                        filtered_results[device_ip] = device_data.copy()
                        filtered_results[device_ip]['jobs'] = filtered_jobs
                
                results_by_device = filtered_results
            
            # Create Excel file
            excel_buffer = create_tiles_excel(results_by_device)
            
            # Return as downloadable file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'tiles_detection_results_{timestamp}.xlsx'
            
            return send_file(
                excel_buffer,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=filename
            )
        except Exception as e:
            return jsonify({'error': f'Failed to generate Excel: {str(e)}'}), 500