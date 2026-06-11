"""
Database Migration Utilities
Migrate from JSON-based persistence (v1.0) to PostgreSQL (v2.0)
"""

import json
import os
import hashlib
import shutil
from datetime import datetime, timezone
from typing import Dict, List, Any
import logging

from models.database import (
    Session, User, Device, LogPattern, SystemCommand, Method,
    SavedSequence, Job, TestResult, AuditLog, ExecutionContext
)

logger = logging.getLogger(__name__)

# JSON file paths (from config.config_paths)
JSON_FILES_DIR = 'Json'
DEVICES_FILE = f'{JSON_FILES_DIR}/devices.json'
JOBS_FILE = f'{JSON_FILES_DIR}/jobs.json'
TEST_RESULTS_FILE = f'{JSON_FILES_DIR}/test_results_history.json'
SAVED_SEQUENCES_FILE = f'{JSON_FILES_DIR}/saved_sequences.json'
LOG_PATTERNS_FILE = f'{JSON_FILES_DIR}/log_patterns.json'
SYSTEM_COMMANDS_FILE = f'{JSON_FILES_DIR}/system_commands.json'
USERS_FILE = f'{JSON_FILES_DIR}/users.json'


class JSONDataLoader:
    """Load data from existing JSON files"""
    
    @staticmethod
    def load_json(file_path: str) -> Dict | List:
        """Load JSON file safely"""
        try:
            if not os.path.exists(file_path):
                logger.warning(f"⚠️  File not found: {file_path}")
                return {} if file_path.endswith(DEVICES_FILE) else []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"✅ Loaded {file_path}")
                return data
        except Exception as e:
            logger.error(f"❌ Error loading {file_path}: {e}")
            return {} if file_path.endswith(DEVICES_FILE) else []
    
    @staticmethod
    def backup_json_files():
        """Create backup of all JSON files before migration"""
        backup_dir = f'{JSON_FILES_DIR}_backup_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}'
        try:
            os.makedirs(backup_dir, exist_ok=True)
            
            json_files = [
                DEVICES_FILE, JOBS_FILE, TEST_RESULTS_FILE,
                SAVED_SEQUENCES_FILE, LOG_PATTERNS_FILE,
                SYSTEM_COMMANDS_FILE, USERS_FILE
            ]
            
            for json_file in json_files:
                if os.path.exists(json_file):
                    shutil.copy2(json_file, os.path.join(backup_dir, os.path.basename(json_file)))
                    logger.info(f"✅ Backed up {json_file}")
            
            logger.info(f"✅ Backup directory created: {backup_dir}")
            return backup_dir
        except Exception as e:
            logger.error(f"❌ Error creating backup: {e}")
            return None


class DataMigration:
    """Handle data migration from JSON to PostgreSQL"""
    
    def __init__(self):
        self.session = Session()
        self.migration_report = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'totals': {},
            'errors': [],
            'warnings': []
        }
    
    def migrate_users(self) -> int:
        """Migrate users from JSON to PostgreSQL"""
        logger.info("🔄 Migrating users...")
        try:
            users_data = JSONDataLoader.load_json(USERS_FILE)
            count = 0
            
            for user_dict in (users_data.values() if isinstance(users_data, dict) else users_data):
                try:
                    # Check if user already exists
                    existing = self.session.query(User).filter_by(username=user_dict.get('username')).first()
                    if existing:
                        logger.debug(f"User {user_dict.get('username')} already exists, skipping")
                        continue
                    
                    user = User(
                        username=user_dict.get('username'),
                        password_hash=user_dict.get('password_hash', 'PLACEHOLDER'),
                        email=user_dict.get('email'),
                        team_name=user_dict.get('team_name', ''),
                        is_admin=user_dict.get('is_admin', False),
                        is_approved=user_dict.get('is_approved', True)
                    )
                    self.session.add(user)
                    count += 1
                except Exception as e:
                    self.migration_report['errors'].append(f"User migration error: {str(e)}")
                    logger.error(f"Error migrating user: {e}")
            
            self.session.commit()
            self.migration_report['totals']['users'] = count
            logger.info(f"✅ Migrated {count} users")
            return count
        except Exception as e:
            self.session.rollback()
            self.migration_report['errors'].append(f"Users migration failed: {str(e)}")
            logger.error(f"❌ Error migrating users: {e}")
            return 0
    
    def migrate_devices(self) -> int:
        """Migrate devices from JSON to PostgreSQL"""
        logger.info("🔄 Migrating devices...")
        try:
            devices_data = JSONDataLoader.load_json(DEVICES_FILE)
            count = 0
            
            for ip, device_dict in devices_data.items():
                try:
                    # Check if device already exists
                    existing = self.session.query(Device).filter_by(ip=ip).first()
                    if existing:
                        logger.debug(f"Device {ip} already exists, skipping")
                        continue
                    
                    device = Device(
                        ip=ip,
                        name=device_dict.get('name', 'Unknown'),
                        username=device_dict.get('username', 'root'),
                        password=device_dict.get('password'),
                        port=device_dict.get('port', 10022),
                        device_type=device_dict.get('device_type', ''),
                        mac_address=device_dict.get('mac_address', ''),
                        vnc_url=device_dict.get('vnc_url', ''),
                        location=device_dict.get('location', ''),
                        team_name=device_dict.get('team_name', 'DEFAULT'),
                        use_jump_host=device_dict.get('use_jump_host', False),
                        jump_host_config=device_dict.get('jump_host_config'),
                        ir_config=device_dict.get('ir_config'),
                        is_active=True
                    )
                    self.session.add(device)
                    count += 1
                except Exception as e:
                    self.migration_report['errors'].append(f"Device {ip} migration error: {str(e)}")
                    logger.error(f"Error migrating device {ip}: {e}")
            
            self.session.commit()
            self.migration_report['totals']['devices'] = count
            logger.info(f"✅ Migrated {count} devices")
            return count
        except Exception as e:
            self.session.rollback()
            self.migration_report['errors'].append(f"Devices migration failed: {str(e)}")
            logger.error(f"❌ Error migrating devices: {e}")
            return 0
    
    def migrate_log_patterns(self) -> int:
        """Migrate log patterns from JSON to PostgreSQL"""
        logger.info("🔄 Migrating log patterns...")
        try:
            patterns_data = JSONDataLoader.load_json(LOG_PATTERNS_FILE)
            count = 0
            
            for pattern_id, pattern_dict in patterns_data.items():
                try:
                    existing = self.session.query(LogPattern).filter_by(pattern_id=pattern_id).first()
                    if existing:
                        continue
                    
                    pattern = LogPattern(
                        pattern_id=pattern_id,
                        name=pattern_dict.get('name'),
                        regex=pattern_dict.get('regex'),
                        description=pattern_dict.get('description'),
                        team_name=pattern_dict.get('team_name', ''),
                        location=pattern_dict.get('location', ''),
                        is_custom=pattern_dict.get('is_custom', False),
                        is_active=True
                    )
                    self.session.add(pattern)
                    count += 1
                except Exception as e:
                    self.migration_report['errors'].append(f"LogPattern {pattern_id} error: {str(e)}")
                    logger.error(f"Error migrating log pattern {pattern_id}: {e}")
            
            self.session.commit()
            self.migration_report['totals']['log_patterns'] = count
            logger.info(f"✅ Migrated {count} log patterns")
            return count
        except Exception as e:
            self.session.rollback()
            self.migration_report['errors'].append(f"Log patterns migration failed: {str(e)}")
            logger.error(f"❌ Error migrating log patterns: {e}")
            return 0
    
    def migrate_system_commands(self) -> int:
        """Migrate system commands from JSON to PostgreSQL"""
        logger.info("🔄 Migrating system commands...")
        try:
            commands_data = JSONDataLoader.load_json(SYSTEM_COMMANDS_FILE)
            count = 0
            
            for cmd_id, cmd_dict in commands_data.items():
                try:
                    existing = self.session.query(SystemCommand).filter_by(cmd_id=cmd_id).first()
                    if existing:
                        continue
                    
                    command = SystemCommand(
                        cmd_id=cmd_id,
                        name=cmd_dict.get('name'),
                        command=cmd_dict.get('command'),
                        description=cmd_dict.get('description'),
                        category=cmd_dict.get('category', ''),
                        team_name=cmd_dict.get('team_name', ''),
                        location=cmd_dict.get('location', ''),
                        is_custom=cmd_dict.get('is_custom', False),
                        is_active=True
                    )
                    self.session.add(command)
                    count += 1
                except Exception as e:
                    self.migration_report['errors'].append(f"SystemCommand {cmd_id} error: {str(e)}")
                    logger.error(f"Error migrating system command {cmd_id}: {e}")
            
            self.session.commit()
            self.migration_report['totals']['system_commands'] = count
            logger.info(f"✅ Migrated {count} system commands")
            return count
        except Exception as e:
            self.session.rollback()
            self.migration_report['errors'].append(f"System commands migration failed: {str(e)}")
            logger.error(f"❌ Error migrating system commands: {e}")
            return 0
    
    def migrate_saved_sequences(self) -> int:
        """Migrate saved sequences from JSON to PostgreSQL"""
        logger.info("🔄 Migrating saved sequences...")
        try:
            sequences_data = JSONDataLoader.load_json(SAVED_SEQUENCES_FILE)
            count = 0
            
            for seq_id, seq_dict in sequences_data.items():
                try:
                    existing = self.session.query(SavedSequence).filter_by(seq_id=seq_id).first()
                    if existing:
                        continue
                    
                    sequence = SavedSequence(
                        seq_id=seq_id,
                        name=seq_dict.get('name', 'Unknown'),
                        description=seq_dict.get('description'),
                        methods=seq_dict.get('methods', []),
                        method_rationale=seq_dict.get('method_rationale'),
                        execution_count=seq_dict.get('execution_count', 0),
                        total_duration_seconds=seq_dict.get('total_duration_seconds'),
                        average_duration_seconds=seq_dict.get('average_duration_seconds'),
                        team_name=seq_dict.get('team_name', 'DEFAULT'),
                        location=seq_dict.get('location', ''),
                        is_active=True
                    )
                    self.session.add(sequence)
                    count += 1
                except Exception as e:
                    self.migration_report['errors'].append(f"SavedSequence {seq_id} error: {str(e)}")
                    logger.error(f"Error migrating saved sequence {seq_id}: {e}")
            
            self.session.commit()
            self.migration_report['totals']['saved_sequences'] = count
            logger.info(f"✅ Migrated {count} saved sequences")
            return count
        except Exception as e:
            self.session.rollback()
            self.migration_report['errors'].append(f"Saved sequences migration failed: {str(e)}")
            logger.error(f"❌ Error migrating saved sequences: {e}")
            return 0
    
    def migrate_test_results(self) -> int:
        """Migrate test results from JSON to PostgreSQL"""
        logger.info("🔄 Migrating test results...")
        try:
            results_data = JSONDataLoader.load_json(TEST_RESULTS_FILE)
            count = 0
            
            for result_dict in results_data:
                try:
                    result = TestResult(
                        job_id=result_dict.get('job_id'),
                        iteration=result_dict.get('iteration'),
                        phase=result_dict.get('phase'),
                        status=result_dict.get('status'),
                        details=result_dict.get('details'),
                        device_ip=result_dict.get('device_ip'),
                        device_name=result_dict.get('device_name'),
                        method=result_dict.get('method'),
                        username=result_dict.get('username'),
                        sequence_name=result_dict.get('sequence_name'),
                        screenshots=result_dict.get('screenshots'),
                        logs=result_dict.get('logs'),
                        performance_seconds=result_dict.get('performance_seconds'),
                        optional_checks=result_dict.get('optional_checks'),
                        build_info=result_dict.get('build_info'),
                        tiles_summary=result_dict.get('tiles_summary'),
                        rdk_milestones_log=result_dict.get('rdk_milestones_log'),
                        boot_type=result_dict.get('boot_type'),
                        timestamp=result_dict.get('timestamp')
                    )
                    self.session.add(result)
                    count += 1
                except Exception as e:
                    self.migration_report['errors'].append(f"TestResult error: {str(e)}")
                    logger.error(f"Error migrating test result: {e}")
            
            self.session.commit()
            self.migration_report['totals']['test_results'] = count
            logger.info(f"✅ Migrated {count} test results")
            return count
        except Exception as e:
            self.session.rollback()
            self.migration_report['errors'].append(f"Test results migration failed: {str(e)}")
            logger.error(f"❌ Error migrating test results: {e}")
            return 0
    
    def run_full_migration(self) -> Dict:
        """Run full migration from JSON to PostgreSQL"""
        logger.info("=" * 60)
        logger.info("🚀 STARTING v2.0 DATABASE MIGRATION")
        logger.info("=" * 60)
        
        # Backup JSON files
        backup_dir = JSONDataLoader.backup_json_files()
        if backup_dir:
            self.migration_report['backup_directory'] = backup_dir
        
        # Run migrations in order
        self.migrate_users()
        self.migrate_devices()
        self.migrate_log_patterns()
        self.migrate_system_commands()
        self.migrate_saved_sequences()
        self.migrate_test_results()
        
        # Close session
        self.session.close()
        
        # Summary
        logger.info("=" * 60)
        logger.info("📊 MIGRATION SUMMARY")
        logger.info("=" * 60)
        for entity_type, count in self.migration_report['totals'].items():
            logger.info(f"  {entity_type}: {count} records migrated")
        
        if self.migration_report['errors']:
            logger.warning(f"  ⚠️  {len(self.migration_report['errors'])} errors encountered")
        
        logger.info("=" * 60)
        
        return self.migration_report
    
    def export_report(self, file_path: str = 'migration_report.json'):
        """Export migration report to JSON file"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.migration_report, f, indent=2)
            logger.info(f"✅ Migration report exported to {file_path}")
        except Exception as e:
            logger.error(f"❌ Error exporting migration report: {e}")


def main():
    """Run migration from command line"""
    from models.database import init_db
    
    # Initialize database
    init_db()
    
    # Run migration
    migration = DataMigration()
    report = migration.run_full_migration()
    migration.export_report()
    
    # Print summary
    print("\n✅ Migration completed!")
    print(f"  Total users: {report['totals'].get('users', 0)}")
    print(f"  Total devices: {report['totals'].get('devices', 0)}")
    print(f"  Total log patterns: {report['totals'].get('log_patterns', 0)}")
    print(f"  Total system commands: {report['totals'].get('system_commands', 0)}")
    print(f"  Total saved sequences: {report['totals'].get('saved_sequences', 0)}")
    print(f"  Total test results: {report['totals'].get('test_results', 0)}")


if __name__ == '__main__':
    main()
