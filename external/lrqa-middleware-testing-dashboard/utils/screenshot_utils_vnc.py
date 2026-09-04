"""
VNC-Based Screenshot Utility - Direct Device Screen Capture
Alternative to ScreenCapture plugin-based approach

This module provides faster, more reliable screenshot capture by directly accessing
the device's VNC port (5800) without requiring ScreenCapture plugin activation.

Benefits over ScreenCapture plugin:
- No plugin activation needed
- No server upload/download overhead
- Faster capture (5-10 seconds vs 20-30 seconds)
- Works offline (only needs VNC access)
- More reliable in network-constrained environments

Author: LRQA Dashboard Team
"""

import requests
import time
import os
from datetime import datetime, timezone
from PIL import Image
from io import BytesIO
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_vnc_screenshot_url(device_ip, device_name, iteration, timestamp=None, vnc_port=5800):
    """
    Generate VNC screenshot URL from SkyWebVNC server.
    
    Args:
        device_ip: IP address of the device (e.g., "10.0.0.195")
        device_name: Name of the device (e.g., "SKY-GLASS-G1") - for reference only
        iteration: Iteration number (e.g., 49) - for reference only
        timestamp: Optional timestamp string - for reference only
        vnc_port: VNC port (default: 5800)
    
    Returns:
        str: VNC screenshot URL endpoint
    
    Note:
        The VNC web server serves screenshots via a static endpoint.
        The endpoint always returns the current frame buffer as PNG.
        No custom naming/parameters are supported.
    
    Example:
        >>> get_vnc_screenshot_url("10.0.0.195", "SKY-GLASS-G1", 49)
        'http://10.0.0.195:5800/screenshot.png'
    """
    # SkyWebVNC server uses a static endpoint for screenshots
    # The device_name and iteration parameters are for reference/logging only
    # The VNC server always returns the current frame buffer as PNG
    url = f"http://{device_ip}:{vnc_port}/screenshot.png"
    
    return url


def take_vnc_screenshot(
    device_ip, 
    device_name, 
    iteration,
    screenshot_folder='screenshots',
    vnc_port=5800,
    log_callback=None,
    timeout=15,
    validate_image=True,
    context=None,
    app_name=None,
    step=None,
    ssh=None
):
    """
    Capture screenshot directly from VNC port (NO ScreenCapture plugin needed).
    
    This is FASTER and MORE RELIABLE than the ScreenCapture plugin approach:
    - VNC capture: 5-10 seconds
    - ScreenCapture plugin: 20-30 seconds (includes plugin activation, upload, download)
    
    Args:
        device_ip: IP address of the device (e.g., "10.0.0.195")
        device_name: Device name (e.g., "SKY-GLASS-G1")
        iteration: Iteration number for logging
        screenshot_folder: Folder to save screenshot (default: 'screenshots')
        vnc_port: VNC port (default: 5800)
        log_callback: Optional logging function
        timeout: HTTP request timeout in seconds (default: 15)
        validate_image: Whether to validate the downloaded image (default: True)
        context: Context label for naming (e.g., "Before", "After-Reboot-SUCCESS", "After-Reboot-FAILED")
        ssh: Optional R-Pi tunnel/SSH client. The device's VNC port is only reachable
             from the R-Pi's LAN, not from the dashboard host, so when provided the
             request is proxied through the R-Pi (curl + base64) instead of being
             attempted directly from here.
    
    Returns:
        dict: {
            'success': bool,
            'local_path': str,      # Path to saved screenshot
            'url': str,             # VNC URL used
            'file_size': int,       # Size in bytes
            'dimensions': tuple,    # (width, height)
            'screen_state': dict,   # Validation results
            'error': str,           # Error message if failed
            'capture_time': float   # Time taken in seconds
        }
    
    Example:
        >>> result = take_vnc_screenshot("10.0.0.195", "SKY-GLASS-G1", 49)
        >>> if result['success']:
        ...     print(f"Screenshot saved to {result['local_path']}")
        ...     print(f"Dimensions: {result['dimensions']}")
    """
    if screenshot_folder == 'screenshots':
        from methods.method_utils import get_execution_screenshots_dir
        screenshot_folder = get_execution_screenshots_dir(screenshot_folder)

    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            logger.info(msg)
    
    start_time = time.time()
    
    try:
        # Step 1: Generate VNC URL
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        vnc_url = get_vnc_screenshot_url(device_ip, device_name, iteration, timestamp, vnc_port)
        log(f"📸 VNC Screenshot: Generating capture from {vnc_url}")
        
        # Step 2: Download screenshot from VNC port. The device's VNC server is only
        # reachable from the R-Pi's network, so route through the R-Pi tunnel when
        # available; only fall back to a direct request if no tunnel was supplied.
        image_bytes = None
        if ssh is not None and hasattr(ssh, 'execute_rpi_command'):
            import base64
            import shlex
            log(f"⏳ Downloading screenshot from VNC port {vnc_port} via R-Pi tunnel...")
            command = (
                f"curl --fail --silent --show-error --max-time {int(timeout)} "
                f"http://{shlex.quote(device_ip)}:{int(vnc_port)}/screenshot.png | base64 -w 0"
            )
            success, encoded_image, error = ssh.execute_rpi_command(command, timeout=timeout + 5)
            if not success or not encoded_image:
                error_msg = error or 'VNC screenshot capture through R-Pi tunnel failed'
                log(f"❌ VNC Screenshot Failed: {error_msg}")
                return {
                    'success': False,
                    'local_path': None,
                    'url': vnc_url,
                    'file_size': 0,
                    'dimensions': None,
                    'screen_state': None,
                    'error': error_msg,
                    'capture_time': time.time() - start_time
                }
            try:
                image_bytes = base64.b64decode(encoded_image)
            except Exception as decode_err:
                error_msg = f"Invalid VNC screenshot response: {decode_err}"
                log(f"❌ VNC Screenshot Failed: {error_msg}")
                return {
                    'success': False,
                    'local_path': None,
                    'url': vnc_url,
                    'file_size': 0,
                    'dimensions': None,
                    'screen_state': None,
                    'error': error_msg,
                    'capture_time': time.time() - start_time
                }
            if len(image_bytes) == 0:
                error_msg = "VNC server returned 0-byte file"
                log(f"❌ VNC Screenshot Failed: {error_msg}")
                return {
                    'success': False,
                    'local_path': None,
                    'url': vnc_url,
                    'file_size': 0,
                    'dimensions': None,
                    'screen_state': None,
                    'error': error_msg,
                    'capture_time': time.time() - start_time
                }
        else:
            log(f"⏳ Downloading screenshot from VNC port {vnc_port}...")
            response = requests.get(
                vnc_url,
                timeout=timeout,
                verify=False,
                stream=True
            )
            
            if response.status_code != 200:
                error_msg = f"HTTP {response.status_code} from VNC server"
                log(f"❌ VNC Screenshot Failed: {error_msg}")
                return {
                    'success': False,
                    'local_path': None,
                    'url': vnc_url,
                    'file_size': 0,
                    'dimensions': None,
                    'screen_state': None,
                    'error': error_msg,
                    'capture_time': time.time() - start_time
                }
            
            # Step 3: Verify content
            file_size = int(response.headers.get('Content-Length', 0))
            if file_size == 0:
                error_msg = "VNC server returned 0-byte file"
                log(f"❌ VNC Screenshot Failed: {error_msg}")
                return {
                    'success': False,
                    'local_path': None,
                    'url': vnc_url,
                    'file_size': 0,
                    'dimensions': None,
                    'screen_state': None,
                    'error': error_msg,
                    'capture_time': time.time() - start_time
                }
            image_bytes = response.content
        
        # Step 4: Save to local storage
        os.makedirs(screenshot_folder, exist_ok=True)
        
        # Build filename with context if provided
        if context:
            # Sanitize context for filename
            context_clean = context.replace(' ', '-').replace('_', '-')
            if step is not None:
                filename = f"{device_ip}_{device_name.replace(' ', '_')}_Step-{step}_Iteration-{iteration}_{context_clean}_{timestamp}.png"
            else:
                filename = f"{device_ip}_{device_name.replace(' ', '_')}_Iteration-{iteration}_{context_clean}_{timestamp}.png"
        else:
            if step is not None:
                filename = f"{device_ip}_{device_name.replace(' ', '_')}_Step-{step}_Iteration-{iteration}_{timestamp}.png"
            else:
                filename = f"{device_ip}_{device_name.replace(' ', '_')}_Iteration-{iteration}_{timestamp}.png"
        local_path = os.path.join(screenshot_folder, filename)
        
        with open(local_path, 'wb') as f:
            f.write(image_bytes)
        
        file_size = os.path.getsize(local_path)
        log(f"✓ Screenshot downloaded: {file_size / 1024:.2f} KB")
        
        # Step 5: Validate image if requested
        dimensions = None
        screen_state = {'screen_detected': 'Unknown', 'confidence': 0.0}
        
        if validate_image:
            try:
                image = Image.open(local_path)
                dimensions = image.size
                log(f"✓ Image validation: {dimensions[0]}x{dimensions[1]} pixels")
                
                # Skip heavy AI validation - use lightweight pixel-based validator with reference screens
                # This is faster and more reliable than waiting for Ollama/Gemini which typically times out
                try:
                    log(f"🔍 Performing screen validation using reference-based detection...")
                    
                    # PRIMARY: Use pixel/layout matching (fast, accurate, reliable)
                    screen_detected = None
                    confidence = 0.0
                    validation_method = None
                    ollama_confidence = None
                    
                    # FAST PATH: Reference screen matching (pixel/layout-based)
                    log(f"⚡ Using reference screen matching (pixel/layout-based) for fast validation...")
                    
                    try:
                        from tools.screen.screen_validator_lightweight import LightweightScreenValidator
                        
                        # Determine reference directory path
                        app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                        data_ref = os.path.join(app_root, "data/references")
                        
                        if os.path.exists(data_ref):
                            ref_dir = data_ref
                            log(f"✓ Using app-specific reference directory: {ref_dir}")
                        else:
                            ref_dir = "reference_screens"
                            if not os.path.exists(ref_dir):
                                ref_dir = os.path.join(app_root, "reference_screens")
                            log(f"✓ Using fallback reference directory: {ref_dir}")
                        
                        if app_name:
                            log(f"📁 Searching {app_name} reference screens in: {ref_dir}")
                        
                        # Use reference screens for pixel matching
                        lightweight_validator = LightweightScreenValidator(
                            reference_dir=ref_dir,
                            excluded_folders=['FactoryReset-XUMO-TV'],
                            app_name=app_name
                        )
                        validation_result = lightweight_validator.find_best_match(local_path)
                        
                        screen_detected = validation_result.get('best_match', 'Unknown')
                        confidence = validation_result.get('confidence', 0.0)
                        validation_method = 'PIXEL_MATCHING_WITH_APP_SPECIFIC_REFERENCES'
                        
                        log(f"✓ Pixel matching result: {screen_detected} ({confidence:.2%})")
                    except Exception as pixel_err:
                        log(f"⚠ Pixel matching error: {pixel_err}, attempting fallback...")
                    
                    # OPTIONAL: Validate with OLLAMA AI if pixel matching succeeded but with low confidence
                    # This adds semantic understanding without slowing down fast cases
                    if screen_detected and screen_detected != 'Unknown' and confidence < 0.85:
                        try:
                            log(f"🤖 Running AI validation for enhanced confidence...")
                            from services.ai_vision.ai_screen_validator_ollama import OllamaScreenValidator
                            
                            ollama_validator = OllamaScreenValidator(debug=False)
                            if ollama_validator.available:
                                screen_context = app_name if app_name else "Device"
                                result = ollama_validator.validate_screen_detailed(local_path, screen_context)
                                
                                if result and 'error' not in result:
                                    ai_detected = result.get('detected_screen', screen_detected)
                                    ai_confidence = result.get('confidence', 0) / 100.0
                                    
                                    # Use AI result if it provides higher confidence or matches pixel result
                                    if ai_confidence > confidence:
                                        ollama_confidence = ai_confidence
                                        log(f"  ⬆ AI validation improved confidence: {ai_confidence:.2%}")
                                        confidence = ai_confidence
                                    elif ai_detected == screen_detected:
                                        ollama_confidence = ai_confidence
                                        log(f"  ✓ AI validation confirms: {screen_detected}")
                                    else:
                                        log(f"  ℹ AI suggests: {ai_detected} ({ai_confidence:.2%}) - keeping pixel match")
                        except Exception as ai_err:
                            log(f"  ℹ AI validation skipped (optional): {ai_err}")
                    
                    screen_state = {
                        'screen_detected': screen_detected,
                        'confidence': confidence,
                        'validation_details': {
                            'analysis_method': validation_method,
                            'primary_validator': 'PIXEL_MATCHING',
                            'ai_enhanced': ollama_confidence is not None,
                            'app_name': app_name,
                        }
                    }
                except Exception as val_err:
                    log(f"⚠ Screen validation warning: {val_err}")
                    import traceback
                    log(f"  Traceback: {traceback.format_exc()}")
                    screen_state = {'screen_detected': 'Unknown', 'confidence': 0.0}
                
                image.close()
                
            except Exception as img_err:
                log(f"⚠ Image validation warning: {img_err}")
        
        elapsed = time.time() - start_time
        log(f"✓ VNC Screenshot Complete ({elapsed:.2f}s)")
        
        return {
            'success': True,
            'local_path': local_path,
            'url': vnc_url,
            'file_size': file_size,
            'dimensions': dimensions,
            'screen_state': screen_state,
            'error': None,
            'capture_time': elapsed
        }
        
    except requests.exceptions.Timeout:
        error_msg = f"VNC request timed out after {timeout}s"
        log(f"❌ VNC Screenshot Failed: {error_msg}")
        return {
            'success': False,
            'local_path': None,
            'url': vnc_url if 'vnc_url' in locals() else None,
            'file_size': 0,
            'dimensions': None,
            'screen_state': None,
            'error': error_msg,
            'capture_time': time.time() - start_time
        }
    except requests.exceptions.ConnectionError as conn_err:
        error_msg = f"Cannot connect to VNC server: {str(conn_err)}"
        log(f"❌ VNC Screenshot Failed: {error_msg}")
        return {
            'success': False,
            'local_path': None,
            'url': vnc_url if 'vnc_url' in locals() else None,
            'file_size': 0,
            'dimensions': None,
            'screen_state': None,
            'error': error_msg,
            'capture_time': time.time() - start_time
        }
    except Exception as e:
        error_msg = f"VNC screenshot error: {str(e)}"
        log(f"❌ VNC Screenshot Failed: {error_msg}")
        return {
            'success': False,
            'local_path': None,
            'url': vnc_url if 'vnc_url' in locals() else None,
            'file_size': 0,
            'dimensions': None,
            'screen_state': None,
            'error': error_msg,
            'capture_time': time.time() - start_time
        }


def take_vnc_screenshot_with_fallback(
    ssh,
    device_ip,
    device_name,
    iteration,
    screenshot_folder='screenshots',
    vnc_port=5800,
    log_callback=None,
    fallback_to_plugin=True,
    context=None,
    app_name=None,
    step=None
):
    """
    Take screenshot using VNC first, with automatic fallback to ScreenCapture plugin if VNC fails.
    
    This provides the best of both worlds:
    - Fast VNC capture when available
    - Fallback to ScreenCapture plugin when VNC is unavailable
    
    Args:
        ssh: Active SSH connection (needed for fallback only)
        device_ip: IP address of device
        device_name: Device name
        iteration: Iteration number
        screenshot_folder: Folder to save screenshot
        vnc_port: VNC port (default: 5800)
        log_callback: Logging callback
        fallback_to_plugin: If True, fall back to ScreenCapture plugin on VNC failure
        context: Context label for naming (e.g., "Before", "After-Reboot-SUCCESS", "After-Reboot-FAILED")
        app_name: App name for reference screen matching (e.g., 'netflix')
        step: Step number for UI display (e.g., 0, 1, 2)
    
    Returns:
        dict: Same as take_vnc_screenshot()
    """
    def log(msg):
        if log_callback:
            log_callback(msg)
    
    # Try VNC first
    log("[SCREENSHOT] Attempting VNC-based capture (fast method)...")
    result = take_vnc_screenshot(
        device_ip, device_name, iteration,
        screenshot_folder=screenshot_folder,
        vnc_port=vnc_port,
        log_callback=log_callback,
        validate_image=True,
        context=context,
        app_name=app_name,
        step=step,
        ssh=ssh
    )
    
    if result['success']:
        log("[SCREENSHOT] ✓ VNC capture successful!")
        return result
    
    # VNC failed, try fallback
    if fallback_to_plugin and ssh:
        log(f"[SCREENSHOT] ⚠ VNC failed ({result['error']}), falling back to ScreenCapture plugin...")
        try:
            from utils.screenshot_utils import take_and_analyze_screenshot
            
            screenshot_name = f"{device_ip}_{device_name}_Iteration-{iteration}"
            plugin_result = take_and_analyze_screenshot(
                ssh, screenshot_name, device_ip,
                log_callback=log_callback,
                screenshot_folder=screenshot_folder,
                after_reboot=False
            )
            
            if plugin_result.get('success'):
                log("[SCREENSHOT] ✓ ScreenCapture plugin fallback successful!")
                return {
                    'success': True,
                    'local_path': plugin_result.get('local_path'),
                    'url': plugin_result.get('screenshot_url'),
                    'file_size': 0,  # Not available from plugin result
                    'dimensions': None,
                    'screen_state': plugin_result.get('screen_state'),
                    'error': None,
                    'capture_time': 0,
                    'method': 'ScreenCapture-Plugin'
                }
            else:
                log(f"[SCREENSHOT] ❌ Both VNC and plugin methods failed")
                return result  # Return original VNC error
        except Exception as fallback_err:
            log(f"[SCREENSHOT] ⚠ Fallback error: {fallback_err}")
            return result
    
    # No fallback available
    log(f"[SCREENSHOT] ❌ VNC capture failed, no fallback available")
    return result


# ============================================================================
# INTEGRATION GUIDE
# ============================================================================
"""
HOW TO USE VNC SCREENSHOTS IN YOUR METHODS:

Option 1: Replace ScreenCapture with VNC (Fastest)
-----------
from utils.screenshot_utils_vnc import take_vnc_screenshot

result = take_vnc_screenshot(
    device_ip="10.0.0.195",
    device_name="SKY-GLASS-G1",
    iteration=49,
    log_callback=log_message
)

if result['success']:
    print(f"Screenshot saved to {result['local_path']}")
    print(f"Detected screen: {result['screen_state']['screen_detected']}")

Option 2: Use Fallback (Reliable)
-----------
from utils.screenshot_utils_vnc import take_vnc_screenshot_with_fallback

result = take_vnc_screenshot_with_fallback(
    ssh=ssh,
    device_ip="10.0.0.195",
    device_name="SKY-GLASS-G1",
    iteration=49,
    fallback_to_plugin=True,
    log_callback=log_message
)

Option 3: Add to Existing Methods
-----------
In methods/method_netflix_playback.py, method_deepsleep.py, etc.:

# Replace:
# screenshot_result = take_and_analyze_screenshot(...)

# With:
from utils.screenshot_utils_vnc import take_vnc_screenshot_with_fallback
screenshot_result = take_vnc_screenshot_with_fallback(
    ssh, device_ip, safe_device_name, iteration,
    fallback_to_plugin=True
)

PERFORMANCE METRICS:
- VNC Method:                5-10 seconds
- ScreenCapture Plugin:      20-30 seconds
- Speedup:                   ~2-3x faster

REQUIREMENTS:
- Device must have VNC port 5800 accessible
- No ScreenCapture plugin activation needed
- Works in network-constrained environments
"""
