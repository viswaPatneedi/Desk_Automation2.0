"""User model for authentication and user management."""
import json
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from config.config_paths import USERS_FILE
from models.database import Session, User as DBUser


class User:
    """User model for storing user information and authentication."""
    
    def __init__(self, ntid, email, name, password_hash, created_at=None, user_id=None, alternate_email=None, is_admin=False, team_name=None):
        self.user_id = user_id or ntid  # Use NTID as user_id if not provided
        self.ntid = ntid
        self.email = email
        self.alternate_email = alternate_email or f"{ntid}@cable.comcast.com"  # Auto-generate alternate email
        self.name = name
        self.password_hash = password_hash
        self.is_admin = is_admin  # Admin flag
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False
        self.team_name = team_name or ''
    
    def get_id(self):
        """Return user ID for Flask-Login."""
        return self.user_id
    
    def check_password(self, password):
        """Verify password against stored hash."""
        return check_password_hash(self.password_hash, password)
    
    def set_password(self, password):
        """Set a new password for the user."""
        self.password_hash = generate_password_hash(password)
    
    def save(self):
        """Save the current user to the users file."""
        users = User.load_users()
        users[self.user_id] = self
        User.save_users(users)
    
    def to_dict(self):
        """Convert user object to dictionary."""
        return {
            'user_id': self.user_id,
            'ntid': self.ntid,
            'email': self.email,
            'alternate_email': self.alternate_email,
            'name': self.name,
            'password_hash': self.password_hash,
            'created_at': self.created_at,
            'is_admin': self.is_admin,
            'team_name': self.team_name
        }
    
    @staticmethod
    def from_dict(data):
        """Create User object from dictionary."""
        return User(
            ntid=data['ntid'],
            email=data['email'],
            name=data['name'],
            password_hash=data['password_hash'],
            created_at=data.get('created_at'),
            user_id=data.get('user_id'),
            alternate_email=data.get('alternate_email'),
            is_admin=data.get('is_admin', False),
            team_name=data.get('team_name', '')
        )

    @staticmethod
    def _load_json_users():
        if not os.path.exists(USERS_FILE):
            return {}

        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                users_data = json.load(f)
                return users_data if isinstance(users_data, dict) else {}
        except (json.JSONDecodeError, IOError):
            return {}

    @staticmethod
    def _write_json_backup(users):
        users_data = {uid: user.to_dict() for uid, user in users.items()}
        os.makedirs(os.path.dirname(USERS_FILE) or '.', exist_ok=True)
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users_data, f, indent=2)

    @staticmethod
    def _from_db_row(row, backup_data=None):
        backup_data = backup_data or {}
        user = User(
            ntid=row.username,
            email=row.email,
            name=backup_data.get('name', row.username),
            password_hash=row.password_hash,
            created_at=row.created_at.isoformat() if row.created_at else None,
            user_id=backup_data.get('user_id', row.username),
            alternate_email=backup_data.get('alternate_email', row.email or f"{row.username}@cable.comcast.com"),
            is_admin=row.is_admin,
            team_name=row.team_name or backup_data.get('team_name', '')
        )
        user.is_approved = row.is_approved
        user.is_active = row.active
        return user
    
    @staticmethod
    def load_users():
        """Load all users from the database, with JSON fallback."""
        backup_users = User._load_json_users()

        session = Session()
        try:
            rows = session.query(DBUser).filter_by(active=True).order_by(DBUser.username.asc()).all()
            if rows:
                users = {}
                for row in rows:
                    users[row.username] = User._from_db_row(row, backup_users.get(row.username, {}))

                for uid, data in backup_users.items():
                    if uid not in users:
                        users[uid] = User.from_dict(data)

                return users
        except Exception:
            pass
        finally:
            session.close()

        return {uid: User.from_dict(data) for uid, data in backup_users.items()}
    
    @staticmethod
    def save_users(users):
        """Save all users to the database and mirror them to JSON."""
        session = Session()
        try:
            for uid, user in users.items():
                row = session.query(DBUser).filter_by(username=user.ntid).first()
                if row is None:
                    row = DBUser(
                        username=user.ntid,
                        password_hash=user.password_hash,
                        email=user.email,
                        team_name=user.team_name,
                        is_admin=user.is_admin,
                        is_approved=getattr(user, 'is_approved', True),
                        active=getattr(user, 'is_active', True)
                    )
                    session.add(row)
                else:
                    row.password_hash = user.password_hash
                    row.email = user.email
                    row.team_name = user.team_name
                    row.is_admin = user.is_admin
                    row.is_approved = getattr(user, 'is_approved', row.is_approved)
                    row.active = getattr(user, 'is_active', row.active)

            session.commit()
            User._write_json_backup(users)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    @staticmethod
    def create_user(ntid, email, name, password, team_name=None):
        """Create a new user with hashed password."""
        users = User.load_users()
        
        # Check if user already exists
        if ntid in users or any(u.email == email for u in users.values()):
            return None, "User with this NTID or email already exists"
        
        # Create new user with team_name
        password_hash = generate_password_hash(password)
        user = User(ntid, email, name, password_hash, team_name=team_name)
        users[user.user_id] = user
        User.save_users(users)
        
        return user, None
    
    @staticmethod
    def get_user_by_id(user_id):
        """Get user by user ID."""
        users = User.load_users()
        return users.get(user_id)
    
    @staticmethod
    def get_user_by_ntid(ntid):
        """Get user by NTID."""
        users = User.load_users()
        return users.get(ntid)
    
    @staticmethod
    def get_user_by_email(email):
        """Get user by email (checks both primary and alternate email)."""
        users = User.load_users()
        for user in users.values():
            if user.email == email or getattr(user, 'alternate_email', '') == email:
                return user
        return None
    
    @staticmethod
    def authenticate(identifier, password):
        """Authenticate user by NTID or email (primary/alternate) and password."""
        # Try to find user by NTID first
        user = User.get_user_by_ntid(identifier)
        
        # If not found, try by email (checks both primary and alternate)
        if not user:
            user = User.get_user_by_email(identifier)
        
        # Verify password
        if user and user.check_password(password):
            return user
        
        return None
