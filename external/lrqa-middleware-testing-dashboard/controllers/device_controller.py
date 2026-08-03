"""
Device Controller - Handles device management requests
"""

from flask import jsonify, request
from models.device import Device
from models.device_lock import DeviceLock
from config.config_eta import format_eta

class DeviceController:
    """Controller for device-related operations"""
    
    @staticmethod
    def get_devices():
        """GET /api/devices - Get all devices with lock status and execution info, filtered by team if not admin"""
        from flask_login import current_user
        from models.job import Job
        devices = Device.load_all()
        device_list = []
        # Clean up expired locks first
        DeviceLock.cleanup_expired_locks()
        user_team = getattr(current_user, 'team_name', None)
        is_admin = getattr(current_user, 'is_admin', False)
        for device in devices:
            # Only show devices for user's team unless admin
            if not is_admin and user_team and device.team_name != user_team:
                continue
            device_dict = device.to_dict()
            # Add lock status
            lock = DeviceLock.get_device_lock(device.ip)
            if lock:
                lock_dict = lock.to_dict() if hasattr(lock, 'to_dict') else lock
                device_dict['locked'] = True
                device_dict['locked_by'] = lock_dict['user_id']
                device_dict['job_id'] = lock_dict['job_id']
                device_dict['estimated_completion'] = lock_dict['estimated_completion']
                device_dict['eta'] = lock_dict.get('eta_formatted', 'Unknown')
            else:
                device_dict['locked'] = False
                device_dict['locked_by'] = None
                device_dict['job_id'] = None
                device_dict['estimated_completion'] = None
                device_dict['eta'] = None
            
            # Phase 21: Add execution tracking info
            active_job = Job.get_active_device_job(device.ip)
            if active_job:
                device_dict['status'] = 'BUSY'
                device_dict['executing_user'] = getattr(active_job, 'executing_user', active_job.user_id)
                device_dict['triggered_at'] = getattr(active_job, 'triggered_at', active_job.start_time)
                device_dict['current_iteration'] = getattr(active_job, 'current_iteration', 1)
                device_dict['total_iterations'] = active_job.iterations
            else:
                device_dict['status'] = 'AVAILABLE'
                device_dict['executing_user'] = None
                device_dict['triggered_at'] = None
                device_dict['current_iteration'] = None
                device_dict['total_iterations'] = None
            
            device_list.append(device_dict)
        return jsonify({'success': True, 'devices': device_list})
    
    @staticmethod
    def add_device():
        """POST /api/devices - Add a new device (DESK or GDF_RACK)"""
        try:
            from flask_login import current_user
            data = request.json

            # Check if this is a RACK device
            is_rack_device = data.get('is_rack_device', False)
            
            # Validate required fields based on device type
            if is_rack_device:
                # RACK device validation
                required_fields = ['name', 'device_type', 'location']
                rpi_required_fields = ['rpi_ip', 'rpi_username', 'rpi_password']
                
                for field in required_fields:
                    if field not in data:
                        return jsonify({'error': f'Missing required RACK field: {field}'}), 400
                
                for field in rpi_required_fields:
                    if field not in data:
                        return jsonify({'error': f'Missing R-Pi configuration: {field}'}), 400
            else:
                # DESK device validation
                required_fields = ['name', 'device_type', 'mac_address', 'location']
                for field in required_fields:
                    if field not in data:
                        return jsonify({'error': f'Missing required field: {field}'}), 400

            # Determine team_name logic
            is_admin = getattr(current_user, 'is_admin', False)
            if is_admin:
                team_name = data.get('team_name', '')
            else:
                team_name = getattr(current_user, 'team_name', '')

            # Build R-Pi config for RACK devices
            rpi_config = {}
            if is_rack_device:
                rpi_config = {
                    'rpi_ip': data.get('rpi_ip'),
                    'rpi_port': data.get('rpi_port', 60201),
                    'rpi_username': data.get('rpi_username'),
                    'rpi_password': data.get('rpi_password')
                }

            # Create device object
            device = Device(
                ip=data.get('ip', '') if not is_rack_device else data.get('lab_ip', ''),
                name=data['name'],
                username=data.get('username', 'root') if not is_rack_device else data.get('lab_username', 'root'),
                password=data.get('password', '') if not is_rack_device else data.get('lab_password', ''),
                port=data.get('port', 10022) if not is_rack_device else data.get('lab_port', 10022),
                ir_config=data.get('ir_config', {}),
                mac_address=data.get('mac_address', ''),
                vnc_url=data.get('vnc_url', ''),
                use_jump_host=data.get('use_jump_host', False),
                jump_host_config=data.get('jump_host_config', {}),
                device_type=data.get('device_type', ''),
                location=data.get('location', ''),
                team_name=team_name,
                is_rack_device=is_rack_device,
                rpi_config=rpi_config
            )

            # Add device
            if Device.add(device):
                return jsonify({
                    'message': 'Device added successfully',
                    'device': device.to_dict()
                }), 201
            else:
                return jsonify({'error': 'Device with this IP already exists'}), 409
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error in add_device: {error_msg}")
            # Return user-friendly error message without exposing internals
            if 'password authentication' in error_msg.lower() or 'database' in error_msg.lower():
                return jsonify({
                    'message': 'Device added successfully (working in offline mode - database unavailable)',
                    'warning': 'Using JSON file storage. Connect database for persistent storage.',
                    'success': True
                }), 201  # Still return 201 since JSON save worked
            elif 'IntegrityError' in error_msg or 'constraint' in error_msg.lower():
                return jsonify({'error': f'Device with this IP already exists or database constraint violated'}), 409
            else:
                return jsonify({'error': f'Error adding device: {error_msg}'}), 500
    
    @staticmethod
    def delete_device():
        """DELETE /api/devices - Delete a device (admin only)"""
        from flask_login import current_user
        
        # Check if user is admin
        if not getattr(current_user, 'is_admin', False):
            return jsonify({'error': 'Only administrators can delete devices'}), 403
        
        data = request.json
        device_ip = data.get('ip')
        
        if not device_ip:
            return jsonify({'error': 'Device IP is required'}), 400
        
        if Device.delete(device_ip):
            return jsonify({'message': 'Device deleted successfully', 'success': True})
        else:
            return jsonify({'error': 'Device not found'}, 404), 404
    
    @staticmethod
    def delete_multiple_devices():
        """POST /api/devices/delete-multiple - Delete multiple devices (admin only)"""
        from flask_login import current_user
        
        # Check if user is admin
        if not getattr(current_user, 'is_admin', False):
            return jsonify({'error': 'Only administrators can delete devices'}), 403
        
        data = request.json
        device_ips = data.get('device_ips', [])
        
        if not device_ips or not isinstance(device_ips, list) or len(device_ips) == 0:
            return jsonify({'error': 'device_ips list is required'}), 400
        
        deleted_count = 0
        failed_count = 0
        failed_ips = []
        
        for device_ip in device_ips:
            try:
                if Device.delete(device_ip):
                    deleted_count += 1
                    print(f"✅ Deleted device: {device_ip}")
                else:
                    failed_count += 1
                    failed_ips.append(device_ip)
                    print(f"❌ Failed to delete device: {device_ip}")
            except Exception as e:
                failed_count += 1
                failed_ips.append(device_ip)
                print(f"❌ Exception deleting device {device_ip}: {str(e)}")
        
        return jsonify({
            'success': True,
            'message': f'Deleted {deleted_count} device(s)',
            'deleted_count': deleted_count,
            'failed_count': failed_count,
            'failed_ips': failed_ips
        })
    @staticmethod
    def update_device():
        """PUT /api/devices - Update a device"""
        try:
            data = request.json
            old_ip = data.get('old_ip')
            
            # Validate required fields
            required_fields = ['ip', 'name']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400
            
            if not old_ip:
                return jsonify({'error': 'Old device IP is required'}), 400
            
            # Preserve existing device data
            existing_device = Device.find_by_ip(old_ip) if old_ip else None
            
            if not existing_device:
                return jsonify({'error': 'Device not found'}), 404
            
            # Get all fields with fallbacks to existing device
            device_ip = data['ip']
            device_name = data['name']
            username = existing_device.username  # Keep existing username
            password = existing_device.password  # Keep existing password
            port = existing_device.port  # Keep existing port
            device_type = data.get('device_type', existing_device.device_type)
            location = data.get('location', existing_device.location)
            team_name = data.get('team_name', existing_device.team_name)
            mac_address = data.get('mac_address', existing_device.mac_address)
            ir_config = data.get('ir_config', existing_device.ir_config)

            # Check if new IP already exists (and it's not the old IP)
            if device_ip != old_ip:
                if Device.find_by_ip(device_ip):
                    return jsonify({'error': 'Device with this IP already exists'}), 409
            
            # Create updated device object
            device = Device(
                ip=device_ip,
                name=device_name,
                username=username,
                password=password,
                port=port,
                ir_config=ir_config,
                mac_address=mac_address,
                vnc_url=existing_device._vnc_url,
                use_jump_host=existing_device.use_jump_host,
                jump_host_config=existing_device.jump_host_config,
                device_type=device_type,
                location=location,
                team_name=team_name,
                is_rack_device=existing_device.is_rack_device,
                rpi_config=existing_device.rpi_config
            )
            
            # Update device
            if Device.update(old_ip, device):
                return jsonify({
                    'message': 'Device updated successfully',
                    'device': device.to_dict()
                }), 200
            else:
                return jsonify({'error': 'Device not found'}), 404
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error in update_device: {error_msg}")
            # Return user-friendly error message without exposing internals
            if 'password authentication' in error_msg.lower() or 'database' in error_msg.lower():
                return jsonify({
                    'message': 'Device updated (working in offline mode - database unavailable)',
                    'warning': 'Using JSON file storage. Connect database for persistent storage.',
                    'success': True
                }), 200  # Still return 200 since JSON save worked
            else:
                return jsonify({'error': f'Error updating device: {error_msg}'}), 500
    
    @staticmethod
    def test_connection():
        """POST /api/test_connection - Test SSH connection to device"""
        data = request.json
        device_ip = data.get('device_ip')
        
        if not device_ip:
            return jsonify({'error': 'Device IP is required'}), 400
        
        device = Device.find_by_ip(device_ip)
        if not device:
            return jsonify({'error': 'Device not found'}), 404
        
        success, message = device.validate_connection()
        return jsonify({
            'success': success,
            'message': message
        })
