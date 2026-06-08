"""User model for authentication and user management."""
import json
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from config_paths import USERS_FILE


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
    def load_users():
        """Load all users from JSON file."""
        if not os.path.exists(USERS_FILE):
            return {}
        
        try:
            with open(USERS_FILE, 'r') as f:
                users_data = json.load(f)
                return {uid: User.from_dict(data) for uid, data in users_data.items()}
        except (json.JSONDecodeError, IOError):
            return {}
    
    @staticmethod
    def save_users(users):
        """Save all users to JSON file."""
        users_data = {uid: user.to_dict() for uid, user in users.items()}
        with open(USERS_FILE, 'w') as f:
            json.dump(users_data, f, indent=2)
    
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
