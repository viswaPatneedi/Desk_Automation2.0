"""
INDEPENDENT AI SCREEN VALIDATOR - OLLAMA VERSION
================================================

This module provides independent screen validation using a local Ollama vision model.
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
    ✓ Uses an installed Ollama vision model
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
            model: Model to use (default: configured OLLAMA_MODEL)
            timeout: Request timeout in seconds (default: 45)
            debug: Enable debug logging (default: False)
        """
        self.ollama_url = ollama_url or os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
        self.model = model or os.environ.get('OLLAMA_MODEL', 'qwen3.5:9b')
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
                model_names = [m['name'] for m in models]
                available_model_families = {name.split(':')[0] for name in model_names}

                if self.model in model_names or self.model.split(':')[0] in available_model_families:
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
                           expected_screen: str,
                           reference_path: Optional[str] = None,
                           layout_only: bool = False) -> Dict:
        """
        Analyze screenshot using the configured Ollama vision model

        layout_only: judge by page type/layout and ignore rotating content (banners,
        posters, thumbnails, clock, focus), as needed for screen identification.
        
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
            
            images = [img_base64]
            if reference_path:
                ref_base64 = self._encode_image(reference_path)
                if not ref_base64:
                    return {'error': f'Failed to encode reference image: {reference_path}'}
                images = [ref_base64, img_base64]
                task = (f'The FIRST image is the REFERENCE screen "{expected_screen}". '
                        'The SECOND image is the CAPTURED screen. Decide whether the captured '
                        'screen shows the same screen as the reference (same page/app, same main '
                        'layout and content; ignore minor differences such as focus highlight, '
                        'clock or small animated content).')
                if layout_only:
                    task += (' Judge by page type and layout only: the same persistent UI elements '
                             '(logo, header, menu/app row, tile grid, dialog structure). The large hero '
                             'banner, promo tiles, posters, show titles and thumbnails rotate and are '
                             'EXPECTED to differ; do not treat that as a different screen.')
            else:
                task = f'Decide whether this screenshot shows the screen: "{expected_screen}".'
            strict = ('If it is a different page/app/dialog, match must be false.' if layout_only
                      else 'Be strict: if it is a different screen, match must be false.')
            prompt = (task + ' ' + strict + ' '
                      'Reply with ONLY a JSON object: {"match": true|false, "confidence": 0-100, '
                      '"detected_screen": "short name of what is shown", "reason": "one short sentence"}')
            
            # Call Ollama API
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "images": images,
                    "stream": False,
                    "think": False,
                    "options": {"temperature": 0.3},  # Lower temperature for more consistent results
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                analysis_text = result.get('response', '')
                
                if not analysis_text or len(analysis_text.strip()) < 5:
                    logger.warning(f"Empty or invalid OLLAMA response")
                    return {'error': 'Empty OLLAMA response'}
                
                parsed = self._parse_json_verdict(analysis_text)
                if parsed is not None:
                    confidence = parsed['confidence']
                    is_match = parsed['match'] and confidence >= 60
                    detected_screen = parsed['detected_screen']
                else:
                    confidence = self._extract_confidence(analysis_text, expected_screen)
                    is_match = confidence >= 60  # 60% threshold
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
    
    @staticmethod
    def _parse_json_verdict(text: str) -> Optional[Dict]:
        """Parse the structured JSON verdict; return None if the reply is not valid JSON."""
        try:
            data = json.loads(text[text.index('{'):text.rindex('}') + 1])
            match = data['match']
            if isinstance(match, str):
                match = match.strip().lower() == 'true'
            confidence = int(float(data.get('confidence', 100 if match else 0)))
            return {'match': bool(match), 'confidence': min(100, max(0, confidence)),
                    'detected_screen': data.get('detected_screen')}
        except (ValueError, KeyError, TypeError):
            return None

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
                       device_name: str = None,
                       reference_path: Optional[str] = None) -> bool:
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
        
        result = self._analyze_with_ollama(screenshot_path, expected_screen, reference_path)
        
        if 'error' in result:
            logger.error(f"Validation error: {result['error']}")
            return False
        
        match = result.get('match', False)
        confidence = result.get('confidence', 0)
        
        logger.info(f"Screen validation: {expected_screen} | Match: {match} | Confidence: {confidence}%")
        
        return match
    
    def validate_screen_detailed(self, screenshot_path: str, 
                                expected_screen: str,
                                device_name: str = None,
                                reference_path: Optional[str] = None) -> Dict:
        """
        Validate screen and return detailed analysis
        
        Returns:
            dict: Full analysis with match, confidence, and details
        """
        if not self.available:
            return {'error': 'Ollama not available', 'match': False}
        
        result = self._analyze_with_ollama(screenshot_path, expected_screen, reference_path)
        
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

    REFERENCE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                 'reference_screens')
    _IMAGE_EXTS = ('.png', '.jpg', '.jpeg')

    @classmethod
    def list_reference_screens(cls, reference_dir: Optional[str] = None) -> Dict[str, str]:
        """Map screen name (file stem) -> image path for every image under reference_screens/."""
        base = reference_dir or cls.REFERENCE_DIR
        screens = {}
        for root, _dirs, files in os.walk(base):
            for fname in sorted(files):
                if fname.lower().endswith(cls._IMAGE_EXTS):
                    screens.setdefault(os.path.splitext(fname)[0], os.path.join(root, fname))
        return screens

    @staticmethod
    def _thumb(path: str, bottom_only: bool = False):
        with Image.open(path) as img:
            img = img.convert('RGB')
            if bottom_only:
                w, h = img.size
                img = img.crop((0, int(h * 0.62), w, h))
            return list(img.resize((24, 24)).getdata())

    @classmethod
    def _rank_references(cls, screenshot_path: str, screens: Dict[str, str]):
        """Cheap pixel-distance pre-filter so the vision model only compares the closest few references."""
        def distance(a, b):
            return sum(abs(x - y) for p, q in zip(a, b) for x, y in zip(p, q)) / (len(a) * 3 * 255.0)

        # Hero banners rotate, so weight the mostly-static bottom strip as much as the full frame.
        shot, shot_bottom = cls._thumb(screenshot_path), cls._thumb(screenshot_path, True)
        ranked = []
        for name, path in screens.items():
            try:
                dist = 0.5 * distance(shot, cls._thumb(path)) + 0.5 * distance(shot_bottom, cls._thumb(path, True))
            except Exception:
                continue
            ranked.append((dist, name, path))
        ranked.sort()
        return ranked

    def identify_screen(self, screenshot_path: str, top_k: int = 3,
                        accept_confidence: int = 85,
                        reference_dir: Optional[str] = None) -> Dict:
        """
        Work out which known screen a screenshot shows by comparing it with the images in
        reference_screens/. The closest references (by image similarity) are shown to the
        Ollama vision model one by one; the best confirmed match wins.

        Returns:
            dict: {'success', 'detected_screen' (reference name or 'Unknown'), 'confidence' (0-1),
                   'reference_path', 'candidates': [...], 'description'}
        """
        if not self.available:
            return {'error': 'Ollama not available'}
        if not os.path.exists(screenshot_path):
            return {'error': f'Screenshot not found: {screenshot_path}'}

        screens = self.list_reference_screens(reference_dir)
        if not screens:
            return {'error': 'No reference screens found'}

        candidates, best, description = [], None, ''
        for dist, name, path in self._rank_references(screenshot_path, screens)[:max(1, top_k)]:
            result = self._analyze_with_ollama(screenshot_path, name, path, layout_only=True)
            if 'error' in result:
                candidates.append({'screen': name, 'error': result['error']})
                continue
            confidence = result.get('confidence', 0)
            description = description or result.get('detected_screen') or ''
            candidates.append({'screen': name, 'match': result.get('match', False),
                               'confidence': confidence, 'similarity': round(1 - dist, 3)})
            if result.get('match') and (best is None or confidence > best['confidence']):
                best = {'screen': name, 'confidence': confidence, 'path': path}
            if best and best['confidence'] >= accept_confidence:
                break

        if best:
            return {'success': True, 'detected_screen': best['screen'],
                    'confidence': best['confidence'] / 100.0, 'reference_path': best['path'],
                    'candidates': candidates, 'description': description, 'provider': 'ollama'}
        if all('error' in c for c in candidates):
            return {'error': candidates[0]['error'] if candidates else 'Identification failed'}
        return {'success': True, 'detected_screen': 'Unknown', 'confidence': 0.0,
                'reference_path': None, 'candidates': candidates,
                'description': description, 'provider': 'ollama'}


def identify_screen_ollama(screenshot_path: str, timeout: int = 60, top_k: int = 3) -> Dict:
    """Identify which reference screen a screenshot shows (see OllamaScreenValidator.identify_screen)."""
    return OllamaScreenValidator(timeout=timeout).identify_screen(screenshot_path, top_k=top_k)


def ocr_ollama(image, timeout: int = 90) -> Optional[str]:
    """
    Read all visible text from a screenshot with the Ollama vision model.

    image: file path or PIL image. Returns the text ('' if none) or None when Ollama
    is unavailable / the call failed, so callers can fall back to another OCR engine.
    """
    import io
    import requests
    validator = OllamaScreenValidator(timeout=timeout)
    if not validator.available:
        return None
    try:
        if isinstance(image, (str, os.PathLike)):
            encoded = validator._encode_image(str(image))
        else:
            buf = io.BytesIO()
            image.convert('RGB').save(buf, format='PNG')
            encoded = base64.b64encode(buf.getvalue()).decode('utf-8')
        if not encoded:
            return None
        response = requests.post(
            f"{validator.ollama_url}/api/generate",
            json={"model": validator.model, "images": [encoded], "stream": False, "think": False,
                  "prompt": ("Transcribe ALL text visible in this TV screen screenshot (titles, menu labels, "
                             "dialogs, error messages, clock). Output only the text, one item per line, "
                             "no commentary."),
                  "options": {"temperature": 0.1}},
            timeout=timeout)
        if response.status_code != 200:
            return None
        return (response.json().get('response') or '').strip()
    except Exception as e:
        logger.warning(f"Ollama OCR failed: {e}")
        return None


def screen_matches_ollama(screenshot_path: str, name_pattern: str, timeout: int = 60,
                          top_k: int = 4) -> Optional[Dict]:
    """
    Identify the screen with Ollama and test whether the matched reference name matches
    the regex name_pattern. Returns {'is_match', 'confidence', 'detected_screen', ...} or
    None when AI is unavailable (caller should fall back).
    """
    import re
    result = identify_screen_ollama(screenshot_path, timeout=timeout, top_k=top_k)
    if not result or result.get('error'):
        return None
    detected = result.get('detected_screen', 'Unknown')
    return {'is_match': bool(re.search(name_pattern, detected, re.IGNORECASE)),
            'confidence': result.get('confidence', 0.0), 'detected_screen': detected,
            'validation_method': 'ollama_ai', 'description': result.get('description', '')}


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
