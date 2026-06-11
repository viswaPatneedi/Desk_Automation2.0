"""
pytest configuration file for the project
This file allows pytest to discover and properly configure tests
"""
import os
import sys
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

# Set up test environment variables (if not already set)
if not os.environ.get('SMTP_SERVER'):
    os.environ['SMTP_SERVER'] = 'smtp.gmail.com'
if not os.environ.get('SMTP_PORT'):
    os.environ['SMTP_PORT'] = '587'
if not os.environ.get('SENDER_EMAIL'):
    os.environ['SENDER_EMAIL'] = 'test@example.com'
if not os.environ.get('SENDER_PASSWORD'):
    os.environ['SENDER_PASSWORD'] = 'test-password'

@pytest.fixture(scope="session")
def test_setup():
    """Set up test environment"""
    print("\n📋 Test Environment Setup Complete")
    yield
    print("\n✅ Tests Complete")
