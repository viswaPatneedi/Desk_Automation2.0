"""
Device Access Control - Manage device sharing and permissions
Handles device access levels and permission checks similar to sequences
"""

from enum import Enum
from typing import Optional, Dict


class AccessLevel(Enum):
    """Device access permission levels"""
    NONE = 'none'
    VIEW = 'view'  # Read-only access
    USE = 'use'    # Can use the device
    MANAGE = 'manage'  # Can manage sharing
    FULL = 'full'  # Full access (owner)

    def __lt__(self, other):
        """Compare access levels by restrictiveness (for inheritance)"""
        order = [AccessLevel.NONE, AccessLevel.VIEW, AccessLevel.USE, AccessLevel.MANAGE, AccessLevel.FULL]
        return order.index(self) < order.index(other)

    def __le__(self, other):
        return order.index(self) <= order.index(other) if hasattr(self, 'order') else self.value <= other.value


class DeviceAccessControl:
    """Control access to shared devices"""

    @staticmethod
    def get_user_access_level(current_user, device) -> AccessLevel:
        """
        Determine user's access level to a device
        
        Args:
            current_user: Current user object
            device: Device object
            
        Returns:
            AccessLevel enum
        """
        if not current_user:
            return AccessLevel.NONE

        user_team = getattr(current_user, 'team_name', '')
        user_ntid = getattr(current_user, 'ntid', '')
        is_super_admin = getattr(current_user, 'is_super_admin', False)
        is_team_admin = getattr(current_user, 'is_team_admin', False)
        
        device_team = getattr(device, 'team_name', '')
        device_owner = getattr(device, 'created_by', '')

        # Super admin always has full access
        if is_super_admin:
            return AccessLevel.FULL

        # Creator has full access
        if user_ntid == device_owner:
            return AccessLevel.FULL

        # Team admin on same team has manage access
        if is_team_admin and user_team == device_team:
            return AccessLevel.MANAGE

        # Check if device is shared with user's team
        shared_with_teams = getattr(device, 'shared_with_teams', {})
        if user_team in shared_with_teams:
            access_str = shared_with_teams[user_team]
            try:
                return AccessLevel(access_str)
            except ValueError:
                return AccessLevel.NONE

        # Same team members can view
        if user_team and user_team == device_team:
            return AccessLevel.USE

        return AccessLevel.NONE

    @staticmethod
    def can_view(current_user, device) -> bool:
        """Check if user can view device details"""
        access_level = DeviceAccessControl.get_user_access_level(current_user, device)
        return access_level != AccessLevel.NONE

    @staticmethod
    def can_use(current_user, device) -> bool:
        """Check if user can use the device"""
        access_level = DeviceAccessControl.get_user_access_level(current_user, device)
        viewable_levels = [AccessLevel.USE, AccessLevel.MANAGE, AccessLevel.FULL]
        return access_level in viewable_levels

    @staticmethod
    def can_manage(current_user, device) -> bool:
        """Check if user can manage device (share, etc)"""
        access_level = DeviceAccessControl.get_user_access_level(current_user, device)
        manageable_levels = [AccessLevel.MANAGE, AccessLevel.FULL]
        return access_level in manageable_levels

    @staticmethod
    def can_share(current_user, device) -> bool:
        """Check if user can share the device (only creator and super admin)"""
        is_super_admin = getattr(current_user, 'is_super_admin', False)
        user_ntid = getattr(current_user, 'ntid', '')
        device_owner = getattr(device, 'created_by', '')

        # Only super admin and device creator can share
        return is_super_admin or (user_ntid == device_owner)

    @staticmethod
    def can_manage_permissions(current_user) -> bool:
        """Check if user can manage any permissions (super admin only)"""
        return getattr(current_user, 'is_super_admin', False)

    @staticmethod
    def get_permission_info(current_user, device) -> Dict:
        """Get permission info for device"""
        access_level = DeviceAccessControl.get_user_access_level(current_user, device)
        return {
            'can_view': DeviceAccessControl.can_view(current_user, device),
            'can_use': DeviceAccessControl.can_use(current_user, device),
            'can_manage': DeviceAccessControl.can_manage(current_user, device),
            'can_share': DeviceAccessControl.can_share(current_user, device),
            'is_owner': (getattr(current_user, 'ntid', '') == getattr(device, 'created_by', '')),
            'access_level': access_level.value
        }
