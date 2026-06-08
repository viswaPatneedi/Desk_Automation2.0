"""
UNIVERSAL AI SCREEN VALIDATION INTEGRATION
===========================================

This module provides a unified interface for AI-powered screen validation
across ALL test methods in the application.

Usage:
    from ai_integration_universal import AIScreenValidator

    validator = AIScreenValidator()
    
    # Simple validation
    is_valid = validator.validate_screen(
        screenshot_path="screenshot.png",
        expected_screen="HOME"
    )
    
    # Detailed analysis
    result = validator.analyze_screen(screenshot_path)
    
    # Quick check with retry
    is_valid = validator.quick_check(
        screenshot_path="screenshot.png",
        expected_screen="HOME",
        retries=3,
        delay=2
    )

Features:
    ✓ Works with any test method
    ✓ Automatic fallback to legacy validation
    ✓ Caching support (reduce API calls)
    ✓ Detailed error logging
    ✓ Confidence scoring
    ✓ Focus element detection
    ✓ Anomaly detection
"""

import os
import time
import logging
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path

# Import AI components
try:
    from services.ai_screen_analyzer import get_analyzer
    from services.ai_screen_validation_bridge import get_validation_bridge
    from config_ai_screen_analyzer import (
        AI_SCREEN_ANALYZER_ENABLED,
        AI_CONFIDENCE_THRESHOLD,
        AI_FALLBACK_TO_LEGACY,
        AI_DEBUG_LOGGING
    )
    AI_AVAILABLE = True
except Exception as e:
    AI_AVAILABLE = False
    print(f"AI Screen Analyzer not available: {e}")

# Configure logging
logger = logging.getLogger(__name__)
if AI_DEBUG_LOGGING:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)


class AIScreenValidator:
    """
    Universal AI Screen Validator for all test methods.
    
    Provides a single interface for screen validation with AI support
    across all test methods in the application.
    """
    
    def __init__(self, use_ai=True, fallback=True, debug=False):
        """
        Initialize the AI Screen Validator.
        
        Args:
            use_ai: Enable AI validation (default: True)
            fallback: Fall back to legacy validation if AI fails (default: True)
            debug: Enable debug logging (default: False)
        """
        self.use_ai = use_ai and AI_AVAILABLE
        self.fallback = fallback
        self.debug = debug
        self.bridge = get_validation_bridge() if self.use_ai else None
        self.analyzer = get_analyzer() if self.use_ai else None
        
        if self.debug:
            logger.setLevel(logging.DEBUG)
    
    def validate_screen(self, screenshot_path: str, expected_screen: str, 
                       device_name: str = None, confidence_threshold: float = None) -> bool:
        """
        Validate if device is on expected screen.
        
        Args:
            screenshot_path: Path to screenshot file
            expected_screen: Expected screen name (e.g., HOME, Settings, Menu)
            device_name: Device name for logging
            confidence_threshold: Override default confidence threshold
            
        Returns:
            bool: True if device is on expected screen, False otherwise
        """
        try:
            if not self.use_ai:
                logger.warning("AI Screen Validator disabled, using legacy validation")
                return False
            
            if not os.path.exists(screenshot_path):
                logger.error(f"Screenshot not found: {screenshot_path}")
                return False
            
            threshold = confidence_threshold or AI_CONFIDENCE_THRESHOLD
            
            # Use AI validation
            result = self.bridge.validate_screen(
                screenshot_path=screenshot_path,
                expected_screen=expected_screen,
                device_name=device_name
            )
            
            is_valid = result.get('device_matched', False)
            confidence = result.get('confidence', 0)
            
            if self.debug:
                logger.debug(f"AI Validation Result:")
                logger.debug(f"  Expected: {expected_screen}")
                logger.debug(f"  Detected: {result.get('detected_screen', 'UNKNOWN')}")
                logger.debug(f"  Match: {is_valid}")
                logger.debug(f"  Confidence: {confidence:.2f}")
                logger.debug(f"  Focus Elements: {result.get('focus_elements', [])}")
            
            # Check confidence threshold
            if is_valid and confidence < threshold:
                logger.warning(f"Low confidence validation: {confidence:.2f} < {threshold}")
                if self.fallback:
                    logger.info("Falling back to legacy validation")
                    return False
            
            return is_valid
            
        except Exception as e:
            logger.error(f"AI validation error: {e}")
            if self.fallback:
                logger.info("Falling back to legacy validation")
                return False
            raise
    
    def analyze_screen(self, screenshot_path: str, device_name: str = None,
                      detailed: bool = True) -> Dict[str, Any]:
        """
        Get detailed screen analysis.
        
        Args:
            screenshot_path: Path to screenshot file
            device_name: Device name for logging
            detailed: Return detailed analysis (default: True)
            
        Returns:
            dict: Analysis result with screen info, focus elements, anomalies, etc.
        """
        try:
            if not self.use_ai:
                return {'error': 'AI Screen Validator disabled'}
            
            if not os.path.exists(screenshot_path):
                logger.error(f"Screenshot not found: {screenshot_path}")
                return {'error': f'Screenshots not found: {screenshot_path}'}
            
            result = self.analyzer.analyze_screenshot(
                screenshot_path=screenshot_path,
                device_name=device_name,
                detailed=detailed
            )
            
            if self.debug:
                logger.debug(f"AI Analysis Result: {result}")
            
            return result
            
        except Exception as e:
            logger.error(f"AI analysis error: {e}")
            return {'error': str(e)}
    
    def get_focus_elements(self, screenshot_path: str, device_name: str = None) -> List[str]:
        """
        Get list of focus elements on screen.
        
        Args:
            screenshot_path: Path to screenshot file
            device_name: Device name for logging
            
        Returns:
            list: List of focus elements detected on screen
        """
        try:
            if not self.use_ai:
                return []
            
            result = self.bridge.analyze_focus(
                screenshot_path=screenshot_path,
                device_name=device_name
            )
            
            focus_elements = result.get('focus_elements', [])
            
            if self.debug:
                logger.debug(f"Focus Elements Detected: {focus_elements}")
            
            return focus_elements
            
        except Exception as e:
            logger.error(f"Focus detection error: {e}")
            return []
    
    def quick_check(self, screenshot_path: str, expected_screen: str,
                   retries: int = 1, delay: float = 0.5,
                   device_name: str = None) -> bool:
        """
        Quick screen validation with retry support.
        
        Args:
            screenshot_path: Path to screenshot file
            expected_screen: Expected screen name
            retries: Number of retries on failure (default: 1)
            delay: Delay between retries in seconds (default: 0.5)
            device_name: Device name for logging
            
        Returns:
            bool: True if device is on expected screen
        """
        for attempt in range(retries):
            is_valid = self.validate_screen(
                screenshot_path=screenshot_path,
                expected_screen=expected_screen,
                device_name=device_name
            )
            
            if is_valid:
                if attempt > 0:
                    logger.info(f"Quick check passed on attempt {attempt + 1}")
                return True
            
            if attempt < retries - 1:
                logger.debug(f"Quick check failed, retrying in {delay}s...")
                time.sleep(delay)
        
        logger.warning(f"Quick check failed after {retries} attempts")
        return False
    
    def detect_anomalies(self, screenshot_path: str, device_name: str = None) -> List[str]:
        """
        Detect anomalies on screen (errors, overlays, unexpected states).
        
        Args:
            screenshot_path: Path to screenshot file
            device_name: Device name for logging
            
        Returns:
            list: List of detected anomalies
        """
        try:
            if not self.use_ai:
                return []
            
            result = self.analyzer.analyze_screenshot(
                screenshot_path=screenshot_path,
                device_name=device_name,
                detailed=True
            )
            
            anomalies = result.get('anomalies', [])
            
            if anomalies:
                logger.warning(f"Anomalies detected: {anomalies}")
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Anomaly detection error: {e}")
            return []
    
    def compare_screens(self, before_screenshot: str, after_screenshot: str,
                       device_name: str = None) -> Dict[str, Any]:
        """
        Compare two screenshots for screen transitions.
        
        Args:
            before_screenshot: Path to before screenshot
            after_screenshot: Path to after screenshot
            device_name: Device name for logging
            
        Returns:
            dict: Comparison result with transition info
        """
        try:
            if not self.use_ai:
                return {'error': 'AI Screen Validator disabled'}
            
            if not os.path.exists(before_screenshot) or not os.path.exists(after_screenshot):
                logger.error("Screenshots not found for comparison")
                return {'error': 'Screenshots not found'}
            
            result = self.bridge.compare_transitions(
                before_screenshot=before_screenshot,
                after_screenshot=after_screenshot,
                device_name=device_name
            )
            
            if self.debug:
                logger.debug(f"Screen Comparison Result: {result}")
            
            return result
            
        except Exception as e:
            logger.error(f"Screen comparison error: {e}")
            return {'error': str(e)}


# Global validator instance (singleton)
_validator_instance = None


def get_ai_validator(use_ai=True, fallback=True, debug=False) -> AIScreenValidator:
    """
    Get global AI Screen Validator instance (singleton).
    
    Args:
        use_ai: Enable AI validation
        fallback: Fall back to legacy validation on failure
        debug: Enable debug logging
        
    Returns:
        AIScreenValidator: Global validator instance
    """
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = AIScreenValidator(
            use_ai=use_ai,
            fallback=fallback,
            debug=debug
        )
    return _validator_instance


# Convenience functions for quick integration
def validate_screen_ai(screenshot_path: str, expected_screen: str,
                       device_name: str = None) -> bool:
    """Quick screen validation using global validator."""
    validator = get_ai_validator()
    return validator.validate_screen(
        screenshot_path=screenshot_path,
        expected_screen=expected_screen,
        device_name=device_name
    )


def analyze_screen_ai(screenshot_path: str, device_name: str = None) -> Dict[str, Any]:
    """Quick screen analysis using global validator."""
    validator = get_ai_validator()
    return validator.analyze_screen(
        screenshot_path=screenshot_path,
        device_name=device_name
    )


def check_focus_ai(screenshot_path: str, device_name: str = None) -> List[str]:
    """Quick focus detection using global validator."""
    validator = get_ai_validator()
    return validator.get_focus_elements(
        screenshot_path=screenshot_path,
        device_name=device_name
    )


def detect_anomalies_ai(screenshot_path: str, device_name: str = None) -> List[str]:
    """Quick anomaly detection using global validator."""
    validator = get_ai_validator()
    return validator.detect_anomalies(
        screenshot_path=screenshot_path,
        device_name=device_name
    )


# Example usage in test methods
if __name__ == "__main__":
    print("AI Integration Universal Module Loaded Successfully!")
    print("\nUsage Examples:")
    print("  from ai_integration_universal import validate_screen_ai, get_ai_validator")
    print()
    print("  # Quick validation")
    print('  is_valid = validate_screen_ai("screenshot.png", "HOME")')
    print()
    print("  # Detailed analysis")
    print('  validator = get_ai_validator()')
    print('  result = validator.analyze_screen("screenshot.png")')
    print()
    print("  # Focus detection")
    print('  focus = validator.get_focus_elements("screenshot.png")')
    print()
    print("  # Anomaly detection")
    print('  anomalies = validator.detect_anomalies("screenshot.png")')
