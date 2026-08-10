"""
Device Grouping Integration Guide for Test Execution Service
Shows how to integrate TunnelGroupCoordinator for smart parallel execution

Problem (Current State):
- Multiple devices triggered simultaneously
- Each device tries to establish its own tunnel to R-Pi
- Causes tunnel conflicts and sequential execution

Solution (Proposed):
- Upfront device grouping by R-Pi configuration
- All devices in group share ONE tunnel
- Devices in group execute in parallel
- Different groups (different R-Pis) execute simultaneously

Integration Points in test_execution_service.py:
"""

# ============================================================================
# STEP 1: Add import at top of services/test_execution_service.py
# ============================================================================

"""
Add this import to existing imports:

from services.tunnel_group_coordinator import get_tunnel_group_coordinator
"""

# ============================================================================
# STEP 2: Add group-aware execution method to TestExecutionService class
# ============================================================================

"""
Add this new method to TestExecutionService class:

def execute_tests_for_multiple_devices(self, devices: List[Device], 
                                       execution_queue: List[dict],
                                       iterations: int,
                                       job_id: str) -> Dict:
    '''
    Execute tests on multiple devices with smart grouping by R-Pi backend
    
    Workflow:
    1. Analyze devices and group by R-Pi config
    2. For each group:
       a. Acquire group-level lock (blocks other groups using same R-Pi)
       b. Establish ONE tunnel for entire group
       c. Launch execution threads for all devices in group (PARALLEL)
       d. Wait for all devices in group to complete
       e. Release group lock (allows other groups to proceed)
    
    Example:
    - 4 devices: A (R-Pi X), B (R-Pi X), C (R-Pi Y), D (R-Pi Y)
    - Groups created: [A,B] for R-Pi X, [C,D] for R-Pi Y
    - Execution:
      - Acquire lock for R-Pi X
      - Start A and B in parallel (sharing tunnel)
      - While A & B execute, acquire different lock for R-Pi Y
      - Start C and D in parallel (on different R-Pi)
      - Result: A, B, C, D all execute simultaneously!
    
    Args:
        devices: List of Device objects to execute on
        execution_queue: Test methods to execute
        iterations: Number of iterations
        job_id: Job ID for tracking
    
    Returns:
        Dict with execution results for all devices
    '''
    
    tunnel_group_coordinator = get_tunnel_group_coordinator()
    
    # ========== PHASE 1: ANALYSIS ==========
    print(f"\\n{'='*80}")
    print(f"PHASE 1: DEVICE GROUPING ANALYSIS")
    print(f"{'='*80}")
    
    # Analyze and group devices by R-Pi config
    groups = tunnel_group_coordinator.analyze_and_group_devices(devices)
    
    # Print execution plan
    tunnel_group_coordinator.print_execution_plan()
    
    # Results tracking
    all_results = {}
    execution_threads = []
    
    # ========== PHASE 2: EXECUTION BY GROUP ==========
    print(f"{'='*80}")
    print(f"PHASE 2: GROUPED EXECUTION")
    print(f"{'='*80}\\n")
    
    # Each group can acquire lock independently and execute
    for rpi_ip, group in groups.items():
        group_thread = threading.Thread(
            target=self._execute_group,
            args=(group, execution_queue, iterations, job_id, tunnel_group_coordinator, all_results),
            daemon=False
        )
        group_thread.start()
        execution_threads.append(group_thread)
    
    # Wait for all groups to complete
    for thread in execution_threads:
        thread.join()
    
    print(f"\\n{'='*80}")
    print(f"✅ ALL GROUPS COMPLETED")
    print(f"{'='*80}\\n")
    
    return all_results


def _execute_group(self, group, execution_queue: List[dict], 
                   iterations: int, job_id: str, 
                   tunnel_group_coordinator, results_dict: Dict):
    '''
    Execute all devices in a group using shared tunnel
    
    Workflow:
    1. Acquire group-level lock for R-Pi
    2. Establish tunnel for group
    3. Launch execution threads for all devices
    4. Wait for devices to complete
    5. Release group lock
    '''
    rpi_ip = group.rpi_ip
    
    try:
        # ========== ACQUIRE GROUP LOCK ==========
        print(f"[GROUP-EXEC] {group.group_id}: Attempting to acquire lock for R-Pi {rpi_ip}...")
        success, msg = tunnel_group_coordinator.acquire_tunnel_for_group(
            rpi_ip=rpi_ip,
            timeout=60
        )
        
        if not success:
            print(f"[GROUP-EXEC] ❌ {group.group_id}: Failed to acquire lock - timeout or conflict")
            for device in group.devices:
                results_dict[device['name']] = {
                    'status': 'failed',
                    'reason': 'Could not acquire R-Pi tunnel access'
                }
            return
        
        # ========== ESTABLISH TUNNEL ONCE FOR GROUP ==========
        print(f"[GROUP-EXEC] {group.group_id}: Establishing tunnel to R-Pi {rpi_ip}...")
        
        # Get first device from group to establish tunnel
        first_device = group.devices[0]['object']
        tunnel_success, tunnel_msg, tunnel_service = self.establish_tunnel_for_device(first_device)
        
        if not tunnel_success:
            print(f"[GROUP-EXEC] ❌ {group.group_id}: Failed to establish tunnel - {tunnel_msg}")
            for device in group.devices:
                results_dict[device['name']] = {
                    'status': 'failed',
                    'reason': tunnel_msg
                }
            return
        
        print(f"[GROUP-EXEC] ✅ {group.group_id}: Tunnel established - {len(group.devices)} devices will share it")
        
        # ========== EXECUTE DEVICES IN PARALLEL ==========
        device_threads = []
        
        for device_dict in group.devices:
            device = device_dict['object']
            device_thread = threading.Thread(
                target=self._execute_single_device_with_shared_tunnel,
                args=(device, execution_queue, iterations, job_id, tunnel_service, results_dict),
                daemon=False,
                name=f"DeviceExec-{device.name}"
            )
            device_thread.start()
            device_threads.append(device_thread)
        
        # Wait for all devices in group to complete
        print(f"[GROUP-EXEC] {group.group_id}: Waiting for {len(device_threads)} devices to complete...")
        for thread in device_threads:
            thread.join()
        
        print(f"[GROUP-EXEC] ✅ {group.group_id}: All devices completed")
        
    finally:
        # ========== RELEASE GROUP LOCK ==========
        print(f"[GROUP-EXEC] {group.group_id}: Releasing lock for R-Pi {rpi_ip}...")
        tunnel_group_coordinator.release_tunnel_for_group(rpi_ip)
        print(f"[GROUP-EXEC] ✅ {group.group_id}: Lock released - other groups can now use R-Pi {rpi_ip}")


def _execute_single_device_with_shared_tunnel(self, device: Device, 
                                              execution_queue: List[dict],
                                              iterations: int, job_id: str,
                                              tunnel_service, results_dict: Dict):
    '''
    Execute tests on single device using a shared (already-established) tunnel
    
    Key Difference from standard execution:
    - Tunnel already exists (established by group)
    - Skip tunnel establishment/cleanup
    - Just run the test methods
    - Multiple devices can execute simultaneously (same tunnel)
    '''
    
    try:
        print(f"[DEVICE-EXEC] {device.name}: Starting execution (using group tunnel)...")
        
        # Store tunnel for this device to use
        self.active_tunnels[device.ip] = tunnel_service
        
        # Execute tests normally but with pre-established tunnel
        result = self._execute_queue_sequence(
            device=device,
            execution_queue=execution_queue,
            iterations=iterations,
            job_id=job_id,
            skip_tunnel_cleanup=True  # Don't release tunnel afterward
        )
        
        results_dict[device.name] = result
        print(f"[DEVICE-EXEC] ✅ {device.name}: Execution completed")
        
    except Exception as e:
        error_msg = f"Exception during device execution: {str(e)}"
        print(f"[DEVICE-EXEC] ❌ {device.name}: {error_msg}")
        results_dict[device.name] = {
            'status': 'failed',
            'reason': error_msg
        }
    finally:
        # Clean up tunnel reference (but don't release SSH tunnel)
        if device.ip in self.active_tunnels:
            del self.active_tunnels[device.ip]
"""

# ============================================================================
# STEP 3: Modify existing execute_test_queue to detect multi-device scenario
# ============================================================================

"""
In execute_test_queue method, add this logic around line 307:

    # Check if multiple devices need to execute same test (NEW)
    from models.device import Device
    
    # Get all selected devices (from request or job)
    selected_devices_ips = request.json.get('selected_devices', [])  # NEW
    
    if len(selected_devices_ips) > 1:
        # Multi-device execution - use grouping
        print(f"[MULTI-DEVICE] Detected {len(selected_devices_ips)} devices for parallel execution")
        
        devices = [Device.find_by_ip(ip) for ip in selected_devices_ips]
        devices = [d for d in devices if d is not None]
        
        # Use NEW grouped execution method
        results = self.execute_tests_for_multiple_devices(
            devices=devices,
            execution_queue=execution_queue,
            iterations=iterations,
            job_id=job_id
        )
        
        return jsonify({'success': True, 'results': results})
    else:
        # Single device or legacy - use existing flow
        device_ip = data.get('device_ip')
        ...rest of existing code...
"""

# ============================================================================
# STEP 4: Modify establish_tunnel_for_device to support skip_tunnel_cleanup
# ============================================================================

"""
Update the establish_tunnel_for_device method signature to accept skip_tunnel_cleanup
and modify cleanup_tunnel_for_device to respect this flag.

Around line 100 in establish_tunnel_for_device, change:

    try:
        # Get R-Pi IP from config
        rpi_ip = device.rpi_config.get('rpi_ip', 'unknown')
        
        # OLD: tunnel_coordinator.acquire_tunnel(...)
        
        # NEW: Don't use coordinator in grouped execution
        if not skip_tunnel_cleanup:
            tunnel_coordinator = get_tunnel_coordinator()
            acquired, acquire_result = tunnel_coordinator.acquire_tunnel(...)
        else:
            # Tunnel already acquired at group level
            print(f"[TUNNEL] Using group-level tunnel for {device.name}")
"""

# ============================================================================
# STEP 5: Testing & Validation
# ============================================================================

"""
Test the implementation:

1. Trigger execution on 4 devices (2 with same R-Pi, 2 with different R-Pi)
   Example:
   - Device A: R-Pi 10.138.17.42
   - Device B: R-Pi 10.138.17.42
   - Device C: R-Pi 10.138.17.43  
   - Device D: R-Pi 10.138.17.43

2. Expected output:
   - PHASE 1 shows 2 groups created
   - PHASE 2 shows parallel execution
   - Devices A & B execute with lock for 10.138.17.42
   - Devices C & D execute with lock for 10.138.17.43
   - Log shows devices executing simultaneously

3. Performance metrics:
   - Old way: Sequential queueing, 4 × (test_duration + tunnel_overhead)
   - New way: 2 × (test_duration + tunnel_overhead) due to parallel groups
"""
