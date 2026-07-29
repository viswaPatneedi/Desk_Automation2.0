"""
App Credential Model - Stores app credentials like Netflix, Disney+, Hulu, etc.
Desk-Automation v2.0 - PostgreSQL + SQLAlchemy
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .database import Base


class AppCredential(Base):
    """
    App Credential model for storing streaming/app credentials securely.
    Supports multiple apps (Netflix, Disney+, Hulu, etc.) with team scoping.
    """
    __tablename__ = "app_credentials"

    id = Column(Integer, primary_key=True)
    credential_id = Column(String(255), unique=True, nullable=False)  # e.g., 'netflix_v1', 'disney_v1'
    app_name = Column(String(100), nullable=False)  # netflix, disney_plus, hulu, youtube, etc.
    username = Column(String(255), nullable=False)
    password = Column(String(255), nullable=False)  # Should be encrypted in production
    login_url = Column(Text)  # URL for logging in to the app
    profile_name = Column(String(255))  # Optional profile name (e.g., "Kids", "Adult")
    
    # App-specific configurations
    api_key = Column(String(500))  # Optional API key for app integration
    custom_config = Column(Text)  # JSON string for app-specific settings
    
    # Metadata
    app_version = Column(String(50))  # App version if applicable
    device_type = Column(String(100))  # e.g., 'RDK', 'XUMO-TV', 'FIRETV'
    is_primary = Column(Boolean, default=True)  # Mark primary credential for the app
    
    # Team and Access Control
    team_name = Column(String(255), nullable=False)
    location = Column(String(100))
    
    # Audit Trail
    created_by = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    updated_by = Column(Integer, ForeignKey('users.id'))
    is_active = Column(Boolean, default=True)
    
    # Access tracking
    last_used_at = Column(DateTime)
    usage_count = Column(Integer, default=0)
    
    # Indexes
    __table_args__ = (
        Index('idx_app_credentials_app_name', 'app_name'),
        Index('idx_app_credentials_team_name', 'team_name'),
        Index('idx_app_credentials_is_primary', 'is_primary'),
        Index('idx_app_credentials_is_active', 'is_active'),
    )

    def to_dict(self):
        """Convert to dictionary (exclude sensitive data)"""
        return {
            'id': self.id,
            'credential_id': self.credential_id,
            'app_name': self.app_name,
            'username': self.username,
            'password': '***hidden***',  # Don't expose password in API responses
            'login_url': self.login_url,
            'profile_name': self.profile_name,
            'app_version': self.app_version,
            'device_type': self.device_type,
            'is_primary': self.is_primary,
            'team_name': self.team_name,
            'location': self.location,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'usage_count': self.usage_count
        }

    def to_dict_with_credentials(self):
        """Convert to dictionary WITH sensitive data - for authorized internal use only"""
        return {
            'id': self.id,
            'credential_id': self.credential_id,
            'app_name': self.app_name,
            'username': self.username,
            'password': self.password,  # Include password for internal use
            'login_url': self.login_url,
            'profile_name': self.profile_name,
            'api_key': self.api_key,
            'custom_config': self.custom_config,
            'app_version': self.app_version,
            'device_type': self.device_type,
            'is_primary': self.is_primary,
            'team_name': self.team_name,
            'location': self.location,
            'is_active': self.is_active
        }

    def __repr__(self):
        return f"<AppCredential(app_name='{self.app_name}', username='{self.username}', team='{self.team_name}')>"
