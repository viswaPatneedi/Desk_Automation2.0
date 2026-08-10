"""
Sequence Permission Controller - Manages sequence access and permissions
Handles sharing, cloning, and access control for saved sequences
"""

from flask import jsonify
from models.saved_sequence import SavedSequence
from models.sequence_access_control import SequenceAccessControl, AccessLevel


class SequencePermissionController:
    """Controller for managing sequence permissions"""

    @staticmethod
    def get_sequence_permissions(sequence_id: str, current_user):
        """
        Get permissions for a sequence
        
        Returns:
            {
                'sequence_id': str,
                'name': str,
                'owner_team': str,
                'created_by': str,
                'access_level': str,
                'shared_with': {team_name: access_level},
                'permissions': {can_view, can_edit, can_delete, can_clone, can_share}
            }
        """
        try:
            sequence = SavedSequence.find_by_id(sequence_id)
            if not sequence:
                return None, {'error': 'Sequence not found'}, 404

            # Check if user can view
            if not SequenceAccessControl.can_view(current_user, sequence):
                return None, {'error': 'Permission denied. No access to this sequence.'}, 403

            access_level = SequenceAccessControl.get_user_access_level(current_user, sequence)

            return {
                'sequence_id': sequence.sequence_id,
                'name': sequence.name,
                'owner_team': sequence.team_name,
                'created_by': sequence.created_by,
                'access_level': access_level.value,
                'shared_with': sequence.shared_with_teams or {},
                'permissions': {
                    'can_view': True,  # Already checked above
                    'can_edit': SequenceAccessControl.can_edit(current_user, sequence),
                    'can_delete': SequenceAccessControl.can_delete(current_user, sequence),
                    'can_clone': SequenceAccessControl.can_clone(current_user, sequence),
                    'can_share': SequenceAccessControl.can_share(current_user, sequence)
                }
            }, None, 200

        except Exception as e:
            return None, {'error': str(e)}, 500

    @staticmethod
    def share_sequence_with_team(sequence_id: str, team_name: str, access_level: str, current_user):
        """
        Share a sequence with another team (Super Admin only)
        
        Args:
            sequence_id: Sequence to share
            team_name: Team to share with
            access_level: 'view_only' or 'view_clone'
        """
        try:
            # Only super admin can share
            if not SequenceAccessControl.can_manage_permissions(current_user):
                return {'error': 'Permission denied. Only super admin can share sequences.'}, 403

            sequence = SavedSequence.find_by_id(sequence_id)
            if not sequence:
                return {'error': 'Sequence not found'}, 404

            # Validate access level
            valid_levels = ['view_only', 'view_clone']
            if access_level not in valid_levels:
                return {'error': f'Invalid access level. Must be one of: {valid_levels}'}, 400

            # Share the sequence
            success = SavedSequence.share_sequence_with_team(sequence_id, team_name, access_level)
            if success:
                return {
                    'success': True,
                    'message': f'Sequence shared with team {team_name}',
                    'team_name': team_name,
                    'access_level': access_level
                }, 200
            else:
                return {'error': 'Failed to share sequence'}, 500

        except Exception as e:
            return {'error': str(e)}, 500

    @staticmethod
    def revoke_sequence_access(sequence_id: str, team_name: str, current_user):
        """
        Revoke team access to sequence (Super Admin only)
        """
        try:
            # Only super admin can revoke
            if not SequenceAccessControl.can_manage_permissions(current_user):
                return {'error': 'Permission denied. Only super admin can revoke access.'}, 403

            sequence = SavedSequence.find_by_id(sequence_id)
            if not sequence:
                return {'error': 'Sequence not found'}, 404

            # Revoke access
            success = SavedSequence.revoke_sequence_sharing(sequence_id, team_name)
            if success:
                return {
                    'success': True,
                    'message': f'Access revoked from team {team_name}',
                    'team_name': team_name
                }, 200
            else:
                return {'error': 'Failed to revoke access'}, 500

        except Exception as e:
            return {'error': str(e)}, 500

    @staticmethod
    def clone_sequence(sequence_id: str, new_name: str, current_user):
        """
        Clone a sequence to current user's team
        
        Requirements:
            - User must have clone permission (can_clone returns True)
            - User must have team_name set
        """
        try:
            sequence = SavedSequence.find_by_id(sequence_id)
            if not sequence:
                return {'error': 'Sequence not found'}, 404

            # Check if user can clone
            if not SequenceAccessControl.can_clone(current_user, sequence):
                return {'error': 'Permission denied. You cannot clone this sequence.'}, 403

            # User must have a team
            user_team = getattr(current_user, 'team_name', '')
            if not user_team:
                return {'error': 'Your account does not have a team assigned. Cannot clone sequence.'}, 400

            # Validate new name
            if not new_name or not new_name.strip():
                return {'error': 'Sequence name is required'}, 400

            cloned_user = getattr(current_user, 'ntid', 'unknown')
            
            # Clone the sequence
            cloned_seq = SavedSequence.clone_sequence(
                sequence_id,
                new_name.strip(),
                user_team,
                cloned_user
            )

            if cloned_seq:
                return {
                    'success': True,
                    'message': f'Sequence cloned successfully to your team',
                    'cloned_sequence': cloned_seq.to_dict(),
                    'cloned_by': cloned_user,
                    'team': user_team
                }, 200
            else:
                return {'error': 'Failed to clone sequence'}, 500

        except Exception as e:
            return {'error': str(e)}, 500

    @staticmethod
    def list_sequences_with_permissions(current_user):
        """
        List all sequences with permission info for current user
        Filters based on user's access level
        """
        try:
            sequences = SavedSequence.load_all()
            
            # Filter and add permission info
            accessible_sequences = []
            for seq in sequences:
                if SequenceAccessControl.can_view(current_user, seq):
                    seq_dict = seq.to_dict()
                    # Add permission info
                    seq_dict = SequenceAccessControl.add_permission_info_to_sequence(seq_dict, current_user)
                    accessible_sequences.append(seq_dict)

            user_team = getattr(current_user, 'team_name', '')
            is_super_admin = getattr(current_user, 'is_super_admin', False)
            is_team_admin = getattr(current_user, 'is_team_admin', False)

            return {
                'success': True,
                'sequences': accessible_sequences,
                'current_user': getattr(current_user, 'ntid', 'unknown'),
                'user_team': user_team,
                'is_super_admin': is_super_admin,
                'is_team_admin': is_team_admin,
                'count': len(accessible_sequences)
            }, 200

        except Exception as e:
            return {'error': str(e)}, 500
