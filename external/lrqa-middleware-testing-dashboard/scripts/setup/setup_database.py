#!/usr/bin/env python3
"""
Database Setup & Migration Runner
Handles PostgreSQL initialization, schema creation, and data migration from JSON
"""

import os
import sys
import logging
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================
# DATABASE SETUP
# ============================================================

class DatabaseSetup:
    """Handle PostgreSQL database setup"""
    
    def __init__(self, config_dict: Dict[str, Any] = None):
        """
        Initialize database setup
        
        Args:
            config_dict: Dict with host, port, user, password, database keys
        """
        self.host = (config_dict or {}).get('host', os.environ.get('DB_HOST', 'localhost'))
        self.port = (config_dict or {}).get('port', int(os.environ.get('DB_PORT', 5432)))
        self.user = (config_dict or {}).get('user', os.environ.get('DB_USER', 'lrqa'))
        self.password = (config_dict or {}).get('password', os.environ.get('DB_PASSWORD', 'lrqa_password'))
        self.database = (config_dict or {}).get('database', os.environ.get('DB_NAME', 'lrqa_v2'))
        self.admin_user = 'postgres'
    
    def check_postgresql_installed(self) -> bool:
        """Check if PostgreSQL is installed"""
        try:
            result = subprocess.run(
                ['psql', '--version'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                logger.info(f"✅ PostgreSQL is installed: {result.stdout.strip()}")
                return True
            else:
                logger.error("❌ PostgreSQL not found")
                return False
        except FileNotFoundError:
            logger.error("❌ PostgreSQL not found - Please install PostgreSQL")
            return False
    
    def check_postgresql_running(self) -> bool:
        """Check if PostgreSQL server is running"""
        try:
            result = subprocess.run(
                ['pg_isready', '-h', self.host, '-p', str(self.port)],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"✅ PostgreSQL server is running at {self.host}:{self.port}")
                return True
            else:
                logger.warning(f"⚠️  PostgreSQL server not responding at {self.host}:{self.port}")
                return False
        except Exception as e:
            logger.error(f"❌ Error checking PostgreSQL: {e}")
            return False
    
    def create_database(self) -> bool:
        """Create the application database"""
        try:
            logger.info(f"Creating database '{self.database}'...")
            
            # Build psql command to create database as admin user
            cmd = f"psql -h {self.host} -p {self.port} -U {self.admin_user} -tc \"SELECT 1 FROM pg_database WHERE datname = '{self.database}'\" | grep -q 1"
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"✅ Database '{self.database}' already exists")
                return True
            
            # Create database
            create_cmd = f"psql -h {self.host} -p {self.port} -U {self.admin_user} -c \"CREATE DATABASE {self.database};\""
            result = subprocess.run(create_cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"✅ Database '{self.database}' created successfully")
                return True
            else:
                logger.error(f"❌ Database creation failed: {result.stderr}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Error creating database: {e}")
            return False
    
    def create_tables_from_schema(self, schema_file: str = 'config/database_schema.sql') -> bool:
        """Create database tables from SQL schema"""
        try:
            schema_path = Path(schema_file)
            if not schema_path.exists():
                logger.error(f"❌ Schema file not found: {schema_file}")
                return False
            
            logger.info(f"Creating tables from {schema_file}...")
            
            # Read schema file
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
            
            # Create connection
            import psycopg2
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            
            cursor = conn.cursor()
            
            # Execute schema creation
            cursor.execute(schema_sql)
            conn.commit()
            
            cursor.close()
            conn.close()
            
            logger.info("✅ Database tables created successfully")
            return True
        
        except Exception as e:
            logger.error(f"❌ Error creating tables: {e}")
            return False
    
    def verify_tables(self) -> Dict[str, int]:
        """Verify that all tables were created"""
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema='public'
            """)
            
            table_count = cursor.fetchone()[0]
            
            # Get detailed table info
            cursor.execute("""
                SELECT table_name, 
                       (SELECT COUNT(*) FROM information_schema.columns 
                        WHERE table_name=t.table_name) as column_count
                FROM information_schema.tables t
                WHERE table_schema='public'
                ORDER BY table_name
            """)
            
            tables = {}
            for row in cursor.fetchall():
                tables[row[0]] = row[1]
            
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Database verification: {table_count} tables found")
            for table_name, col_count in sorted(tables.items()):
                logger.info(f"   - {table_name} ({col_count} columns)")
            
            return tables
        
        except Exception as e:
            logger.error(f"❌ Error verifying tables: {e}")
            return {}


# ============================================================
# MIGRATION RUNNER
# ============================================================

class MigrationRunner:
    """Run JSON to PostgreSQL migration"""
    
    def __init__(self, config_dict: Dict[str, Any] = None):
        """Initialize migration runner"""
        self.config = config_dict or {}
    
    def run_migration(self) -> bool:
        """Execute full migration from JSON to PostgreSQL"""
        try:
            logger.info("🔄 Starting JSON to PostgreSQL migration...")
            
            from utilities.database_migration import DataMigration
            
            migrator = DataMigration()
            report = migrator.run_full_migration()
            
            # Export report
            report_file = migrator.export_report('migration_report.json')
            
            logger.info(f"✅ Migration completed successfully")
            logger.info(f"   Report saved to: {report_file}")
            
            # Print summary
            self._print_migration_summary(report)
            
            return True
        
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            return False
    
    def _print_migration_summary(self, report: Dict[str, Any]):
        """Print migration report summary"""
        if 'entities' in report:
            logger.info("\n📊 Migration Summary:")
            for entity, stats in report['entities'].items():
                logger.info(f"   {entity}:")
                logger.info(f"      - Loaded: {stats.get('loaded', 0)}")
                logger.info(f"      - Inserted: {stats.get('inserted', 0)}")
                logger.info(f"      - Errors: {stats.get('errors', 0)}")


# ============================================================
# COMPLETE SETUP & MIGRATION
# ============================================================

def setup_database_complete(config_dict: Dict[str, Any] = None) -> Tuple[bool, Dict[str, str]]:
    """
    Complete database setup and migration
    
    Args:
        config_dict: Optional database configuration
    
    Returns:
        Tuple of (success: bool, status_dict: Dict)
    """
    status = {}
    
    # 1. PostgreSQL Check
    logger.info("\n" + "="*60)
    logger.info("STEP 1: Checking PostgreSQL Installation")
    logger.info("="*60)
    
    setup = DatabaseSetup(config_dict)
    if not setup.check_postgresql_installed():
        status['postgresql_install'] = 'FAILED'
        return False, status
    status['postgresql_install'] = 'OK'
    
    # 2. PostgreSQL Running Check
    logger.info("\n" + "="*60)
    logger.info("STEP 2: Checking PostgreSQL Service")
    logger.info("="*60)
    
    if not setup.check_postgresql_running():
        logger.warning("⚠️  PostgreSQL service may not be running")
        logger.info("   On Linux: sudo systemctl start postgresql")
        logger.info("   On macOS: brew services start postgresql")
        status['postgresql_running'] = 'WARNING'
    else:
        status['postgresql_running'] = 'OK'
    
    # 3. Create Database
    logger.info("\n" + "="*60)
    logger.info("STEP 3: Creating Database")
    logger.info("="*60)
    
    if not setup.create_database():
        status['database_create'] = 'FAILED'
        return False, status
    status['database_create'] = 'OK'
    
    # 4. Create Tables
    logger.info("\n" + "="*60)
    logger.info("STEP 4: Creating Database Schema")
    logger.info("="*60)
    
    if not setup.create_tables_from_schema():
        status['tables_create'] = 'FAILED'
        return False, status
    status['tables_create'] = 'OK'
    
    # 5. Verify Tables
    logger.info("\n" + "="*60)
    logger.info("STEP 5: Verifying Database Schema")
    logger.info("="*60)
    
    tables = setup.verify_tables()
    if not tables:
        status['tables_verify'] = 'FAILED'
        return False, status
    status['tables_verify'] = f'OK ({len(tables)} tables)'
    
    # 6. Run Migration
    logger.info("\n" + "="*60)
    logger.info("STEP 6: Migrating Data from JSON")
    logger.info("="*60)
    
    migrator = MigrationRunner(config_dict)
    if not migrator.run_migration():
        status['data_migration'] = 'FAILED'
        logger.warning("⚠️  Data migration failed - continuing with empty database")
        status['data_migration'] = 'WARNING'
    else:
        status['data_migration'] = 'OK'
    
    # 7. Print Summary
    logger.info("\n" + "="*60)
    logger.info("SETUP COMPLETE")
    logger.info("="*60)
    logger.info("\n✅ Database setup and migration completed successfully!\n")
    
    for step, result in status.items():
        emoji = "✅" if result == "OK" else ("⚠️ " if result.startswith("WARNING") else "❌")
        logger.info(f"{emoji} {step}: {result}")
    
    return True, status


# ============================================================
# CLI INTERFACE
# ============================================================

def main():
    """CLI interface for database setup and migration"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Database Setup & Migration Tool'
    )
    parser.add_argument(
        '--complete',
        action='store_true',
        help='Run complete setup: PostgreSQL check → create DB → create schema → migrate data'
    )
    parser.add_argument(
        '--check-postgres',
        action='store_true',
        help='Check if PostgreSQL is installed and running'
    )
    parser.add_argument(
        '--create-db',
        action='store_true',
        help='Create the application database'
    )
    parser.add_argument(
        '--create-schema',
        action='store_true',
        help='Create database schema from SQL file'
    )
    parser.add_argument(
        '--migrate-data',
        action='store_true',
        help='Migrate data from JSON to PostgreSQL'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify database tables and data'
    )
    parser.add_argument(
        '--host',
        default='localhost',
        help='Database host (default: localhost)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=5432,
        help='Database port (default: 5432)'
    )
    parser.add_argument(
        '--user',
        default='lrqa',
        help='Database user (default: lrqa)'
    )
    parser.add_argument(
        '--password',
        default='lrqa_password',
        help='Database password (default: lrqa_password)'
    )
    parser.add_argument(
        '--database',
        default='lrqa_v2',
        help='Database name (default: lrqa_v2)'
    )
    
    args = parser.parse_args()
    
    # Build config from arguments
    config = {
        'host': args.host,
        'port': args.port,
        'user': args.user,
        'password': args.password,
        'database': args.database
    }
    
    setup = DatabaseSetup(config)
    
    if args.complete:
        success, status = setup_database_complete(config)
        sys.exit(0 if success else 1)
    
    elif args.check_postgres:
        setup.check_postgresql_installed()
        setup.check_postgresql_running()
    
    elif args.create_db:
        setup.create_database()
    
    elif args.create_schema:
        setup.create_tables_from_schema()
    
    elif args.migrate_data:
        migrator = MigrationRunner(config)
        migrator.run_migration()
    
    elif args.verify:
        setup.verify_tables()
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
