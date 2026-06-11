#!/usr/bin/env python3
"""
Phase 1 Database Setup & Validation - Python Implementation
Eliminates need for psql shell access
"""

import sys
import os
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_environment():
    """Setup .env file for database testing"""
    env_file = '.env'
    env_content = """# Database Configuration for Phase 1 Testing
DB_HOST=localhost
DB_PORT=5432
DB_NAME=lrqa_v2_test
DB_USER=postgres
DB_PASSWORD=postgres
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
DB_POOL_PRE_PING=true
DB_ECHO=false

# Feature Flags
ENABLE_DATABASE_MIGRATION=true
ENABLE_JSON_FALLBACK=true

# API Keys (for other services)
ANTHROPIC_API_KEY=
SECRET_KEY=dev-secret-key-change-in-production
"""
    
    if not os.path.exists(env_file):
        with open(env_file, 'w') as f:
            f.write(env_content)
        logger.info("✓ Created .env file")
    else:
        logger.info("✓ .env file already exists")

def test_sqlalchemy_models():
    """Test that SQLAlchemy models load correctly"""
    logger.info("\n" + "="*60)
    logger.info("PHASE 1B: Testing SQLAlchemy ORM Models")
    logger.info("="*60)
    
    try:
        from models.device import Device
        from models.user import User
        from models.job import Job
        from models.test_result import TestResult
        from models.device_lock import DeviceLock
        from models.saved_sequence import SavedSequence
        from models.database import Database, Base
        
        logger.info("✓ All ORM models imported successfully")
        logger.info("  - Device")
        logger.info("  - User")
        logger.info("  - Job")
        logger.info("  - TestResult")
        logger.info("  - DeviceLock")
        logger.info("  - SavedSequence")
        
        return True
    except ImportError as e:
        logger.error(f"✗ Failed to import ORM models: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ Unexpected error: {e}")
        return False

def test_database_connection():
    """Test database connection via SQLAlchemy"""
    logger.info("\n" + "="*60)
    logger.info("PHASE 1C: Testing Database Connection")
    logger.info("="*60)
    
    try:
        from models.database import Database
        
        db = Database()
        logger.info(f"✓ Database URI: postgresql+psycopg2://postgres:***@localhost:5432/lrqa_v2_test")
        
        # Test connection
        session = db.get_session()
        result = session.execute("SELECT 1")
        session.close()
        
        logger.info("✓ Successfully connected to PostgreSQL via SQLAlchemy")
        return True
        
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        logger.info("\n💡 Troubleshooting tips:")
        logger.info("  1. Is PostgreSQL running? (systemctl status postgresql)")
        logger.info("  2. Is D_PASSWORD set correctly in .env?")
        logger.info("  3. Try: sudo -u postgres psql -c 'SELECT 1;'")
        return False

def test_config_loading():
    """Test Flask database config loading"""
    logger.info("\n" + "="*60)
    logger.info("PHASE 1D: Testing Flask Database Config")
    logger.info("="*60)
    
    try:
        from config.flask_database import DatabaseConfig
        
        config = DatabaseConfig()
        logger.info("✓ DatabaseConfig loaded successfully")
        logger.info(f"  Host: {config.host}")
        logger.info(f"  Port: {config.port}")
        logger.info(f"  Database: {config.database}")
        logger.info(f"  User: {config.user}")
        logger.info(f"  Pool size: {config.pool_size}")
        logger.info(f"  Echo: {config.echo}")
        
        return True
    except Exception as e:
        logger.error(f"✗ Config loading failed: {e}")
        return False

def test_migration_utilities():
    """Test migration utilities are available"""
    logger.info("\n" + "="*60)
    logger.info("PHASE 1E: Testing Migration Utilities")
    logger.info("="*60)
    
    try:
        from utilities.database_migration import JSONDataLoader, DataMigration
        
        logger.info("✓ JSONDataLoader imported")
        logger.info("✓ DataMigration imported")
        
        # Test JSON file detection
        loader = JSONDataLoader()
        json_files = loader.get_available_json_files()
        
        logger.info(f"✓ Found {len(json_files)} JSON files to migrate:")
        for json_file in json_files[:5]:
            logger.info(f"  - {json_file}")
        if len(json_files) > 5:
            logger.info(f"  ... and {len(json_files) - 5} more")
        
        return True
    except Exception as e:
        logger.error(f"✗ Migration utilities test failed: {e}")
        return False

def test_app_loading():
    """Test that Flask app loads with database config"""
    logger.info("\n" + "="*60)
    logger.info("PHASE 1F: Testing Flask App Loading")
    logger.info("="*60)
    
    try:
        # Suppress Flask debug logging
        logging.getLogger('flask').setLevel(logging.ERROR)
        
        from app import app
        
        logger.info("✓ Flask app imported successfully")
        logger.info(f"  Secret key configured: {'Yes' if app.secret_key else 'No'}")
        logger.info(f"  Debug mode: {app.debug}")
        logger.info(f"  Testing mode: {app.testing}")
        
        return True
    except Exception as e:
        logger.error(f"✗ Flask app loading failed: {e}")
        return False

def test_schema_file():
    """Test that schema file exists and is readable"""
    logger.info("\n" + "="*60)
    logger.info("PHASE 1G: Testing Database Schema File")
    logger.info("="*60)
    
    schema_file = "config/database_schema.sql"
    
    if not os.path.exists(schema_file):
        logger.error(f"✗ Schema file not found: {schema_file}")
        return False
    
    try:
        with open(schema_file, 'r') as f:
            content = f.read()
            table_count = content.count('CREATE TABLE')
            
        logger.info(f"✓ Schema file found: {schema_file}")
        logger.info(f"  File size: {len(content):,} bytes")
        logger.info(f"  Tables defined: {table_count}")
        
        return table_count >= 20  # Should have ~22 tables
    except Exception as e:
        logger.error(f"✗ Failed to read schema file: {e}")
        return False

def main():
    """Run all validation tests"""
    logger.info("\n" + "="*60)
    logger.info("PHASE 1 VALIDATION TESTING")
    logger.info("Desk-Automation v2.0 Database Migration")
    logger.info("="*60)
    
    # Change to project directory
    os.chdir('/home/lrqa/Desktop/viswa/Desk-automation2.0/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard')
    sys.path.insert(0, '.')
    
    # Run tests
    tests = [
        ("Environment Setup", setup_environment),
        ("ORM Models", test_sqlalchemy_models),
        ("Flask DB Config", test_config_loading),
        ("Migration Utils", test_migration_utilities),
        ("Schema File", test_schema_file),
        ("Flask App", test_app_loading),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"✗ Test '{test_name}' crashed: {e}")
            results[test_name] = False
    
    # Database connection test
    logger.info("\n" + "="*60)
    logger.info("⏳ Attempting database connection...")
    logger.info("(May prompt for password)")
    logger.info("="*60)
    
    results["DB Connection"] = test_database_connection()
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("TEST SUMMARY")
    logger.info("="*60)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    logger.info("\n" + "="*60)
    logger.info(f"Result: {passed}/{total} tests passed ({100*passed//total}%)")
    logger.info("="*60)
    
    if passed == total:
        logger.info("\n✅ Phase 1 Validation PASSED - Ready for database setup!")
        return 0
    else:
        logger.info("\n⚠️  Phase 1 Validation PARTIAL - Some tests failed")
        logger.info("Check troubleshooting section in PHASE_1_TESTING_GUIDE.md")
        return 1

if __name__ == '__main__':
    sys.exit(main())
