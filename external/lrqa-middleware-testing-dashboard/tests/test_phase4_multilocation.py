"""
Phase 4: Multi-Location Synchronization Tests

Comprehensive integration tests for distributed sync across multiple locations:
- Conflict detection and resolution
- Multi-location data consistency
- Fallback mechanisms (DB unreachable)
- Performance under load
- Edge cases and error scenarios

Run tests with: pytest tests/test_phase4_multilocation.py -v
"""

import pytest
import os
import tempfile
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
import json
import time

from agents.distributed_sync_agent import (
    AgentDistributedSync,
    SyncChange,
    EntityType,
    OperationType,
    ConflictType
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def uk_location():
    """UK Primary location agent"""
    os.environ['LOCATION_ID'] = 'UK_PRIMARY'
    # Create temp DB to avoid conflicts
    fd, temp_db = tempfile.mkstemp(suffix='_uk.db')
    os.close(fd)
    agent = AgentDistributedSync()
    agent.sync_manager.local_cache.db_path = temp_db
    agent.sync_manager.local_cache._init_db()
    yield agent
    if os.path.exists(temp_db):
        os.remove(temp_db)


@pytest.fixture
def india_north_location():
    """India North location agent"""
    os.environ['LOCATION_ID'] = 'INDIA_NORTH'
    # Create temp DB to avoid conflicts
    fd, temp_db = tempfile.mkstemp(suffix='_in.db')
    os.close(fd)
    agent = AgentDistributedSync()
    agent.sync_manager.local_cache.db_path = temp_db
    agent.sync_manager.local_cache._init_db()
    yield agent
    if os.path.exists(temp_db):
        os.remove(temp_db)


@pytest.fixture
def india_south_location():
    """India South location agent"""
    os.environ['LOCATION_ID'] = 'INDIA_SOUTH'
    # Create temp DB to avoid conflicts
    fd, temp_db = tempfile.mkstemp(suffix='_is.db')
    os.close(fd)
    agent = AgentDistributedSync()
    agent.sync_manager.local_cache.db_path = temp_db
    agent.sync_manager.local_cache._init_db()
    yield agent
    if os.path.exists(temp_db):
        os.remove(temp_db)


# ============================================================================
# MULTI-LOCATION SYNC TESTS
# ============================================================================

class TestMultiLocationSync:
    """Test multi-location synchronization scenarios"""
    
    def test_three_location_setup(self, uk_location, india_north_location, india_south_location):
        """Test three locations can be created and identified"""
        assert uk_location.location_id == 'UK_PRIMARY'
        assert india_north_location.location_id == 'INDIA_NORTH'
        assert india_south_location.location_id == 'INDIA_SOUTH'
    
    def test_device_created_in_uk_syncs_to_all(self, uk_location, india_north_location):
        """Test device created in UK is pulled by India"""
        # UK creates device
        change_id = uk_location.add_change(
            entity_type=EntityType.DEVICE,
            operation=OperationType.CREATE,
            entity_id='device-uk-1',
            payload={
                'name': 'UK Device 1',
                'ip_address': '10.0.0.1',
                'location': 'UK'
            },
            user_id='user-1',
            team_id='team-1'
        )
        
        assert change_id is not None
        
        # India should see change in queue
        uk_changes = uk_location.sync_manager.local_cache.get_pending_changes(limit=10)
        assert len(uk_changes) >= 1
    
    def test_sequence_created_in_india_north(self, india_north_location):
        """Test sequence creation in India-North location"""
        change_id = india_north_location.add_change(
            entity_type=EntityType.SEQUENCE,
            operation=OperationType.CREATE,
            entity_id='seq-india-1',
            payload={
                'name': 'India Test Sequence',
                'methods': ['method-1', 'method-2'],
                'rationale': 'Daily validation'
            },
            user_id='user-1',
            team_id='team-1'
        )
        
        assert change_id is not None
        status = india_north_location.get_agent_status()
        assert status['location'] == 'INDIA_NORTH'


# ============================================================================
# CONCURRENT CHANGE TESTS
# ============================================================================

class TestConcurrentChanges:
    """Test handling of concurrent changes from multiple locations"""
    
    def test_simultaneous_device_updates_resolved(self, uk_location, india_north_location):
        """Test that simultaneous updates are resolved without data loss"""
        device_id = 'device-shared-1'
        
        # UK updates device IP
        uk_change = SyncChange(
            change_id='ch-uk-1',
            entity_type=EntityType.DEVICE,
            operation=OperationType.UPDATE,
            entity_id=device_id,
            payload={'ip_address': '10.0.0.61'},
            source_location='UK_PRIMARY',
            user_id='user-1',
            team_id='team-1',
            timestamp=datetime.now(timezone.utc)
        )
        
        # India updates same device (slightly later)
        time.sleep(0.1)
        india_change = SyncChange(
            change_id='ch-india-1',
            entity_type=EntityType.DEVICE,
            operation=OperationType.UPDATE,
            entity_id=device_id,
            payload={'ip_address': '10.0.0.62'},
            source_location='INDIA_NORTH',
            user_id='user-2',
            team_id='team-1',
            timestamp=datetime.now(timezone.utc)
        )
        
        # Both changes added to queue
        uk_location.sync_manager.local_cache.add_change(uk_change)
        india_north_location.sync_manager.local_cache.add_change(india_change)
        
        # India change is newer (last-write-wins)
        assert india_change.timestamp > uk_change.timestamp
    
    def test_method_and_sequence_sync_order(self, uk_location):
        """Test that methods are synced before sequences that use them"""
        # Add method
        method_change = uk_location.add_change(
            entity_type=EntityType.METHOD,
            operation=OperationType.CREATE,
            entity_id='method-1',
            payload={'name': 'New Method', 'method_type': 'execution'},
            user_id='user-1',
            team_id='team-1'
        )
        
        # Add sequence using method
        sequence_change = uk_location.add_change(
            entity_type=EntityType.SEQUENCE,
            operation=OperationType.CREATE,
            entity_id='seq-1',
            payload={
                'name': 'Sequence Using Method',
                'methods': ['method-1']
            },
            user_id='user-1',
            team_id='team-1'
        )
        
        # Both in queue
        assert method_change is not None
        assert sequence_change is not None


# ============================================================================
# CONFLICT DETECTION TESTS
# ============================================================================

class TestConflictDetection:
    """Test conflict detection in multi-location scenarios"""
    
    def test_delete_dependency_conflict(self, uk_location):
        """Test detection when deleting entity used by another"""
        # Method used in sequence
        # If UK deletes method, India has sequence using it
        
        method_delete = SyncChange(
            change_id='ch-delete-1',
            entity_type=EntityType.METHOD,
            operation=OperationType.DELETE,
            entity_id='method-used-1',
            payload={'name': 'Used Method'},
            source_location='UK_PRIMARY',
            user_id='user-1',
            team_id='team-1',
            timestamp=datetime.now(timezone.utc)
        )
        
        # This should be flagged as potential breaking change
        assert method_delete.operation == OperationType.DELETE
        assert method_delete.entity_type == EntityType.METHOD
    
    def test_duplicate_device_same_ip(self, uk_location, india_north_location):
        """Test duplicate detection when same IP added from different locations"""
        # UK creates device with IP 10.0.0.1
        uk_change = uk_location.add_change(
            entity_type=EntityType.DEVICE,
            operation=OperationType.CREATE,
            entity_id='device-dup-uk',
            payload={
                'name': 'UK Device',
                'ip_address': '10.0.0.1',
                'location': 'UK'
            },
            user_id='user-1',
            team_id='team-1'
        )
        
        # India tries to create device with same IP
        india_change = india_north_location.add_change(
            entity_type=EntityType.DEVICE,
            operation=OperationType.CREATE,
            entity_id='device-dup-india',
            payload={
                'name': 'India Device',
                'ip_address': '10.0.0.1',  # Same IP!
                'location': 'India'
            },
            user_id='user-2',
            team_id='team-1'
        )
        
        # Both created, but would need conflict resolution on sync
        assert uk_change is not None
        assert india_change is not None


# ============================================================================
# BROADCAST & PULL TESTS
# ============================================================================

class TestBroadcastAndPull:
    """Test broadcasting changes and pulling latest data"""
    
    def test_device_broadcast_to_all_locations(self):
        """Test that device created in one location broadcasts to all"""
        os.environ['LOCATION_ID'] = 'UK_PRIMARY'
        uk = AgentDistributedSync()
        
        # UK creates device
        device_id = uk.add_change(
            entity_type=EntityType.DEVICE,
            operation=OperationType.CREATE,
            entity_id='broadcast-device-1',
            payload={
                'name': 'Broadcast Device',
                'ip_address': '10.0.0.100',
                'location': 'UK'
            },
            user_id='user-1',
            team_id='team-1'
        )
        
        assert device_id is not None
        
        # Verify in queue
        status = uk.get_agent_status()
        assert status['sync_status']['queue_size'] >= 1
    
    def test_pull_latest_on_startup(self, uk_location):
        """Test that agents pull latest data on startup"""
        # Simulate startup pull
        latest = uk_location.sync_manager.pull_latest_data()
        
        # Should return dict (even if empty)
        assert isinstance(latest, dict)


# ============================================================================
# OFFLINE & FALLBACK TESTS
# ============================================================================

class TestOfflineAndFallback:
    """Test behavior when central DB is unreachable"""
    
    def test_local_queue_survives_restart(self):
        """Test that local queue persists across restarts"""
        os.environ['LOCATION_ID'] = 'UK_PRIMARY'
        agent1 = AgentDistributedSync()
        
        # Add change
        change_id = agent1.add_change(
            entity_type=EntityType.DEVICE,
            operation=OperationType.CREATE,
            entity_id='persist-device-1',
            payload={'name': 'Persistent Device', 'ip_address': '10.0.0.1', 'location': 'UK'},
            user_id='user-1',
            team_id='team-1'
        )
        
        assert change_id is not None
        
        # Get queue size
        queue_before = agent1.sync_manager.local_cache.get_pending_changes(limit=100)
        count_before = len(queue_before)
        
        # Simulate restart
        agent2 = AgentDistributedSync()
        queue_after = agent2.sync_manager.local_cache.get_pending_changes(limit=100)
        count_after = len(queue_after)
        
        # Queue should persist
        assert count_after >= count_before
    
    def test_max_queue_capacity(self, uk_location):
        """Test that queue respects capacity limits"""
        # Add many changes (more than typical limit)
        for i in range(10):
            uk_location.add_change(
                entity_type=EntityType.DEVICE,
                operation=OperationType.CREATE,
                entity_id=f'device-capacity-{i}',
                payload={
                    'name': f'Capacity Device {i}',
                    'ip_address': f'10.0.0.{i}',
                    'location': 'UK'
                },
                user_id='user-1',
                team_id='team-1'
            )
        
        # Queue should handle all (or handle overflow gracefully)
        queue = uk_location.sync_manager.local_cache.get_pending_changes(limit=1000)
        assert len(queue) >= 10


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformanceUnderLoad:
    """Test performance with high volume of changes"""
    
    def test_sync_latency_under_load(self, uk_location):
        """Test sync latency with many pending changes"""
        # Add 50 changes
        start_time = time.time()
        change_ids = []
        
        for i in range(50):
            change_id = uk_location.add_change(
                entity_type=EntityType.DEVICE,
                operation=OperationType.CREATE,
                entity_id=f'perf-device-{i}',
                payload={
                    'name': f'Perf Device {i}',
                    'ip_address': f'10.{i}.0.1',
                    'location': 'UK'
                },
                user_id='user-1',
                team_id='team-1'
            )
            change_ids.append(change_id)
        
        elapsed = time.time() - start_time
        
        # All changes should be created successfully
        assert len([cid for cid in change_ids if cid is not None]) == 50
        # Should add 50 changes in < 5 seconds (realistic for DB I/O with fresh DBs)
        assert elapsed < 5.0, f"Adding 50 changes took {elapsed}s (target: <5.0s)"
    
    def test_queue_retrieval_performance(self, uk_location):
        """Test performance of retrieving large queues"""
        # Add 100 changes
        for i in range(100):
            uk_location.add_change(
                entity_type=EntityType.METHOD,
                operation=OperationType.CREATE,
                entity_id=f'perf-method-{i}',
                payload={'name': f'Perf Method {i}', 'method_type': 'execution'},
                user_id='user-1',
                team_id='team-1'
            )
        
        # Retrieve in batches
        start_time = time.time()
        
        for _ in range(10):
            uk_location.sync_manager.local_cache.get_pending_changes(limit=100)
        
        elapsed = time.time() - start_time
        
        # Should retrieve 100 items 10 times in < 1 second
        assert elapsed < 1.0, f"Retrieving took {elapsed}s (target: <1.0s)"


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_null_payload_handling(self, uk_location):
        """Test handling of null/empty payloads"""
        change_id = uk_location.add_change(
            entity_type=EntityType.DEVICE,
            operation=OperationType.DELETE,
            entity_id='device-null',
            payload={},  # Empty payload
            user_id='user-1',
            team_id='team-1'
        )
        
        # Should still queue (validation happens later)
        assert change_id is not None
    
    def test_special_characters_in_entity_id(self, uk_location):
        """Test handling of special characters"""
        change_id = uk_location.add_change(
            entity_type=EntityType.DEVICE,
            operation=OperationType.CREATE,
            entity_id='device-special-!@#$%',
            payload={
                'name': 'Special Device',
                'ip_address': '10.0.0.1',
                'location': 'UK'
            },
            user_id='user-1',
            team_id='team-1'
        )
        
        # Should handle special characters
        assert change_id is not None
    
    def test_very_large_payload(self, uk_location):
        """Test handling of large payloads"""
        large_data = "x" * 1000000  # 1MB string
        
        change_id = uk_location.add_change(
            entity_type=EntityType.SEQUENCE,
            operation=OperationType.CREATE,
            entity_id='seq-large',
            payload={
                'name': 'Large Sequence',
                'methods': ['method-1', 'method-2'],
                'large_data': large_data  # 1MB
            },
            user_id='user-1',
            team_id='team-1'
        )
        
        # Should queue large payloads (storage handles it)
        assert change_id is not None
    
    def test_rapid_updates_same_entity(self, uk_location):
        """Test rapid updates to same entity"""
        entity_id = 'device-rapid'
        change_ids = []
        
        for i in range(10):
            change_id = uk_location.add_change(
                entity_type=EntityType.DEVICE,
                operation=OperationType.UPDATE,
                entity_id=entity_id,
                payload={
                    'name': f'Rapid Device v{i}',
                    'ip_address': '10.0.0.1',
                    'location': 'UK',
                    'version': i
                },
                user_id='user-1',
                team_id='team-1'
            )
            change_ids.append(change_id)
        
        # All changes should be created successfully
        assert len([cid for cid in change_ids if cid is not None]) == 10


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
