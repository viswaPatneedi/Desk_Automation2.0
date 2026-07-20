"""
Team Management Controller
Handles team creation, user management, and team-based access control
Only super admin (vpatne290) can create and manage teams
"""

from flask import request, jsonify, current_app
from flask_login import current_user, login_required
from models.user import User
from models.device import Device
from models.saved_sequence import SavedSequence
from datetime import datetime
import sys


class TeamController:
    """Controller for team management operations"""
    
    @staticmethod
    def require_super_admin():
        """Helper to check if user is super admin"""
        is_super_admin = getattr(current_user, 'is_super_admin', False)
        if not is_super_admin:
            return jsonify({
                'success': False,
                'error': 'Access denied. Only super admin can perform this action.'
            }), 403
        return None

    @staticmethod
    def list_teams():
        """GET /api/teams - List all teams (super admin only)"""
        # Check super admin
        error = TeamController.require_super_admin()
        if error:
            return error
        
        try:
            users = User.load_users()
            teams = {}
            
            # Collect unique teams and their members
            for user in users.values():
                team_name = getattr(user, 'team_name', '')
                if team_name:
                    if team_name not in teams:
                        teams[team_name] = {
                            'team_name': team_name,
                            'members': [],
                            'member_count': 0,
                            'created_at': None
                        }
                    
                    member_info = {
                        'ntid': user.ntid,
                        'email': user.email,
                        'name': user.name,
                        'is_team_admin': getattr(user, 'is_team_admin', False),
                        'created_at': user.created_at
                    }
                    teams[team_name]['members'].append(member_info)
                    teams[team_name]['member_count'] = len(teams[team_name]['members'])
            
            return jsonify({
                'success': True,
                'teams': list(teams.values()),
                'team_count': len(teams)
            })
        except Exception as e:
            print(f"❌ [LIST_TEAMS] Error: {str(e)}", file=sys.stderr)
            return jsonify({'success': False, 'error': str(e)}), 500

    @staticmethod
    def create_team():
        """POST /api/teams - Create a new team (super admin only)"""
        # Check super admin
        error = TeamController.require_super_admin()
        if error:
            return error
        
        try:
            data = request.json
            team_name = data.get('team_name', '').strip()
            description = data.get('description', '')
            members = data.get('members', [])  # List of {"ntid": str, "email": str, "name": str, "is_team_admin": bool}
            
            if not team_name:
                return jsonify({'success': False, 'error': 'Team name is required'}), 400
            
            if len(team_name) < 3:
                return jsonify({'success': False, 'error': 'Team name must be at least 3 characters'}), 400
            
            # Validate members
            if members and not isinstance(members, list):
                return jsonify({'success': False, 'error': 'Members must be a list'}), 400
            
            print(f"[CREATE_TEAM] Creating team: {team_name} by {current_user.ntid}", file=sys.stderr)
            print(f"  Members: {len(members)} user(s)", file=sys.stderr)
            
            # Load existing users
            users = User.load_users()
            
            # Create team members
            created_users = []
            for member in members:
                ntid = member.get('ntid', '').strip()
                email = member.get('email', '').strip()
                name = member.get('name', ntid)
                is_team_admin = member.get('is_team_admin', False)
                
                if not ntid or not email:
                    print(f"⚠️  [CREATE_TEAM] Skipping invalid member: {member}", file=sys.stderr)
                    continue
                
                # Check if user already exists
                if ntid in users:
                    print(f"⚠️  [CREATE_TEAM] User {ntid} already exists, skipping", file=sys.stderr)
                    continue
                
                # Create new user with team assignment
                from werkzeug.security import generate_password_hash
                temp_password = f"{ntid}@TempPass123"  # Temporary password
                
                new_user = User(
                    ntid=ntid,
                    email=email,
                    name=name,
                    password_hash=generate_password_hash(temp_password),
                    team_name=team_name,
                    is_super_admin=False,
                    is_team_admin=is_team_admin
                )
                users[ntid] = new_user
                created_users.append({
                    'ntid': ntid,
                    'email': email,
                    'is_team_admin': is_team_admin
                })
                
                print(f"✅ [CREATE_TEAM] User created: {ntid} (team_admin: {is_team_admin})", file=sys.stderr)
            
            # Save all users
            User.save_users(users)
            
            return jsonify({
                'success': True,
                'team_name': team_name,
                'description': description,
                'members_created': len(created_users),
                'created_members': created_users,
                'timestamp': datetime.utcnow().isoformat()
            })
        except Exception as e:
            print(f"❌ [CREATE_TEAM] Error: {str(e)}", file=sys.stderr)
            return jsonify({'success': False, 'error': str(e)}), 500

    @staticmethod
    def add_team_member():
        """POST /api/teams/<team_name>/members - Add member to team (super admin only)"""
        # Check super admin
        error = TeamController.require_super_admin()
        if error:
            return error
        
        try:
            data = request.json
            team_name = data.get('team_name', '').strip()
            ntid = data.get('ntid', '').strip()
            email = data.get('email', '').strip()
            name = data.get('name', ntid)
            is_team_admin = data.get('is_team_admin', False)
            
            if not team_name or not ntid or not email:
                return jsonify({'success': False, 'error': 'Team name, NTID, and email are required'}), 400
            
            users = User.load_users()
            
            # Check if user already exists
            if ntid in users:
                user = users[ntid]
                # Update user's team if they exist
                user.team_name = team_name
                user.is_team_admin = is_team_admin
                print(f"[ADD_TEAM_MEMBER] Updated existing user {ntid} to team {team_name}", file=sys.stderr)
            else:
                # Create new user
                from werkzeug.security import generate_password_hash
                temp_password = f"{ntid}@TempPass123"
                
                user = User(
                    ntid=ntid,
                    email=email,
                    name=name,
                    password_hash=generate_password_hash(temp_password),
                    team_name=team_name,
                    is_super_admin=False,
                    is_team_admin=is_team_admin
                )
                users[ntid] = user
                print(f"✅ [ADD_TEAM_MEMBER] Created user {ntid} in team {team_name}", file=sys.stderr)
            
            User.save_users(users)
            
            return jsonify({
                'success': True,
                'user': {
                    'ntid': user.ntid,
                    'email': user.email,
                    'name': user.name,
                    'team_name': user.team_name,
                    'is_team_admin': user.is_team_admin
                },
                'timestamp': datetime.utcnow().isoformat()
            })
        except Exception as e:
            print(f"❌ [ADD_TEAM_MEMBER] Error: {str(e)}", file=sys.stderr)
            return jsonify({'success': False, 'error': str(e)}), 500

    @staticmethod
    def update_team_member():
        """PUT /api/teams/members/<ntid> - Update team member (super admin only)"""
        # Check super admin
        error = TeamController.require_super_admin()
        if error:
            return error
        
        try:
            data = request.json
            ntid = data.get('ntid', '').strip()
            team_name = data.get('team_name')
            is_team_admin = data.get('is_team_admin')
            
            if not ntid:
                return jsonify({'success': False, 'error': 'NTID is required'}), 400
            
            users = User.load_users()
            
            if ntid not in users:
                return jsonify({'success': False, 'error': f'User {ntid} not found'}), 404
            
            user = users[ntid]
            
            # Don't allow changing vpatne290's super admin status
            if ntid == 'vpatne290' and team_name:
                return jsonify({'success': False, 'error': 'Cannot change super admin team assignment'}), 403
            
            if team_name is not None:
                user.team_name = team_name
            if is_team_admin is not None:
                user.is_team_admin = is_team_admin
            
            User.save_users(users)
            
            return jsonify({
                'success': True,
                'user': {
                    'ntid': user.ntid,
                    'email': user.email,
                    'team_name': user.team_name,
                    'is_team_admin': user.is_team_admin
                }
            })
        except Exception as e:
            print(f"❌ [UPDATE_TEAM_MEMBER] Error: {str(e)}", file=sys.stderr)
            return jsonify({'success': False, 'error': str(e)}), 500

    @staticmethod
    def delete_team_member():
        """DELETE /api/teams/members/<ntid> - Remove user from team (super admin only)"""
        # Check super admin
        error = TeamController.require_super_admin()
        if error:
            return error
        
        try:
            ntid = request.args.get('ntid', '').strip()
            
            if not ntid:
                return jsonify({'success': False, 'error': 'NTID is required'}), 400
            
            # Don't allow deleting super admin
            if ntid == 'vpatne290':
                return jsonify({'success': False, 'error': 'Cannot delete super admin user'}), 403
            
            users = User.load_users()
            
            if ntid not in users:
                return jsonify({'success': False, 'error': f'User {ntid} not found'}), 404
            
            del users[ntid]
            User.save_users(users)
            
            print(f"✅ [DELETE_TEAM_MEMBER] Deleted user {ntid}", file=sys.stderr)
            return jsonify({
                'success': True,
                'deleted_ntid': ntid,
                'timestamp': datetime.utcnow().isoformat()
            })
        except Exception as e:
            print(f"❌ [DELETE_TEAM_MEMBER] Error: {str(e)}", file=sys.stderr)
            return jsonify({'success': False, 'error': str(e)}), 500

    @staticmethod
    def get_team_stats():
        """GET /api/teams/<team_name>/stats - Get team statistics"""
        try:
            team_name = request.args.get('team_name', '').strip()
            
            if not team_name:
                return jsonify({'success': False, 'error': 'Team name is required'}), 400
            
            users = User.load_users()
            devices = Device.load_all()
            sequences = SavedSequence.load_all()
            
            # Count team resources
            team_users = [u for u in users.values() if getattr(u, 'team_name', '') == team_name]
            team_devices = [d for d in devices if getattr(d, 'team_name', '') == team_name]
            team_sequences = [s for s in sequences if getattr(s, 'team_name', '') == team_name]
            
            return jsonify({
                'success': True,
                'team_name': team_name,
                'stats': {
                    'users': len(team_users),
                    'team_admins': len([u for u in team_users if getattr(u, 'is_team_admin', False)]),
                    'devices': len(team_devices),
                    'sequences': len(team_sequences)
                }
            })
        except Exception as e:
            print(f"❌ [GET_TEAM_STATS] Error: {str(e)}", file=sys.stderr)
            return jsonify({'success': False, 'error': str(e)}), 500
