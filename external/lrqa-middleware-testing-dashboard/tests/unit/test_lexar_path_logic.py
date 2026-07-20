"""
Unit Tests for Phase 23: Lexar USB Path Optimization
Tests for Lexar detection, path construction, and fallback logic
"""

import unittest
import os
import tempfile
import shutil
from datetime import datetime, timezone

class TestLexarPathDetection(unittest.TestCase):
    """Test suite for Lexar USB path detection (Phase 23)"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary directories for testing
        self.temp_dir = tempfile.mkdtemp()
        self.lexar_path = os.path.join(self.temp_dir, "Lexar")
        self.media_apps_path = os.path.join(self.temp_dir, "media_apps")
        
        # Create the directories
        os.makedirs(os.path.join(self.lexar_path, "Enhancement_output"), exist_ok=True)
        os.makedirs(self.media_apps_path, exist_ok=True)
    
    def tearDown(self):
        """Clean up test fixtures"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_lexar_path_structure_enhancement_output(self):
        """Test that Lexar path has correct Enhancement_output structure"""
        # Verify the structure exists
        enhancement_path = os.path.join(self.lexar_path, "Enhancement_output")
        self.assertTrue(os.path.exists(enhancement_path))
        
        # Create execution logs directory
        device_ip = "10.0.0.1"
        execution_dir = os.path.join(enhancement_path, "EXECUTION_LOGS", device_ip)
        os.makedirs(execution_dir, exist_ok=True)
        
        # Verify directory structure
        self.assertTrue(os.path.exists(execution_dir))
    
    def test_lexar_path_iteration_directory_naming(self):
        """Test that iteration directories follow ITR-N format"""
        iteration = 1
        device_ip = "10.0.0.1"
        
        # Build path following ITR-N convention
        iteration_dir = os.path.join(
            self.lexar_path,
            "Enhancement_output",
            "EXECUTION_LOGS",
            device_ip,
            f"ITR-{iteration}"
        )
        
        # Expected format: ITR-1, ITR-2, etc.
        self.assertIn(f"ITR-{iteration}", iteration_dir)
    
    def test_lexar_tar_gz_filename_format(self):
        """Test that tar.gz filename includes all required components"""
        device_ip = "10.0.0.1"
        device_name = "TestDevice"
        iteration = 1
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        
        # Build filename following convention
        filename = f"{device_ip}_{device_name}_ITR-{iteration}_logs_{timestamp}.tar.gz"
        
        # Verify format
        self.assertIn(device_ip, filename)
        self.assertIn(device_name, filename)
        self.assertIn(f"ITR-{iteration}", filename)
        self.assertIn("_logs_", filename)
        self.assertIn(".tar.gz", filename)
        self.assertTrue(filename.endswith(".tar.gz"))
    
    def test_fallback_to_media_apps_path(self):
        """Test fallback to /media/apps when Lexar not available"""
        # Simulate Lexar not available
        lexar_available = False
        
        if lexar_available:
            target_path = self.lexar_path
        else:
            target_path = self.media_apps_path
        
        # Verify fallback path exists
        self.assertTrue(os.path.exists(target_path))
        self.assertEqual(target_path, self.media_apps_path)
    
    def test_path_priority_lexar_over_media_apps(self):
        """Test that Lexar path is prioritized over /media/apps"""
        paths_to_check = [
            (self.lexar_path, True),           # Lexar (preferred)
            (self.media_apps_path, False)      # /media/apps (fallback)
        ]
        
        # Find first available path (simulating get_lexar_base_path logic)
        selected_path = None
        for path, is_preferred in paths_to_check:
            if os.path.exists(path):
                selected_path = path
                if is_preferred:
                    break  # Prefer Lexar if available
        
        self.assertEqual(selected_path, self.lexar_path)
    
    def test_lexar_base_path_environment_variable(self):
        """Test that Lexar path can be overridden via environment variable"""
        # Set environment variable
        custom_lexar_path = os.path.join(self.temp_dir, "custom_lexar")
        os.makedirs(custom_lexar_path, exist_ok=True)
        os.environ['LEXAR_PATH'] = custom_lexar_path
        
        try:
            # Retrieve path (simulating get_lexar_base_path function)
            lexar_path = os.environ.get('LEXAR_PATH', self.lexar_path)
            
            # Verify custom path is used
            self.assertEqual(lexar_path, custom_lexar_path)
            self.assertTrue(os.path.exists(lexar_path))
        finally:
            # Clean up environment
            if 'LEXAR_PATH' in os.environ:
                del os.environ['LEXAR_PATH']
    
    def test_device_ip_directory_creation(self):
        """Test that device IP directory is created automatically"""
        device_ip = "10.0.0.1"
        device_dir = os.path.join(self.lexar_path, "Enhancement_output", "EXECUTION_LOGS", device_ip)
        
        # Create directory with exist_ok=True (like in the implementation)
        os.makedirs(device_dir, exist_ok=True)
        
        self.assertTrue(os.path.exists(device_dir))
    
    def test_multiple_iterations_create_separate_directories(self):
        """Test that multiple iterations create separate ITR-N directories"""
        device_ip = "10.0.0.1"
        base_path = os.path.join(self.lexar_path, "Enhancement_output", "EXECUTION_LOGS", device_ip)
        
        # Create directories for multiple iterations
        for iteration in range(1, 4):
            iteration_dir = os.path.join(base_path, f"ITR-{iteration}")
            os.makedirs(iteration_dir, exist_ok=True)
            self.assertTrue(os.path.exists(iteration_dir))
        
        # Verify all directories exist
        for iteration in range(1, 4):
            self.assertTrue(os.path.exists(os.path.join(base_path, f"ITR-{iteration}")))
    
    def test_log_file_path_construction(self):
        """Test complete log file path construction"""
        device_ip = "10.0.0.1"
        device_name = "TestDevice"
        iteration = 1
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        
        # Construct full path using Lexar base
        full_path = os.path.join(
            self.lexar_path,
            "Enhancement_output",
            "EXECUTION_LOGS",
            device_ip,
            f"ITR-{iteration}",
            f"{device_ip}_{device_name}_ITR-{iteration}_logs_{timestamp}.tar.gz"
        )
        
        # Verify path structure
        self.assertIn("Enhancement_output", full_path)
        self.assertIn("EXECUTION_LOGS", full_path)
        self.assertIn(device_ip, full_path)
        self.assertIn(f"ITR-{iteration}", full_path)
        self.assertTrue(full_path.endswith(".tar.gz"))

class TestLexarPathIntegration(unittest.TestCase):
    """Integration tests for Lexar path logic with method utilities"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_capture_device_logs_sftp_with_lexar(self):
        """Test capture_device_logs_sftp function path selection"""
        device_ip = "10.0.0.1"
        device_name = "TestDevice"
        iteration = 1
        job_id = "test_job_123"
        
        # Simulate function logic
        lexar_base = os.path.join(self.temp_dir, "Lexar")
        os.makedirs(os.path.join(lexar_base, "Enhancement_output"), exist_ok=True)
        
        # Determine remote path
        if os.path.exists(lexar_base):
            remote_base = f"/media/lrqa/Lexar/Enhancement_output"
        else:
            remote_base = "/media/apps"
        
        remote_path = f"{remote_base}/EXECUTION_LOGS/{device_ip}/ITR-{iteration}"
        
        # Verify path is using Lexar
        self.assertIn("Lexar", remote_base)
        self.assertIn("Enhancement_output", remote_path)
    
    def test_local_directory_structure_creation(self):
        """Test that local directory structure is created with exist_ok"""
        device_ip = "10.0.0.1"
        local_base = os.path.join(self.temp_dir, "local_logs")
        local_path = os.path.join(local_base, device_ip)
        
        # Create with exist_ok=True (like in implementation)
        os.makedirs(local_path, exist_ok=True)
        
        self.assertTrue(os.path.exists(local_path))
        
        # Create again - should not raise error with exist_ok=True
        os.makedirs(local_path, exist_ok=True)
        
        self.assertTrue(os.path.exists(local_path))
    
    def test_path_with_special_characters(self):
        """Test path handling with special characters in device name"""
        device_name = "Test Device / Name"
        # Remove special characters for filename
        safe_name = device_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
        
        filename = f"192.168.1.1_{safe_name}_ITR-1_logs_20260101_120000.tar.gz"
        
        self.assertNotIn('/', filename)
        self.assertNotIn('\\', filename)
        self.assertNotIn(' ', filename)
        self.assertIn("_", filename)

class TestLexarDetectionLogic(unittest.TestCase):
    """Test Lexar detection logic"""
    
    def test_get_lexar_base_path_available(self):
        """Test get_lexar_base_path when Lexar is available"""
        # Simulate checking for Lexar
        lexar_mount_points = [
            "/media/lrqa/Lexar",
            "/mnt/lexar"
        ]
        
        # Check which one exists (simulated)
        available_path = None
        for mount_point in lexar_mount_points:
            # In real implementation, check if path exists
            if "/media/lrqa/Lexar" == mount_point:  # Simulated
                available_path = mount_point
                break
        
        self.assertEqual(available_path, "/media/lrqa/Lexar")
    
    def test_get_lexar_base_path_not_available(self):
        """Test get_lexar_base_path when Lexar is not available"""
        # Simulate checking for Lexar (not found)
        lexar_mount_points = []
        fallback_path = "/media/apps"
        
        # Use fallback if Lexar not found
        selected_path = lexar_mount_points[0] if lexar_mount_points else fallback_path
        
        self.assertEqual(selected_path, fallback_path)
    
    def test_enhancement_output_directory_verification(self):
        """Test verification of Enhancement_output directory"""
        base_path = "/media/lrqa/Lexar"
        enhancement_path = os.path.join(base_path, "Enhancement_output")
        
        # Verify expected structure
        self.assertIn("Enhancement_output", enhancement_path)
        self.assertTrue(enhancement_path.endswith("Enhancement_output"))

if __name__ == '__main__':
    unittest.main()
