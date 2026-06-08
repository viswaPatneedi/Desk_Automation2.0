#!/usr/bin/env python3
"""
USB Storage Manager - Auto-detects and manages external USB storage

Features:
- Auto-detects USB drives on Linux (desktop and R-PI)
- Supports multiple USB paths (Lexar, USB, etc.)
- Creates necessary directory structure on USB
- Handles fallback to local storage
- Provides configuration for Docker volume mounts
- Thread-safe operations
"""

import os
import sys
import shutil
import json
from pathlib import Path
from typing import Optional, Dict, Tuple
from datetime import datetime, timezone


class USBStorageManager:
    """Manages USB storage detection and configuration"""
    
    # Possible USB mount locations on Linux desktop
    LINUX_DESKTOP_USB_PATHS = [
        '/media/lrqa/Lexar',           # Current user desktop setup
        '/media/lrqa/USB',
        '/media/$(whoami)/Lexar',
        '/media/*/Lexar',              # Any user
        '/mnt/usb',
        '/mnt/usb_storage',
        '/mnt/external',
    ]
    
    # Possible USB mount locations on R-PI
    RPI_USB_PATHS = [
        '/mnt/usb',
        '/mnt/usb_storage',
        '/media/pi/Lexar',             # Pi user (official Raspi OS)
        '/media/pi/USB',
        '/media/root/Lexar',           # Root user
        '/media/root/USB',
        '/media/usb',
        '/media/lrqa/Lexar',           # Desktop user (for testing)
        '/media/lrqa/USB',
    ]
    
    # Required subdirectories for execution data
    REQUIRED_DIRS = [
        'screenshots',
        'iteration_logs',
        'execution_logs',
        'device_logs',
        'app_logs',
        'sessions',
    ]
    
    def __init__(self, enable_logging: bool = True):
        """
        Initialize USB Storage Manager
        
        Args:
            enable_logging: Whether to print debug information
        """
        self.enable_logging = enable_logging
        self.usb_path: Optional[str] = None
        self.storage_root: Optional[str] = None
        self.is_usb_available: bool = False
        self.detected_system: str = self._detect_system()
        
        # Auto-detect USB on initialization
        self._detect_usb()
    
    def _detect_system(self) -> str:
        """Detect system type"""
        if sys.platform.startswith('linux'):
            # Check if running on R-PI
            if os.path.exists('/proc/device-tree/model'):
                return 'rpi'
            else:
                return 'linux_desktop'
        elif sys.platform.startswith('darwin'):
            return 'macos'
        elif sys.platform.startswith('win'):
            return 'windows'
        else:
            return 'unknown'
    
    def _print(self, message: str):
        """Print log message if logging enabled"""
        if self.enable_logging:
            timestamp = datetime.now(timezone.utc).strftime('[%Y-%m-%d %H:%M:%S UTC]')
            print(f"{timestamp} [USB Storage] {message}")
    
    def _detect_usb(self):
        """Detect available USB storage"""
        self._print(f"Detecting USB storage (System: {self.detected_system})...")
        
        paths_to_check = self.RPI_USB_PATHS if self.detected_system == 'rpi' else self.LINUX_DESKTOP_USB_PATHS
        
        for usb_path in paths_to_check:
            # Expand wildcards
            if '*' in usb_path:
                # For wildcard paths, try to find matching directories
                pattern_dir = os.path.dirname(usb_path)
                if os.path.exists(pattern_dir):
                    for entry in os.listdir(pattern_dir):
                        full_path = os.path.join(pattern_dir, entry)
                        if os.path.isdir(full_path) and self._is_valid_usb(full_path):
                            self.usb_path = full_path
                            break
            else:
                # Normal path check
                if os.path.exists(usb_path) and self._is_valid_usb(usb_path):
                    self.usb_path = usb_path
                    break
            
            if self.usb_path:
                break
        
        if self.usb_path:
            self.is_usb_available = True
            self.storage_root = self.usb_path  # Changed: don't add /enhancement_data here
            self._print(f"✓ USB detected at: {self.usb_path}")
            self._print(f"  Storage root: {self.storage_root}")
        else:
            self.is_usb_available = False
            self.storage_root = 'Enhancement_output'  # Fallback to local
            self._print(f"⚠ USB not detected, using local storage: {self.storage_root}")
    
    def _is_valid_usb(self, path: str) -> bool:
        """Check if path is a valid, writable USB storage"""
        try:
            # Check if path exists and is a directory
            if not os.path.isdir(path):
                return False
            
            # Check if we can write to it
            test_file = os.path.join(path, '.usb_test_write')
            try:
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                return True
            except (IOError, OSError):
                return False
        except Exception:
            return False
    
    def setup_storage_directories(self) -> bool:
        """
        Create necessary directory structure for execution data
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self._print(f"Setting up storage directories at: {self.storage_root}")
            
            for subdir in self.REQUIRED_DIRS:
                full_path = os.path.join(self.storage_root, subdir)
                os.makedirs(full_path, exist_ok=True)
                self._print(f"  ✓ Created: {full_path}")
            
            # Create symlink for easy access (on Linux)
            if sys.platform.startswith('linux'):
                symlink_path = '/app/data'
                if not os.path.exists(symlink_path):
                    try:
                        os.symlink(self.storage_root, symlink_path)
                        self._print(f"  ✓ Created symlink: {symlink_path} -> {self.storage_root}")
                    except (OSError, Exception) as e:
                        self._print(f"  ⚠ Could not create symlink: {e}")
            
            # Write configuration file
            self._write_storage_config()
            
            return True
        except Exception as e:
            self._print(f"✗ Error setting up storage directories: {e}")
            return False
    
    def _write_storage_config(self):
        """Write storage configuration to JSON file"""
        config = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'system': self.detected_system,
            'usb_available': self.is_usb_available,
            'storage_root': self.storage_root,
            'usb_path': self.usb_path,
            'directories': {
                'screenshots': os.path.join(self.storage_root, 'screenshots'),
                'iteration_logs': os.path.join(self.storage_root, 'iteration_logs'),
                'execution_logs': os.path.join(self.storage_root, 'execution_logs'),
                'device_logs': os.path.join(self.storage_root, 'device_logs'),
                'app_logs': os.path.join(self.storage_root, 'app_logs'),
            }
        }
        
        config_file = os.path.join(self.storage_root, 'storage_config.json')
        try:
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            self._print(f"  ✓ Storage config written: {config_file}")
        except Exception as e:
            self._print(f"  ⚠ Could not write storage config: {e}")
    
    def get_storage_paths(self) -> Dict[str, str]:
        """
        Get all storage paths
        
        Returns:
            Dictionary with storage paths for different data types
        """
        return {
            'root': self.storage_root,
            'screenshots': os.path.join(self.storage_root, 'screenshots'),
            'iteration_logs': os.path.join(self.storage_root, 'iteration_logs'),
            'execution_logs': os.path.join(self.storage_root, 'execution_logs'),
            'device_logs': os.path.join(self.storage_root, 'device_logs'),
            'app_logs': os.path.join(self.storage_root, 'app_logs'),
        }
    
    def get_health_status(self) -> Dict:
        """
        Get health status of storage
        
        Returns:
            Dictionary with health information
        """
        status = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'system': self.detected_system,
            'usb_available': self.is_usb_available,
            'usb_path': self.usb_path,
            'storage_root': self.storage_root,
        }
        
        # Check disk space if possible
        if os.path.exists(self.storage_root):
            try:
                stat = shutil.disk_usage(self.storage_root)
                status['disk_total_gb'] = stat.total / (1024**3)
                status['disk_used_gb'] = stat.used / (1024**3)
                status['disk_free_gb'] = stat.free / (1024**3)
                status['disk_percent_used'] = (stat.used / stat.total) * 100
            except Exception as e:
                status['disk_error'] = str(e)
        
        # Check if storage is writable
        try:
            test_file = os.path.join(self.storage_root, '.health_check')
            with open(test_file, 'w') as f:
                f.write('healthy')
            os.remove(test_file)
            status['writable'] = True
        except Exception:
            status['writable'] = False
        
        return status
    
    def create_execution_folder(self, method: str, device_name: str, device_ip: str, 
                               iterations: int) -> Tuple[str, str, str, str]:
        """
        Create execution session folder structure
        
        Args:
            method: Method name
            device_name: Device name
            device_ip: Device IP address
            iterations: Number of iterations
        
        Returns:
            Tuple of (session_folder, screenshots_dir, execution_logs_dir, device_logs_dir)
        """
        # Create safe folder names
        safe_device_name = device_name.replace(' ', '-').replace('/', '_').upper()
        safe_ip = device_ip.replace('.', '-')
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_UTC')
        
        session_name = f"{method}_{safe_device_name}_{safe_ip}_{iterations}_ITR_{timestamp}"
        
        # Truncate if too long (filesystem limit is typically 255 chars)
        if len(session_name) > 200:
            session_name = f"{method[:50]}_{safe_device_name[:30]}_{safe_ip}_{iterations}_ITR_{timestamp}"
        
        # Create directories
        session_folder = os.path.join(self.storage_root, 'sessions', session_name)
        screenshots_dir = os.path.join(session_folder, 'screenshots')
        execution_logs_dir = os.path.join(session_folder, 'execution_logs')
        device_logs_dir = os.path.join(session_folder, 'device_logs')
        
        for folder in [session_folder, screenshots_dir, execution_logs_dir, device_logs_dir]:
            os.makedirs(folder, exist_ok=True)
        
        return session_folder, screenshots_dir, execution_logs_dir, device_logs_dir


# Singleton instance for application-wide use
_storage_manager: Optional[USBStorageManager] = None


def get_storage_manager(enable_logging: bool = True) -> USBStorageManager:
    """Get or create singleton USB storage manager"""
    global _storage_manager
    if _storage_manager is None:
        _storage_manager = USBStorageManager(enable_logging=enable_logging)
    return _storage_manager


def initialize_storage(enable_setup: bool = True) -> USBStorageManager:
    """
    Initialize USB storage for the application
    
    Args:
        enable_setup: Whether to create necessary directories
    
    Returns:
        USBStorageManager instance
    """
    manager = get_storage_manager()
    
    if enable_setup:
        manager.setup_storage_directories()
    
    # Print health status
    health = manager.get_health_status()
    print("\n" + "="*60)
    print("USB STORAGE STATUS")
    print("="*60)
    print(f"System: {health['system']}")
    print(f"USB Available: {'✓ Yes' if health['usb_available'] else '❌ No'}")
    print(f"Storage Root: {health['storage_root']}")
    if 'disk_free_gb' in health:
        print(f"Disk Free: {health['disk_free_gb']:.1f} GB")
        print(f"Disk Used: {health['disk_percent_used']:.1f}%")
    print(f"Writable: {'✓ Yes' if health['writable'] else '❌ No'}")
    print("="*60 + "\n")
    
    return manager


if __name__ == '__main__':
    # Test the USB storage manager
    manager = initialize_storage(enable_setup=True)
    
    print("\nStorage Paths:")
    for key, path in manager.get_storage_paths().items():
        print(f"  {key}: {path}")
