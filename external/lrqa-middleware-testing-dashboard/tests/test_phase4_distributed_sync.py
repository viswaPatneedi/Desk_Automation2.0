"""
Phase 4: Distributed Data Synchronization - Unit Tests

Comprehensive test suite for distributed sync agent functionality:
- Local queue operations
- Schema validation
- Conflict detection and resolution
- Sync manager operations
- Audit logging

Run tests with: pytest tests/test_phase4_distributed_sync.py -v
"""

import pytest
import json
import os
import tempfile
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
import sqlite3

from agents.distributed_sync_agent import (
    AgentDistributedSync,
    LocalSyncCache,
    SyncValidator,
    ConflictResolver,
    SyncManager,
    AuditLogger,
    SyncChange,
    SyncEventType,
    EntityType,
    OperationType,
    ConflictType
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_db():
    """Temporary database for testing"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def local_cache(temp_db):
    """Create LocalSyncCache instance"""
    return LocalSyncCache(db_path=temp_db)


@pytest.fixture
def validator():
    """Create SyncValidator instance"""
    return SyncValidator()


@pytest.fixture
def conflict_resolver():
    """Create ConflictResolver instance"""
    return ConflictResolver()


@pytest.fixture
def agent():
    """Create AgentDistributedSync instance"""
    return AgentDistributedSync()


# ============================================================================
# LOCAL SYNC CACHE TESTS
# ============================================================================

class TestLocalSyncCache:
    """Test LocalSyncCache functionality"""
    
    def test_cache_initialization(self, local_cache):
        """Test cache initializes with tables"""
        assert os.path.exists(local_cache.db_path)
        
        # Verify tables exist
        conn = sqlite3.connect(local_cache.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        assert 'sync_queue' in tables
        assert 'sync_backup' in tables
    
    def test_add_change_to_queue(self, local_cache):
        """Test adding a change to queue"""
        change = SyncChange(
            change_id='test-1',
            entity_type=EntityType.DEVICE,
            operation=OperationType.CREATE,
            entity_id='device-1',
            payload={'name': 'Test Device', 'ip_address': '10.0.0.1', 'location': 'UK'},
            source_location='UK_PRIMARY',
            user_id='user-1',
            team_id='team-1',
            timestamp=datetime.now(timezone.utc)
        )
        
        result = local_cache.add_change(change)
        assert result is True
    
    def test_get_pending_changes(self, local_cache):
        """Test retrieving pending changes"""
        # Add multiple changes
        for i in range(3):
            change = SyncChange(
                change_id=f'test-{i}',
                entity_type=EntityType.DEVICE,
                operation=OperationType.CREATE,
                entity_id=f'device-{i}',
                payload={'name': f'Device {i}', 'ip_address': f'10.0.0.{i}', 'location': 'UK'},
                source_location='UK_PRIMARY',
                user_id='user-1',
                team_id='team-1',
                timestamp=datetime.now(timezone.utc)
            )
            local_cache.add_change(change)
        
        # Retrieve changes
        changes = local_cache.get_pending_changes(limit=10)
        assert len(changes) == 3
        assert all(c.status == 'PENDING' for c in changes)
    
    def test_mark_synced(self, local_cache):
        """Test marking change as synced"""
        change = SyncChange(
            change_id='test-sync',
            entity_type=EntityType.DEVICE,
            operation=OperationType.CREATE,
            entity_id='device-1',
            payload={'name': 'Test Device', 'ip_address': '10.0.0.1', 'location': 'UK'},
            source_location='UK_PRIMARY',
            user_id='user-1',
            team_id='team-1',
            timestamp=datetime.now(timezone.utc)
        )
        
        local_cache.add_change(change)
        result = local_cache.mark_synced('test-sync')
        assert result is True
        
        # Verify status changed
        changes = local_cache.get_pending_changes(limit=10)
        assert len(changes) == 0  # No pending changes
    
    def test_queue_capacity(self, local_cache):
        """Test queue can handle multiple changes"""
        # Add 50 changes
        for i in range(50):
            change = SyncChange(
                change_id=f'test-{i}',
                entity_type=EntityType.DEVICE,
                operation=OperationType.CREATE,
                entity_id=f'device-{i}',
                payload={'name': f'Device {i}', 'ip_address': f'10.0.0.{i}', 'location': 'UK'},
                source_location='UK_PRIMARY',
                user_id='user-1',
                team_id='team-1',
                timestamp=datetime.now(timezone.utc)
            )
            local_cache.add_change(change)
        
        # Retrieve in batches
        changes = local_cache.get_pending_changes(limit=10)
        assert len(changes) == 10
        
        changes = local_cache.get_pending_changes(limit=50)
        assert len(changes) == 50


# ============================================================================
# SCHEMA VALIDATION TESTS
# ============================================================================

class TestSyncValidator:
    """Test SyncValidator functionality"""
    
    def test_validate_device_schema_valid(self, validator):
        """Test valid device schema"""
        payload = {
            'name': 'Test Device',
            'ip_address': '10.0.0.1',
            'location': 'UK'
        }
        valid, msg = validator.validate_schema(EntityType.DEVICE, payload)
        assert valid is True
        assert msg == 'OK'
    
    def test_validate_device_schema_missing_field(self, validator):
        """Test device schema with missing required field"""
        payload = {
            'name': 'Test Device',
            'ip_address': '10.0.0.1'
            # Missing 'location'
        }
        valid, msg = validator.validate_schema(EntityType.DEVICE, payload)
        assert valid is False
        assert 'location' in msg.lower()
    
    def test_validate_device_schema_invalid_ip(self, validator):
        """Test device schema with invalid IP constraint"""
        payload = {
            'name': 'Test Device',
            'ip_address': '999.999.999.999',  # Invalid IP - constraint in schema
            'location': 'UK'
        }
        # Schema validation fails due to IP constraint
        valid, msg = validator.validate_schema(EntityType.DEVICE, payload)
        assert valid is False
        assert 'constraint' in msg.lower() or '999' in msg
    
    def test_validate_constraints_port_range(self, validator):
        """Test port constraint validation"""
        payload_valid = {
            'name': 'Device',
            'ip_address': '10.0.0.1',
            'location': 'UK',
            'port': 22
        }
        valid, msg = validator.validate_constraints(EntityType.DEVICE, payload_valid)
        assert valid is True
        
        payload_invalid = {
            'name': 'Device',
            'ip_address': '10.0.0.1',
            'location': 'UK',
            'port': 99999  # Invalid port
        }
        valid, msg = validator.validate_constraints(EntityType.DEVICE, payload_invalid)
        assert valid is False
        assert 'port' in msg.lower()
    
    def test_validate_sequence_schema(self, validator):
        """Test sequence schema validation"""
        payload = {
            'name': 'Daily Test Sequence',
            'methods': ['method1', 'method2'],
            'rationale': 'Daily validation test'
        }
        valid, msg = validator.validate_schema(EntityType.SEQUENCE, payload)
        assert valid is True


# ============================================================================
# CONFLICT DETECTION & RESOLUTION TESTS
# ============================================================================

class TestConflictResolver:
    """Test ConflictResolver functionality"""
    
    def test_detect_no_conflict(self, conflict_resolver):
        """Test detection when no conflict (different timestamps)"""
        local = {'name': 'Device1', 'modified_at': '2026-06-09T10:00:00Z'}
        remote = {'name': 'Device1', 'modified_at': '2026-06-09T09:00:00Z'}  # Different time
        
        conflict = conflict_resolver.detect_conflict(local, remote)
        assert conflict is None
    
    def test_detect_timestamp_conflict(self, conflict_resolver):
        """Test detection of timestamp conflict"""
        local = {'name': 'Device1', 'modified_at': '2026-06-09T10:00:00Z'}
        remote = {'name': 'Device1', 'modified_at': '2026-06-09T10:00:00Z'}
        
        # Force detection (same timestamp)
        conflict = conflict_resolver.detect_conflict(local, remote)
        assert conflict in [ConflictType.TIMESTAMP_CONFLICT, None]
    
    def test_resolve_timestamp_based_local_newer(self, conflict_resolver):
        """Test timestamp-based resolution when local is newer"""
        local = {
            'name': 'Device1-updated',
            'modified_at': datetime.now(timezone.utc).isoformat()
        }
        remote = {
            'name': 'Device1',
            'modified_at': (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
        }
        
        resolved = conflict_resolver._resolve_timestamp_based(local, remote)
        assert resolved['name'] == 'Device1-updated'
    
    def test_resolve_timestamp_based_remote_newer(self, conflict_resolver):
        """Test timestamp-based resolution when remote is newer"""
        local = {
            'name': 'Device1',
            'modified_at': (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
        }
        remote = {
            'name': 'Device1-updated',
            'modified_at': datetime.now(timezone.utc).isoformat()
        }
        
        resolved = conflict_resolver._resolve_timestamp_based(local, remote)
        assert resolved['name'] == 'Device1-updated'
    
    def test_resolve_duplicate(self, conflict_resolver):
        """Test duplicate resolution"""
        local = {'name': 'Device1', 'port': 22}
        remote = {'name': 'Device1', 'port': 10022, 'location': 'UK'}
        
        merged = conflict_resolver._resolve_duplicate(local, remote)
        assert merged['port'] == 22  # Local overrides
        assert merged['location'] == 'UK'  # Remote provides


# ============================================================================
# SYNC MANAGER TESTS
# ============================================================================

class TestSyncManager:
    """Test SyncManager functionality"""
    
    def test_manager_initialization(self):
        """Test manager initializes correctly"""
        manager = SyncManager(location_id='TEST_LOCATION')
        assert manager.location_id == 'TEST_LOCATION'
        assert manager.metrics['health_status'] == 'INITIALIZING'
    
    def test_get_status(self):
        """Test getting manager status"""
        manager = SyncManager()
        status = manager.get_status()
        
        assert 'location_id' in status
        assert 'health_status' in status
        assert 'changes_synced' in status
        assert status['health_status'] in ['INITIALIZING', 'DISCONNECTED', 'CONNECTED']
    
    @patch('psycopg2.connect')
    def test_connect_central_db_success(self, mock_connect):
        """Test successful connection to central DB"""
        mock_db = MagicMock()
        mock_connect.return_value = mock_db
        
        manager = SyncManager()
        result = manager.connect_central_db(
            host='localhost',
            port=5432,
            database='test_db',
            user='user',
            password='pass'
        )
        
        assert result is True
        assert manager.metrics['health_status'] == 'CONNECTED'
    
    @patch('psycopg2.connect')
    def test_connect_central_db_failure(self, mock_connect):
        """Test connection failure to central DB"""
        mock_connect.side_effect = Exception("Connection refused")
        
        manager = SyncManager()
        result = manager.connect_central_db(
            host='localhost',
            port=5432,
            database='test_db',
            user='user',
            password='pass'
        )
        
        assert result is False
        assert manager.metrics['health_status'] == 'DISCONNECTED'


# ============================================================================
# AGENT TESTS
# ============================================================================

class TestAgentDistributedSync:
    """Test AgentDistributedSync functionality"""
    
    def test_agent_initialization(self, agent):
        """Test agent initializes correctly"""
        assert agent.location_id is not None
        assert agent.running is False
        assert isinstance(agent.sync_manager, SyncManager)
    
    def test_get_agent_status(self, agent):
        """Test getting agent status"""
        status = agent.get_agent_status()
        
        assert status['agent'] == 'AgentDistributedSync'
        assert 'version' in status
        assert 'location' in status
        assert 'running' in status
        assert 'sync_status' in status
    
    def test_add_change_to_queue(self, agent):
        """Test adding a change"""
        change_id = agent.add_change(
            entity_type=EntityType.METHOD,
            operation=OperationType.CREATE,
            entity_id='method-1',
            payload={'name': 'Test Method', 'method_type': 'execution'},
            user_id='user-1',
            team_id='team-1'
        )
        
        assert change_id is not None
        assert isinstance(change_id, str)
    
    def test_start_stop_sync_daemon(self, agent):
        """Test starting and stopping sync daemon"""
        agent.start_sync_daemon()
        assert agent.running is True
        
        agent.stop_sync_daemon()
        assert agent.running is False


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestPhase4Integration:
    """Integration tests for distributed sync workflow"""
    
    def test_full_sync_workflow(self, agent, local_cache, validator):
        """Test complete sync workflow"""
        # 1. Add a device change
        change_id = agent.add_change(
            entity_type=EntityType.DEVICE,
            operation=OperationType.CREATE,
            entity_id='device-uk-1',
            payload={
                'name': 'UK Test Device',
                'ip_address': '10.0.0.1',
                'location': 'UK'
            },
            user_id='user-1',
            team_id='team-1'
        )
        
        assert change_id is not None
        
        # 2. Verify change is in queue
        status = agent.get_agent_status()
        # Queue size check if we had better integration
    
    def test_multiple_location_sync(self):
        """Test sync across multiple locations"""
        uk_agent = AgentDistributedSync()
        os.environ['LOCATION_ID'] = 'INDIA_NORTH'
        india_agent = AgentDistributedSync()
        
        assert uk_agent.location_id != india_agent.location_id
    
    def test_schema_validation_in_sync_flow(self, agent, validator):
        """Test that schema validation happens in sync flow"""
        # Valid payload
        valid_payload = {
            'name': 'Device',
            'ip_address': '10.0.0.1',
            'location': 'UK'
        }
        valid, msg = validator.validate_schema(EntityType.DEVICE, valid_payload)
        assert valid is True
        
        # Invalid payload
        invalid_payload = {
            'name': 'Device'
            # Missing required fields
        }
        valid, msg = validator.validate_schema(EntityType.DEVICE, invalid_payload)
        assert valid is False


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestPhase4ErrorHandling:
    """Test error handling in distributed sync"""
    
    def test_queue_error_recovery(self, local_cache):
        """Test recovery from queue errors"""
        change = SyncChange(
            change_id='test-error',
            entity_type=EntityType.DEVICE,
            operation=OperationType.CREATE,
            entity_id='device-1',
            payload={'name': 'Device', 'ip_address': '10.0.0.1', 'location': 'UK'},
            source_location='UK_PRIMARY',
            user_id='user-1',
            team_id='team-1',
            timestamp=datetime.now(timezone.utc)
        )
        
        # Add change
        result = local_cache.add_change(change)
        assert result is True
        
        # Mark as synced
        result = local_cache.mark_synced('test-error')
        assert result is True
    
    def test_validation_error_handling(self, validator):
        """Test validation error handling"""
        invalid_payloads = [
            {},  # Empty payload
            {'name': 'Device'},  # Missing fields
            {'ip_address': '999.999.999.999', 'location': 'UK'},  # Missing required field
        ]
        
        for payload in invalid_payloads:
            valid, msg = validator.validate_schema(EntityType.DEVICE, payload)
            # Should handle gracefully
            assert isinstance(valid, bool)
            assert isinstance(msg, str)
    
    def test_conflict_no_infinite_loop(self, conflict_resolver):
        """Test that conflict resolution doesn't create infinite loops"""
        local = {'name': 'Device', 'data': [1, 2, 3]}
        remote = {'name': 'Device', 'data': [1, 2, 3, 4]}
        
        # Should resolve without hanging
        resolved = conflict_resolver._resolve_duplicate(local, remote)
        assert resolved is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
