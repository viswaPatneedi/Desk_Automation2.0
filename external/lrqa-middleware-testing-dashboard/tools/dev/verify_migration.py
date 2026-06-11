#!/usr/bin/env python3
"""
Phase 1 Data Migration Test & Verification
Validates data is migrated from JSON to PostgreSQL without loss
"""

import os
import json
import sys
from pathlib import Path

def count_json_data():
    """Count records in JSON files"""
    counts = {}
    
    json_files = {
        'devices.json': 'devices',
        'users.json': 'users',
        'job_queue.json': 'jobs',
        'Json/test_results.json': 'test_results',
    }
    
    for json_file, entity_name in json_files.items():
        if os.path.exists(json_file):
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, dict) and entity_name in data:
                        count = len(data[entity_name])
                    elif isinstance(data, list):
                        count = len(data)
                    else:
                        count = len(data)
                    counts[entity_name] = count
                    print(f"✓ {entity_name}: {count} records in JSON")
            except Exception as e:
                print(f"⚠ {entity_name}: Could not read JSON - {e}")
                counts[entity_name] = 0
    
    return counts

def count_database_data():
    """Count records in PostgreSQL"""
    try:
        from models.database import Session
        from models.device import Device
        from models.user import User
        from models.job import Job
        from models.test_result import TestResult
        
        session = Session()
        counts = {
            'devices': session.query(Device).count(),
            'users': session.query(User).count(),
            'jobs': session.query(Job).count(),
            'test_results': session.query(TestResult).count(),
        }
        
        session.close()
        
        for entity, count in counts.items():
            print(f"✓ {entity}: {count} records in PostgreSQL")
        
        return counts
    except Exception as e:
        print(f"✗ Could not connect to database: {e}")
        return {}

def verify_migration():
    """Verify migration success"""
    print("\n" + "="*60)
    print("PHASE 1 DATA MIGRATION VERIFICATION")
    print("="*60)
    
    print("\nJSON Data Counts:")
    json_counts = count_json_data()
    
    print("\nDatabase Data Counts:")
    db_counts = count_database_data()
    
    if not db_counts:
        print("\n✗ Database connection failed - migration cannot be verified")
        return False
    
    print("\n" + "="*60)
    print("MIGRATION VERIFICATION RESULTS")
    print("="*60)
    
    all_match = True
    for entity in json_counts:
        json_count = json_counts.get(entity, 0)
        db_count = db_counts.get(entity, 0)
        
        if json_count == db_count:
            print(f"✓ {entity}: {json_count} → {db_count} (MATCH)")
        else:
            print(f"✗ {entity}: {json_count} → {db_count} (MISMATCH)")
            all_match = False
    
    print("\n" + "="*60)
    if all_match:
        print("✅ DATA MIGRATION: 100% SUCCESS")
        print("All data verified successfully!")
    else:
        print("⚠ DATA MIGRATION: PARTIAL - Review mismatches above")
    
    return all_match

if __name__ == '__main__':
    os.chdir('/home/lrqa/Desktop/viswa/Desk-automation2.0/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard')
    sys.path.insert(0, '.')
    
    success = verify_migration()
    sys.exit(0 if success else 1)
