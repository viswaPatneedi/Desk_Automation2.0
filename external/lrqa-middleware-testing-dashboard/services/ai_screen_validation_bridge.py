"""
AI Screen Validation Integration - Bridge between AI analyzer and existing validation methods

This module provides integration points for using the AI Screen Analyzer
with existing screen validation code.
"""

import os
from typing import Dict, Optional, Tuple
from services.ai_screen_analyzer import get_analyzer


class AIScreenValidationBridge:
    """Bridge to integrate AI Screen Analyzer with existing validation methods"""
    
    def __init__(self, use_ai: bool = True, fallback_to_legacy: bool = True):
        """
        Initialize the bridge
        
        Args:
            use_ai (bool): Whether to use AI analyzer
            fallback_to_legacy (bool): Whether to fallback to legacy validation if AI fails
        """
        self.use_ai = use_ai and os.environ.get('ANTHROPIC_API_KEY') is not None
        self.fallback_to_legacy = fallback_to_legacy
        self.analyzer = get_analyzer() if self.use_ai else None
    
    def validate_screen(self, screenshot_path: str, expected_screen: str,
                       device_name: str = None, use_legacy_fallback: bool = True) -> Dict:
        """
        Validate screenshot using AI analyzer
        
        Args:
            screenshot_path (str): Path to screenshot
            expected_screen (str): Expected screen name
            device_name (str): Device name for context
            use_legacy_fallback (bool): Whether to fallback to legacy validation
            
        Returns:
            dict: Validation result
        """
        
        if not self.use_ai:
            return {
                'success': False,
                'error': 'AI Screen Analyzer not enabled',
                'is_valid': False,
                'method': 'none'
            }
        
        try:
            # Use AI analyzer
            result = self.analyzer.validate_screen_match(
                screenshot_path,
                expected_screen,
                device_name=device_name,
                confidence_threshold=0.7
            )
            
            # Map result to standard validation format
            return {
                'success': result.get('success', False),
                'is_valid': result.get('is_valid', False),
                'device_matched': result.get('device_matched', False),
                'detected_screen': result.get('detected_screen'),
                'expected_screen': expected_screen,
                'confidence': result.get('confidence', 0),
                'focus_elements': result.get('focus_elements', []),
                'ui_elements': result.get('ui_elements', []),
                'anomalies': result.get('anomalies', []),
                'method': 'ai_vision',
                'timestamp': result.get('timestamp'),
                'error': result.get('error')
            }
        
        except Exception as e:
            if use_legacy_fallback and self.fallback_to_legacy:
                return {
                    'success': False,
                    'error': f'AI validation failed: {str(e)}. Fallback to legacy validation.',
                    'is_valid': False,
                    'method': 'fallback_required'
                }
            else:
                return {
                    'success': False,
                    'error': str(e),
                    'is_valid': False,
                    'method': 'ai_vision'
                }
    
    def analyze_focus(self, screenshot_path: str, device_name: str = None) -> Dict:
        """
        Get detailed focus analysis
        
        Args:
            screenshot_path (str): Path to screenshot
            device_name (str): Device name for context
            
        Returns:
            dict: Focus analysis result
        """
        
        if not self.use_ai:
            return {
                'success': False,
                'error': 'AI Screen Analyzer not enabled'
            }
        
        return self.analyzer.get_focus_analysis(screenshot_path, device_name)
    
    def compare_transitions(self, before_path: str, after_path: str,
                           device_name: str = None) -> Dict:
        """
        Compare screen transitions
        
        Args:
            before_path (str): Path to before screenshot
            after_path (str): Path to after screenshot
            device_name (str): Device name for context
            
        Returns:
            dict: Comparison result
        """
        
        if not self.use_ai:
            return {
                'success': False,
                'error': 'AI Screen Analyzer not enabled'
            }
        
        return self.analyzer.compare_screenshots(before_path, after_path, device_name)
    
    def get_screen_status(self, screenshot_path: str, device_name: str = None) -> Tuple[bool, str, list]:
        """
        Quick method to get screen status
        
        Returns:
            tuple: (is_healthy, screen_name, focus_elements)
        """
        
        if not self.use_ai:
            return False, 'UNKNOWN', []
        
        result = self.analyzer.analyze_screenshot(screenshot_path, device_name=device_name)
        
        if not result.get('success'):
            return False, 'ERROR', []
        
        is_healthy = len(result.get('anomalies', [])) == 0
        screen_name = result.get('detected_screen', 'UNKNOWN')
        focus = result.get('focus_elements', [])
        
        return is_healthy, screen_name, focus


# Singleton bridge instance
_bridge_instance = None


def get_validation_bridge(use_ai: bool = True) -> AIScreenValidationBridge:
    """Get or create singleton validation bridge"""
    global _bridge_instance
    
    if _bridge_instance is None:
        _bridge_instance = AIScreenValidationBridge(use_ai=use_ai)
    
    return _bridge_instance


def validate_screen_with_ai(screenshot_path: str, expected_screen: str,
                           device_name: str = None) -> Dict:
    """Convenience function for one-off validation"""
    bridge = get_validation_bridge()
    return bridge.validate_screen(screenshot_path, expected_screen, device_name)


def analyze_screen_focus(screenshot_path: str, device_name: str = None) -> Dict:
    """Convenience function to analyze focus"""
    bridge = get_validation_bridge()
    return bridge.analyze_focus(screenshot_path, device_name)
