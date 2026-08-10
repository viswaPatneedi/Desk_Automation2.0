"""
Access Control Controller
Handles team access management for methods and sequences
Only super admin can manage access control
"""

from flask import request, jsonify
from flask_login import current_user, login_required
from models.access_control import AccessControl
from models.user import User
from models.saved_sequence import SavedSequence
from config.config_commands import AVAILABLE_METHODS
from datetime import datetime
import sys


class AccessControlController:
    """Controller for managing team access to resources"""

    @staticmethod
    def require_super_admin():
        """Helper to check if user is super admin"""
        is_super_admin = getattr(current_user, 'is_super_admin', False)
        if not is_super_admin:
            return jsonify({
                'success': False,
                'error': 'Access denied. Only super admin can manage access control.'
            }), 403
        return None

    @staticmethod
    def get_method_access_list():
        """GET /api/access/methods - Get access control for all methods"""
        error = AccessControlController.require_super_admin()
        if error:
            return error
        
        try:
            from models.teams import Teams
            
            # Get all teams from metadata
            teams_metadata = Teams.get_all_teams()
            team_list = list(teams_metadata.keys())
            
            method_access = AccessControl.get_all_method_access()
            
            # Build response with all methods
            methods_data = []
            for method_name in sorted(AVAILABLE_METHODS):
                methods_data.append({
                    'method_name': method_name,
                    'accessible_teams': method_access.get(method_name, []),
                    'total_teams': len(team_list)
                })
            
            return jsonify({
                'success': True,
                'methods': methods_data,
                'available_teams': team_list,
                'total_methods': len(AVAILABLE_METHODS),
                'total_teams': len(team_list)
            })
        except Exception as e:
            print(f"❌ [GET_METHOD_ACCESS] Error: {str(e)}", file=sys.stderr)
            return jsonify({'success': False, 'error': str(e)}), 500

    @staticmethod
    def update_method_access():
        """PUT /api/access/methods/<method_name> - Update team access for a method"""
        error = AccessControlController.require_super_admin()
        if error:
            return error
        
        try:
            from models.teams import Teams
            
            data = request.json
            method_name = data.get('method_name', '').strip()
            team_names = data.get('team_names', [])
            
            if not method_name:
                return jsonify({'success': False, 'error': 'Method name is required'}), 400
            
            if method_name not in AVAILABLE_METHODS:
                return jsonify({'success': False, 'error': f'Method {method_name} not found'}), 404
            
            # Validate team names exist in metadata
            teams_metadata = Teams.get_all_teams()
            
            for team in team_names:
                if team not in teams_metadata:
                    return jsonify({'success': False, 'error': f'Team {team} not found'}), 400
            
            AccessControl.set_method_team_access(method_name, team_names)
            
            print(f"✅ [UPDATE_METHOD_ACCESS] Method '{method_name}' access granted to teams: {team_names}", file=sys.stderr)
            return jsonify({
                'success': True,
                'method_name': method_name,
                'teams_granted': team_names,
                'timestamp': datetime.utcnow().isoformat()
            })
        except Exception as e:
            print(f"❌ [UPDATE_METHOD_ACCESS] Error: {str(e)}", file=sys.stderr)
            return jsonify({'success': False, 'error': str(e)}), 500

    @staticmethod
    def get_sequence_access_list():
        """GET /api/access/sequences - Get access control for all sequences"""
        error = AccessControlController.require_super_admin()
        if error:
            return error
        
        try:
            from models.teams import Teams
            
            sequences = SavedSequence.load_all()
            
            # Get all teams from metadata
            teams_metadata = Teams.get_all_teams()
            team_list = list(teams_metadata.keys())
            
            sequence_access = AccessControl.get_all_sequence_access()
            
            # Build response with all sequences
            sequences_data = []
            for seq in sequences:
                sequences_data.append({
                    'sequence_id': seq.sequence_id,
                    'sequence_name': seq.name,
                    'description': seq.description or '',
                    'created_by': seq.created_by,
                    'team_name': seq.team_name or 'Unassigned',
                    'accessible_teams': sequence_access.get(seq.sequence_id, []),
                    'created_at': seq.created_at,
                    'total_teams': len(team_list)
                })
            
            return jsonify({
                'success': True,
                'sequences': sequences_data,
                'available_teams': team_list,
                'total_sequences': len(sequences),
                'total_teams': len(team_list)
            })
        except Exception as e:
            print(f"❌ [GET_SEQUENCE_ACCESS] Error: {str(e)}", file=sys.stderr)
            return jsonify({'success': False, 'error': str(e)}), 500

    @staticmethod
    def update_sequence_access():
        """PUT /api/access/sequences/<sequence_id> - Update team access for a sequence"""
        error = AccessControlController.require_super_admin()
        if error:
            return error
        
        try:
            from models.teams import Teams
            
            data = request.json
            sequence_id = data.get('sequence_id', '').strip()
            team_names = data.get('team_names', [])
            
            if not sequence_id:
                return jsonify({'success': False, 'error': 'Sequence ID is required'}), 400
            
            sequences = SavedSequence.load_all()
            sequence = next((s for s in sequences if s.sequence_id == sequence_id), None)
            
            if not sequence:
                return jsonify({'success': False, 'error': f'Sequence {sequence_id} not found'}), 404
            
            # Validate team names exist in metadata
            teams_metadata = Teams.get_all_teams()
            
            for team in team_names:
                if team not in teams_metadata:
                    return jsonify({'success': False, 'error': f'Team {team} not found'}), 400
            
            AccessControl.set_sequence_team_access(sequence_id, team_names)
            
            print(f"✅ [UPDATE_SEQUENCE_ACCESS] Sequence '{sequence.name}' access granted to teams: {team_names}", file=sys.stderr)
            return jsonify({
                'success': True,
                'sequence_id': sequence_id,
                'sequence_name': sequence.name,
                'teams_granted': team_names,
                'timestamp': datetime.utcnow().isoformat()
            })
        except Exception as e:
            print(f"❌ [UPDATE_SEQUENCE_ACCESS] Error: {str(e)}", file=sys.stderr)
            return jsonify({'success': False, 'error': str(e)}), 500
