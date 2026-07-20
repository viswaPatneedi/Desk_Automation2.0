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


def get_vnc_port_for_device(device_ip, tunnel_mode=False, tunnel_host='localhost'):
    """
    Get the VNC port for a device based on deployment mode.
    
    Args:
        device_ip: IP address of the device
        tunnel_mode: If True, uses tunnel mode port mapping
        tunnel_host: Host to use in tunnel mode (default: localhost)
    
    Returns:
        tuple: (host, port)
    """
    from config.config_deployment import VNC_PORT_MAPPING, DEFAULT_VNC_PORT, TUNNEL_MODE
    
    if tunnel_mode or TUNNEL_MODE:
        # Tunnel mode: Use mapped port on tunnel host
        vnc_port = VNC_PORT_MAPPING.get(device_ip, DEFAULT_VNC_PORT)
        return tunnel_host, vnc_port
    else:
        # Local mode: Use device IP with default port
        return device_ip, DEFAULT_VNC_PORT


def take_vnc_screenshot(
    device_ip, 
    device_name, 
    iteration,
    screenshot_folder='screenshots',
    vnc_port=5800,
    log_callback=None,
    timeout=15,
    validate_image=True,
    context=None
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
        
        # Step 2: Download screenshot from VNC port
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
        
        # Step 4: Save to local storage
        os.makedirs(screenshot_folder, exist_ok=True)
        
        # Build filename with context if provided
        if context:
            # Sanitize context for filename
            context_clean = context.replace(' ', '-').replace('_', '-')
            filename = f"{device_ip}_{device_name.replace(' ', '_')}_Iteration-{iteration}_{context_clean}_{timestamp}.png"
        else:
            filename = f"{device_ip}_{device_name.replace(' ', '_')}_Iteration-{iteration}_{timestamp}.png"
        local_path = os.path.join(screenshot_folder, filename)
        
        with open(local_path, 'wb') as f:
            f.write(response.content)
        
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
                
                # Perform AI-based screen validation (V2.0 implementation - using Ollama default)
                try:
                    from services.unified_screen_validator import UnifiedScreenValidator
                    
                    log(f"🔍 Performing AI-based screen validation (provider: auto-detected)...")
                    validator = UnifiedScreenValidator(debug=False)
                    provider_info = validator.get_provider_info()
                    log(f"   Using provider: {provider_info.get('actual', 'unknown')}")
                    
                    # Call unified validator with expected screen context
                    ai_result = validator.validate_screen_detailed(
                        screenshot_path=local_path,
                        expected_screen=None,  # Will be auto-detected by AI
                        device_name=device_name
                    )
                    
                    if ai_result.get('success', False):
                        screen_detected = ai_result.get('detected_screen', 'Unknown')
                        confidence = ai_result.get('confidence', 0.0)
                        
                        log(f"✓ Screen detected: {screen_detected} ({confidence:.2%})")
                        log(f"  Focus elements: {', '.join(ai_result.get('focus_elements', []))}")
                        
                        if ai_result.get('anomalies'):
                            log(f"  ⚠ Anomalies detected: {', '.join(ai_result.get('anomalies', []))}")
                        
                        screen_state = {
                            'screen_detected': screen_detected,
                            'confidence': confidence,
                            'device_matched': ai_result.get('device_matched', False),
                            'validation_details': {
                                'focus_elements': ai_result.get('focus_elements', []),
                                'ui_elements': ai_result.get('ui_elements', []),
                                'anomalies': ai_result.get('anomalies', []),
                                'analysis_method': 'AI_VISION',
                                'device_name': device_name,
                                'context': context
                            }
                        }
                    else:
                        log(f"⚠ AI validation failed: {ai_result.get('error', 'Unknown error')}")
                        log(f"  Falling back to lightweight validation...")
                        
                        # Fallback to lightweight validator
                        from screen_validator_lightweight import LightweightScreenValidator
                        validator = LightweightScreenValidator(excluded_folders=['FactoryReset-XUMO-TV'])
                        validation_result = validator.find_best_match(local_path)
                        
                        screen_detected = validation_result.get('best_match', 'Unknown')
                        confidence = validation_result.get('confidence', 0.0)
                        
                        log(f"✓ Screen detected (fallback): {screen_detected} ({confidence:.2%})")
                        screen_state = {
                            'screen_detected': screen_detected,
                            'confidence': confidence,
                            'device_matched': False,
                            'validation_details': {
                                'analysis_method': 'PIXEL_MATCHING_FALLBACK',
                                'fallback_reason': ai_result.get('error', 'AI analysis failed'),
                                **validation_result.get('details', {})
                            }
                        }
                
                except ImportError:
                    log(f"⚠ AI analyzer not available, using lightweight validation...")
                    from screen_validator_lightweight import LightweightScreenValidator
                    
                    validator = LightweightScreenValidator(excluded_folders=['FactoryReset-XUMO-TV'])
                    validation_result = validator.find_best_match(local_path)
                    
                    screen_detected = validation_result.get('best_match', 'Unknown')
                    confidence = validation_result.get('confidence', 0.0)
                    
                    log(f"✓ Screen detected (lightweight): {screen_detected} ({confidence:.2%})")
                    screen_state = {
                        'screen_detected': screen_detected,
                        'confidence': confidence,
                        'device_matched': False,
                        'validation_details': validation_result.get('details', {})
                    }
                
                except Exception as val_err:
                    log(f"⚠ Screen validation failed: {val_err}")
                
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
    context=None
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
        context=context
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


def compare_screenshot_methods(device_ip, device_name, iteration, log_callback=None):
    """
    Compare VNC vs ScreenCapture plugin performance and quality.
    
    Useful for benchmarking and validating which method works best for a device.
    
    Args:
        device_ip: Device IP
        device_name: Device name
        iteration: Iteration number
        log_callback: Logging callback
    
    Returns:
        dict: Comparison results
    """
    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            logger.info(msg)
    
    import paramiko
    from config.config_devices import get_device_by_ip
    
    log("=" * 80)
    log("SCREENSHOT METHOD COMPARISON: VNC vs ScreenCapture Plugin")
    log("=" * 80)
    
    results = {}
    
    # Test VNC method
    log("\n[METHOD 1] Testing VNC-based capture...")
    vnc_start = time.time()
    vnc_result = take_vnc_screenshot(
        device_ip, device_name, iteration,
        log_callback=log_callback
    )
    vnc_time = time.time() - vnc_start
    results['vnc'] = {
        'success': vnc_result['success'],
        'time': vnc_time,
        'file_size': vnc_result.get('file_size', 0),
        'error': vnc_result.get('error')
    }
    
    if vnc_result['success']:
        log(f"✓ VNC Success: {vnc_time:.2f}s, {vnc_result['file_size']/1024:.2f}KB")
    else:
        log(f"❌ VNC Failed: {vnc_result['error']}")
    
    # Test ScreenCapture plugin method
    log("\n[METHOD 2] Testing ScreenCapture plugin capture...")
    try:
        device = get_device_by_ip(device_ip)
        if device:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(device_ip, port=device.port, username=device.username, password=device.password)
            
            from utils.screenshot_utils import take_and_analyze_screenshot
            
            plugin_start = time.time()
            plugin_result = take_and_analyze_screenshot(
                ssh, f"{device_ip}_{device_name}_Iteration-{iteration}",
                device_ip, log_callback=log_callback
            )
            plugin_time = time.time() - plugin_start
            
            results['plugin'] = {
                'success': plugin_result.get('success', False),
                'time': plugin_time,
                'error': plugin_result.get('error')
            }
            
            if plugin_result.get('success'):
                log(f"✓ Plugin Success: {plugin_time:.2f}s")
            else:
                log(f"❌ Plugin Failed: {plugin_result.get('error')}")
            
            ssh.close()
    except Exception as e:
        log(f"⚠ Plugin test failed: {e}")
        results['plugin'] = {'success': False, 'error': str(e)}
    
    # Summary
    log("\n" + "=" * 80)
    log("SUMMARY")
    log("=" * 80)
    
    if results['vnc']['success'] and results['plugin']['success']:
        vnc_faster = results['vnc']['time'] < results['plugin']['time']
        speedup = results['plugin']['time'] / results['vnc']['time']
        method = "VNC" if vnc_faster else "Plugin"
        log(f"🏆 {method} method is {speedup:.1f}x faster")
    
    log(f"VNC:    {results['vnc']['success']} ({results['vnc']['time']:.2f}s)")
    log(f"Plugin: {results['plugin']['success']} ({results['plugin']['time']:.2f}s)")
    
    return results


# ============================================================================
# INTEGRATION GUIDE
# ============================================================================
"""
HOW TO USE VNC SCREENSHOTS IN YOUR METHODS:

Option 1: Replace ScreenCapture with VNC (Fastest)
-----------
from tools.screen.screenshot_utils_vnc import take_vnc_screenshot

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
from tools.screen.screenshot_utils_vnc import take_vnc_screenshot_with_fallback

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
In method_deepsleep.py, method_reboot.py, etc.:

# Replace:
# screenshot_result = take_and_analyze_screenshot(...)

# With:
from tools.screen.screenshot_utils_vnc import take_vnc_screenshot_with_fallback
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
