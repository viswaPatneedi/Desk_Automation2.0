#!/usr/bin/env python3
"""
Temporary script to set a test password for vpatne290
Directly update JSON file since database is not accessible
"""
import json
import os
from models.user import hash_password

# Set test password for vpatne290
test_password = "TestPassword123!"

users_file = os.path.join(os.path.dirname(__file__), 'Json', 'users.json')

# Load users JSON
with open(users_file, 'r') as f:
    users = json.load(f)

if 'vpatne290' in users:
    # Update password hash
    users['vpatne290']['password_hash'] = hash_password(test_password)
    
    # Save back to JSON
    with open(users_file, 'w') as f:
        json.dump(users, f, indent=2)
    
    print(f"✅ Password set for vpatne290")
    print(f"   Username: vpatne290")
    print(f"   Password: {test_password}")
else:
    print("❌ User vpatne290 not found!")
    print(f"Available users: {list(users.keys())}")
