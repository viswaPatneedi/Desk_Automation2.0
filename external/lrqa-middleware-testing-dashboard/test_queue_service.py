import unittest
import os
import json
from services.queue_service import QueueService
from models.job import Job

class MockTestExecutionService:
    def __init__(self):
        self.executed_jobs = []
    def execute_test(self, device_ip, methods, iterations, selected_ir_keys=None, voice_text=''):
        self.executed_jobs.append({
            'device_ip': device_ip,
            'methods': methods,
            'iterations': iterations,
            'selected_ir_keys': selected_ir_keys,
            'voice_text': voice_text
        })

class TestQueueService(unittest.TestCase):
    def setUp(self):
        # Clean up queue file before each test
        self.queue_file = 'device_job_queue.json'
        if os.path.exists(self.queue_file):
            os.remove(self.queue_file)
        self.test_service = MockTestExecutionService()
        self.queue_service = QueueService(self.test_service)
        # Clean up jobs.json
        jobs_file = 'jobs.json'
        if os.path.exists(jobs_file):
            os.remove(jobs_file)

    def test_add_job_to_free_device_starts_immediately(self):
        result = self.queue_service.add_job(
            device_ip='10.0.0.1', device_name='TestDevice', method='reboot',
            iterations=1, username='user', password='pass')
        self.assertFalse(result.get('queued'))
        self.assertEqual(result.get('position'), 1)

    def test_add_job_to_busy_device_enqueues(self):
        # Simulate running job
        Job.create_job('user', '10.0.0.2', 'TestDevice2', ['reboot'], 1)
        result = self.queue_service.add_job(
            device_ip='10.0.0.2', device_name='TestDevice2', method='reboot',
            iterations=1, username='user', password='pass')
        self.assertTrue(result.get('queued'))
        self.assertEqual(result.get('position'), 1)
        # Check queue file
        with open(self.queue_file) as f:
            queue_data = json.load(f)
        self.assertIn('10.0.0.2', queue_data)
        self.assertEqual(len(queue_data['10.0.0.2']), 1)

    def test_auto_trigger_next_job(self):
        import time
        # Simulate running job
        Job.create_job('user', '10.0.0.3', 'TestDevice3', ['reboot'], 1)
        # Enqueue two jobs
        self.queue_service.add_job('10.0.0.3', 'TestDevice3', 'reboot', 1, 'user', 'pass')
        self.queue_service.add_job('10.0.0.3', 'TestDevice3', 'reboot', 1, 'user', 'pass')
        # Mark the active job as completed
        Job.update_job_status(Job.get_device_jobs('10.0.0.3')[0].job_id, 'completed')
        # Trigger next job for device
        self.queue_service.trigger_next_job_for_device('10.0.0.3')
        self.queue_service.start_processor()
        time.sleep(1)
        self.assertGreaterEqual(len(self.test_service.executed_jobs), 1)

    def tearDown(self):
        # Clean up queue file after each test
        if os.path.exists(self.queue_file):
            os.remove(self.queue_file)
        jobs_file = 'jobs.json'
        if os.path.exists(jobs_file):
            os.remove(jobs_file)

if __name__ == '__main__':
    unittest.main()
