#!/usr/bin/env python3
"""
Wait Method
Pauses execution for a specified duration before proceeding to the next method.
Useful for waiting for UI animations, loading screens, or allowing device to settle.
"""

import time
from typing import Dict, Callable, Optional


def wait_duration(
    wait_seconds: int,
    log_callback: Optional[Callable] = None
) -> Dict:
    """
    Wait for a specified number of seconds before proceeding.
    
    This method:
    1. Validates the wait duration
    2. Waits with progress updates
    3. Returns success when complete
    
    Args:
        wait_seconds: Number of seconds to wait (minimum 1 second, no maximum limit)
        log_callback: Optional function for logging progress
    
    Returns:
        Dict with fields:
            - success (bool): Always True if wait completes
            - message (str): Summary of wait duration
            - waited_seconds (int): Actual seconds waited
    
    Example:
        # Wait 5 seconds
        result = wait_duration(5, log_callback=print)
        
        # Wait 30 seconds
        result = wait_duration(30)
    """
    
    def log(message):
        """Helper to log messages"""
        print(message)
        if log_callback:
            log_callback(message)
    
    try:
        # Validate wait duration
        if not isinstance(wait_seconds, (int, float)):
            return {
                "success": False,
                "message": "Wait duration must be a number",
                "waited_seconds": 0
            }
        
        wait_seconds = int(wait_seconds)
        
        if wait_seconds < 1:
            return {
                "success": False,
                "message": "Wait duration must be at least 1 second",
                "waited_seconds": 0
            }
        
        log(f"⏳ Waiting for {wait_seconds} seconds...")
        
        # Wait with progress updates for longer durations
        if wait_seconds <= 5:
            # Short wait - just wait
            time.sleep(wait_seconds)
        elif wait_seconds <= 30:
            # Medium wait - update every 5 seconds
            elapsed = 0
            while elapsed < wait_seconds:
                chunk = min(5, wait_seconds - elapsed)
                time.sleep(chunk)
                elapsed += chunk
                if elapsed < wait_seconds:
                    remaining = wait_seconds - elapsed
                    log(f"   ⏱️  {elapsed}s elapsed, {remaining}s remaining...")
        else:
            # Long wait - update every 10 seconds
            elapsed = 0
            while elapsed < wait_seconds:
                chunk = min(10, wait_seconds - elapsed)
                time.sleep(chunk)
                elapsed += chunk
                if elapsed < wait_seconds:
                    remaining = wait_seconds - elapsed
                    log(f"   ⏱️  {elapsed}s elapsed, {remaining}s remaining...")
        
        log(f"✅ Wait complete - {wait_seconds} seconds elapsed")
        
        return {
            "success": True,
            "message": f"Successfully waited {wait_seconds} seconds",
            "waited_seconds": wait_seconds
        }
    
    except KeyboardInterrupt:
        return {
            "success": False,
            "message": "Wait interrupted by user",
            "waited_seconds": 0
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error during wait: {str(e)}",
            "waited_seconds": 0
        }


# Example usage and testing
if __name__ == "__main__":
    print("Test 1: Wait 3 seconds")
    result = wait_duration(3)
    print(f"Result: {result}\n")
    
    print("Test 2: Wait 10 seconds with progress")
    result = wait_duration(10)
    print(f"Result: {result}\n")
    
    print("Test 3: Invalid duration")
    result = wait_duration(0)
    print(f"Result: {result}\n")
