"""
Flask Database Integration Module
Initializes and manages PostgreSQL connection for Flask application
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# ============================================================
# DATABASE CONFIGURATION
# ============================================================

class DatabaseConfig:
    """PostgreSQL connection configuration"""
    
    def __init__(self):
        # Load from environment or use defaults
        self.host = os.environ.get('DB_HOST', 'localhost')
        self.port = int(os.environ.get('DB_PORT', 5432))
        self.database = os.environ.get('DB_NAME', 'lrqa_v2')
        self.user = os.environ.get('DB_USER', 'lrqa')
        self.password = os.environ.get('DB_PASSWORD', 'lrqa_password')
        
        # Connection pool settings
        self.pool_size = int(os.environ.get('DB_POOL_SIZE', 20))
        self.max_overflow = int(os.environ.get('DB_MAX_OVERFLOW', 40))
        self.pool_pre_ping = os.environ.get('DB_POOL_PRE_PING', 'true').lower() == 'true'
        self.echo = os.environ.get('DB_ECHO', 'false').lower() == 'true'
        
        self.sqlalchemy_database_uri = self._build_connection_string()
    
    def _build_connection_string(self) -> str:
        """Build SQLAlchemy connection string"""
        return (
            f"postgresql+psycopg2://{self.user}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Return config as dictionary (without password)"""
        return {
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'user': self.user,
            'pool_size': self.pool_size,
            'max_overflow': self.max_overflow,
            'pool_pre_ping': self.pool_pre_ping
        }


# ============================================================
# FLASK APP DATABASE INTEGRATION
# ============================================================

def init_database_for_flask(app, db_config: Optional[DatabaseConfig] = None):
    """
    Initialize PostgreSQL for Flask application
    
    Args:
        app: Flask application instance
        db_config: DatabaseConfig instance (creates default if None)
    
    Returns:
        DatabaseConfig used for initialization
    """
    
    if db_config is None:
        db_config = DatabaseConfig()
    
    # Configure Flask for SQLAlchemy
    app.config['SQLALCHEMY_DATABASE_URI'] = db_config.sqlalchemy_database_uri
    app.config['SQLALCHEMY_ECHO'] = db_config.echo
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': db_config.pool_size,
        'max_overflow': db_config.max_overflow,
        'pool_pre_ping': db_config.pool_pre_ping,
        'pool_recycle': 3600,  # Recycle connections after 1 hour
        'connect_args': {
            'connect_timeout': 10,
            'options': '-c default_transaction_isolation=read_committed'
        }
    }
    
    logger.info("✅ Flask database configuration initialized")
    logger.info(f"   Database: {db_config.database}")
    logger.info(f"   Host: {db_config.host}:{db_config.port}")
    logger.info(f"   Pool Size: {db_config.pool_size}")
    
    return db_config


def initialize_database_on_startup(app):
    """
    Run database initialization on Flask startup
    
    This should be called in app.before_first_request or in __init__
    """
    try:
        from models.database import init_db, health_check
        
        logger.info("🔄 Initializing database on startup...")
        
        # Initialize database tables
        init_db()
        logger.info("✅ Database tables initialized")
        
        # Run health check
        if health_check():
            logger.info("✅ Database health check passed")
        else:
            logger.warning("⚠️  Database health check failed")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Error initializing database: {e}")
        return False


def register_database_routes(app):
    """
    Register Flask routes for database health and status
    
    Args:
        app: Flask application instance
    """
    from flask import jsonify
    from models.database import health_check, get_session, close_session
    
    @app.route('/api/health/database', methods=['GET'])
    def database_health():
        """Check database health"""
        try:
            session = get_session()
            result = session.execute('SELECT 1')
            close_session()
            
            return jsonify({
                'status': 'healthy',
                'database': 'PostgreSQL',
                'connected': True,
                'timestamp': str(datetime.now(timezone.utc))
            }), 200
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'database': 'PostgreSQL',
                'connected': False,
                'error': str(e),
                'timestamp': str(datetime.now(timezone.utc))
            }), 503
    
    @app.route('/api/health/database/config', methods=['GET'])
    def database_config():
        """Get database configuration (non-sensitive)"""
        from functools import lru_cache
        
        @lru_cache(maxsize=1)
        def get_config():
            db_config = DatabaseConfig()
            return db_config.to_dict()
        
        return jsonify(get_config()), 200
    
    @app.route('/api/health/database/status', methods=['GET'])
    def database_status():
        """Get detailed database status"""
        try:
            from models.database import get_session, close_session
            
            session = get_session()
            
            # Get connection pool status
            engine = session.get_bind()
            pool = engine.pool
            
            status = {
                'status': 'connected',
                'pool_size': pool.size(),
                'checked_in': pool.checkedout(),
                'overflow': pool.overflow(),
                'connection_count': pool.size() + pool.overflow(),
                'timestamp': str(datetime.now(timezone.utc))
            }
            
            close_session()
            return jsonify(status), 200
        
        except Exception as e:
            return jsonify({
                'status': 'error',
                'error': str(e),
                'timestamp': str(datetime.now(timezone.utc))
            }), 503
    
    logger.info("✅ Database health and status routes registered")


# ============================================================
# DATABASE MIGRATION SUPPORT
# ============================================================

def create_migration_endpoints(app, migration_utils_path: str = 'utilities/database_migration.py'):
    """
    Create Flask endpoints for data migration
    
    Args:
        app: Flask application instance
        migration_utils_path: Path to migration utilities module
    """
    from flask import jsonify, request
    from flask_login import login_required, current_user
    
    @app.route('/api/migration/status', methods=['GET'])
    @login_required
    def migration_status():
        """Get migration status"""
        try:
            # Check if migration has been run
            from models.database import db
            from pathlib import Path
            
            migration_log = Path('migration_report.json')
            
            status = {
                'migration_complete': migration_log.exists(),
                'last_migration': str(migration_log.stat().st_mtime) if migration_log.exists() else None,
                'timestamp': str(datetime.now(timezone.utc))
            }
            
            return jsonify(status), 200
        
        except Exception as e:
            return jsonify({
                'error': str(e),
                'timestamp': str(datetime.now(timezone.utc))
            }), 500
    
    @app.route('/api/migration/json-to-postgresql', methods=['POST'])
    @login_required
    def run_migration():
        """
        Run JSON to PostgreSQL migration
        Only accessible to admin users
        """
        try:
            # Check admin permission
            if not getattr(current_user, 'is_admin', False):
                return jsonify({'error': 'Admin access required'}), 403
            
            from utilities.database_migration import DataMigration
            
            migrator = DataMigration()
            report = migrator.run_full_migration()
            
            # Export report
            migrator.export_report('migration_report.json')
            
            return jsonify({
                'success': True,
                'report': report,
                'timestamp': str(datetime.now(timezone.utc))
            }), 200
        
        except Exception as e:
            logger.error(f"Migration error: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'timestamp': str(datetime.now(timezone.utc))
            }), 500
    
    logger.info("✅ Migration endpoints registered")


# ============================================================
# UTILITIES
# ============================================================

from datetime import datetime, timezone

def verify_database_connection(db_config: Optional[DatabaseConfig] = None) -> bool:
    """
    Verify that database connection works
    
    Args:
        db_config: DatabaseConfig instance (creates default if None)
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        if db_config is None:
            db_config = DatabaseConfig()
        
        import psycopg2
        conn = psycopg2.connect(
            host=db_config.host,
            port=db_config.port,
            database=db_config.database,
            user=db_config.user,
            password=db_config.password,
            connect_timeout=5
        )
        conn.close()
        logger.info("✅ Database connection verified")
        return True
    
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


def get_db_config() -> DatabaseConfig:
    """Get current database configuration"""
    return DatabaseConfig()


if __name__ == '__main__':
    # Test database configuration
    logging.basicConfig(level=logging.INFO)
    config = DatabaseConfig()
    print("Database Configuration:")
    print(f"  Host: {config.host}")
    print(f"  Port: {config.port}")
    print(f"  Database: {config.database}")
    print(f"  User: {config.user}")
    print(f"  Connection String: {config.sqlalchemy_database_uri}")
    print("\nVerifying connection...")
    if verify_database_connection(config):
        print("✅ Connection successful!")
    else:
        print("❌ Connection failed!")
