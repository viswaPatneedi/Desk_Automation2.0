# New method: validate_available_inputs_on_screen
def validate_available_inputs_on_screen(ssh, device_ip, log_callback=None, screenshot_folder='screenshots', reference_folder='reference_inputs', input_names=None, right_key_callback=None, max_icons=12):
    """
    Validate all available input icons on the TV screen WITHOUT downloading screenshots per tile.
    Uses ONLY the validation without full captures during the loop.
    
    Strategy: Only take ONE screenshot and validate it; for tile navigation, query device state without downloads.
    
    Args:
        ssh: Active SSH connection to the device
        device_ip: IP address of the device
        log_callback: Optional function to call for logging
        screenshot_folder: Not used (for compatibility)
        reference_folder: Not used (for compatibility)
        input_names: List of expected input names
        right_key_callback: Function to send RIGHT key to device
        max_icons: Max number of icons to check
    
    Returns:
        dict: { 'found': [inputs], 'not_found': [inputs], 'details': {input: result} }
    """
    import time
    from config.config_screenshot import rpc_url

    if input_names is None:
        input_names = ["ANTENNA", "HDMI 1", "HDMI 2", "HDMI 3", "COMPOSITE", "AIRPLAY", "USB", "SCREEN MIRRORING"]

    found = set()
    not_found = set(input_names)
    details = {}
    checked_inputs = set()

    def log(msg):
        if log_callback:
            log_callback(msg)

    log("[INPUT-VALIDATION] Starting LIGHTWEIGHT validation (no per-tile downloads)")
    log(f"[INPUT-VALIDATION] Expected inputs: {', '.join(input_names)}")

    # Mapping from detected screen names to input names (from AI validation)
    screen_to_input_map = {
        'InputScreens_XUMO-TV_INPUT_SCREEN_ANTENNA': 'ANTENNA',
        'InputScreens_XUMO-TV_INPUT_SCREEN_ANTEENA': 'ANTENNA',
        'InputScreens_XUMO-TV_INPUT_SCREEN_HDMI_1': 'HDMI 1',
        'InputScreens_XUMO-TV_INPUT_SCREEN_HDMI_2': 'HDMI 2',
        'InputScreens_XUMO-TV_INPUT_SCREEN_HDMI_3': 'HDMI 3',
        'InputScreens_XUMO-TV_INPUT_SCREEN_COMPOSITE': 'COMPOSITE',
        'InputScreens_XUMO-TV_INPUT_SCREEN_AIRPLAY': 'AIRPLAY',
        'InputScreens_XUMO-TV_INPUT_SCREEN_USB': 'USB',
        'InputScreens_XUMO-TV_INPUT_SCREEN_SCREEN-MIRRORING': 'SCREEN MIRRORING',
        'InputScreens_XUMO-TV_INPUT_SCREEN_SCREEN_MIRRORING': 'SCREEN MIRRORING',
    }

    for idx in range(max_icons):
        log(f"\n[INPUT-VALIDATION-TILE-{idx+1}] Tile {idx+1}: Querying device state (no download)...")
        
        # LIGHTWEIGHT approach: Query device RPC for current screen WITHOUT downloading
        # This avoids the 10s+ wait per tile
        try:
            # Query device for current screen detection WITHOUT full capture/download
            # Just make a quick RPC call to get the current highlighted input
            query_cmd = f"curl -s {rpc_url} -d '{{\"jsonrpc\":\"2.0\",\"id\":\"77\",\"method\":\"org.rdk.ScreenCapture.1.getScreenCapture\"}}' 2>/dev/null | grep -o 'INPUT_SCREEN[^\"]*' | head -1"
            
            stdin, stdout, stderr = ssh.exec_command(query_cmd, timeout=5)
            screen_raw = stdout.read().decode('utf-8', errors='ignore').strip()
            try:
                stdout.channel.close()
            except:
                pass
            
            if not screen_raw:
                log(f"[INPUT-VALIDATION-TILE-{idx+1}] ⚠ No screen detected via RPC query")
                # Fallback: Just take ONE lightweight screenshot for this tile
                # But don't download it - just use the validator's built-in cache
                log(f"[INPUT-VALIDATION-TILE-{idx+1}] Using fallback tile validation...")
            else:
                # Map the detected screen from RPC response
                matched_input = screen_to_input_map.get(screen_raw)
                
                if matched_input and matched_input not in checked_inputs:
                    if matched_input in input_names:
                        found.add(matched_input)
                        not_found.discard(matched_input)
                        checked_inputs.add(matched_input)
                        details[matched_input] = f"✓ {matched_input}"
                        log(f"[INPUT-VALIDATION-TILE-{idx+1}] ✓ Found (via RPC): {matched_input}")
                    else:
                        log(f"[INPUT-VALIDATION-TILE-{idx+1}] ⚠ Detected '{screen_raw}' not in expected list")
                elif matched_input in checked_inputs:
                    log(f"[INPUT-VALIDATION-TILE-{idx+1}] ℹ Already found: {matched_input}")
                else:
                    log(f"[INPUT-VALIDATION-TILE-{idx+1}] ⚠ Could not map RPC response: {screen_raw}")
                    
                # If RPC worked, we can skip to next tile without downloading
                if matched_input:
                    # Early exit if all inputs found
                    if len(found) == len(input_names):
                        log(f"\n[INPUT-VALIDATION] ✓ All {len(input_names)} inputs found!")
                        break
                    
                    # Move to next tile
                    if right_key_callback:
                        moved = right_key_callback(ssh)
                        if not moved:
                            log(f"[INPUT-VALIDATION] RIGHT key failed at tile {idx+1}")
                            break
                    else:
                        break
                    continue
            
            # FALLBACK: If RPC query didn't work, take ONE screenshot for validation
            # This is slow but necessary if device doesn't expose screen state via RPC
            log(f"[INPUT-VALIDATION-TILE-{idx+1}] Taking verification screenshot...")
            result = take_and_analyze_screenshot(
                ssh, f"input_verify_{idx+1}", device_ip, 
                log_callback=log,
                screenshot_folder=screenshot_folder,
                after_reboot=False
            )
            
            if not result.get('success'):
                log(f"[INPUT-VALIDATION-TILE-{idx+1}] ⚠ Screenshot verification failed: {result.get('error')}")
            else:
                # Extract detected screen from validation result
                screen_state = result.get('screen_state', {})
                detected_screen = screen_state.get('screen_detected', '')
                confidence = screen_state.get('confidence', 0.0)
                
                if detected_screen:
                    matched_input = screen_to_input_map.get(detected_screen)
                    
                    if matched_input and matched_input not in checked_inputs:
                        if matched_input in input_names:
                            found.add(matched_input)
                            not_found.discard(matched_input)
                            checked_inputs.add(matched_input)
                            details[matched_input] = f"✓ {matched_input} ({confidence:.0%})"
                            log(f"[INPUT-VALIDATION-TILE-{idx+1}] ✓ Found: {matched_input}")
                    
        except Exception as e:
            log(f"[INPUT-VALIDATION-TILE-{idx+1}] ⚠ Exception: {e}")
            continue
        
        # Move to next tile
        if right_key_callback:
            moved = right_key_callback(ssh)
            if not moved:
                log(f"[INPUT-VALIDATION] RIGHT key failed at tile {idx+1}")
                break
        else:
            break
        
        # Early exit if all inputs found
        if len(found) == len(input_names):
            log(f"\n[INPUT-VALIDATION] ✓ All {len(input_names)} inputs found!")
            break
    
    log(f"\n[INPUT-VALIDATION-SUMMARY]")
    log(f"  ✓ Found: {len(found)}/{len(input_names)} - {', '.join(sorted(found)) if found else 'None'}")
    log(f"  ✗ Missing: {len(not_found)} - {', '.join(sorted(not_found)) if not_found else 'None'}")
    
    return {
        'found': sorted(list(found)),
        'not_found': sorted(list(not_found)),
        'details': details
    }
"""
Screenshot Utility Module
Handles screen capture and OCR text extraction from device
Supports both AI Vision and Tesseract OCR
"""

import time
import requests
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import io
import re
import signal
import os
from contextlib import contextmanager
from config.config_screenshot import *

def normalize_screenshot_path(file_path):
    """
    Convert absolute filesystem path to web-friendly path for Flask screenshot serving.
    Returns paths in format /screenshots/relative/path which Flask can handle directly.
    
    Args:
        file_path: Absolute or relative filesystem path to screenshot
        
    Returns:
        Web-friendly path (e.g., '/screenshots/screenshots/file.png' or '/screenshots/reference_screens/file.png')
    """
    if not file_path:
        return None
    
    # If path is already a web URL format, return as-is
    if file_path.startswith('/screenshots/') or file_path.startswith('http'):
        return file_path
    
    # If path is already relative and doesn't look like an absolute path, return as-is
    if not file_path.startswith('/'):
        return file_path
    
    # Handle absolute paths - extract the relevant relative portion
    # Priority: reference_screens > Enhancement_output > screenshots > filename only
    
    # Check for reference_screens directory
    if 'reference_screens' in file_path.lower():
        lower_path = file_path.lower()
        idx = lower_path.find('reference_screens')
        if idx >= 0:
            return f"/screenshots/{file_path[idx:]}"
    
    # Check for Enhancement_output directory  
    if 'Enhancement_output' in file_path or 'enhancement_output' in file_path.lower():
        lower_path = file_path.lower()
        idx = lower_path.find('enhancement_output')
        if idx >= 0:
            return f"/screenshots/{file_path[idx:]}"
    
    # Check for screenshots directory
    if 'screenshots' in file_path.lower():
        lower_path = file_path.lower()
        idx = lower_path.find('screenshots')
        if idx >= 0:
            return f"/screenshots/{file_path[idx:]}"
    
    # If none of the known directories found, return with just the filename
    filename = os.path.basename(file_path)
    return f"/screenshots/{filename}"

# Global timeout for entire screenshot operation (prevents infinite hangs)
SCREENSHOT_HARD_TIMEOUT = 60  # Maximum 60 seconds for entire screenshot operation

@contextmanager
def timeout_handler(seconds, error_message="Operation timed out"):
    """
    Context manager to enforce hard timeout on operations.
    Raises TimeoutError if operation exceeds time limit.
    Note: Only works in main thread, not in sub-threads.
    """
    def _handle_timeout(signum, frame):
        raise TimeoutError(error_message)
    
    # Set the signal handler
    old_handler = signal.signal(signal.SIGALRM, _handle_timeout)
    signal.alarm(seconds)
    
    try:
        yield
    finally:
        # Restore the old signal handler
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

# Try to import AI vision if available
try:
    from services.ai_vision.ai_vision_ocr import extract_text_with_ai_vision
    AI_VISION_AVAILABLE = False  # Disabled to prevent hangs - use Tesseract instead
except ImportError:
    AI_VISION_AVAILABLE = False

def activate_screencapture_plugin(ssh, log_callback=None):
    """
    Activate the ScreenCapture plugin on the device
    This should be called after SSH connection is established and before taking screenshots
    
    Args:
        ssh: Active SSH connection to the device
        log_callback: Optional function to call for logging
    
    Returns:
        tuple: (success, error_message)
    """
    def log(message):
        if log_callback:
            log_callback(message)
    
    try:
        activate_command = f"curl -d '{{\"jsonrpc\":\"2.0\",\"id\":\"1\",\"method\": \"Controller.1.activate\", \"params\":{{\"callsign\":\"org.rdk.ScreenCapture\"}}}}' {rpc_url}"
        
        log("Activating ScreenCapture plugin...")
        
        stdin, stdout, stderr = ssh.exec_command(activate_command)
        time.sleep(2)  # Wait for activation to complete
        
        response = stdout.read().decode('utf-8', errors='ignore')
        error_output = stderr.read().decode('utf-8', errors='ignore')
        
        # Always close the channel after reading
        stdout.channel.close()
        stderr.channel.close()
        
        if error_output:
            log(f"⚠ Warning during plugin activation: {error_output}")
        
        log(f"✓ ScreenCapture plugin activated")
        return True, None
        
    except Exception as e:
        error_msg = f"Failed to activate ScreenCapture plugin: {str(e)}"
        log(f"❌ {error_msg}")
        return False, error_msg

def extract_text_with_preprocessing(image, log_callback=None):
    """
    Extract text from image using multiple Tesseract configurations and preprocessing
    to get the best quality OCR results similar to AI-level extraction
    
    Args:
        image: PIL Image object
        log_callback: Optional function to call for logging
    
    Returns:
        str: Extracted text with best quality
    """
    def log(message):
        if log_callback:
            log_callback(message)
    
    # Strategy: Try multiple Tesseract configurations and preprocessing techniques
    # to maximize text extraction quality
    
    results = []
    
    # Configuration 1: Default with PSM 3 (fully automatic page segmentation)
    # This is best for full page text with multiple paragraphs
    try:
        custom_config = r'--oem 3 --psm 3'
        text1 = pytesseract.image_to_string(image, config=custom_config)
        results.append(('PSM 3 (Auto page segmentation)', text1))
    except Exception as e:
        if log_callback:
            log(f"⚠ PSM 3 extraction failed: {e}")
    
    # Configuration 2: PSM 11 (sparse text - best for UI elements)
    # This works well for screens with scattered UI text like menus, buttons
    try:
        custom_config = r'--oem 3 --psm 11'
        text2 = pytesseract.image_to_string(image, config=custom_config)
        results.append(('PSM 11 (Sparse text)', text2))
    except Exception as e:
        if log_callback:
            log(f"⚠ PSM 11 extraction failed: {e}")
    
    # Configuration 3: Enhanced contrast preprocessing with PSM 6
    # PSM 6 assumes a single uniform block of text
    try:
        # Enhance image contrast and sharpness
        enhancer = ImageEnhance.Contrast(image)
        enhanced = enhancer.enhance(2.0)  # Increase contrast
        sharpener = ImageEnhance.Sharpness(enhanced)
        enhanced = sharpener.enhance(1.5)  # Increase sharpness
        
        custom_config = r'--oem 3 --psm 6'
        text3 = pytesseract.image_to_string(enhanced, config=custom_config)
        results.append(('PSM 6 (Enhanced contrast)', text3))
    except Exception as e:
        if log_callback:
            log(f"⚠ Enhanced contrast extraction failed: {e}")
    
    # Configuration 4: Upscaled image with PSM 4 (single column)
    # Upscaling can help with small text
    try:
        width, height = image.size
        upscaled = image.resize((width * 2, height * 2), Image.Resampling.LANCZOS)
        custom_config = r'--oem 3 --psm 4'
        text4 = pytesseract.image_to_string(upscaled, config=custom_config)
        results.append(('PSM 4 (Upscaled 2x)', text4))
    except Exception as e:
        if log_callback:
            log(f"⚠ Upscaled extraction failed: {e}")
    
    # Configuration 5: Grayscale + High contrast + Upscale 3x (TV UI optimized)
    # This combination works best for TV screenshots with text on backgrounds
    try:
        # Convert to grayscale for better text detection
        grayscale = image.convert('L')
        # Upscale 3x for better small text recognition
        width, height = grayscale.size
        upscaled = grayscale.resize((width * 3, height * 3), Image.Resampling.LANCZOS)
        # Enhance contrast significantly
        enhancer = ImageEnhance.Contrast(upscaled)
        enhanced = enhancer.enhance(2.5)
        # Sharpen
        sharpener = ImageEnhance.Sharpness(enhanced)
        enhanced = sharpener.enhance(2.0)
        # Adjust brightness
        brightness = ImageEnhance.Brightness(enhanced)
        enhanced = brightness.enhance(1.2)
        
        custom_config = r'--oem 3 --psm 11'
        text5 = pytesseract.image_to_string(enhanced, config=custom_config)
        results.append(('TV UI Optimized (3x upscale)', text5))
    except Exception as e:
        if log_callback:
            log(f"⚠ Grayscale extraction failed: {e}")
    
    # Select the best result (longest text with most content)
    if not results:
        if log_callback:
            log("❌ All OCR configurations failed")
        return ""
    
    best_result = max(results, key=lambda x: len(x[1].strip()))
    method, text = best_result
    
    if log_callback:
        log(f"✓ Best OCR method: {method} ({len(text)} characters)")
    
    return text

def take_and_analyze_screenshot(ssh, screenshot_name, device_ip, log_callback=None, screenshot_folder='screenshots', after_reboot=False):
    """
    Complete screenshot workflow: Capture device screen and extract text
    This matches the implementation from Device-Reboot-Deepsleep-Wakeup_Updated.py
    
    IMPORTANT: This function has a HARD TIMEOUT of 60 seconds to prevent hanging.
    If screenshot fails, execution continues - screenshot is non-critical.
    
    Args:
        ssh: Active SSH connection to the device
        screenshot_name: Name for the screenshot file (e.g., "ITR-1_beforeReboot_HomeScreen")
        device_ip: IP address of device (for logging)
        log_callback: Optional function to call for logging
        screenshot_folder: Folder path where screenshot should be saved (default: 'screenshots')
        after_reboot: If True, use longer retry delays for post-reboot captures
    
    Returns:
        dict: {
            'success': bool,
            'screenshot_url': str,
            'local_path': str,
            'extracted_text': str,
            'screen_state': dict,
            'error': str
        }
    """
    def log(message):
        if log_callback:
            log_callback(message)
    
    # Wrap entire operation in hard timeout to prevent infinite hangs
    start_time = time.time()
    log(f"⏱ Starting screenshot capture (max timeout: {SCREENSHOT_HARD_TIMEOUT}s)")
    
    try:
        return _take_screenshot_with_timeout(ssh, screenshot_name, device_ip, log, screenshot_folder, after_reboot, start_time)
    except TimeoutError as te:
        elapsed = time.time() - start_time
        error_msg = f"Screenshot operation timed out after {elapsed:.1f}s (hard limit: {SCREENSHOT_HARD_TIMEOUT}s)"
        log(f"❌ {error_msg}")
        log(f"⚠ CONTINUING EXECUTION - Screenshot is non-critical")
        return {
            'success': False,
            'screenshot_url': None,
            'local_path': None,
            'extracted_text': None,
            'screen_state': None,
            'error': error_msg
        }
    except Exception as e:
        elapsed = time.time() - start_time
        error_msg = f"Screenshot failed after {elapsed:.1f}s: {str(e)}"
        log(f"❌ {error_msg}")
        log(f"⚠ CONTINUING EXECUTION - Screenshot is non-critical")
        return {
            'success': False,
            'screenshot_url': None,
            'local_path': None,
            'extracted_text': None,
            'screen_state': None,
            'error': error_msg
        }

def _take_screenshot_with_timeout(ssh, screenshot_name, device_ip, log, screenshot_folder, after_reboot, start_time):
    """
    Internal function with actual screenshot logic.
    Separated to allow timeout wrapper.
    """
    try:
        # Activate ScreenCapture plugin before taking screenshot
        activate_success, activate_error = activate_screencapture_plugin(ssh, log)
        if not activate_success:
            log(f"⚠ Plugin activation failed but continuing: {activate_error}")
        
        # Build filenames and URLs - matching reference implementation
        upload_filename = f"{screenshot_name}.png"
        upload_url = f"{upload_base_url}?filename={upload_filename}"
        download_url = f"{download_base_url}{upload_filename}"
        
        log(f"Taking screenshot: {screenshot_name}")
        log(f"Upload filename: {upload_filename}")
        
        # Execute screenshot command with -k flag for insecure SSL
        screenshot_command = f"curl -k -d '{{\"jsonrpc\":\"2.0\",\"id\":\"3\",\"method\": \"org.rdk.ScreenCapture.1.uploadScreenCapture\", \"params\" : {{\"url\": \"{upload_url}\"}}}}' {rpc_url}"
        
        stdin, stdout, stderr = ssh.exec_command(screenshot_command)
        screenshot_response = stdout.read().decode('utf-8', errors='ignore')
        stderr_output = stderr.read().decode('utf-8', errors='ignore')
        
        # Always close the channel after reading
        stdout.channel.close()
        stderr.channel.close()
        
        # Check if screenshot command returned success
        import json
        try:
            response_json = json.loads(screenshot_response)
            if 'error' in response_json:
                log(f"⚠ Screenshot capture error: {response_json.get('error')}")
                log(f"   This may indicate the ScreenCapture service is not ready yet")
            elif 'result' in response_json:
                log(f"✓ Screenshot capture command accepted by device")
        except:
            pass  # Response might not be JSON
        
        # Note: curl outputs progress to stderr, which is not an error - ignore it
        log(f"Screenshot command response: {screenshot_response}")
        
        # Check device file size after capture (before upload completes)
        device_file_size = None
        try:
            log(f"Checking screenshot file size on device...")
            # ScreenCapture plugin typically saves to /opt/persistent/ or /tmp/
            check_size_cmd = f"ls -l /opt/persistent/*.png 2>/dev/null | tail -1 | awk '{{print $5}}' || ls -l /tmp/screenshot*.png 2>/dev/null | tail -1 | awk '{{print $5}}'"
            stdin, stdout, stderr = ssh.exec_command(check_size_cmd)
            size_output = stdout.read().decode('utf-8', errors='ignore').strip()
            
            # Always close the channel after reading
            stdout.channel.close()
            
            if size_output and size_output.isdigit():
                device_file_size = int(size_output)
                log(f"✓ Device file size: {device_file_size} bytes ({device_file_size/1024:.2f} KB)")
            else:
                log(f"⚠ Could not determine device file size (may not be accessible)")
        except Exception as e:
            log(f"⚠ Error checking device file size: {e}")
        
        log(f"Waiting {screenshot_upload_timeout} seconds for screenshot upload to complete...")
        time.sleep(screenshot_upload_timeout)
        
        # Download screenshot from server with retry mechanism
        log(f"Downloading screenshot from {download_url}...")

        try:
            import requests
            import os

            # For after-reboot screenshots the server upload can be delayed; use shorter retries to avoid hanging
            if after_reboot:
                # Small extra wait before starting attempts to give device time to finish upload
                extra_wait = 5  # Reduced from 10s to 5s
                log(f"After-reboot capture: waiting extra {extra_wait}s before first download attempt")
                
                # Check if we're approaching timeout limit
                elapsed = time.time() - start_time
                if elapsed > 40:  # If already spent 40s, skip extra wait
                    log(f"⚠ Already spent {elapsed:.1f}s, skipping extra wait to avoid timeout")
                else:
                    time.sleep(extra_wait)
                
                max_retries = 2  # Reduced from 3 to 2 (2 total attempts)
                retry_delays = [0, 5]  # Attempt 0: no delay, Retry 1: 5s (max 10s total)
            else:
                max_retries = 2  # Reduced from 3 to 2
                retry_delays = [0, 5]  # Attempt 0: no delay, Retry 1: 5s

            response = None
            upload_verified = False

            for attempt in range(max_retries):
                # Check if we're approaching timeout limit
                elapsed = time.time() - start_time
                if elapsed > (SCREENSHOT_HARD_TIMEOUT - 10):  # If less than 10s remaining, abort
                    log(f"⚠ Approaching timeout limit (elapsed: {elapsed:.1f}s), aborting download attempts")
                    break
                
                if attempt > 0:
                    delay = retry_delays[attempt]
                    log(f"Retry {attempt}/{max_retries-1}: Waiting {delay} seconds before next attempt...")
                    time.sleep(delay)

                # STEP 1: Verify file exists on server with valid size using HEAD request
                try:
                    log(f"Verifying upload completion on server (attempt {attempt + 1})...")
                    # Reduced timeout from 30s to 15s to be more aggressive
                    head_resp = requests.head(download_url, verify=False, timeout=15)
                    
                    if head_resp.status_code == 200:
                        content_length = head_resp.headers.get('Content-Length', '0')
                        content_type = head_resp.headers.get('Content-Type', '')
                        
                        try:
                            file_size = int(content_length)
                        except:
                            file_size = 0
                        
                        log(f"   Server response: HTTP {head_resp.status_code}")
                        log(f"   Content-Type: {content_type}")
                        log(f"   Content-Length: {file_size} bytes ({file_size/1024:.2f} KB)")
                        
                        # Compare device and server file sizes if device size is available
                        if device_file_size is not None and file_size > 0:
                            size_diff = abs(device_file_size - file_size)
                            size_diff_percent = (size_diff / device_file_size * 100) if device_file_size > 0 else 0
                            
                            log(f"   Device size: {device_file_size} bytes ({device_file_size/1024:.2f} KB)")
                            log(f"   Server size: {file_size} bytes ({file_size/1024:.2f} KB)")
                            log(f"   Size difference: {size_diff} bytes ({size_diff_percent:.2f}%)")
                            
                            # Allow small differences due to compression/encoding (up to 5%)
                            if size_diff_percent > 5:
                                log(f"⚠ WARNING: Significant size mismatch between device and server!")
                                log(f"   This may indicate incomplete upload or file corruption")
                                if attempt < max_retries - 1:
                                    log(f"   Will retry to verify upload stability...")
                                    continue
                            else:
                                log(f"✓ Size comparison PASSED: Device and server sizes match within tolerance")
                        
                        # Verify file has content and is an image
                        if file_size > 0 and 'image' in content_type:
                            log(f"✓ Upload verified: File exists on server with {file_size} bytes")
                            upload_verified = True
                        elif file_size == 0:
                            log(f"⚠ File exists but has 0 bytes - upload may still be in progress")
                            if attempt < max_retries - 1:
                                log(f"   Waiting for upload to complete...")
                                continue
                            else:
                                log(f"❌ File still 0 bytes after all retries - upload failed")
                                break
                        else:
                            log(f"⚠ File exists but Content-Type is not image: {content_type}")
                            if attempt < max_retries - 1:
                                continue
                    else:
                        log(f"⚠ HEAD request failed: HTTP {head_resp.status_code}")
                        if attempt < max_retries - 1:
                            log(f"   File may not be uploaded yet, will retry...")
                            continue
                        
                except Exception as head_err:
                    log(f"⚠ HEAD request error on attempt {attempt + 1}: {head_err}")
                    if attempt < max_retries - 1:
                        log(f"   Will retry...")
                        continue

                # STEP 2: If upload verified, download the file
                if upload_verified:
                    try:
                        log(f"Downloading verified file...")
                        # Reduced timeout from 30s to 15s for faster failure detection
                        response = requests.get(download_url, stream=True, verify=False, timeout=15)
                        
                        if response.status_code == 200:
                            log(f"✓ Screenshot download successful on attempt {attempt + 1}")
                            break
                        else:
                            log(f"⚠ Download failed: HTTP {response.status_code}")
                            response = None
                            upload_verified = False
                            if attempt < max_retries - 1:
                                log(f"   Will retry...")
                                
                    except Exception as req_err:
                        log(f"⚠ HTTP download error on attempt {attempt + 1}: {req_err}")
                        response = None
                        upload_verified = False
                        if attempt < max_retries - 1:
                            log(f"   Will retry...")

            # Check if download was successful
            if not upload_verified or response is None or response.status_code != 200:
                error_msg = f"Failed to download screenshot after {max_retries} attempts - file not uploaded or 0 bytes"
                log(f"❌ {error_msg}")
                return {
                    'success': False,
                    'screenshot_url': download_url,
                    'local_path': None,
                    'extracted_text': None,
                    'screen_state': None,
                    'error': error_msg
                }
            
            # Create screenshots directory if it doesn't exist
            if not os.path.exists(screenshot_folder):
                os.makedirs(screenshot_folder)
            
            # Save screenshot to local file
            local_path = os.path.join(screenshot_folder, upload_filename)
            with open(local_path, 'wb') as f:
                f.write(response.content)
            
            file_size = os.path.getsize(local_path)
            log(f"✓ Screenshot downloaded successfully to {local_path}")
            log(f"✓ File size: {file_size} bytes ({file_size/1024:.2f} KB)")
            
            # Verify the image is valid
            if file_size > 0:
                try:
                    test_image = Image.open(local_path)
                    width, height = test_image.size
                    log(f"✓ Valid image file - Dimensions: {width}x{height}")
                    test_image.close()
                except Exception as img_error:
                    log(f"⚠ Warning: File exists but may be corrupted: {img_error}")
            else:
                error_msg = "Downloaded screenshot file is empty (0 bytes)"
                log(f"❌ {error_msg}")
                return {
                    'success': False,
                    'screenshot_url': download_url,
                    'local_path': normalize_screenshot_path(local_path),
                    'extracted_text': None,
                    'screen_state': None,
                    'error': error_msg
                }
            
            # Verify image using AI-based validation (V2.0) with automatic provider selection
            try:
                # Use unified screen validator (Ollama by default, Gemini optional)
                from services.unified_screen_validator import UnifiedScreenValidator
                
                log(f"🔍 Performing AI-based screen validation (provider: auto-detected)...")
                validator = UnifiedScreenValidator(debug=False)
                provider_info = validator.get_provider_info()
                log(f"   Using provider: {provider_info.get('actual', 'unknown')}")
                
                # Call unified validator
                ai_result = validator.validate_screen_detailed(
                    screenshot_path=local_path,
                    expected_screen=None,
                    device_name=None
                )
                
                if ai_result.get('match', False) or 'error' not in ai_result:
                    screen_detected = ai_result.get('detected_screen', 'Unknown')
                    confidence = ai_result.get('confidence', 0.0) / 100.0 if ai_result.get('confidence', 0) > 1 else ai_result.get('confidence', 0.0)
                    
                    log(f"✓ Screen detected: {screen_detected} ({confidence:.2%})")
                    
                    screen_state = {
                        'screen_detected': screen_detected,
                        'confidence': confidence,
                        'device_matched': ai_result.get('match', False),
                        'validation_details': {
                            'analysis': ai_result.get('analysis', ''),
                            'provider': ai_result.get('provider', 'unknown'),
                            'analysis_method': 'AI_UNIFIED'
                        }
                    }
                else:
                    log(f"⚠ AI validation failed: {ai_result.get('error', 'Unknown error')}")
                    log(f"  Falling back to lightweight validation...")
                    
                    from tools.screen.screen_validator_lightweight import LightweightScreenValidator
                    lightweight_validator = LightweightScreenValidator(excluded_folders=['FactoryReset-XUMO-TV'])
                    validation_result = lightweight_validator.find_best_match(local_path)
                    
                    screen_detected = validation_result.get('best_match', 'Unknown')
                    confidence = validation_result.get('confidence', 0.0)
                    
                    log(f"✓ Screen detected (fallback to pixel-matching): {screen_detected} ({confidence:.2%})")
                    screen_state = {
                        'screen_detected': screen_detected,
                        'confidence': confidence,
                        'validation_details': {
                            'analysis_method': 'PIXEL_MATCHING_FALLBACK',
                            **validation_result.get('details', {})
                        }
                    }
            
            except ImportError as ie:
                log(f"⚠ Unified validator not available: {ie}, using lightweight validation...")
                from tools.screen.screen_validator_lightweight import LightweightScreenValidator
                
                lightweight_validator = LightweightScreenValidator(excluded_folders=['FactoryReset-XUMO-TV'])
                validation_result = lightweight_validator.find_best_match(local_path)
                
                screen_detected = validation_result.get('best_match', 'Unknown')
                confidence = validation_result.get('confidence', 0.0)
                
                log(f"✓ Screen detected (lightweight): {screen_detected} ({confidence:.2%})")
                screen_state = {
                    'screen_detected': screen_detected,
                    'confidence': confidence,
                    'validation_details': validation_result.get('details', {})
                }
            
            except Exception as e:
                log(f"⚠ Image validation error: {str(e)}, continuing without validation")
                screen_state = {'screen_detected': 'Unknown', 'confidence': 0.0}
            
            return {
                'success': True,
                'screenshot_url': download_url,
                'local_path': normalize_screenshot_path(local_path),
                'extracted_text': None,
                'screen_state': screen_state,
                'error': None
            }
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error downloading screenshot: {str(e)}"
            log(f"❌ {error_msg}")
            return {
                'success': False,
                'screenshot_url': download_url,
                'local_path': None,
                'extracted_text': None,
                'screen_state': None,
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"Error during text extraction: {str(e)}"
            log(f"❌ {error_msg}")
            return {
                'success': False,
                'screenshot_url': download_url,
                'local_path': None,
                'extracted_text': None,
                'screen_state': None,
                'error': error_msg
            }
            
    except Exception as e:
        error_msg = f"Exception during screenshot capture: {str(e)}"
        log(f"❌ {error_msg}")
        return {
            'success': False,
            'screenshot_url': None,
            'local_path': None,
            'extracted_text': None,
            'screen_state': None,
            'error': error_msg
        }

def take_screenshot(ssh, screenshot_name, log_callback=None):
    """
    Take a screenshot of the device and upload it to the server
    Activates ScreenCapture plugin before capturing
    
    Args:
        ssh: Active SSH connection to the device
        screenshot_name: Name for the screenshot file
        log_callback: Optional function to call for logging
    
    Returns:
        tuple: (success, screenshot_url, error_message)
    """
    def log(message):
        if log_callback:
            log_callback(message)
    
    try:
        # Activate ScreenCapture plugin first
        activate_success, activate_error = activate_screencapture_plugin(ssh, log_callback)
        if not activate_success:
            log(f"⚠ Plugin activation failed but continuing: {activate_error}")
        
        upload_filename = f"{screenshot_name}.png"
        upload_url = f"{upload_base_url}?filename={upload_filename}"
        screenshot_command = f"curl -k -d '{{\"jsonrpc\":\"2.0\",\"id\":\"3\",\"method\": \"org.rdk.ScreenCapture.1.uploadScreenCapture\", \"params\" : {{\"url\": \"{upload_url}\"}}}}' {rpc_url}"
        
        log(f"Taking screenshot: {screenshot_name}")
        log(f"Upload filename: {upload_filename}")
        
        stdin, stdout, stderr = ssh.exec_command(screenshot_command)
        time.sleep(screenshot_upload_timeout)  # Allow time for the command to take effect
        
        screenshot_response = stdout.read().decode('utf-8', errors='ignore')
        error_output = stderr.read().decode('utf-8', errors='ignore')
        
        # Always close the channel after reading
        stdout.channel.close()
        stderr.channel.close()
        
        if error_output:
            log(f"⚠ Error taking screenshot: {error_output}")
            return False, None, error_output
        
        log(f"Screenshot command response: {screenshot_response}")
        
        return True, upload_url, None
        
    except Exception as e:
        error_msg = f"Exception during screenshot: {str(e)}"
        log(f"❌ {error_msg}")
        return False, None, error_msg

def extract_text_from_screenshot(screenshot_url, log_callback=None):
    """
    Download screenshot and extract text using OCR
    
    Args:
        screenshot_url: URL of the screenshot to analyze
        log_callback: Optional function to call for logging
    
    Returns:
        tuple: (success, extracted_text, error_message)
    """
    def log(message):
        if log_callback:
            log_callback(message)
    
    try:
        log(f"Downloading screenshot from {screenshot_url}...")
        
        response = requests.get(screenshot_url, stream=True, timeout=screenshot_download_timeout)
        if response.status_code != 200:
            error_msg = f"Failed to download screenshot, HTTP {response.status_code}"
            log(f"❌ {error_msg}")
            return False, None, error_msg
        
        # Open image from response
        capture_image = Image.open(io.BytesIO(response.content))
        
        log("Extracting text from screenshot using OCR...")
        text = pytesseract.image_to_string(capture_image)
        
        # Extract filename from URL for display
        screenshot_filename = screenshot_url.split('/')[-1] if screenshot_url else "unknown"
        log(f"Text Read from Captured Image {screenshot_filename}: {text}")
        log(f"✓ Text extraction completed ({len(text)} characters)")
        
        return True, text, None
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Network error downloading screenshot: {str(e)}"
        log(f"❌ {error_msg}")
        return False, None, error_msg
    except Exception as e:
        error_msg = f"Exception during text extraction: {str(e)}"
        log(f"❌ {error_msg}")
        return False, None, error_msg

def capture_and_analyze_screen(ssh, screenshot_name, log_callback=None):
    """
    Complete workflow: Take screenshot and extract text
    
    Args:
        ssh: Active SSH connection to the device
        screenshot_name: Name for the screenshot file
        log_callback: Optional function to call for logging
    
    Returns:
        tuple: (success, screenshot_url, extracted_text, error_message)
    """
    def log(message):
        if log_callback:
            log_callback(message)
    
    # Take screenshot
    success, screenshot_url, error = take_screenshot(ssh, screenshot_name, log_callback)
    if not success:
        return False, None, None, error
    
    # Extract text
    success, text, error = extract_text_from_screenshot(screenshot_url, log_callback)
    if not success:
        return False, screenshot_url, None, error
    
    return True, screenshot_url, text, None

def analyze_screen_state(extracted_text, log_callback=None):
    """
    Analyze extracted text to determine screen state
    
    Args:
        extracted_text: Text extracted from screenshot
        log_callback: Optional function to call for logging
    
    Returns:
        dict: Screen state information
    """
    def log(message):
        if log_callback:
            log_callback(message)
    
    if not extracted_text:
        return {
            'state': 'unknown',
            'is_home_screen': False,
            'has_error': False,
            'details': 'No text extracted'
        }
    
    text_lower = extracted_text.lower()
    
    # Check for various states
    is_home_screen = any(keyword in text_lower for keyword in HOME_SCREEN_KEYWORDS)
    has_network_error = any(keyword in text_lower for keyword in NETWORK_ERROR_KEYWORDS)
    has_loading = any(keyword in text_lower for keyword in LOADING_KEYWORDS)
    has_error = any(keyword in text_lower for keyword in ERROR_KEYWORDS)
    is_blank = len(extracted_text.strip()) < MIN_TEXT_LENGTH
    
    # Determine state
    if is_blank:
        state = 'blank_screen'
        details = 'Screen appears to be blank or in standby'
    elif has_network_error:
        state = 'network_error'
        details = 'Network error detected on screen'
    elif has_loading:
        state = 'loading'
        details = 'Screen is showing loading state'
    elif is_home_screen:
        state = 'home_screen'
        details = 'Device appears to be on home screen'
    else:
        state = 'unknown'
        details = 'Unable to determine screen state'
    
    result = {
        'state': state,
        'is_home_screen': is_home_screen,
        'has_error': has_network_error or has_error,
        'has_network_error': has_network_error,
        'is_loading': has_loading,
        'is_blank': is_blank,
        'details': details,
        'text_preview': extracted_text[:200] if extracted_text else ''
    }
    
    log(f"Screen state analysis: {state} - {details}")
    
    return result

def get_screen_state(ssh, screenshot_name, log_callback=None):
    """
    Complete workflow: Capture, analyze, and return screen state
    
    Args:
        ssh: Active SSH connection to the device
        screenshot_name: Name for the screenshot file
        log_callback: Optional function to call for logging
    
    Returns:
        dict: Complete screen state information including screenshot URL
    """
    success, screenshot_url, text, error = capture_and_analyze_screen(ssh, screenshot_name, log_callback)
    
    if not success:
        return {
            'success': False,
            'error': error,
            'screenshot_url': screenshot_url,
            'state': 'error',
            'details': error
        }
    
    state_info = analyze_screen_state(text, log_callback)
    state_info['success'] = True
    state_info['screenshot_url'] = screenshot_url
    state_info['extracted_text'] = text
    
    return state_info
