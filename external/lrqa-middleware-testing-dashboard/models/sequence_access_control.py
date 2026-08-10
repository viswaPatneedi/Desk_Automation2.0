"""
Sequence Access Control Model - Manages team access to saved sequences
Handles permission levels: FULL (owner), VIEW_CLONE (shared), NONE (no access)
"""

from __future__ import annotations
from enum import Enum
from typing import List, Dict, Optional, Tuple
from datetime import datetime


class AccessLevel(Enum):
    """Permission levels for sequence access"""
    NONE = "none"              # No access
    VIEW_ONLY = "view_only"    # Can only view (super admin shared with team)
    VIEW_CLONE = "view_clone"  # Can view and clone (default for shared)
    EDIT_DELETE = "edit_delete" # Can edit and delete (team admin over own team sequences)
    FULL = "full"              # Full control (creator and super admin)


class SequenceAccessControl:
    """Manages team access to saved sequences"""
    
    @staticmethod
    def get_user_access_level(current_user, sequence) -> AccessLevel:
        """
        Determine access level for current user on a sequence.
        
        Returns:
            AccessLevel: The access level for the user on this sequence
        """
        is_super_admin = getattr(current_user, 'is_super_admin', False)
        is_team_admin = getattr(current_user, 'is_team_admin', False)
        user_team = getattr(current_user, 'team_name', '')
        
        # Super admin has full access to everything
        if is_super_admin:
            return AccessLevel.FULL
        
        # Get sequence owner and team
        sequence_owner = getattr(sequence, 'created_by', '')
        sequence_team = getattr(sequence, 'team_name', '')
        shared_access = getattr(sequence, 'shared_with_teams', {})  # {team_name: access_level}
        
        # Creator has full access
        if sequence_owner == getattr(current_user, 'ntid', None):
            return AccessLevel.FULL
        
        # Users in the same team as the sequence owner
        # Team admins get EDIT_DELETE, regular members get VIEW_CLONE
        if user_team and user_team == sequence_team:
            if is_team_admin:
                return AccessLevel.EDIT_DELETE
            else:
                # Regular team members can view and clone their team's sequences
                return AccessLevel.VIEW_CLONE
        
        # Check if user's team has shared access from super admin
        if user_team in shared_access:
            access_level_str = shared_access[user_team]
            try:
                return AccessLevel(access_level_str)
            except ValueError:
                return AccessLevel.VIEW_CLONE  # Default to view/clone
        
        # No access
        return AccessLevel.NONE

    @staticmethod
    def can_view(current_user, sequence) -> bool:
        """Check if user can view the sequence"""
        access_level = SequenceAccessControl.get_user_access_level(current_user, sequence)
        viewable_levels = [
            AccessLevel.VIEW_ONLY,
            AccessLevel.VIEW_CLONE,
            AccessLevel.EDIT_DELETE,
            AccessLevel.FULL
        ]
        return access_level in viewable_levels

    @staticmethod
    def can_edit(current_user, sequence) -> bool:
        """Check if user can edit the sequence"""
        access_level = SequenceAccessControl.get_user_access_level(current_user, sequence)
        editable_levels = [
            AccessLevel.EDIT_DELETE,
            AccessLevel.FULL
        ]
        return access_level in editable_levels

    @staticmethod
    def can_delete(current_user, sequence) -> bool:
        """Check if user can delete the sequence"""
        access_level = SequenceAccessControl.get_user_access_level(current_user, sequence)
        deletable_levels = [
            AccessLevel.EDIT_DELETE,
            AccessLevel.FULL
        ]
        return access_level in deletable_levels

    @staticmethod
    def can_clone(current_user, sequence) -> bool:
        """Check if user can clone the sequence"""
        access_level = SequenceAccessControl.get_user_access_level(current_user, sequence)
        cloneable_levels = [
            AccessLevel.VIEW_ONLY,
            AccessLevel.VIEW_CLONE,
            AccessLevel.EDIT_DELETE,
            AccessLevel.FULL
        ]
        return access_level in cloneable_levels

    @staticmethod
    def can_share(current_user, sequence) -> bool:
        """Check if user can share the sequence (only creator and super admin)"""
        access_level = SequenceAccessControl.get_user_access_level(current_user, sequence)
        # Only creator and super admin can share
        return access_level == AccessLevel.FULL

    @staticmethod
    def can_manage_permissions(current_user) -> bool:
        """Check if user can manage sequence permissions (only super admin)"""
        return getattr(current_user, 'is_super_admin', False)

    @staticmethod
    def filter_sequences_by_access(sequences, current_user) -> List:
        """
        Filter sequences based on user's access level.
        Returns only sequences the user can view.
        """
        accessible_sequences = []
        for seq in sequences:
            if SequenceAccessControl.can_view(current_user, seq):
                accessible_sequences.append(seq)
        return accessible_sequences

    @staticmethod
    def add_permission_info_to_sequence(sequence_dict: dict, current_user) -> dict:
        """
        Add permission information to a sequence dict for API response.
        """
        from models.saved_sequence import SavedSequence
        
        # Create a temporary sequence object to check access
        seq = SavedSequence(
            name=sequence_dict.get('name', ''),
            queue_data=sequence_dict.get('queue_data', []),
            sequence_id=sequence_dict.get('sequence_id'),
            created_by=sequence_dict.get('created_by'),
            team_name=sequence_dict.get('team_name', ''),
            description=sequence_dict.get('description', '')
        )
        # Manually set shared_with_teams if it exists
        if 'shared_with_teams' in sequence_dict:
            seq.shared_with_teams = sequence_dict['shared_with_teams']
        else:
            seq.shared_with_teams = {}
        
        access_level = SequenceAccessControl.get_user_access_level(current_user, seq)
        
        sequence_dict['access'] = {
            'level': access_level.value,
            'can_view': access_level in [
                AccessLevel.VIEW_ONLY,
                AccessLevel.VIEW_CLONE,
                AccessLevel.EDIT_DELETE,
                AccessLevel.FULL
            ],
            'can_edit': access_level in [AccessLevel.EDIT_DELETE, AccessLevel.FULL],
            'can_delete': access_level in [AccessLevel.EDIT_DELETE, AccessLevel.FULL],
            'can_clone': access_level in [
                AccessLevel.VIEW_ONLY,    # Shared read-only sequences can be cloned
                AccessLevel.VIEW_CLONE    # Shared cloneable sequences can be cloned
            ],
            'can_share': access_level == AccessLevel.FULL,
            'is_owner': access_level == AccessLevel.FULL
        }
        
        return sequence_dict
