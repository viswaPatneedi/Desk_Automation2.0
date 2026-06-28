"""
AI Screen Analyzer Service - Standalone AI Agent for Screen Validation

This service uses Google Gemini Vision API to intelligently analyze device screenshots
and provide comprehensive screen validation results including:
- Whether device is on the desired screen
- What is currently in focus
- UI elements visible
- Screen status and anomalies

✅ FREE TIER: No credit card required, uses Google's free Gemini API
"""

import os
import sys
import json
import threading
import time
from datetime import datetime
from typing import Dict, Optional, List
from pathlib import Path

try:
    import google.generativeai as genai
except ImportError:
    genai = None


class AIScreenAnalyzer:
    """AI-powered screen analysis agent using Google Gemini Vision API (Free Tier)"""
    
    def __init__(self, api_key: str = None, model: str = "gemini-2.0-flash"):
        """
        Initialize AI Screen Analyzer with Google Gemini (Free API)
        
        Args:
            api_key (str): Google Gemini API key (or use GOOGLE_API_KEY env var)
            model (str): Gemini model to use for vision analysis (default: gemini-2.0-flash)
        """
        self.api_key = api_key or os.environ.get('GOOGLE_API_KEY')
        self.model = model
        self.client = None
        self.analysis_cache = {}
        self.lock = threading.Lock()
        
        # Debug: Show API key status
        if self.api_key:
            key_preview = self.api_key[:10] + "..." + self.api_key[-10:] if len(self.api_key) > 20 else "***"
            print(f"📍 [DEBUG] GOOGLE_API_KEY found: {key_preview}")
        else:
            print(f"📍 [DEBUG] GOOGLE_API_KEY status: {os.environ.get('GOOGLE_API_KEY', 'NOT SET')}")
            print(f"📍 [DEBUG] Available env vars containing 'GOOGLE': {[k for k in os.environ if 'GOOGLE' in k]}")
        
        if not self.api_key:
            print("⚠️  Warning: GOOGLE_API_KEY not configured")
            print("   Get free API key from: https://makersuite.google.com/app/apikey")
            print("   Set environment variable: export GOOGLE_API_KEY='your-key-here'")
            print("   AI Screen Analyzer will be disabled")
            return
        
        try:
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(self.model)
            print(f"✅ AI Screen Analyzer initialized with Google Gemini (Free Tier)")
            print(f"   Model: {self.model}")
        except Exception as e:
            print(f"❌ Error initializing Gemini client: {e}")
            self.client = None
    
    def analyze_screenshot(self, screenshot_path: str, expected_screen: str = None,
                          device_name: str = None, detailed: bool = True) -> Dict:
        """
        Analyze a screenshot using AI vision
        
        Args:
            screenshot_path (str): Path to screenshot image
            expected_screen (str): Expected screen name (e.g., 'HOME', 'NETFLIX', 'YOUTUBE')
            device_name (str): Device name for context
            detailed (bool): Whether to provide detailed analysis
            
        Returns:
            dict: {
                'timestamp': str,
                'success': bool,
                'device_matched': bool,  # Is device on expected screen?
                'expected_screen': str,
                'detected_screen': str,  # What screen is actually shown
                'focus_elements': list,  # What's in focus
                'ui_elements': list,     # All visible UI elements
                'anomalies': list,       # Any issues detected
                'confidence': float,     # Confidence level (0-1)
                'analysis_text': str,    # Full AI analysis
                'error': str or None
            }
        """
        
        if not self.client:
            return {
                'success': False,
                'error': 'AI Screen Analyzer not initialized - API key not configured',
                'device_matched': False,
                'timestamp': datetime.now().isoformat()
            }
        
        if not os.path.exists(screenshot_path):
            return {
                'success': False,
                'error': f'Screenshot not found: {screenshot_path}',
                'device_matched': False,
                'timestamp': datetime.now().isoformat()
            }
        
        try:
            # Load image using Gemini's file API
            if not os.path.exists(screenshot_path):
                return {
                    'success': False,
                    'error': f'Screenshot not found: {screenshot_path}',
                    'device_matched': False,
                    'timestamp': datetime.now().isoformat()
                }
            
            # Read image file
            image_file = Path(screenshot_path)
            
            # Build analysis prompt
            prompt = self._build_analysis_prompt(expected_screen, device_name, detailed)
            
            # Call Gemini Vision API
            with open(screenshot_path, 'rb') as f:
                image_data = f.read()
            
            # Upload to Gemini (it handles the image encoding)
            response = self.client.generate_content([
                prompt,
                {
                    'mime_type': self._get_media_type(image_file.suffix),
                    'data': image_data
                }
            ])
            
            # Parse AI response
            analysis_text = response.text
            result = self._parse_analysis_response(analysis_text, expected_screen, screenshot_path)
            result['timestamp'] = datetime.now().isoformat()
            result['analysis_text'] = analysis_text
            result['success'] = True
            
            return result
            
        except Exception as e:
            print(f"❌ Error analyzing screenshot: {e}")
            return {
                'success': False,
                'error': str(e),
                'device_matched': False,
                'timestamp': datetime.now().isoformat()
            }
    
    def validate_screen_match(self, screenshot_path: str, expected_screen: str,
                             device_name: str = None, confidence_threshold: float = 0.7) -> Dict:
        """
        Validate if screenshot matches expected screen
        
        Args:
            screenshot_path (str): Path to screenshot
            expected_screen (str): Expected screen name
            device_name (str): Device name for context
            confidence_threshold (float): Minimum confidence for valid match
            
        Returns:
            dict: Validation result with match status and confidence
        """
        result = self.analyze_screenshot(screenshot_path, expected_screen, device_name)
        
        if not result['success']:
            return result
        
        # Check if device matched and confidence is above threshold
        is_valid = (
            result.get('device_matched', False) and 
            result.get('confidence', 0) >= confidence_threshold
        )
        
        result['is_valid'] = is_valid
        result['validation_passed'] = is_valid
        
        return result
    
    def get_focus_analysis(self, screenshot_path: str, device_name: str = None) -> Dict:
        """
        Get detailed analysis of what's in focus in the screenshot
        
        Args:
            screenshot_path (str): Path to screenshot
            device_name (str): Device name for context
            
        Returns:
            dict: Focus analysis with elements and details
        """
        result = self.analyze_screenshot(screenshot_path, device_name=device_name, detailed=True)
        
        if not result['success']:
            return result
        
        return {
            'success': result['success'],
            'focus_elements': result.get('focus_elements', []),
            'primary_focus': result['focus_elements'][0] if result.get('focus_elements') else None,
            'secondary_focus': result['focus_elements'][1:] if len(result.get('focus_elements', [])) > 1 else [],
            'detected_screen': result.get('detected_screen'),
            'ui_elements': result.get('ui_elements', []),
            'anomalies': result.get('anomalies', []),
            'timestamp': result.get('timestamp')
        }
    
    def batch_analyze_screenshots(self, screenshot_paths: List[str], expected_screen: str = None,
                                 device_name: str = None, parallel: bool = False) -> List[Dict]:
        """
        Analyze multiple screenshots
        
        Args:
            screenshot_paths (list): List of screenshot paths
            expected_screen (str): Expected screen name
            device_name (str): Device name for context
            parallel (bool): Whether to analyze in parallel (not recommended - API rate limits)
            
        Returns:
            list: List of analysis results
        """
        results = []
        
        for path in screenshot_paths:
            result = self.analyze_screenshot(path, expected_screen, device_name)
            results.append(result)
        
        return results
    
    def _build_analysis_prompt(self, expected_screen: str = None, device_name: str = None,
                              detailed: bool = True) -> str:
        """Build the analysis prompt for Claude Vision"""
        
        base_prompt = """Analyze this device screenshot and provide a comprehensive assessment.

IMPORTANT: Respond in JSON format with this structure:
{
    "detected_screen": "NAME of the screen shown (e.g., HOME, NETFLIX, YOUTUBE, SETTINGS, etc.)",
    "screen_description": "Brief description of what screen this is",
    "device_matched": true/false,
    "focus_elements": ["primary element in focus", "secondary element if any"],
    "ui_elements": ["list of all visible UI elements"],
    "status": "current status of device",
    "anomalies": ["any issues or unexpected elements"],
    "confidence": 0.0-1.0,
    "notes": "additional observations"
}

Please analyze:
1. What screen is currently displayed?
2. What elements are in focus or prominent?
3. What UI components are visible?
4. Are there any loading states, errors, or anomalies?
5. Is the device in a normal state?
"""
        
        if expected_screen:
            base_prompt += f"\n\nEXPECTED SCREEN: {expected_screen}"
            base_prompt += f"\nDetermine if the actual screen matches '{expected_screen}' and set device_matched accordingly."
        
        if device_name:
            base_prompt += f"\n\nDEVICE: {device_name}"
        
        if detailed:
            base_prompt += """

DETAILED ANALYSIS REQUIREMENTS:
- Identify all visible text and buttons
- Describe the layout and positioning of elements
- Note any animations or transitions
- Identify focus state of interactive elements
- Report any visual errors or glitches
- Assess overall UI responsiveness indicators
"""
        
        return base_prompt
    
    def _parse_analysis_response(self, response_text: str, expected_screen: str = None,
                                 screenshot_path: str = None) -> Dict:
        """Parse AI response and extract structured data"""
        
        try:
            # Try to extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                parsed = json.loads(json_str)
                
                # Map to standard result format
                return {
                    'detected_screen': parsed.get('detected_screen', 'UNKNOWN'),
                    'screen_description': parsed.get('screen_description', ''),
                    'device_matched': parsed.get('device_matched', False),
                    'focus_elements': parsed.get('focus_elements', []),
                    'ui_elements': parsed.get('ui_elements', []),
                    'anomalies': parsed.get('anomalies', []),
                    'confidence': parsed.get('confidence', 0.5),
                    'status': parsed.get('status', 'unknown'),
                    'expected_screen': expected_screen,
                    'screenshot_path': screenshot_path,
                    'raw_response': response_text
                }
            else:
                # If no JSON found, return raw response
                return {
                    'detected_screen': 'UNKNOWN',
                    'device_matched': False,
                    'confidence': 0.0,
                    'raw_response': response_text,
                    'expected_screen': expected_screen,
                    'screenshot_path': screenshot_path
                }
        
        except json.JSONDecodeError as e:
            return {
                'detected_screen': 'UNKNOWN',
                'device_matched': False,
                'confidence': 0.0,
                'error': f'JSON parsing error: {str(e)}',
                'raw_response': response_text,
                'expected_screen': expected_screen,
                'screenshot_path': screenshot_path
            }
    
    def _get_media_type(self, file_ext: str) -> str:
        """Get MIME type for image file"""
        ext_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        return ext_map.get(file_ext.lower(), 'image/jpeg')
    
    def compare_screenshots(self, before_path: str, after_path: str,
                           device_name: str = None) -> Dict:
        """
        Compare before and after screenshots to detect changes
        
        Args:
            before_path (str): Path to 'before' screenshot
            after_path (str): Path to 'after' screenshot
            device_name (str): Device name for context
            
        Returns:
            dict: Comparison results with detected changes
        """
        
        if not self.client:
            return {
                'success': False,
                'error': 'AI Screen Analyzer not initialized'
            }
        
        try:
            # Read both images
            with open(before_path, 'rb') as f:
                before_data = base64.standard_b64encode(f.read()).decode('utf-8')
            
            with open(after_path, 'rb') as f:
                after_data = base64.standard_b64encode(f.read()).decode('utf-8')
            
            # Get media types
            before_type = self._get_media_type(Path(before_path).suffix)
            after_type = self._get_media_type(Path(after_path).suffix)
            
            # Build comparison prompt
            prompt = """Compare these two screenshots (BEFORE and AFTER) and identify:
1. Major layout changes
2. Content changes
3. Navigation state changes
4. Error or loading states
5. Focus changes
6. Any unexpected transitions

Respond in JSON format:
{
    "changed": true/false,
    "change_type": "navigation|content|loading|error|focus|other",
    "major_changes": ["list of significant changes"],
    "minor_changes": ["list of small changes"],
    "screen_transitioned": true/false,
    "before_screen": "detected screen name",
    "after_screen": "detected screen name",
    "navigation_success": true/false,
    "anomalies": ["any issues detected"],
    "confidence": 0.0-1.0
}
"""
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "BEFORE:"
                            },
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": before_type,
                                    "data": before_data
                                }
                            },
                            {
                                "type": "text",
                                "text": "AFTER:"
                            },
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": after_type,
                                    "data": after_data
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )
            
            response_text = response.content[0].text
            
            # Parse response
            try:
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                json_str = response_text[json_start:json_end]
                parsed = json.loads(json_str)
                
                parsed['success'] = True
                parsed['timestamp'] = datetime.now().isoformat()
                return parsed
            
            except:
                return {
                    'success': True,
                    'raw_response': response_text,
                    'timestamp': datetime.now().isoformat()
                }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }


# Singleton instance
_analyzer_instance = None


def get_analyzer(api_key: str = None) -> AIScreenAnalyzer:
    """Get or create singleton AI Screen Analyzer instance"""
    global _analyzer_instance
    
    if _analyzer_instance is None:
        _analyzer_instance = AIScreenAnalyzer(api_key)
    
    return _analyzer_instance
