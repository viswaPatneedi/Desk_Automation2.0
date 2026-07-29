"""
INDEPENDENT AI SCREEN VALIDATOR - OLLAMA VERSION
================================================

This module provides a truly independent screen validation using Ollama LLaVA model.
NO external API keys needed. NO cloud services. Runs 100% locally and free.

Usage:
    from services.ai_vision.ai_screen_validator_ollama import OllamaScreenValidator
    
    validator = OllamaScreenValidator()
    
    # Simple validation
    is_valid = validator.validate_screen(
        screenshot_path="screenshot.png",
        expected_screen="HOME"
    )
    
    # Get confidence score
    result = validator.validate_screen_detailed(
        screenshot_path="screenshot.png",
        expected_screen="HOME"
    )
    print(f"Match: {result['match']}, Confidence: {result['confidence']}")

Features:
    ✓ 100% Local - No cloud dependencies
    ✓ Free - No API keys needed
    ✓ Fast - LLaVA model optimized for speed
    ✓ Accurate - Uses Ollama vision intelligence
    ✓ Independent - Requires only Ollama service running locally
    ✓ Fallback support - Can degrade to lightweight validation
"""

import os
import time
import json
import logging
import base64
from pathlib import Path
from typing import Dict, Optional, Tuple
from PIL import Image

logger = logging.getLogger(__name__)


class OllamaScreenValidator:
    """
    Screen validation using Ollama (100% local, free, no API keys)
    """
    
    def __init__(self, 
                 ollama_url: str = None,
                 model: str = None,
                 timeout: int = 45,
                 debug: bool = False):
        """
        Initialize Ollama Screen Validator
        
        Args:
            ollama_url: Ollama API base URL (default: http://localhost:11434)
            model: Model to use (default: llava)
            timeout: Request timeout in seconds (default: 45)
            debug: Enable debug logging (default: False)
        """
        self.ollama_url = ollama_url or os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
        self.model = model or os.environ.get('OLLAMA_MODEL', 'llava')
        self.timeout = timeout
        self.debug = debug
        self.available = False
        
        if debug:
            logger.setLevel(logging.DEBUG)
        
        self._check_ollama_availability()
    
    def _check_ollama_availability(self):
        """Check if Ollama service is running and model is available"""
        try:
            import requests
            response = requests.get(
                f"{self.ollama_url}/api/tags",
                timeout=5
            )
            
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m['name'].split(':')[0] for m in models]
                
                if self.model in model_names:
                    self.available = True
                    logger.info(f"✅ Ollama available with model: {self.model}")
                else:
                    logger.warning(f"⚠ Model '{self.model}' not found. Available: {model_names}")
                    logger.warning(f"   Install with: ollama pull {self.model}")
            else:
                logger.error(f"❌ Ollama not responding (status {response.status_code})")
        except Exception as e:
            logger.error(f"❌ Ollama not available: {e}")
            logger.info(f"   Start Ollama with: ollama serve")
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64 for API transmission"""
        try:
            with open(image_path, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encoding image: {e}")
            return None
    
    def _analyze_with_ollama(self, screenshot_path: str, 
                           expected_screen: str) -> Dict:
        """
        Analyze screenshot using Ollama LLaVA vision model
        
        Returns:
            dict: Analysis result with screen info and confidence
        """
        try:
            import requests
            
            if not os.path.exists(screenshot_path):
                return {'error': f'Screenshot not found: {screenshot_path}'}
            
            # Encode image
            img_base64 = self._encode_image(screenshot_path)
            if not img_base64:
                return {'error': 'Failed to encode image'}
            
            # Prepare analysis prompt - simplified for faster response
            prompt = f"""Screen: {expected_screen}

Analyze this screenshot BRIEFLY:
1. Current screen/app name?
2. Match? (Yes/No + confidence 0-100)
3. Main UI elements?

Be VERY CONCISE."""
            
            # Call Ollama API
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "images": [img_base64],
                    "stream": False,
                    "temperature": 0.3,  # Lower temperature for more consistent results
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                analysis_text = result.get('response', '')
                
                if not analysis_text or len(analysis_text.strip()) < 5:
                    logger.warning(f"Empty or invalid OLLAMA response")
                    return {'error': 'Empty OLLAMA response'}
                
                # Parse response for confidence
                confidence = self._extract_confidence(analysis_text, expected_screen)
                is_match = confidence >= 60  # 60% threshold
                
                # Extract detected screen name from analysis
                detected_screen = self._extract_screen_name(analysis_text, expected_screen)
                
                return {
                    'success': True,
                    'match': is_match,
                    'confidence': confidence,
                    'detected_screen': detected_screen or expected_screen,
                    'analysis': analysis_text,
                    'model': self.model,
                    'provider': 'ollama'
                }
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                return {'error': f'Ollama API returned {response.status_code}'}
        
        except requests.exceptions.Timeout:
            logger.error(f"OLLAMA request timed out after {self.timeout}s")
            return {'error': f'Ollama timeout after {self.timeout}s'}
        except Exception as e:
            logger.error(f"Ollama analysis error: {e}")
            return {'error': str(e)}
    
    def _extract_confidence(self, analysis_text: str, expected_screen: str) -> int:
        """
        Extract confidence score from Ollama analysis
        
        Looks for patterns like:
        - "confidence: 85"
        - "90% confident"
        - "confidence 0-100: 75"
        """
        analysis_lower = analysis_text.lower()
        
        # Look for explicit confidence mention
        import re
        
        # Pattern: "confidence: XX" or "confidence XX" or "XX% confident"
        patterns = [
            r'confidence\s*(?:score)?[:\s]*(\d+)',
            r'(\d+)%\s*confident',
            r'confidence\s*\(0-100\)\s*[:\s]*(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, analysis_lower)
            if match:
                confidence = int(match.group(1))
                logger.debug(f"Extracted confidence: {confidence}% from: {analysis_text[:100]}...")
                return min(100, max(0, confidence))
        
        # Fallback: keyword-based scoring
        positive_keywords = [
            'yes', 'correct', 'match', 'confirmed', 'accurate',
            'exactly', 'displays', expected_screen.lower()
        ]
        negative_keywords = [
            'no', 'not', 'different', 'wrong', 'incorrect', 'mismatch'
        ]
        
        positive_count = sum(1 for kw in positive_keywords if kw in analysis_lower)
        negative_count = sum(1 for kw in negative_keywords if kw in analysis_lower)
        
        # Calculate confidence based on keyword presence
        if positive_count > 0 and negative_count == 0:
            confidence = 85
        elif positive_count > negative_count:
            confidence = 70
        elif negative_count > positive_count:
            confidence = 20
        else:
            confidence = 50
        
        logger.debug(f"Inferred confidence: {confidence}% (positive: {positive_count}, negative: {negative_count})")
        return confidence
    
    def validate_screen(self, screenshot_path: str, expected_screen: str,
                       device_name: str = None) -> bool:
        """
        Validate if device is on expected screen
        
        Args:
            screenshot_path: Path to screenshot
            expected_screen: Expected screen name
            device_name: Optional device name for logging
            
        Returns:
            bool: True if match, False otherwise
        """
        if not self.available:
            logger.error("Ollama not available for validation")
            return False
        
        result = self._analyze_with_ollama(screenshot_path, expected_screen)
        
        if 'error' in result:
            logger.error(f"Validation error: {result['error']}")
            return False
        
        match = result.get('match', False)
        confidence = result.get('confidence', 0)
        
        logger.info(f"Screen validation: {expected_screen} | Match: {match} | Confidence: {confidence}%")
        
        return match
    
    def validate_screen_detailed(self, screenshot_path: str, 
                                expected_screen: str,
                                device_name: str = None) -> Dict:
        """
        Validate screen and return detailed analysis
        
        Returns:
            dict: Full analysis with match, confidence, and details
        """
        if not self.available:
            return {'error': 'Ollama not available', 'match': False}
        
        result = self._analyze_with_ollama(screenshot_path, expected_screen)
        
        if self.debug:
            logger.debug(f"Detailed validation result: {json.dumps(result, indent=2)}")
        
        return result
    
    def quick_check(self, screenshot_path: str, expected_screen: str,
                   retries: int = 1, delay: float = 0.5) -> bool:
        """
        Quick validation with retry support
        
        Args:
            screenshot_path: Path to screenshot
            expected_screen: Expected screen
            retries: Number of retries
            delay: Delay between retries (seconds)
            
        Returns:
            bool: True if validation passed
        """
        for attempt in range(retries):
            if self.validate_screen(screenshot_path, expected_screen):
                if attempt > 0:
                    logger.info(f"Quick check passed on attempt {attempt + 1}/{retries}")
                return True
            
            if attempt < retries - 1:
                logger.debug(f"Quick check failed, retrying in {delay}s...")
                time.sleep(delay)
        
        logger.warning(f"Quick check failed after {retries} attempt(s)")
        return False
    
    def _extract_screen_name(self, analysis_text: str, expected_screen: str) -> Optional[str]:
        """
        Extract detected screen name from OLLAMA analysis text
        
        Tries to identify screen name mentioned in the analysis
        """
        analysis_lower = analysis_text.lower()
        expected_lower = expected_screen.lower()
        
        # If expected screen is mentioned in analysis, that's likely the detected screen
        if expected_lower in analysis_lower:
            return expected_screen
        
        # Look for explicit screen mentions
        screen_keywords = {
            'netflix': ['netflix', 'profile', 'search', 'asset', 'playback'],
            'home': ['home', 'xumo', 'tiles', 'apps'],
            'youtube': ['youtube', 'video', 'search'],
            'disney': ['disney', 'plus'],
        }
        
        for screen, keywords in screen_keywords.items():
            if any(kw in analysis_lower for kw in keywords):
                return screen.title()
        
        return None


# Convenience function for quick usage
def validate_screen_ollama(screenshot_path: str, expected_screen: str,
                          timeout: int = 60) -> Dict:
    """
    Quick screen validation using Ollama
    
    Args:
        screenshot_path: Path to screenshot
        expected_screen: Expected screen name
        timeout: Request timeout
        
    Returns:
        dict: Validation result with match and confidence
    """
    validator = OllamaScreenValidator(timeout=timeout)
    return validator.validate_screen_detailed(screenshot_path, expected_screen)


if __name__ == '__main__':
    # Test if Ollama is available
    validator = OllamaScreenValidator(debug=True)
    
    if validator.available:
        print("✅ Ollama Screen Validator ready for use")
        print(f"   Model: {validator.model}")
        print(f"   URL: {validator.ollama_url}")
    else:
        print("❌ Ollama is not available")
        print("   Start it with: ollama serve")
        print(f"   Pull model with: ollama pull {validator.model}")
