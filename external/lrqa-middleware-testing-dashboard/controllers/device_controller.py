"""
Device Controller - Handles device management requests
"""

from flask import jsonify, request
from models.device import Device
from models.device_lock import DeviceLock
from config_eta import format_eta

class DeviceController:
    """Controller for device-related operations"""
    
    @staticmethod
    def get_devices():
        """GET /api/devices - Get all devices with lock status, filtered by team if not admin"""
        from flask_login import current_user
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
            device_list.append(device_dict)
        return jsonify({'success': True, 'devices': device_list})
    
    @staticmethod
    def add_device():
        """POST /api/devices - Add a new device"""
        from flask_login import current_user
        data = request.json

        # Validate required fields (except team_name, which is handled below)
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

        # Create device object
        device = Device(
            ip=data.get('ip', ''),
            name=data['name'],
            username=data.get('username', 'root'),
            password=data.get('password', ''),
            port=data.get('port', 10022),
            ir_config=data.get('ir_config', {}),
            mac_address=data.get('mac_address', ''),
            vnc_url=data.get('vnc_url', ''),
            use_jump_host=data.get('use_jump_host', False),
            jump_host_config=data.get('jump_host_config', {}),
            device_type=data.get('device_type', ''),
            location=data.get('location', ''),
            team_name=team_name
        )

        # Add device
        if Device.add(device):
            return jsonify({
                'message': 'Device added successfully',
                'device': device.to_dict()
            }), 201
        else:
            return jsonify({'error': 'Device with this IP already exists'}), 409
    
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
            team_name=team_name
        )
        
        # Update device
        if Device.update(old_ip, device):
            return jsonify({
                'message': 'Device updated successfully',
                'device': device.to_dict()
            }), 200
        else:
            return jsonify({'error': 'Device not found'}), 404
    
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
