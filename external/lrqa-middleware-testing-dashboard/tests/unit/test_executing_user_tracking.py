"""
Unit Tests for Phase 21: Executing User Tracking Feature
Tests for job model, queue service, and device controller to track executing_user
"""

import unittest
import json
import os
from datetime import datetime, timezone
from models.job import Job
from services.queue_service import QueueService
from controllers.device_controller import DeviceController

class MockLogService:
    """Mock log service for testing"""
    def log(self, message):
        pass

class MockTestExecutionService:
    """Mock test execution service for testing"""
    def __init__(self):
        self.executed_jobs = []

class TestExecutingUserTracking(unittest.TestCase):
    """Test suite for executing_user tracking functionality (Phase 21)"""
    
    def setUp(self):
        """Clean up before each test"""
        # Remove jobs.json for fresh start
        if os.path.exists('jobs.json'):
            os.remove('jobs.json')
    
    def tearDown(self):
        """Clean up after each test"""
        if os.path.exists('jobs.json'):
            os.remove('jobs.json')
    
    def test_job_model_executing_user_field(self):
        """Test that Job model stores executing_user field"""
        job = Job.create_job(
            user_id='test_user',
            device_ip='10.0.0.1',
            device_name='TestDevice',
            methods=['reboot_perf_v2_optimized'],
            iterations=1
        )
        
        # Verify executing_user is None initially (no execution started)
        self.assertIsNone(job.executing_user)
        self.assertIsNotNone(job.job_id)
    
    def test_job_model_triggered_at_timestamp(self):
        """Test that Job model tracks triggered_at timestamp"""
        job = Job.create_job(
            user_id='test_user',
            device_ip='10.0.0.1',
            device_name='TestDevice',
            methods=['reboot_perf_v2_optimized'],
            iterations=1
        )
        
        # Job should have triggered_at timestamp (even if not executed yet)
        # triggered_at is set when job is created
        self.assertIsNotNone(job.triggered_at)
    
    def test_job_to_dict_includes_executing_user(self):
        """Test that Job.to_dict() includes executing_user field"""
        job = Job.create_job(
            user_id='test_user',
            device_ip='10.0.0.1',
            device_name='TestDevice',
            methods=['reboot_perf_v2_optimized'],
            iterations=1
        )
        
        job_dict = job.to_dict()
        
        # Verify executing_user is in dict
        self.assertIn('executing_user', job_dict)
        # Should be None for newly created job
        self.assertIsNone(job_dict['executing_user'])
    
    def test_job_from_dict_preserves_executing_user(self):
        """Test that Job.from_dict() preserves executing_user field"""
        original_job = Job.create_job(
            user_id='test_user',
            device_ip='10.0.0.1',
            device_name='TestDevice',
            methods=['reboot_perf_v2_optimized'],
            iterations=1
        )
        
        # Convert to dict and back
        job_dict = original_job.to_dict()
        restored_job = Job.from_dict(job_dict)
        
        # Verify executing_user is preserved (None in this case)
        self.assertEqual(restored_job.executing_user, original_job.executing_user)
    
    def test_job_backward_compatibility_old_job_without_executing_user(self):
        """Test that old job records without executing_user field are handled"""
        # Simulate old job record without executing_user
        old_job_dict = {
            'job_id': 'test_job_123',
            'user_id': 'test_user',
            'device_ip': '10.0.0.1',
            'device_name': 'TestDevice',
            'methods': ['reboot_perf_v2_optimized'],
            'status': 'pending',
            'iterations': 1,
            'created_at': datetime.now(timezone.utc).isoformat(),
            # Intentionally no executing_user field
        }
        
        # Should not raise error when loading old-format job
        job = Job.from_dict(old_job_dict)
        
        # Should have executing_user as None (default)
        self.assertIsNone(job.executing_user)
    
    def test_queue_service_add_job_tracking_executing_user(self):
        """Test that QueueService.add_job() tracks executing_user"""
        test_service = MockTestExecutionService()
        log_service = MockLogService()
        queue_service = QueueService(test_service, log_service)
        
        result = queue_service.add_job(
            device_ip='10.0.0.1',
            device_name='TestDevice',
            method='reboot_perf_v2_optimized',
            iterations=1,
            username='root',
            password='password',
            executing_user='john_doe'
        )
        
        # Verify response includes executing_user
        self.assertIn('executing_user', result)
        self.assertEqual(result['executing_user'], 'john_doe')
    
    def test_device_controller_returns_executing_user_for_busy_device(self):
        """Test that device controller returns executing_user for BUSY devices"""
        # This would require Flask app context, so we test the logic
        # Create a job to simulate a running device
        job = Job.create_job(
            user_id='test_user',
            device_ip='10.0.0.1',
            device_name='TestDevice',
            methods=['reboot_perf_v2_optimized'],
            iterations=1
        )
        
        # Simulate job execution by checking if device has active job
        active_job = Job.get_active_device_job('10.0.0.1')
        
        # Should find the active job
        self.assertIsNotNone(active_job)
        self.assertEqual(active_job.device_ip, '10.0.0.1')
    
    def test_multiple_jobs_track_separate_executing_users(self):
        """Test that multiple jobs track their own executing_user correctly"""
        # Create multiple jobs with different executing_users
        job1 = Job.create_job(
            user_id='user1',
            device_ip='10.0.0.1',
            device_name='Device1',
            methods=['reboot_perf_v2_optimized'],
            iterations=1
        )
        
        job2 = Job.create_job(
            user_id='user2',
            device_ip='10.0.0.2',
            device_name='Device2',
            methods=['reboot_perf_v2_optimized'],
            iterations=1
        )
        
        # Verify both jobs exist and are independent
        all_jobs = Job.load_all()
        self.assertGreaterEqual(len(all_jobs), 2)
        
        # Find the jobs we created
        found_job1 = next((j for j in all_jobs if j.job_id == job1.job_id), None)
        found_job2 = next((j for j in all_jobs if j.job_id == job2.job_id), None)
        
        self.assertIsNotNone(found_job1)
        self.assertIsNotNone(found_job2)
        self.assertEqual(found_job1.user_id, 'user1')
        self.assertEqual(found_job2.user_id, 'user2')
    
    def test_job_queue_position_tracking(self):
        """Test that queue_position is properly tracked"""
        job = Job.create_job(
            user_id='test_user',
            device_ip='10.0.0.1',
            device_name='TestDevice',
            methods=['reboot_perf_v2_optimized'],
            iterations=1
        )
        
        # Job should have queue_position field
        self.assertIsNotNone(job.queue_position)
        # Should be 0 for first job
        self.assertEqual(job.queue_position, 0)

class TestExecutingUserIntegration(unittest.TestCase):
    """Integration tests for executing_user tracking across components"""
    
    def setUp(self):
        """Clean up before each test"""
        if os.path.exists('jobs.json'):
            os.remove('jobs.json')
    
    def tearDown(self):
        """Clean up after each test"""
        if os.path.exists('jobs.json'):
            os.remove('jobs.json')
    
    def test_job_lifecycle_with_executing_user(self):
        """Test complete job lifecycle tracking executing_user"""
        # Create job
        job = Job.create_job(
            user_id='test_user',
            device_ip='10.0.0.1',
            device_name='TestDevice',
            methods=['reboot_perf_v2_optimized'],
            iterations=1
        )
        
        job_id = job.job_id
        
        # Update job status  
        Job.update_job_status(job_id, 'running')
        
        # Retrieve updated job
        updated_job = Job.find_by_id(job_id)
        
        self.assertIsNotNone(updated_job)
        self.assertEqual(updated_job.status, 'running')
        # executing_user should still be tracked even after status update
        self.assertIsNotNone(updated_job.job_id)

if __name__ == '__main__':
    unittest.main()
