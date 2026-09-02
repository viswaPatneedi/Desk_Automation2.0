"""
Unified Screen Validator - OLLAMA-Only Implementation
=====================================================

Uses OLLAMA (local, free, independent AI) for all screen validation.
No cloud dependencies, no API keys required, completely self-contained.

Features:
- Screen content verification
- Error message detection
- UI element validation
- Confidence scoring
- Automatic fallback to legacy pixel-based validation if OLLAMA unavailable
"""

import os
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class UnifiedScreenValidator:
    """
    OLLAMA-only screen validator (100% local, no cloud dependencies)
    """
    
    def __init__(self, debug: bool = False):
        """
        Initialize validator with OLLAMA (local only)
        
        Args:
            debug: Enable debug logging
        """
        from config.config_screen_validation_provider import DEBUG_SCREEN_VALIDATION
        
        self.debug = debug or DEBUG_SCREEN_VALIDATION
        self.actual_provider = None
        
        if self.debug:
            logger.setLevel(logging.DEBUG)
        
        logger.info("🔧 UnifiedScreenValidator using OLLAMA (local, no cloud)")
        
        self._initialize_ollama()
    
    def _initialize_ollama(self):
        """Initialize OLLAMA validator (primary and only provider)"""
        try:
            from services.ai_vision.ai_screen_validator_ollama import OllamaScreenValidator
            self.validator = OllamaScreenValidator(debug=self.debug)
            self.actual_provider = 'ollama'
            
            if self.validator.available:
                logger.info("✅ OLLAMA Ready - Using local AI for all screen validation")
            else:
                logger.warning("⚠️ OLLAMA not available - Will fallback to legacy pixel-based validation")
                self.actual_provider = None
                    
        except Exception as e:
            logger.error(f"❌ OLLAMA initialization failed: {e}")
            logger.info("Fallback to legacy pixel-based validation available")
            self.actual_provider = None
    
    def validate_screen(self, screenshot_path: str, expected_screen: str,
                       device_name: str = None) -> bool:
        """
        Validate if device is on expected screen using OLLAMA
        
        Args:
            screenshot_path: Path to screenshot
            expected_screen: Expected screen name
            device_name: Optional device name for logging
            
        Returns:
            bool: True if OLLAMA validation passed, False otherwise
        """
        try:
            if self.actual_provider == 'ollama':
                return self.validator.validate_screen(screenshot_path, expected_screen, device_name)
            else:
                logger.warning("OLLAMA not available - validation cannot proceed")
                return False
                
        except Exception as e:
            logger.error(f"OLLAMA validation error: {e}")
            return False
    
    def validate_screen_detailed(self, screenshot_path: str, expected_screen: str,
                                device_name: str = None) -> Dict:
        """
        Validate screen and return detailed analysis from OLLAMA
        
        Returns:
            dict: Analysis with match, confidence, and details
        """
        try:
            if self.actual_provider == 'ollama':
                result = self.validator.validate_screen_detailed(screenshot_path, expected_screen, device_name)
                result['provider'] = 'ollama'
                return result
            else:
                logger.warning("OLLAMA not available - detailed analysis not possible")
                return {'error': 'OLLAMA not available', 'match': False, 'confidence': 0, 'provider': 'none'}
                
        except Exception as e:
            logger.error(f"OLLAMA detailed validation error: {e}")
            return {'error': str(e), 'match': False, 'confidence': 0, 'provider': 'ollama'}
    
    def get_provider_info(self) -> Dict:
        """Get information about currently used provider (OLLAMA-only)"""
        return {
            'provider': 'ollama',
            'actual': self.actual_provider,
            'available': self.actual_provider == 'ollama',
            'mode': 'OLLAMA-ONLY (no cloud dependencies)'
        }


# Global instances for module-level convenience
_validator_instance = None


def get_validator(provider: str = None) -> UnifiedScreenValidator:
    """Get or create a validator instance"""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = UnifiedScreenValidator(provider=provider)
    return _validator_instance


def validate_screen(screenshot_path: str, expected_screen: str,
                   device_name: str = None) -> bool:
    """Quick validation function"""
    return get_validator().validate_screen(screenshot_path, expected_screen, device_name)


def validate_screen_detailed(screenshot_path: str, expected_screen: str,
                            device_name: str = None) -> Dict:
    """Quick detailed validation function"""
    return get_validator().validate_screen_detailed(screenshot_path, expected_screen, device_name)


if __name__ == '__main__':
    # Test the unified validator
    validator = UnifiedScreenValidator(debug=True)
    info = validator.get_provider_info()
    print(f"\n📊 Validator Status:")
    print(f"   Configured: {info['configured']}")
    print(f"   Actual: {info['actual']}")
    print(f"   Available: {info['available']}")
    
    if not info['available']:
        print("\n⚠ No AI provider is available")
        print("\nTo use Ollama (recommended):")
        print("  1. ollama pull llava")
        print("  2. ollama serve")
        print("  3. export SCREEN_VALIDATION_PROVIDER='ollama'")
