"""
Screen Validation Integration Utilities (Lightweight)

Helper functions to integrate screen validation into device testing workflows
Using OpenCV + ImageHash (ARM64 compatible)
"""

import os
import sys
from datetime import datetime
from typing import Dict, Optional

# Import lightweight validator
try:
    from screen_validator_lightweight import LightweightScreenValidator
    from config_screen_validation import (
        get_screen_config, 
        get_expected_screen_for_method,
        SCREEN_VALIDATION_CONFIG
    )
    SCREEN_VALIDATION_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Screen validation not available: {e}")
    SCREEN_VALIDATION_AVAILABLE = False


# Global validator instance
_validator = None

def get_validator():
    """Get or create validator instance"""
    global _validator
    if _validator is None and SCREEN_VALIDATION_AVAILABLE:
        _validator = LightweightScreenValidator()
    return _validator


def validate_screenshot(screenshot_path: str, expected_screen: str, 
                       device_ip: str = None) -> Dict:
    """
    Validate a screenshot against expected screen state
    
    Args:
        screenshot_path: Path to captured screenshot
        expected_screen: Expected screen name (e.g., "NetflixHome", "DisneyMenu")
        device_ip: Optional device IP for device-specific validation
        
    Returns:
        Dict with validation results
    """
    if not SCREEN_VALIDATION_AVAILABLE:
        return {
            'valid': None,
            'confidence': 0.0,
            'expected': expected_screen,
            'screenshot': screenshot_path,
            'error': 'Screen validation not available'
        }
        
    validator = get_validator()
    if not validator:
        return {
            'valid': None,
            'confidence': 0.0,
            'expected': expected_screen,
            'screenshot': screenshot_path,
            'error': 'Validator initialization failed'
        }
        
    # Run validation
    result = validator.validate_screen(screenshot_path, expected_screen, method="hybrid")
    
    return {
        'valid': result['match'],
        'confidence': result['confidence'],
        'expected': expected_screen,
        'screenshot': screenshot_path,
        'details': result.get('details', {}),
        'method': result.get('method_used', 'hybrid')
    }


def validate_device_screen_after_method(screenshot_path: str, method_name: str,
                                       device_ip: str, stage: str = "after") -> Dict:
    """
    Validate screenshot based on test method expectations
    
    Args:
        screenshot_path: Path to screenshot
        method_name: Test method name (reboot, deepsleep, voice_command, etc.)
        device_ip: Device IP address
        stage: "before" or "after" the method execution
        
    Returns:
        Validation result dict
    """
    # Get expected screen for this method and stage
    expected_screen = get_expected_screen_for_method(method_name, stage, device_ip)
    
    if not expected_screen:
        return {
            'valid': None,
            'confidence': 0.0,
            'error': f'No expected screen defined for {method_name}/{stage}'
        }
        
    return validate_screenshot(screenshot_path, expected_screen, device_ip)


def find_best_screen_match(screenshot_path: str) -> Dict:
    """Find best matching reference screen for a screenshot"""
    if not SCREEN_VALIDATION_AVAILABLE:
        return {'error': 'Screen validation not available'}
        
    validator = get_validator()
    if not validator:
        return {'error': 'Validator initialization failed'}
        
    return validator.find_best_match(screenshot_path)


def print_validation_summary(validation_result: Dict):
    """Print formatted validation summary"""
    print("\n" + "="*60)
    print("📊 SCREEN VALIDATION SUMMARY")
    print("="*60)
    
    if validation_result.get('error'):
        print(f"❌ Error: {validation_result['error']}")
    else:
        status = "✓ VALID" if validation_result.get('valid') else "✗ INVALID"
        confidence = validation_result.get('confidence', 0) * 100
        
        print(f"Status:     {status}")
        print(f"Expected:   {validation_result.get('expected', 'N/A')}")
        print(f"Confidence: {confidence:.1f}%")
        print(f"Method:     {validation_result.get('method', 'N/A')}")
        
        if validation_result.get('details'):
            print("\nDetails:")
            for key, value in validation_result['details'].items():
                if isinstance(value, float):
                    print(f"  {key}: {value:.4f}")
                else:
                    print(f"  {key}: {value}")
                    
    print("="*60 + "\n")


# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python screen_validation_utils.py <screenshot_path> <expected_screen>")
        sys.exit(1)
        
    screenshot = sys.argv[1]
    expected = sys.argv[2]
    
    result = validate_screenshot(screenshot, expected)
    print_validation_summary(result)
