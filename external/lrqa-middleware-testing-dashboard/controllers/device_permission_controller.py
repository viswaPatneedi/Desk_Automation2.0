"""
Device Permission Controller - Manages device access and sharing
Handles device sharing between teams similar to sequence sharing
"""

from flask import jsonify
from models.device import Device
from models.device_access_control import DeviceAccessControl, AccessLevel


class DevicePermissionController:
    """Controller for managing device permissions and sharing"""

    @staticmethod
    def share_device_with_team(device_ip: str, team_name: str, access_level: str, current_user):
        """
        Share a device with another team (Super Admin only)
        
        Args:
            device_ip: Device IP to share
            team_name: Team to share with
            access_level: 'view' or 'use'
            
        Returns:
            (result_dict, status_code)
        """
        try:
            # Only super admin can share
            if not DeviceAccessControl.can_manage_permissions(current_user):
                return {
                    'error': 'Permission denied. Only super admin can share devices.'
                }, 403

            # Find device
            devices = Device.load_all()
            print(f"🔍 Searching for device {device_ip} in {len(devices)} loaded devices")
            
            device = next((d for d in devices if d.ip == device_ip), None)
            if not device:
                return {'error': 'Device not found'}, 404

            print(f"📦 Found device: {device.name}")
            print(f"  Current shared_with_teams: {device.shared_with_teams}")

            # Don't share with own team
            if team_name == device.team_name:
                return {
                    'error': 'Device already belongs to this team'
                }, 400

            # Validate access level
            valid_levels = ['view', 'use']
            if access_level not in valid_levels:
                return {
                    'error': f'Invalid access level. Must be one of: {", ".join(valid_levels)}'
                }, 400

            # Update shared_with_teams
            if not device.shared_with_teams:
                device.shared_with_teams = {}
            
            device.shared_with_teams[team_name] = access_level
            print(f"✏️  Updated shared_with_teams: {device.shared_with_teams}")

            # Save changes - LOAD ALL DEVICES FIRST to avoid deactivating others!
            print(f"💾 Saving device {device.name} to storage...")
            
            # Replace the updated device in the full device list
            updated_device_ip = device.ip
            all_devices = Device.load_all()
            all_devices = [device if d.ip == updated_device_ip else d for d in all_devices]
            
            # Save ALL devices (not just the one being updated)
            Device.save_all(all_devices)
            print(f"✅ Device saved successfully (along with {len(all_devices) - 1} other devices)")

            return {
                'success': True,
                'message': f'Device shared with {team_name} (access: {access_level})',
                'device_ip': device_ip,
                'team_name': team_name,
                'access_level': access_level,
                'shared_with_teams': device.shared_with_teams
            }, 200

        except Exception as e:
            import traceback
            error_msg = str(e)
            print(f"❌ Error in share_device_with_team: {error_msg}")
            print(traceback.format_exc())
            return {'error': f'Failed to share device: {error_msg}'}, 500

    @staticmethod
    def revoke_device_access(device_ip: str, team_name: str, current_user):
        """
        Revoke a team's access to a device (Super Admin only)
        
        Returns:
            (result_dict, status_code)
        """
        try:
            # Only super admin can revoke
            if not DeviceAccessControl.can_manage_permissions(current_user):
                return {
                    'error': 'Permission denied. Only super admin can revoke device access.'
                }, 403

            # Find device
            devices = Device.load_all()
            device = next((d for d in devices if d.ip == device_ip), None)
            if not device:
                return {'error': 'Device not found'}, 404

            # Check if team has access
            if team_name not in device.shared_with_teams:
                return {
                    'error': f'Device is not shared with {team_name}'
                }, 404

            # Remove access
            del device.shared_with_teams[team_name]

            # Save changes - LOAD ALL DEVICES FIRST to avoid deactivating others!
            updated_device_ip = device.ip
            all_devices = Device.load_all()
            all_devices = [device if d.ip == updated_device_ip else d for d in all_devices]
            
            # Save ALL devices (not just the one being updated)
            Device.save_all(all_devices)

            return {
                'success': True,
                'message': f'Access revoked for {team_name}',
                'device_ip': device_ip,
                'team_name': team_name,
                'shared_with_teams': device.shared_with_teams
            }, 200

        except Exception as e:
            return {'error': f'Failed to revoke access: {str(e)}'}, 500

    @staticmethod
    def get_shareable_devices(current_user):
        """
        Get all devices that can be shared (created by user or super admin)
        
        Returns:
            (result_dict, status_code)
        """
        try:
            # Only super admin can access this
            if not DeviceAccessControl.can_manage_permissions(current_user):
                return {
                    'error': 'Permission denied. Only super admin can manage device sharing.'
                }, 403

            all_devices = Device.load_all()
            print(f"🔍 DEBUG get_shareable_devices: Loaded {len(all_devices)} devices")
            
            devices_list = []

            for device in all_devices:
                device_info = {
                    'ip': device.ip,
                    'name': device.name,
                    'team_name': device.team_name,
                    'device_type': device.device_type,
                    'location': device.location,
                    'created_by': device.created_by,
                    'shared_with_teams': device.shared_with_teams or {},
                    'access': DeviceAccessControl.get_permission_info(current_user, device)
                }
                devices_list.append(device_info)
                print(f"   📦 Device: {device.name} ({device.ip}) | Team: {device.team_name} | Shared: {device.shared_with_teams or {}}")

            print(f"✅ Returning {len(devices_list)} devices to super admin")
            return {
                'success': True,
                'count': len(devices_list),
                'devices': devices_list
            }, 200

        except Exception as e:
            import traceback
            error_msg = str(e)
            print(f"❌ Error in get_shareable_devices: {error_msg}")
            print(traceback.format_exc())
            return {'error': f'Failed to retrieve devices: {error_msg}'}, 500

    @staticmethod
    def get_device_details(device_ip: str, current_user):
        """
        Get device details with sharing information
        """
        try:
            devices = Device.load_all()
            device = next((d for d in devices if d.ip == device_ip), None)
            if not device:
                return {'error': 'Device not found'}, 404

            return {
                'success': True,
                'device': {
                    'ip': device.ip,
                    'name': device.name,
                    'team_name': device.team_name,
                    'device_type': device.device_type,
                    'location': device.location,
                    'created_by': device.created_by,
                    'shared_with_teams': device.shared_with_teams or {},
                    'access': DeviceAccessControl.get_permission_info(current_user, device)
                }
            }, 200

        except Exception as e:
            return {'error': f'Failed to retrieve device: {str(e)}'}, 500
