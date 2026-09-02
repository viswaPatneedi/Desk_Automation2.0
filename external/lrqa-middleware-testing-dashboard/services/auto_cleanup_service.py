"""
Auto Cleanup Service
====================
Background service that automatically cleans up old logs, screenshots, and job folders.

Usage:
    from services.auto_cleanup_service import AutoCleanupService
    
    # Initialize cleanup service
    cleanup = AutoCleanupService()
    
    # Run cleanup once
    cleanup.run_cleanup()
    
    # Or start background scheduler
    cleanup.start_scheduler()
    
    # Stop scheduler
    cleanup.stop_scheduler()
"""

import os
import json
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
import threading
import time
import subprocess

logger = logging.getLogger(__name__)


class AutoCleanupService:
    """
    Handles automatic cleanup of old logs, screenshots, and job folders
    """
    
    def __init__(self, config=None):
        """
        Initialize cleanup service
        
        Args:
            config: Config module (optional, uses default if not provided)
        """
        if config is None:
            from config.config_auto_cleanup import (
                AUTO_CLEANUP_ENABLED, CLEANUP_RETENTION_DAYS, CLEANUP_PATHS,
                EXCLUDE_PATTERNS, EXCLUDE_FOLDERS, DRY_RUN, VERBOSE,
                MINIMUM_FREE_SPACE_GB, SAFETY_FREE_SPACE_GB, MAX_ITEMS_PER_RUN,
                CLEANUP_LOG_FILE, CLEANUP_INTERVAL_SECONDS
            )
            self.enabled = AUTO_CLEANUP_ENABLED
            self.retention_days = CLEANUP_RETENTION_DAYS
            self.cleanup_paths = CLEANUP_PATHS
            self.exclude_patterns = EXCLUDE_PATTERNS
            self.exclude_folders = EXCLUDE_FOLDERS
            self.dry_run = DRY_RUN
            self.verbose = VERBOSE
            self.min_free_space_gb = MINIMUM_FREE_SPACE_GB
            self.safety_free_space_gb = SAFETY_FREE_SPACE_GB
            self.max_items = MAX_ITEMS_PER_RUN
            self.log_file = CLEANUP_LOG_FILE
            self.interval = CLEANUP_INTERVAL_SECONDS
        else:
            self.enabled = config.AUTO_CLEANUP_ENABLED
            self.retention_days = config.CLEANUP_RETENTION_DAYS
            self.cleanup_paths = config.CLEANUP_PATHS
            self.exclude_patterns = config.EXCLUDE_PATTERNS
            self.exclude_folders = config.EXCLUDE_FOLDERS
            self.dry_run = config.DRY_RUN
            self.verbose = config.VERBOSE
            self.min_free_space_gb = config.MINIMUM_FREE_SPACE_GB
            self.safety_free_space_gb = config.SAFETY_FREE_SPACE_GB
            self.max_items = config.MAX_ITEMS_PER_RUN
            self.log_file = config.CLEANUP_LOG_FILE
            self.interval = config.CLEANUP_INTERVAL_SECONDS
        
        self.threshold_date = datetime.now() - timedelta(days=self.retention_days)
        self.threshold_timestamp = self.threshold_date.timestamp()
        
        # Statistics
        self.stats = {
            'files_deleted': 0,
            'folders_deleted': 0,
            'space_freed_mb': 0,
            'errors': 0,
            'last_run': None,
            'run_count': 0
        }
        
        # Scheduler
        self.scheduler_running = False
        self.scheduler_thread = None
        
        self.log(f"AutoCleanupService initialized (retention: {self.retention_days} days, dry-run: {self.dry_run})")
    
    def log(self, message: str, level: str = 'INFO'):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] [{level}] {message}"
        
        if self.verbose:
            print(log_message)
        
        # Also log to file
        try:
            log_dir = os.path.dirname(self.log_file)
            if not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            
            with open(self.log_file, 'a') as f:
                f.write(log_message + '\n')
        except Exception as e:
            print(f"Error writing to cleanup log: {e}")
    
    def get_free_space_gb(self) -> float:
        """Get free disk space in GB"""
        try:
            result = subprocess.run(['df', '/'], capture_output=True, text=True)
            lines = result.stdout.split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                free_kb = int(parts[3])
                return free_kb / (1024 * 1024)
        except Exception as e:
            self.log(f"Error getting free space: {e}", 'ERROR')
        return 0
    
    def should_run_cleanup(self) -> bool:
        """Check if cleanup should run"""
        if not self.enabled:
            return False
        
        free_space = self.get_free_space_gb()
        if free_space < self.min_free_space_gb:
            self.log(f"Free space ({free_space:.1f}GB) below minimum ({self.min_free_space_gb}GB) - running cleanup", 'WARNING')
            return True
        
        return True  # Run cleanup on schedule
    
    def is_excluded(self, path: str) -> bool:
        """Check if path should be excluded from deletion"""
        name = os.path.basename(path)
        
        # Check exclude folders
        if name in self.exclude_folders:
            return True
        
        # Check exclude patterns
        for pattern in self.exclude_patterns:
            if '*' in pattern:
                # Simple wildcard matching
                import fnmatch
                if fnmatch.fnmatch(name, pattern):
                    return True
            elif name.startswith(pattern):
                return True
        
        return False
    
    def is_old_enough(self, path: str) -> bool:
        """Check if file/folder is older than retention period"""
        try:
            mtime = os.path.getmtime(path)
            return mtime < self.threshold_timestamp
        except Exception as e:
            self.log(f"Error checking file age for {path}: {e}", 'ERROR')
            return False
    
    def delete_item(self, path: str, is_dir: bool = False) -> Tuple[bool, float]:
        """
        Delete file or directory
        
        Returns:
            Tuple of (success, size_in_mb)
        """
        if self.is_excluded(path):
            self.log(f"Skipping excluded item: {path}")
            return False, 0
        
        try:
            # Calculate size before deletion
            if is_dir:
                size = sum(
                    os.path.getsize(os.path.join(dirpath, filename))
                    for dirpath, dirnames, filenames in os.walk(path, onerror=lambda e: None)
                    for filename in filenames
                )
            else:
                size = os.path.getsize(path) if os.path.exists(path) else 0
            
            size_mb = size / (1024 * 1024)
            
            if self.dry_run:
                self.log(f"[DRY-RUN] Would delete: {path} ({size_mb:.2f}MB)")
                return True, size_mb
            
            if is_dir:
                shutil.rmtree(path, ignore_errors=True)
                self.log(f"Deleted folder: {path} ({size_mb:.2f}MB)")
            else:
                os.remove(path)
                self.log(f"Deleted file: {path} ({size_mb:.2f}MB)")
            
            return True, size_mb
        
        except Exception as e:
            self.log(f"Error deleting {path}: {e}", 'ERROR')
            self.stats['errors'] += 1
            return False, 0
    
    def cleanup_logs(self) -> Tuple[int, float]:
        """Clean old log files"""
        if not self.cleanup_paths['logs']['enabled']:
            return 0, 0
        
        self.log("Cleaning up logs...")
        log_dir = self.cleanup_paths['logs']['path']
        
        if not os.path.exists(log_dir):
            self.log(f"Log directory not found: {log_dir}")
            return 0, 0
        
        count = 0
        space_freed = 0
        
        try:
            for filename in os.listdir(log_dir):
                if count >= self.max_items:
                    self.log(f"Reached max items limit ({self.max_items})", 'WARNING')
                    break
                
                filepath = os.path.join(log_dir, filename)
                
                if not os.path.isfile(filepath):
                    continue
                
                if not filename.endswith('.log'):
                    continue
                
                if self.is_old_enough(filepath):
                    success, size = self.delete_item(filepath, is_dir=False)
                    if success:
                        count += 1
                        space_freed += size
        
        except Exception as e:
            self.log(f"Error during log cleanup: {e}", 'ERROR')
        
        self.stats['files_deleted'] += count
        self.stats['space_freed_mb'] += space_freed
        
        self.log(f"Log cleanup: {count} files deleted, {space_freed:.2f}MB freed")
        return count, space_freed
    
    def cleanup_job_logs(self) -> Tuple[int, float]:
        """Clean old job execution folders"""
        if not self.cleanup_paths['job_logs']['enabled']:
            return 0, 0
        
        self.log("Cleaning up old job execution folders...")
        job_logs_dir = self.cleanup_paths['job_logs']['path']
        
        if not os.path.exists(job_logs_dir):
            self.log(f"Job logs directory not found: {job_logs_dir}")
            return 0, 0
        
        count = 0
        space_freed = 0
        
        try:
            for foldername in os.listdir(job_logs_dir):
                if count >= self.max_items:
                    self.log(f"Reached max items limit ({self.max_items})", 'WARNING')
                    break
                
                folderpath = os.path.join(job_logs_dir, foldername)
                
                if not os.path.isdir(folderpath):
                    continue
                
                if self.is_old_enough(folderpath):
                    success, size = self.delete_item(folderpath, is_dir=True)
                    if success:
                        count += 1
                        space_freed += size
        
        except Exception as e:
            self.log(f"Error during job logs cleanup: {e}", 'ERROR')
        
        self.stats['folders_deleted'] += count
        self.stats['space_freed_mb'] += space_freed
        
        self.log(f"Job logs cleanup: {count} folders deleted, {space_freed:.2f}MB freed")
        return count, space_freed
    
    def cleanup_screenshots(self) -> Tuple[int, float]:
        """Clean old screenshot files"""
        if not self.cleanup_paths['screenshots']['enabled']:
            return 0, 0
        
        self.log("Cleaning up old screenshots...")
        screenshots_dir = self.cleanup_paths['screenshots']['path']
        
        if not os.path.exists(screenshots_dir):
            self.log(f"Screenshots directory not found: {screenshots_dir}")
            return 0, 0
        
        count = 0
        space_freed = 0
        
        try:
            for filename in os.listdir(screenshots_dir):
                if count >= self.max_items:
                    self.log(f"Reached max items limit ({self.max_items})", 'WARNING')
                    break
                
                filepath = os.path.join(screenshots_dir, filename)
                
                if not os.path.isfile(filepath):
                    continue
                
                if not filename.endswith('.png'):
                    continue
                
                if self.is_old_enough(filepath):
                    success, size = self.delete_item(filepath, is_dir=False)
                    if success:
                        count += 1
                        space_freed += size
        
        except Exception as e:
            self.log(f"Error during screenshots cleanup: {e}", 'ERROR')
        
        self.stats['files_deleted'] += count
        self.stats['space_freed_mb'] += space_freed
        
        self.log(f"Screenshots cleanup: {count} files deleted, {space_freed:.2f}MB freed")
        return count, space_freed
    
    def cleanup_enhancement_output(self) -> Tuple[int, float]:
        """Clean old Enhancement_output session folders"""
        if not self.cleanup_paths['enhancement_output']['enabled']:
            return 0, 0
        
        self.log("Cleaning up old Enhancement_output sessions...")
        output_dir = self.cleanup_paths['enhancement_output']['path']
        
        if not os.path.exists(output_dir):
            self.log(f"Enhancement_output directory not found: {output_dir}")
            return 0, 0
        
        count = 0
        space_freed = 0
        
        try:
            for foldername in os.listdir(output_dir):
                if count >= self.max_items:
                    self.log(f"Reached max items limit ({self.max_items})", 'WARNING')
                    break
                
                folderpath = os.path.join(output_dir, foldername)
                
                if not os.path.isdir(folderpath):
                    continue

                # New execution results are nested by team, user, date, and device.
                # Delete complete sequence folders based on their own age.
                if foldername == 'EXECUTION_RESULTS':
                    for root, dirnames, _ in os.walk(folderpath, topdown=False):
                        for dirname in dirnames:
                            sequence_path = os.path.join(root, dirname)
                            if 'ITERATION_' not in ''.join(os.listdir(sequence_path)):
                                continue
                            if count >= self.max_items:
                                break
                            if self.is_old_enough(sequence_path):
                                success, size = self.delete_item(sequence_path, is_dir=True)
                                if success:
                                    count += 1
                                    space_freed += size
                    continue
                
                if self.is_old_enough(folderpath):
                    success, size = self.delete_item(folderpath, is_dir=True)
                    if success:
                        count += 1
                        space_freed += size
        
        except Exception as e:
            self.log(f"Error during Enhancement_output cleanup: {e}", 'ERROR')
        
        self.stats['folders_deleted'] += count
        self.stats['space_freed_mb'] += space_freed
        
        self.log(f"Enhancement_output cleanup: {count} folders deleted, {space_freed:.2f}MB freed")
        return count, space_freed
    
    def run_cleanup(self) -> Dict:
        """
        Run all cleanup operations
        
        Returns:
            Dictionary with cleanup statistics
        """
        if not self.enabled:
            self.log("Auto cleanup is disabled")
            return self.stats
        
        if not self.should_run_cleanup():
            self.log("Cleanup conditions not met (skipping)")
            return self.stats
        
        self.log("="*80)
        self.log("STARTING AUTO CLEANUP")
        self.log("="*80)
        
        start_time = time.time()
        free_space_before = self.get_free_space_gb()
        
        self.log(f"Free space before: {free_space_before:.2f}GB")
        self.log(f"Retention threshold: {self.threshold_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run cleanup tasks
        self.cleanup_logs()
        self.cleanup_job_logs()
        self.cleanup_screenshots()
        self.cleanup_enhancement_output()
        
        # Check if we're still above safety threshold
        free_space_after = self.get_free_space_gb()
        if free_space_after < self.safety_free_space_gb:
            self.log(f"WARNING: Free space ({free_space_after:.2f}GB) below safety threshold ({self.safety_free_space_gb}GB)", 'WARNING')
        
        elapsed = time.time() - start_time
        
        self.log("="*80)
        self.log("CLEANUP SUMMARY")
        self.log("="*80)
        self.log(f"Files deleted: {self.stats['files_deleted']}")
        self.log(f"Folders deleted: {self.stats['folders_deleted']}")
        self.log(f"Space freed: {self.stats['space_freed_mb']:.2f}MB")
        self.log(f"Errors: {self.stats['errors']}")
        self.log(f"Duration: {elapsed:.2f}s")
        self.log(f"Free space before: {free_space_before:.2f}GB")
        self.log(f"Free space after: {free_space_after:.2f}GB")
        self.log(f"Space gained: {(free_space_after - free_space_before):.2f}GB")
        self.log("="*80)
        
        self.stats['last_run'] = datetime.now().isoformat()
        self.stats['run_count'] += 1
        
        return self.stats
    
    def start_scheduler(self, interval_seconds: int = None):
        """Start background cleanup scheduler"""
        if interval_seconds is None:
            interval_seconds = self.interval
        
        if self.scheduler_running:
            self.log("Scheduler already running")
            return
        
        self.scheduler_running = True
        self.scheduler_thread = threading.Thread(
            target=self._scheduler_worker,
            args=(interval_seconds,),
            daemon=True
        )
        self.scheduler_thread.start()
        self.log(f"Cleanup scheduler started (interval: {interval_seconds}s)")
    
    def _scheduler_worker(self, interval_seconds: int):
        """Background worker for cleanup scheduler"""
        while self.scheduler_running:
            try:
                self.run_cleanup()
            except Exception as e:
                self.log(f"Scheduler error: {e}", 'ERROR')
            
            # Sleep in intervals to allow for quick shutdown
            for _ in range(int(interval_seconds)):
                if not self.scheduler_running:
                    break
                time.sleep(1)
    
    def stop_scheduler(self):
        """Stop background cleanup scheduler"""
        if not self.scheduler_running:
            return
        
        self.scheduler_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        
        self.log("Cleanup scheduler stopped")
    
    def get_stats(self) -> Dict:
        """Get cleanup statistics"""
        return self.stats.copy()


# Global cleanup service instance
_cleanup_service = None


def get_cleanup_service() -> AutoCleanupService:
    """Get or create global cleanup service instance"""
    global _cleanup_service
    
    if _cleanup_service is None:
        _cleanup_service = AutoCleanupService()
    
    return _cleanup_service


def initialize_cleanup_service():
    """Initialize cleanup service (called on app startup)"""
    try:
        from config.config_auto_cleanup import CLEANUP_ON_STARTUP, RUN_ON_STARTUP
        
        cleanup = get_cleanup_service()
        
        if CLEANUP_ON_STARTUP or RUN_ON_STARTUP:
            cleanup.log("Running cleanup on startup...")
            cleanup.run_cleanup()
            cleanup.start_scheduler()
        else:
            cleanup.log("Cleanup on startup disabled, starting scheduler only...")
            cleanup.start_scheduler()
    
    except Exception as e:
        logger.error(f"Error initializing cleanup service: {e}")


if __name__ == '__main__':
    # Manual testing
    cleanup = AutoCleanupService()
    cleanup.run_cleanup()
