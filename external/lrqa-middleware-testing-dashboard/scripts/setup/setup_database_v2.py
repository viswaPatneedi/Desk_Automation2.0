#!/usr/bin/env python3
"""
Phase 1 Database Setup - PostgreSQL Configuration & Schema Creation
Handles authentication without requiring password input
"""

import subprocess
import logging
import sys
import os
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database configuration
DB_NAME = "lrqa_v2"
DB_USER = "postgres"
DB_HOST = "localhost"
DB_PORT = "5432"

# Paths
SCRIPT_DIR = Path(__file__).parent
SCHEMA_FILE = SCRIPT_DIR / "config" / "database_schema.sql"

def run_command(command, shell=False, use_sudo=False):
    """Run a shell command and return success/failure"""
    try:
        if use_sudo and os.geteuid() != 0:
            command = f"sudo {command}"
        
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def check_postgresql():
    """Check if PostgreSQL is installed"""
    logger.info("\n" + "="*60)
    logger.info("STEP 1: Checking PostgreSQL Installation")
    logger.info("="*60)
    
    success, stdout, stderr = run_command("psql --version")
    if success:
        logger.info(f"✅ PostgreSQL is installed: {stdout.strip()}")
        return True
    else:
        logger.error(f"❌ PostgreSQL not found: {stderr}")
        return False

def check_postgres_service():
    """Check if PostgreSQL service is running"""
    logger.info("\n" + "="*60)
    logger.info("STEP 2: Checking PostgreSQL Service")
    logger.info("="*60)
    
    success, stdout, stderr = run_command("pg_isready -h localhost -p 5432")
    if success:
        logger.info(f"✅ PostgreSQL server is running at {DB_HOST}:{DB_PORT}")
        return True
    else:
        logger.error(f"⚠️  PostgreSQL service not running: {stderr}")
        logger.info("Attempting to start PostgreSQL service...")
        
        start_success, start_out, start_err = run_command("systemctl start postgresql", use_sudo=True)
        if start_success:
            logger.info("✅ PostgreSQL service started")
            return True
        else:
            logger.error(f"❌ Failed to start PostgreSQL: {start_err}")
            return False

def setup_postgresql_auth():
    """Configure PostgreSQL for local connections without password"""
    logger.info("\n" + "="*60)
    logger.info("STEP 3: Setting up PostgreSQL Authentication")
    logger.info("="*60)
    
    # Create .pgpass file for automatic authentication
    pgpass_file = Path.home() / ".pgpass"
    pgpass_content = f"{DB_HOST}:{DB_PORT}:{DB_NAME}:*:*\n"
    
    try:
        pgpass_file.write_text(pgpass_content, encoding='utf-8')
        pgpass_file.chmod(0o600)
        logger.info("✅ Created .pgpass file for authentication")
        return True
    except Exception as e:
        logger.warning(f"⚠️  Could not create .pgpass file: {e}")
        return False

def create_database():
    """Create the database using sudo"""
    logger.info("\n" + "="*60)
    logger.info("STEP 4: Creating Database")
    logger.info("="*60)
    
    logger.info(f"Creating database '{DB_NAME}'...")
    
    command = f"sudo -u {DB_USER} createdb {DB_NAME} 2>/dev/null || echo 'Database may already exist'"
    success, stdout, stderr = run_command(command)
    
    if "already exists" in stdout or "already exists" in stderr:
        logger.info(f"✅ Database '{DB_NAME}' already exists")
        return True
    elif success or "already" in stderr.lower():
        logger.info(f"✅ Database '{DB_NAME}' created successfully")
        return True
    else:
        logger.error(f"❌ Failed to create database: {stderr}")
        return False

def import_schema():
    """Import the database schema"""
    logger.info("\n" + "="*60)
    logger.info("STEP 5: Importing Database Schema")
    logger.info("="*60)
    
    if not SCHEMA_FILE.exists():
        logger.error(f"❌ Schema file not found: {SCHEMA_FILE}")
        return False
    
    logger.info(f"Importing schema from {SCHEMA_FILE}...")
    
    command = f"sudo -u {DB_USER} psql {DB_NAME} < {SCHEMA_FILE}"
    success, stdout, stderr = run_command(command)
    
    if success:
        logger.info(f"✅ Schema imported successfully")
        # Count tables created
        if stdout:
            get_count_cmd = f"sudo -u {DB_USER} psql {DB_NAME} -c \"SELECT COUNT(*) FROM pg_tables WHERE schemaname='public';\""
            count_success, count_out, _ = run_command(get_count_cmd)
            if count_success:
                logger.info(f"   Tables created: {count_out.strip()}")
        return True
    else:
        logger.error(f"❌ Schema import failed: {stderr}")
        return False

def verify_database():
    """Verify database setup"""
    logger.info("\n" + "="*60)
    logger.info("STEP 6: Verifying Database Setup")
    logger.info("="*60)
    
    # Get table count
    command = f"sudo -u {DB_USER} psql {DB_NAME} -c \"SELECT COUNT(*) as table_count FROM pg_tables WHERE schemaname='public';\" --tuples-only"
    success, stdout, stderr = run_command(command)
    
    if success:
        table_count = stdout.strip().split('\n')[0].strip()
        logger.info(f"✅ Database verified successfully")
        logger.info(f"   Tables in database: {table_count}")
        
        # Get table list
        list_cmd = f"sudo -u {DB_USER} psql {DB_NAME} -c \"SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;\" --tuples-only"
        list_success, list_out, _ = run_command(list_cmd)
        if list_success:
            tables = [t.strip() for t in list_out.strip().split('\n') if t.strip()]
            logger.info(f"   Tables: {', '.join(tables[:5])}{'...' if len(tables) > 5 else ''}")
        
        return True
    else:
        logger.error(f"❌ Verification failed: {stderr}")
        return False

def main():
    """Main setup flow"""
    logger.info("\n")
    logger.info("╔" + "="*58 + "╗")
    logger.info("║" + " "*15 + "PHASE 1: PostgreSQL Database Setup" + " "*9 + "║")
    logger.info("╚" + "="*58 + "╝")
    
    steps = [
        ("PostgreSQL Installation Check", check_postgresql),
        ("PostgreSQL Service Check", check_postgres_service),
        ("Authentication Setup", setup_postgresql_auth),
        ("Database Creation", create_database),
        ("Schema Import", import_schema),
        ("Database Verification", verify_database),
    ]
    
    completed = 0
    for step_name, step_func in steps:
        try:
            if step_func():
                completed += 1
            else:
                logger.error(f"❌ {step_name} failed")
                break
        except Exception as e:
            logger.error(f"❌ {step_name} error: {e}")
            break
    
    logger.info("\n" + "="*60)
    logger.info(f"Phase 1 Setup Complete: {completed}/{len(steps)} steps successful")
    logger.info("="*60 + "\n")
    
    if completed == len(steps):
        logger.info("✅ Phase 1 PostgreSQL Database Setup: SUCCESS")
        logger.info(f"   Database: {DB_NAME}")
        logger.info(f"   Host: {DB_HOST}:{DB_PORT}")
        logger.info(f"   User: {DB_USER}")
        logger.info("\n⏭️  Next: Phase 2 Testing - Flask agent endpoints")
        return 0
    else:
        logger.error("❌ Phase 1 PostgreSQL Database Setup: INCOMPLETE")
        return 1

if __name__ == "__main__":
    sys.exit(main())
