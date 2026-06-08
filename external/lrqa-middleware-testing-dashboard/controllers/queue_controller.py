"""
Queue Controller - Handles test queue operations
"""

from flask import jsonify, request
from models.device import Device
from services.queue_service import QueueService

class QueueController:
    """Controller for test queue operations"""
    
    def __init__(self, queue_service: QueueService):
        self.queue_service = queue_service
    
    def add_to_queue(self):
        """POST /api/queue/add - Add test to queue"""
        data = request.json
        device_ip = data.get('device_ip')
        method = data.get('method')
        iterations = int(data.get('iterations', 1))
        selected_ir_keys = data.get('selected_ir_keys', ['HOME', 'POWER'])
        voice_text = data.get('voice_text', '')  # Get voice command text
        remote_keys = data.get('remote_keys', '')  # Get remote keys
        expected_screen = data.get('expected_screen', '')  # Get expected screen for validation
        execution_queue = data.get('execution_queue', [])  # Get full execution queue with params
        sequence_name = data.get('sequence_name')  # Get sequence name if from a saved sequence
        
        # Debug logging
        print(f"DEBUG add_to_queue: execution_queue = {execution_queue}")
        print(f"DEBUG add_to_queue: Number of items in execution_queue = {len(execution_queue)}")
        if execution_queue:
            for idx, item in enumerate(execution_queue):
                print(f"DEBUG queue_item[{idx}]: {item}")
                if item.get('method') == 'trail_method':
                    print(f"  ^ TRAIL_METHOD DETECTED!")
                    print(f"    - Keys: {list(item.keys())}")
                    print(f"    - log_search_patterns: {item.get('log_search_patterns')}")
                    print(f"    - auto_collect_logs: {item.get('auto_collect_logs')}")
                    print(f"    - home_screen_timeout: {item.get('home_screen_timeout')}")
                    print(f"    - optional_checks: {item.get('optional_checks')}")
        
        # Get device
        device = Device.find_by_ip(device_ip)
        if not device:
            return jsonify({'error': 'Device not found'}), 404
        
        # Add to queue
        result = self.queue_service.add_job(
            device_ip=device.ip,
            device_name=device.name,
            method=method,
            iterations=iterations,
            username=device.username,
            password=device.password,
            port=device.port,
            selected_ir_keys=selected_ir_keys,
            voice_text=voice_text,
            remote_keys=remote_keys,
            expected_screen=expected_screen,
            execution_queue=execution_queue,
            sequence_name=sequence_name
        )
        
        return jsonify({
            'message': 'Job added to queue',
            'job_id': result['job_id'],
            'position': result['position']
        })
    
    def get_queue_status(self):
        """GET /api/queue/status - Get queue status"""
        status = self.queue_service.get_status()
        return jsonify(status)
    
    def clear_queue(self):
        """POST /api/queue/clear - Clear the queue"""
        self.queue_service.clear_queue()
        return jsonify({'message': 'Queue cleared'})
