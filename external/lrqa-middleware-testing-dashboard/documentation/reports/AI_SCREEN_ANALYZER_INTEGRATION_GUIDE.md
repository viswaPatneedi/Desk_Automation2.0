"""
AI Screen Analyzer Integration Guide for method_deepsleep.py

This document shows how to integrate AI-powered screen validation
into the existing DeepSleep method.
"""

# ============================================================
# BEFORE: Current Screen Validation
# ============================================================

"""
Current approach in method_deepsleep.py:

def check_home_screen(device_ip, username, password, port, device_name, log_callback=None):
    try:
        # Capture screenshot via VNC or plugin
        screenshot_result = capture_screenshot_vnc(device_ip, device_name, ...)
        
        if screenshot_result['success']:
            screenshot_path = screenshot_result['screenshot_path']
            
            # Use pixel-based validation (unreliable)
            # Compares against pre-captured reference images
            # Limited to exact matches
            # Fails with UI variations
            
            from method_utils import is_home_screen
            is_home = is_home_screen(screenshot_path)
            
            if is_home:
                log_message("✅ HOME screen detected")
                return True
            else:
                log_message("❌ Not on HOME screen")
                return False
    
    except Exception as e:
        log_message(f"❌ Error checking HOME screen: {e}")
        return False
"""

# ============================================================
# AFTER: AI-Powered Screen Validation
# ============================================================

"""
Improved approach with AI Screen Analyzer:

def check_home_screen_with_ai(device_ip, username, password, port, device_name, log_callback=None):
    try:
        # Capture screenshot via VNC or plugin
        screenshot_result = capture_screenshot_vnc(device_ip, device_name, ...)
        
        if screenshot_result['success']:
            screenshot_path = screenshot_result['screenshot_path']
            
            # Use AI-powered validation
            from services.ai_screen_validation_bridge import get_validation_bridge
            
            bridge = get_validation_bridge(use_ai=True)
            result = bridge.validate_screen(
                screenshot_path=screenshot_path,
                expected_screen="HOME",
                device_name=device_name
            )
            
            if result['is_valid']:
                log_message(f"✅ HOME screen validated by AI (Confidence: {result['confidence']:.1%})")
                log_message(f"   Focus Elements: {result['focus_elements']}")
                log_message(f"   UI Elements: {len(result['ui_elements'])} detected")
                return True
            else:
                log_message(f"❌ Device NOT on HOME screen")
                log_message(f"   Detected: {result['detected_screen']}")
                if result['anomalies']:
                    log_message(f"   Issues: {', '.join(result['anomalies'])}")
                return False
    
    except Exception as e:
        log_message(f"⚠️  AI validation failed: {e}, falling back to legacy")
        # Fallback to pixel-based validation if AI fails
        from method_utils import is_home_screen
        return is_home_screen(screenshot_path)
"""

# ============================================================
# INTEGRATION CODE
# ============================================================

"""
Add this to method_deepsleep.py at the top:
"""

def integrate_ai_validation():
    code = '''
# At the top of method_deepsleep.py, add:
from services.ai_screen_validation_bridge import get_validation_bridge

# Global AI validation bridge instance
_ai_bridge = None

def get_ai_bridge():
    global _ai_bridge
    if _ai_bridge is None:
        _ai_bridge = get_validation_bridge(use_ai=True)
    return _ai_bridge

def check_home_screen_ai(device_ip, username, password, port, device_name, 
                         log_callback=None, use_ai=True, fallback=True):
    """
    Check if device is on HOME screen using AI validation with fallback
    
    Args:
        device_ip (str): Device IP address
        username (str): SSH username
        password (str): SSH password
        port (int): SSH port
        device_name (str): Device name for logging
        log_callback (callable): Logging function
        use_ai (bool): Whether to use AI validation
        fallback (bool): Whether to fallback to legacy validation on failure
        
    Returns:
        bool: True if device is on HOME screen, False otherwise
    """
    
    try:
        # Capture screenshot
        screenshot_result = capture_screenshot_vnc(
            device_ip=device_ip,
            device_name=device_name,
            log_callback=log_callback
        )
        
        if not screenshot_result['success']:
            if log_callback:
                log_callback("[SCREEN CHECK] Screenshot capture failed")
            return False
        
        screenshot_path = screenshot_result['screenshot_path']
        
        if use_ai:
            # Try AI validation first
            bridge = get_ai_bridge()
            
            result = bridge.validate_screen(
                screenshot_path=screenshot_path,
                expected_screen="HOME",
                device_name=device_name,
                use_legacy_fallback=fallback
            )
            
            if result['success']:
                if result['is_valid']:
                    if log_callback:
                        log_callback(
                            f"✅ HOME screen validated by AI "
                            f"(Confidence: {result['confidence']:.0%})"
                        )
                        log_callback(
                            f"   Focus: {', '.join(result['focus_elements'][:2])}"
                        )
                    return True
                else:
                    if log_callback:
                        log_callback(
                            f"❌ Device on {result['detected_screen']}, not HOME"
                        )
                        if result['anomalies']:
                            log_callback(
                                f"   Anomalies: {', '.join(result['anomalies'][:2])}"
                            )
                    return False
            else:
                # AI validation failed
                if log_callback:
                    log_callback(f"⚠️  AI validation error: {result['error']}")
                
                if fallback:
                    if log_callback:
                        log_callback("   Falling back to legacy validation...")
                    from method_utils import is_home_screen
                    return is_home_screen(screenshot_path)
                else:
                    return False
        else:
            # Use legacy validation only
            from method_utils import is_home_screen
            is_home = is_home_screen(screenshot_path)
            
            if is_home and log_callback:
                log_callback("✅ HOME screen detected (legacy validation)")
            elif log_callback:
                log_callback("❌ Not on HOME screen (legacy validation)")
            
            return is_home
    
    except Exception as e:
        if log_callback:
            log_callback(f"❌ Exception in HOME screen check: {e}")
        return False


def validate_screen_with_detail(screenshot_path, expected_screen="HOME", 
                               device_name=None, log_callback=None):
    """
    Validate screen with detailed analysis output
    
    Args:
        screenshot_path (str): Path to screenshot
        expected_screen (str): Expected screen name
        device_name (str): Device name
        log_callback (callable): Logging function
        
    Returns:
        dict: Validation result with details
    """
    
    try:
        bridge = get_ai_bridge()
        
        result = bridge.validate_screen(
            screenshot_path=screenshot_path,
            expected_screen=expected_screen,
            device_name=device_name
        )
        
        if log_callback:
            log_callback(f"\\n[DETAILED ANALYSIS]")
            log_callback(f"  Detected Screen: {result['detected_screen']}")
            log_callback(f"  Expected Screen: {result['expected_screen']}")
            log_callback(f"  Match: {result['device_matched']}")
            log_callback(f"  Confidence: {result['confidence']:.0%}")
            
            if result['focus_elements']:
                log_callback(f"  In Focus: {', '.join(result['focus_elements'][:3])}")
            
            if result['ui_elements']:
                log_callback(
                    f"  UI Elements: {len(result['ui_elements'])} "
                    f"({', '.join(result['ui_elements'][:3])}...)"
                )
            
            if result['anomalies']:
                log_callback(f"  ⚠️  Issues: {', '.join(result['anomalies'])}")
        
        return result
    
    except Exception as e:
        if log_callback:
            log_callback(f"❌ Detailed analysis error: {e}")
        return None


# Replace all calls to is_home_screen() with:
# check_home_screen_ai(..., use_ai=True, fallback=True)

# Example in method_deepsleep.py execution:
def execute_deepsleep_process(...):
    """Updated DeepSleep execution with AI validation"""
    
    # ... existing code ...
    
    # [STEP 5] Verify HOME screen reached after wakeup
    log_message("[STEP 5/7] POST-VALIDATION: Confirming device is online and on HOME")
    
    # Capture screenshot
    screenshot_result = capture_screenshot_vnc(
        device_ip=device_ip,
        device_name=device_name,
        log_callback=log_message
    )
    
    if screenshot_result['success']:
        # Use AI validation instead of legacy validation
        is_home = check_home_screen_ai(
            device_ip=device_ip,
            username=username,
            password=password,
            port=port,
            device_name=device_name,
            log_callback=log_message,
            use_ai=True,
            fallback=True  # Fallback to legacy if AI fails
        )
        
        if is_home:
            log_message("✅ DeepSleep Wakeup SUCCESSFUL - Device on HOME screen")
            
            # Get detailed analysis for better reporting
            details = validate_screen_with_detail(
                screenshot_result['screenshot_path'],
                expected_screen="HOME",
                device_name=device_name,
                log_callback=log_message
            )
            
            return {
                "iteration": iteration,
                "screenshots": screenshots,
                "logs": logs,
                "success": True,
                "details": details
            }
        else:
            log_message("❌ Device NOT on HOME screen after wakeup")
            return {
                "iteration": iteration,
                "screenshots": screenshots,
                "logs": logs,
                "success": False,
                "details": "Device not responding to wakeup command"
            }
    
    # ... rest of code ...
    '''
    
    return code

# ============================================================
# CONFIGURATION IN deploy
# ============================================================

"""
To enable AI Screen Analyzer for method_deepsleep.py:

1. Set API key:
   export ANTHROPIC_API_KEY='sk-ant-xxxxx'

2. Enable in config_ai_screen_analyzer.py:
   AI_SCREEN_ANALYZER_ENABLED = True
   AI_CONFIDENCE_THRESHOLD = 0.7

3. Use in method call:
   result = check_home_screen_ai(
       device_ip=device.ip,
       username=device.username,
       password=device.password,
       port=device.port,
       device_name=device.name,
       log_callback=log_message,
       use_ai=True,
       fallback=True
   )

4. Monitor logs:
   tail -f logs/app.log | grep "AI validation"
"""

# ============================================================
# MIGRATION STEPS
# ============================================================

"""
Step-by-Step Migration Guide:

Step 1: Add imports to method_deepsleep.py
   from services.ai_screen_validation_bridge import get_validation_bridge

Step 2: Add helper functions (see above)
   get_ai_bridge()
   check_home_screen_ai()
   validate_screen_with_detail()

Step 3: Replace legacy validation calls
   OLD: is_home_screen(screenshot_path)
   NEW: check_home_screen_ai(..., use_ai=True, fallback=True)

Step 4: Set AI environment variable
   export ANTHROPIC_API_KEY='sk-ant-xxxxx'

Step 5: Test with DeepSleep execution:
   1. Start app with API key set
   2. Create DeepSleep job with device
   3. Monitor logs for AI validation messages
   4. Verify HomeScreen is correctly identified

Step 6: Monitor and adjust:
   1. Check confidence scores
   2. Adjust threshold if needed
   3. Review focus elements detected
   4. Validate anomaly detection

Step 7: Full deployment
   1. Update all test methods
   2. Enable AI by default
   3. Keep fallback enabled for safety
   4. Monitor API usage and costs
"""

# ============================================================
# LOGGING OUTPUT EXAMPLES
# ============================================================

"""
With AI Validation Enabled:

[STEP 5/7] POST-VALIDATION: Confirming device is online and on HOME
[SCREEN CHECK] Capturing screenshot...
✅ HOME screen validated by AI (Confidence: 95%)
   Focus: App Grid, Navigation Bar
  Detected Screen: HOME
  Expected Screen: HOME
  Match: True
  Confidence: 95%
  In Focus: App Grid, Navigation Bar, Settings Icon
  UI Elements: 12 detected (Status Bar, App Icon, Navigation Button...)
✅ DeepSleep Wakeup SUCCESSFUL - Device on HOME screen
  Iteration 1/5: PASSED

---

With AI Validation Failed (Fallback):

[STEP 5/7] POST-VALIDATION: Confirming device is online and on HOME
[SCREEN CHECK] Capturing screenshot via VNC...
⚠️  AI validation error: API timeout
   Falling back to legacy validation...
✅ HOME screen detected (legacy validation)
✅ DeepSleep Wakeup SUCCESSFUL - Device on HOME screen

---

Screen NOT on HOME:

[STEP 5/7] POST-VALIDATION: Confirming device is online and on HOME
[SCREEN CHECK] Screenshot captured successfully
❌ Device NOT on HOME screen
   Detected: NETFLIX
   Anomalies: App loading, unexpected overlay
❌ DeepSleep method FAILED at Step 5
   Device responded but not on expected screen
"""
