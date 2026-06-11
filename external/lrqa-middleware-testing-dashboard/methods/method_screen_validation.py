#!/usr/bin/env python3
"""
Screen Validation Method
Captures screenshot and validates against expected screen using layout comparison.
This method can be called multiple times in the same execution to verify device screen state.
"""

import paramiko
import os
import time
import traceback
from typing import Dict, Optional
from datetime import datetime, timezone
from screen_validator_lightweight import LightweightScreenValidator
from config.config_screen_validation import SCREEN_DEFINITIONS, SCREEN_VALIDATION_CONFIG

# Initialize screen validator
validator = LightweightScreenValidator(reference_dir="reference_screens")

def capture_screenshot_ssh(device_ip: str, port: int, username: str, password: str) -> Optional[str]:
    """
    Capture screenshot from device via SSH using Thunder API ScreenCapture plugin.
    
    Returns:
        str: Local path to captured screenshot, or None if failed
    """
    ssh = None
    try:
        # Import required modules
        import requests
        from config.config_screenshot import rpc_url, upload_base_url, download_base_url, screenshot_upload_timeout, screenshot_download_timeout
        from utils.screenshot_utils import activate_screencapture_plugin
        
        # Create SSH connection
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(device_ip, port=port, username=username, password=password, timeout=15)
        
        # Activate ScreenCapture plugin
        activate_success, _ = activate_screencapture_plugin(ssh, print)
        
        # Generate unique filename
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        upload_filename = f"validation_{device_ip.replace('.', '_')}_{timestamp}.png"
        upload_url = f"{upload_base_url}?filename={upload_filename}"
        download_url = f"{download_base_url}{upload_filename}"
        
        # Execute screenshot command via Thunder API
        screenshot_command = f"curl -k -d '{{\"jsonrpc\":\"2.0\",\"id\":\"3\",\"method\": \"org.rdk.ScreenCapture.1.uploadScreenCapture\", \"params\" : {{\"url\": \"{upload_url}\"}}}}' {rpc_url}"
        
        stdin, stdout, stderr = ssh.exec_command(screenshot_command)
        screenshot_response = stdout.read().decode('utf-8', errors='ignore')
        
        print(f"Screenshot upload initiated: {screenshot_response}")
        print(f"Waiting {screenshot_upload_timeout} seconds for upload...")
        time.sleep(screenshot_upload_timeout)
        
        # Download screenshot from server with retry
        print(f"Downloading from {download_url}...")
        
        max_retries = 3
        retry_delays = [0, 5, 10]
        response = None
        
        for attempt in range(max_retries):
            if attempt > 0:
                delay = retry_delays[attempt]
                print(f"Retry {attempt}/{max_retries-1}: Waiting {delay}s...")
                time.sleep(delay)
            
            try:
                response = requests.get(download_url, stream=True, verify=False, timeout=screenshot_download_timeout)
                if response.status_code == 200:
                    break
                else:
                    print(f"⚠ HTTP {response.status_code} on attempt {attempt + 1}")
            except Exception as req_err:
                print(f"⚠ Request error on attempt {attempt + 1}: {req_err}")
        
        if not response or response.status_code != 200:
            print(f"❌ Failed to download screenshot after {max_retries} attempts")
            return None
        
        # Save screenshot locally
        local_dir = f"screenshots/{device_ip.replace('.', '_')}_validation"
        os.makedirs(local_dir, exist_ok=True)
        local_path = f"{local_dir}/validation_{timestamp}.png"
        
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"✓ Screenshot saved: {local_path}")
        return local_path
        
    except Exception as e:
        print(f"Screenshot capture failed: {str(e)}")
        return None
    finally:
        if ssh:
            try:
                ssh.close()
            except:
                pass

def validate_screen(device_ip: str, expected_screen: str, 
                   port: int = 10022, username: str = "root", password: str = "") -> Dict:
    """
    Capture screenshot and validate against expected screen layout.
    
    This method can be called multiple times in the same execution without conflicts.
    Each call creates a new SSH connection, captures a screenshot, and validates independently.
    
    Args:
        device_ip: IP address of the target device
        expected_screen: Expected screen name (e.g., "HOME", "NETFLIX_HOME", "YOUTUBE_HOME")
        port: SSH port (default: 10022)
        username: SSH username (default: "root")
        password: SSH password (default: "")
    
    Returns:
        Dict with fields:
            - success (bool): Validation passed or failed
            - message (str): Detailed result message
            - screenshot_path (str): Path to captured screenshot
            - expected_screen (str): Expected screen name
            - validation_result (dict): Detailed validation metrics
    
    Examples:
        # Validate device is on home screen
        result = validate_screen("10.0.0.126", "HOME")
        
        # Validate Netflix home screen
        result = validate_screen("10.0.0.126", "NETFLIX_HOME")
        
        # Multiple calls in same execution (no conflicts)
        validate_screen("10.0.0.126", "HOME")
        # ... perform some actions ...
        validate_screen("10.0.0.126", "NETFLIX_HOME")
    """
    
    # Validate expected_screen is defined or has reference image
    # Check if it's a predefined screen or if a reference image exists
    reference_dir = "reference_screens"
    custom_reference = None
    
    if expected_screen not in SCREEN_DEFINITIONS:
        # Check for custom reference image in main directory and subdirectories
        possible_files = [
            f"{expected_screen}.png",
            f"{expected_screen.lower()}.png",
            f"{expected_screen.replace('_', '')}.png",
            f"{expected_screen.replace('-', '_')}.png",
            f"{expected_screen.upper()}.png"
        ]
        
        # Search in main reference_screens directory
        for filename in possible_files:
            ref_path = os.path.join(reference_dir, filename)
            if os.path.exists(ref_path):
                custom_reference = ref_path
                print(f"📋 Found custom reference image: {ref_path}")
                break
        
        # If not found, search in subdirectories with flexible matching
        if not custom_reference:
            import re
            best_match = None
            best_match_score = 0
            
            # Extract number and content from expected screen
            expected_match = re.search(r'^(\d+)-(.+)$', expected_screen)
            expected_number = expected_match.group(1) if expected_match else None
            expected_content = expected_match.group(2) if expected_match else expected_screen
            
            # Folders to exclude from search
            excluded_folders = ['Unused_Images', 'Unused_Images_DO_NOT_MERGE', 'backup', 'old']
            
            print(f"🔍 [VALIDATION] Searching for: {expected_screen}")
            if expected_number:
                print(f"   [VALIDATION] Extracted - Number: {expected_number}, Content: {expected_content}")
            
            for root, dirs, files in os.walk(reference_dir):
                # Skip excluded folders
                dirs[:] = [d for d in dirs if not any(excl.lower() in d.lower() for excl in excluded_folders)]
                for filename in files:
                    if filename.endswith('.png'):
                        base_name = os.path.splitext(filename)[0]
                        
                        # Strategy 1: Exact match (with and without special chars)
                        clean_base = base_name.replace('_', '').replace('-', '').upper()
                        clean_expected = expected_screen.replace('_', '').replace('-', '').upper()
                        
                        if clean_base == clean_expected or base_name.upper() == expected_screen.upper():
                            custom_reference = os.path.join(root, filename)
                            print(f"📋 Found custom reference image in subfolder: {custom_reference}")
                            break
                        
                        # Strategy 2: For numbered screens, match by content if number doesn't match
                        file_match = re.search(r'^(\d+)-(.+)$', base_name)
                        if expected_number and file_match:
                            file_number = file_match.group(1)
                            file_content = file_match.group(2)
                            
                            # Clean content for comparison (remove special chars, compare case-insensitive)
                            clean_file_content = file_content.replace('_', '').replace('-', '').upper()
                            clean_expected_content = expected_content.replace('_', '').replace('-', '').upper()
                            
                            # If content matches, this is a good candidate
                            if clean_file_content == clean_expected_content:
                                # Exact content match - use this file even if number differs
                                custom_reference = os.path.join(root, filename)
                                print(f"📋 Found custom reference image in subfolder (matched by content): {custom_reference}")
                                print(f"   Note: File is numbered {file_number} but sequence expects {expected_number}")
                                break
                            
                            # Partial content match - calculate similarity
                            elif len(clean_expected_content) > 5 and clean_expected_content in clean_file_content:
                                similarity = len(clean_expected_content) / len(clean_file_content)
                                if similarity > best_match_score:
                                    best_match_score = similarity
                                    best_match = os.path.join(root, filename)
                
                if custom_reference:
                    break
            
            # If no exact match but found a good partial match, use it
            if not custom_reference and best_match and best_match_score > 0.7:
                custom_reference = best_match
                print(f"📋 Found custom reference image in subfolder (partial match {best_match_score:.0%}): {custom_reference}")
            
            if custom_reference:
                print(f"✅ [VALIDATION] Match found: {os.path.basename(custom_reference)}")
            else:
                print(f"❌ [VALIDATION] No match found for: {expected_screen}")
        
        if not custom_reference:
            available_screens = ", ".join(SCREEN_DEFINITIONS.keys())
            return {
                "success": False,
                "message": f"Invalid screen name '{expected_screen}'. No reference image found and not in predefined screens. Available predefined: {available_screens}",
                "screenshot_path": None,
                "expected_screen": expected_screen,
                "validation_result": None
            }
    
    # Check if screen validation is enabled
    if not SCREEN_VALIDATION_CONFIG.get('enabled', True):
        return {
            "success": False,
            "message": "Screen validation is disabled in config",
            "screenshot_path": None,
            "expected_screen": expected_screen,
            "validation_result": None
        }
    
    try:
        # Step 1: Capture screenshot
        print(f"📸 Capturing screenshot from {device_ip}...")
        screenshot_path = capture_screenshot_ssh(device_ip, port, username, password)
        
        if not screenshot_path:
            return {
                "success": False,
                "message": "Failed to capture screenshot from device",
                "screenshot_path": None,
                "expected_screen": expected_screen,
                "validation_result": None
            }
        
        print(f"✓ Screenshot captured: {screenshot_path}")
        
        # Step 2: Validate against expected screen
        print(f"🔍 Validating against expected screen: {expected_screen}...")
        
        # If using custom reference, validate directly against it
        if custom_reference:
            print(f"📋 Using custom reference image: {custom_reference}")
            try:
                validation_result = validator.validate_against_reference(
                    screenshot_path=screenshot_path,
                    reference_path=custom_reference,
                    method="hybrid"  # Use hybrid method (pHash + SSIM + template matching)
                )
                # Log validation details for debugging
                print(f"🔬 Validation details: {validation_result.get('details', {})}")
                if 'error' in validation_result:
                    print(f"⚠️ Validation error: {validation_result['error']}")
            except Exception as val_err:
                print(f"❌ Exception during validation: {str(val_err)}")
                print(f"📋 Traceback: {traceback.format_exc()}")
                validation_result = {
                    'is_match': False,
                    'confidence': 0.0,
                    'error': str(val_err),
                    'method': 'hybrid'
                }
        else:
            # Use predefined screen validation
            try:
                validation_result = validator.validate_screen(
                    screenshot_path=screenshot_path,
                    expected_screen=expected_screen,
                    method="hybrid"  # Use hybrid method (pHash + SSIM + template matching)
                )
                print(f"🔬 Validation details: {validation_result.get('details', {})}")
                if 'error' in validation_result:
                    print(f"⚠️ Validation error: {validation_result['error']}")
            except Exception as val_err:
                print(f"❌ Exception during validation: {str(val_err)}")
                print(f"📋 Traceback: {traceback.format_exc()}")
                validation_result = {
                    'is_match': False,
                    'confidence': 0.0,
                    'error': str(val_err),
                    'method': 'hybrid'
                }
        
        # Step 3: Interpret results
        is_match = validation_result.get('is_match', False)
        confidence = validation_result.get('confidence', 0.0)
        method_used = validation_result.get('method', 'unknown')
        
        if is_match:
            message = f"✓ Screen validation PASSED: Device is on {expected_screen} (confidence: {confidence:.2%}, method: {method_used})"
            success = True
        else:
            message = f"✗ Screen validation FAILED: Device is NOT on {expected_screen} (confidence: {confidence:.2%}, method: {method_used})"
            success = False
        
        print(message)
        
        return {
            "success": success,
            "message": message,
            "screenshot_path": screenshot_path,
            "expected_screen": expected_screen,
            "validation_result": validation_result
        }
        
    except Exception as e:
        error_msg = f"Screen validation error: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        return {
            "success": False,
            "message": error_msg,
            "screenshot_path": screenshot_path if 'screenshot_path' in locals() else None,
            "expected_screen": expected_screen,
            "validation_result": None
        }

def get_available_screens() -> Dict[str, str]:
    """
    Get list of available screen definitions for validation.
    
    Returns:
        Dict mapping screen names to their descriptions
    """
    return {
        name: config['description'] 
        for name, config in SCREEN_DEFINITIONS.items()
    }

# Example usage and testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python method_screen_validation.py <device_ip> <expected_screen>")
        print("\nAvailable screens:")
        for name, desc in get_available_screens().items():
            print(f"  - {name}: {desc}")
        sys.exit(1)
    
    device_ip = sys.argv[1]
    expected_screen = sys.argv[2]
    
    print(f"\n=== Screen Validation Test ===")
    print(f"Device: {device_ip}")
    print(f"Expected Screen: {expected_screen}")
    print("=" * 40)
    
    result = validate_screen(device_ip, expected_screen)
    
    print("\n=== Validation Result ===")
    print(f"Success: {result['success']}")
    print(f"Message: {result['message']}")
    print(f"Screenshot: {result['screenshot_path']}")
    print(f"Validation Details: {result['validation_result']}")
