"""
Unified Screen Validator - Provider Abstraction Layer
=====================================================

Automatically selects and uses the configured screen validation provider:
- Ollama (local, free, independent)
- Gemini (cloud, requires API key)
- Hybrid (tries local first, falls back to cloud)
- Legacy (pixel-based fallback)

Drop-in replacement for existing validation code.
"""

import os
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class UnifiedScreenValidator:
    """
    Universal screen validator that uses configured provider
    """
    
    def __init__(self, provider: str = None, debug: bool = False):
        """
        Initialize validator with configured provider
        
        Args:
            provider: Override provider ('ollama', 'gemini', 'hybrid', 'legacy')
            debug: Enable debug logging
        """
        from config.config_screen_validation_provider import (
            SCREEN_VALIDATION_PROVIDER,
            DEBUG_SCREEN_VALIDATION
        )
        
        self.provider = provider or os.getenv('SCREEN_VALIDATION_PROVIDER', SCREEN_VALIDATION_PROVIDER)
        self.debug = debug or DEBUG_SCREEN_VALIDATION
        self.actual_provider = None
        
        if self.debug:
            logger.setLevel(logging.DEBUG)
        
        logger.info(f"🔧 UnifiedScreenValidator initializing with provider: {self.provider}")
        
        self._initialize_provider()
    
    def _initialize_provider(self):
        """Initialize the configured provider"""
        try:
            if self.provider == 'ollama':
                from services.ai_vision.ai_screen_validator_ollama import OllamaScreenValidator
                self.validator = OllamaScreenValidator(debug=self.debug)
                self.actual_provider = 'ollama'
                
                if self.validator.available:
                    logger.info("✅ Using Ollama (local, free, independent)")
                else:
                    logger.warning("⚠ Ollama not available, will fallback to legacy validation")
                    
            elif self.provider == 'gemini':
                try:
                    from services.ai_screen_analyzer import AIScreenAnalyzer
                    self.validator = AIScreenAnalyzer()
                    self.actual_provider = 'gemini' if self.validator.client else 'legacy'
                    
                    if self.validator.client:
                        logger.info("✅ Using Gemini (cloud-based)")
                    else:
                        logger.warning("⚠ Gemini not configured, will use legacy validation")
                except Exception as e:
                    logger.warning(f"⚠ Gemini initialization failed: {e}")
                    self.actual_provider = 'legacy'
                    
            elif self.provider == 'hybrid':
                # Initialize both and use with fallback
                try:
                    from services.ai_vision.ai_screen_validator_ollama import OllamaScreenValidator
                    self.ollama = OllamaScreenValidator(debug=self.debug)
                    ollama_available = self.ollama.available
                except:
                    self.ollama = None
                    ollama_available = False
                
                try:
                    from services.ai_screen_analyzer import AIScreenAnalyzer
                    self.gemini = AIScreenAnalyzer()
                    gemini_available = self.gemini.client is not None
                except:
                    self.gemini = None
                    gemini_available = False
                
                if ollama_available or gemini_available:
                    self.actual_provider = 'hybrid'
                    providers = []
                    if ollama_available:
                        providers.append("Ollama (local)")
                    if gemini_available:
                        providers.append("Gemini (cloud)")
                    logger.info(f"✅ Using Hybrid mode: {', '.join(providers)}")
                else:
                    self.actual_provider = 'legacy'
                    logger.warning("⚠ Neither Ollama nor Gemini available, using legacy validation")
                    
            else:  # legacy
                self.actual_provider = 'legacy'
                logger.info("ℹ Using legacy pixel-based validation")
                
        except Exception as e:
            logger.error(f"Error initializing provider: {e}")
            self.actual_provider = 'legacy'
    
    def validate_screen(self, screenshot_path: str, expected_screen: str,
                       device_name: str = None) -> bool:
        """
        Validate if device is on expected screen
        
        Args:
            screenshot_path: Path to screenshot
            expected_screen: Expected screen name
            device_name: Optional device name for logging
            
        Returns:
            bool: True if validation passed
        """
        try:
            if self.actual_provider == 'ollama':
                return self.validator.validate_screen(screenshot_path, expected_screen, device_name)
            
            elif self.actual_provider == 'gemini':
                result = self.validator.validate_screenshot(screenshot_path, expected_screen, device_name)
                return result.get('device_matched', False)
            
            elif self.actual_provider == 'hybrid':
                # Try Ollama first
                if self.ollama and self.ollama.available:
                    try:
                        result = self.ollama.validate_screen_detailed(screenshot_path, expected_screen, device_name)
                        confidence = result.get('confidence', 0) / 100.0  # Convert from 0-100 to 0-1
                        
                        from config.config_screen_validation_provider import HYBRID_FALLBACK_CONFIDENCE_THRESHOLD
                        if confidence >= HYBRID_FALLBACK_CONFIDENCE_THRESHOLD:
                            logger.debug(f"Ollama passed with {confidence:.2%} confidence")
                            return result.get('match', False)
                        else:
                            logger.debug(f"Ollama confidence low ({confidence:.0%}), trying Gemini...")
                    except Exception as e:
                        logger.debug(f"Ollama failed: {e}, trying Gemini...")
                
                # Fallback to Gemini
                if self.gemini and self.gemini.client:
                    try:
                        result = self.gemini.validate_screenshot(screenshot_path, expected_screen, device_name)
                        return result.get('device_matched', False)
                    except Exception as e:
                        logger.error(f"Gemini fallback failed: {e}")
                
                # If both failed, return False (will trigger legacy fallback)
                return False
            
            else:  # legacy
                logger.info("Using fallback legacy validation (pixel-based)")
                return False
                
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False
    
    def validate_screen_detailed(self, screenshot_path: str, expected_screen: str,
                                device_name: str = None) -> Dict:
        """
        Validate screen and return detailed analysis
        
        Returns:
            dict: Analysis with match, confidence, and details
        """
        try:
            if self.actual_provider == 'ollama':
                return self.validator.validate_screen_detailed(screenshot_path, expected_screen, device_name)
            
            elif self.actual_provider == 'gemini':
                result = self.validator.validate_screenshot(screenshot_path, expected_screen, device_name)
                return {
                    'match': result.get('device_matched', False),
                    'confidence': result.get('confidence', 0),
                    'analysis': result.get('analysis_text', ''),
                    'provider': 'gemini'
                }
            
            elif self.actual_provider == 'hybrid':
                # Try Ollama first
                if self.ollama and self.ollama.available:
                    try:
                        result = self.ollama.validate_screen_detailed(screenshot_path, expected_screen, device_name)
                        confidence = result.get('confidence', 0) / 100.0
                        
                        from config.config_screen_validation_provider import HYBRID_FALLBACK_CONFIDENCE_THRESHOLD
                        if confidence >= HYBRID_FALLBACK_CONFIDENCE_THRESHOLD:
                            result['fallback_used'] = False
                            return result
                    except Exception as e:
                        logger.debug(f"Ollama analysis failed: {e}")
                
                # Fallback to Gemini
                if self.gemini and self.gemini.client:
                    try:
                        result = self.gemini.validate_screenshot(screenshot_path, expected_screen, device_name)
                        return {
                            'match': result.get('device_matched', False),
                            'confidence': result.get('confidence', 0),
                            'analysis': result.get('analysis_text', ''),
                            'provider': 'gemini',
                            'fallback_used': True
                        }
                    except Exception as e:
                        logger.error(f"Gemini fallback failed: {e}")
                
                return {'error': 'Both Ollama and Gemini failed', 'match': False, 'confidence': 0}
            
            else:  # legacy
                return {'error': 'Legacy validation has no detailed analysis', 'match': False}
                
        except Exception as e:
            logger.error(f"Detailed validation error: {e}")
            return {'error': str(e), 'match': False}
    
    def get_provider_info(self) -> Dict:
        """Get information about currently used provider"""
        return {
            'configured': self.provider,
            'actual': self.actual_provider,
            'available': self.actual_provider != 'legacy'
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
