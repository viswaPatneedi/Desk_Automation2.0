"""
App Credential Controller - Handle CRUD operations for app credentials
Desk-Automation v2.0
"""

from flask import jsonify
from models.database import Session
from models.app_credential import AppCredential
from datetime import datetime, timezone
import uuid
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)


class AppCredentialController:
    """Controller for managing app credentials"""

    @staticmethod
    def list_credentials(team_name=None, app_name=None, is_active=True):
        """
        List app credentials with optional filters.
        Super admin can see all credentials, others see team-specific ones.
        """
        session = Session()
        try:
            query = session.query(AppCredential)
            
            if team_name:
                query = query.filter(AppCredential.team_name == team_name)
            
            if app_name:
                query = query.filter(AppCredential.app_name == app_name)
            
            if is_active:
                query = query.filter(AppCredential.is_active == True)
            
            query = query.order_by(AppCredential.app_name, AppCredential.is_primary.desc())
            credentials = query.all()
            
            return [cred.to_dict() for cred in credentials], 200
        except Exception as e:
            logger.error(f"Error listing credentials: {str(e)}")
            return {'error': str(e)}, 500
        finally:
            session.close()

    @staticmethod
    def get_credential(credential_id):
        """Get a specific credential by ID (excluding password)"""
        session = Session()
        try:
            cred = session.query(AppCredential).filter(
                AppCredential.credential_id == credential_id
            ).first()
            
            if not cred:
                return {'error': 'Credential not found'}, 404
            
            return cred.to_dict(), 200
        except Exception as e:
            logger.error(f"Error getting credential: {str(e)}")
            return {'error': str(e)}, 500
        finally:
            session.close()

    @staticmethod
    def get_credential_with_password(credential_id, current_user):
        """
        Get credential WITH password - for internal use by authenticated users only.
        Only super admin or team members can access.
        """
        session = Session()
        try:
            cred = session.query(AppCredential).filter(
                AppCredential.credential_id == credential_id
            ).first()
            
            if not cred:
                return {'error': 'Credential not found'}, 404
            
            # Check authorization
            is_super_admin = getattr(current_user, 'is_super_admin', False)
            is_team_admin = getattr(current_user, 'is_team_admin', False)
            user_team = getattr(current_user, 'team_name', None)
            
            if not is_super_admin:
                # Team members can only access their team's credentials
                if cred.team_name != user_team and not is_team_admin:
                    return {'error': 'Unauthorized to access this credential'}, 403
            
            return cred.to_dict_with_credentials(), 200
        except Exception as e:
            logger.error(f"Error getting credential with password: {str(e)}")
            return {'error': str(e)}, 500
        finally:
            session.close()

    @staticmethod
    def get_primary_credential(app_name, team_name):
        """Get the primary (most recently used) credential for an app"""
        session = Session()
        try:
            cred = session.query(AppCredential).filter(
                AppCredential.app_name == app_name,
                AppCredential.team_name == team_name,
                AppCredential.is_primary == True,
                AppCredential.is_active == True
            ).first()
            
            if not cred:
                # If no primary, return the first active one
                cred = session.query(AppCredential).filter(
                    AppCredential.app_name == app_name,
                    AppCredential.team_name == team_name,
                    AppCredential.is_active == True
                ).order_by(AppCredential.usage_count.desc()).first()
            
            if not cred:
                return {'error': f'No credentials found for {app_name}'}, 404
            
            # Return with credentials for internal use
            return cred.to_dict_with_credentials(), 200
        except Exception as e:
            logger.error(f"Error getting primary credential: {str(e)}")
            return {'error': str(e)}, 500
        finally:
            session.close()

    @staticmethod
    def create_credential(app_name, username, password, login_url, team_name, 
                         current_user, profile_name=None, api_key=None, 
                         custom_config=None, app_version=None, device_type=None,
                         is_primary=True):
        """Create a new app credential"""
        session = Session()
        try:
            # Check if this is the first credential for this app in the team
            existing = session.query(AppCredential).filter(
                AppCredential.app_name == app_name,
                AppCredential.team_name == team_name
            ).first()
            
            credential_id = f"{app_name}_{team_name}_{uuid.uuid4().hex[:8]}"
            
            new_cred = AppCredential(
                credential_id=credential_id,
                app_name=app_name,
                username=username,
                password=password,
                login_url=login_url,
                profile_name=profile_name,
                api_key=api_key,
                custom_config=custom_config,
                app_version=app_version,
                device_type=device_type,
                is_primary=is_primary if not existing else False,  # Only first is primary
                team_name=team_name,
                created_by=current_user.id if current_user else None,
                updated_by=current_user.id if current_user else None
            )
            
            session.add(new_cred)
            session.commit()
            
            result = new_cred.to_dict()
            return result, 201
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating credential: {str(e)}")
            return {'error': str(e)}, 500
        finally:
            session.close()

    @staticmethod
    def update_credential(credential_id, current_user, **kwargs):
        """Update an existing credential"""
        session = Session()
        try:
            cred = session.query(AppCredential).filter(
                AppCredential.credential_id == credential_id
            ).first()
            
            if not cred:
                return {'error': 'Credential not found'}, 404
            
            # Update allowed fields
            allowed_fields = [
                'username', 'password', 'login_url', 'profile_name', 
                'api_key', 'custom_config', 'app_version', 'device_type',
                'is_primary', 'is_active'
            ]
            
            for field in allowed_fields:
                if field in kwargs:
                    setattr(cred, field, kwargs[field])
            
            cred.updated_at = datetime.now(timezone.utc)
            cred.updated_by = current_user.id if current_user else None
            
            session.commit()
            return cred.to_dict(), 200
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating credential: {str(e)}")
            return {'error': str(e)}, 500
        finally:
            session.close()

    @staticmethod
    def delete_credential(credential_id):
        """Soft delete a credential (mark as inactive)"""
        session = Session()
        try:
            cred = session.query(AppCredential).filter(
                AppCredential.credential_id == credential_id
            ).first()
            
            if not cred:
                return {'error': 'Credential not found'}, 404
            
            cred.is_active = False
            cred.updated_at = datetime.now(timezone.utc)
            session.commit()
            
            return {'message': 'Credential deleted successfully'}, 200
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting credential: {str(e)}")
            return {'error': str(e)}, 500
        finally:
            session.close()

    @staticmethod
    def set_primary_credential(credential_id, current_user):
        """Set a credential as primary for its app in the team"""
        session = Session()
        try:
            cred = session.query(AppCredential).filter(
                AppCredential.credential_id == credential_id
            ).first()
            
            if not cred:
                return {'error': 'Credential not found'}, 404
            
            # Mark all other credentials for this app in this team as non-primary
            session.query(AppCredential).filter(
                AppCredential.app_name == cred.app_name,
                AppCredential.team_name == cred.team_name,
                AppCredential.credential_id != credential_id
            ).update({'is_primary': False})
            
            cred.is_primary = True
            cred.updated_at = datetime.now(timezone.utc)
            cred.updated_by = current_user.id if current_user else None
            
            session.commit()
            return cred.to_dict(), 200
        except Exception as e:
            session.rollback()
            logger.error(f"Error setting primary credential: {str(e)}")
            return {'error': str(e)}, 500
        finally:
            session.close()

    @staticmethod
    def record_usage(credential_id):
        """Record that a credential was used"""
        session = Session()
        try:
            cred = session.query(AppCredential).filter(
                AppCredential.credential_id == credential_id
            ).first()
            
            if cred:
                cred.last_used_at = datetime.now(timezone.utc)
                cred.usage_count = (cred.usage_count or 0) + 1
                session.commit()
        except Exception as e:
            logger.error(f"Error recording credential usage: {str(e)}")
        finally:
            session.close()
