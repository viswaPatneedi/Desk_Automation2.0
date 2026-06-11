"""
E2E Tests for Login and Authentication Functionality
Verifies user authentication, access control, and login flow
"""

import pytest
import json
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Add parent directory to path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.user import User


class TestUserModel:
    """Test User Model and Database Operations"""
    
    def test_load_users(self):
        """Test loading users from JSON file"""
        users = User.load_users()
        assert isinstance(users, dict), "Users should be a dictionary"
        assert len(users) > 0, "Should have registered users"
        print(f"✓ Loaded {len(users)} users from JSON")
    
    def test_registered_users_exist(self):
        """Test that vpatne290 and other users are registered"""
        users = User.load_users()
        registered_ntids = ['vpatne290', 'landel334', 'rnagal741', 'lsampa662', 'bsatya541']
        
        for ntid in registered_ntids:
            assert ntid in users, f"User {ntid} should be registered"
            user = users[ntid]
            assert hasattr(user, 'ntid'), "User should have ntid attribute"
            assert hasattr(user, 'email'), "User should have email attribute"
            assert hasattr(user, 'password_hash'), "User should have password_hash"
        print(f"✓ All {len(registered_ntids)} expected users are registered")
    
    def test_user_by_id_lookup(self):
        """Test getting user by ID"""
        user = User.get_user_by_id('vpatne290')
        assert user is not None, "vpatne290 should be found by ID"
        assert user.ntid == 'vpatne290'
        assert 'ViswaChaithanya' in user.name or 'Viswa' in user.name
        assert user.is_admin is True, "vpatne290 should be admin"
        print(f"✓ User lookup by ID works: {user.name}")
    
    def test_user_by_ntid_lookup(self):
        """Test getting user by NTID"""
        user = User.get_user_by_ntid('rnagal741')
        assert user is not None, "rnagal741 should be found by NTID"
        assert user.ntid == 'rnagal741'
        assert user.email == 'ramya_nagalashankar@comcast.com'
        print(f"✓ User lookup by NTID works: {user.name}")
    
    def test_user_by_email_lookup(self):
        """Test getting user by primary email"""
        user = User.get_user_by_email('viswachaithanya_patneedi@comcast.com')
        assert user is not None, "Should find user by primary email"
        assert user.ntid == 'vpatne290'
        print(f"✓ User lookup by primary email works")
    
    def test_user_by_alternate_email_lookup(self):
        """Test getting user by alternate email"""
        user = User.get_user_by_email('vpatne290@cable.comcast.com')
        assert user is not None, "Should find user by alternate email"
        assert user.ntid == 'vpatne290'
        print(f"✓ User lookup by alternate email works")
    
    def test_password_verification(self):
        """Test password hashing and verification"""
        # Create a test user with known password
        test_password = "TestPassword123!"
        test_user = User(
            ntid='test_user',
            email='test@comcast.com',
            name='Test User',
            password_hash=generate_password_hash(test_password)
        )
        
        # Test password verification
        assert test_user.check_password(test_password), "Correct password should verify"
        assert not test_user.check_password("WrongPassword"), "Wrong password should fail"
        print(f"✓ Password hashing and verification works")
    
    def test_user_attributes(self):
        """Test user object attributes"""
        user = User.get_user_by_ntid('landel334')
        assert hasattr(user, 'user_id'), "Should have user_id"
        assert hasattr(user, 'ntid'), "Should have ntid"
        assert hasattr(user, 'email'), "Should have email"
        assert hasattr(user, 'name'), "Should have name"
        assert hasattr(user, 'password_hash'), "Should have password_hash"
        assert hasattr(user, 'is_admin'), "Should have is_admin flag"
        assert hasattr(user, 'team_name'), "Should have team_name"
        assert hasattr(user, 'is_authenticated'), "Should have is_authenticated"
        assert user.is_authenticated is True
        print(f"✓ User attributes verified for {user.name}")
    
    def test_authenticate_by_ntid(self):
        """Test authentication by NTID"""
        # Get a registered user first
        user = User.get_user_by_ntid('vpatne290')
        assert user is not None, "Test user should exist"
        
        # Test with wrong password (authentication should fail)
        result = User.authenticate('vpatne290', 'wrongpassword')
        assert result is None, "Authentication with wrong password should fail"
        print(f"✓ Authentication correctly rejects wrong password")
    
    def test_authenticate_by_email(self):
        """Test authentication by primary email"""
        result = User.authenticate('viswachaithanya_patneedi@comcast.com', 'wrongpassword')
        assert result is None, "Authentication with wrong email/password should fail"
        print(f"✓ Authentication by email rejects wrong password")
    
    def test_user_to_dict(self):
        """Test converting user to dictionary"""
        user = User.get_user_by_ntid('rnagal741')
        user_dict = user.to_dict()
        
        assert isinstance(user_dict, dict)
        assert user_dict['ntid'] == 'rnagal741'
        assert user_dict['email'] == 'ramya_nagalashankar@comcast.com'
        assert 'password_hash' in user_dict
        print(f"✓ User to_dict() works correctly")
    
    def test_user_from_dict(self):
        """Test creating user from dictionary"""
        user_data = {
            'user_id': 'test_id',
            'ntid': 'test_ntid',
            'email': 'test@comcast.com',
            'name': 'Test User',
            'password_hash': generate_password_hash('testpass'),
            'created_at': datetime.utcnow().isoformat(),
            'is_admin': False,
            'team_name': 'LRQA'
        }
        
        user = User.from_dict(user_data)
        assert user.ntid == 'test_ntid'
        assert user.email == 'test@comcast.com'
        assert user.name == 'Test User'
        print(f"✓ User from_dict() works correctly")


class TestAuthenticationFlow:
    """Test Complete Authentication Flow"""
    
    def test_login_flow_user_found(self):
        """Test that login flow can find registered users"""
        # This is part of the E2E flow - user should be found
        user = User.get_user_by_ntid('vpatne290')
        assert user is not None, "User should be found in login flow"
        assert user.user_id == 'vpatne290'
        print(f"✓ Login flow: User lookup successful")
    
    def test_login_flow_email_verification(self):
        """Test email matching in login flow"""
        user = User.get_user_by_ntid('vpatne290')
        
        # Verify primary email
        assert user.email == 'viswachaithanya_patneedi@comcast.com'
        
        # Verify alternate email exists
        assert hasattr(user, 'alternate_email')
        assert user.alternate_email == 'vpatne290@cable.comcast.com'
        print(f"✓ Login flow: Email verification successful")
    
    def test_login_flow_admin_check(self):
        """Test that admin status is correctly loaded"""
        admin_user = User.get_user_by_ntid('vpatne290')
        regular_user = User.get_user_by_ntid('rnagal741')
        
        assert admin_user.is_admin is True, "vpatne290 should be admin"
        assert regular_user.is_admin is False, "rnagal741 should not be admin"
        print(f"✓ Login flow: Admin status correctly loaded")


class TestDatabasePath:
    """Test Database File Paths Configuration"""
    
    def test_users_file_path_exists(self):
        """Test that users file path is correct"""
        from config.config_paths import USERS_FILE, BASE_DIR, DATA_DIR
        
        assert os.path.exists(USERS_FILE), f"USERS_FILE should exist at {USERS_FILE}"
        assert os.path.isfile(USERS_FILE), f"USERS_FILE should be a file"
        print(f"✓ Users file path correct: {USERS_FILE}")
    
    def test_base_dir_points_to_project_root(self):
        """Test that BASE_DIR points to project root, not config/"""
        from config.config_paths import BASE_DIR
        
        # BASE_DIR should end with project folder name, not 'config'
        assert not BASE_DIR.endswith('config'), "BASE_DIR should be project root, not config/"
        
        # Check for project root markers
        assert os.path.isdir(os.path.join(BASE_DIR, 'Json')), "Should have Json directory"
        assert os.path.isdir(os.path.join(BASE_DIR, 'config')), "Should have config directory"
        print(f"✓ BASE_DIR correctly points to project root")
    
    def test_data_dir_correct(self):
        """Test that DATA_DIR is correct"""
        from config.config_paths import DATA_DIR, BASE_DIR
        
        expected_data_dir = os.path.join(BASE_DIR, 'Json')
        assert DATA_DIR == expected_data_dir, f"DATA_DIR should be {expected_data_dir}"
        assert os.path.isdir(DATA_DIR), "DATA_DIR should exist"
        print(f"✓ DATA_DIR correctly set to: {DATA_DIR}")
    
    def test_json_files_accessible(self):
        """Test that JSON files are accessible"""
        from config.config_paths import USERS_FILE, DEVICES_FILE, JOBS_FILE
        
        files_to_check = [
            ('USERS_FILE', USERS_FILE),
            ('DEVICES_FILE', DEVICES_FILE),
        ]
        
        for file_name, file_path in files_to_check:
            if os.path.exists(file_path):
                print(f"  ✓ {file_name} exists at {file_path}")
            else:
                print(f"  ⚠ {file_name} not found at {file_path}")


def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "e2e: mark test as E2E test"
    )


if __name__ == '__main__':
    print("=" * 70)
    print("E2E LOGIN FUNCTIONALITY TESTS")
    print("=" * 70)
    print()
    
    # Run with pytest
    pytest.main([__file__, '-v', '--tb=short'])
