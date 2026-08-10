"""
OLLAMA Integration Service
Provides AI-powered screen validation using local OLLAMA instance

Features:
- Screen content verification using Mistral 7B
- Text analysis and pattern matching
- UI element detection and validation
- Error message analysis
"""

from __future__ import annotations
import requests
import json
import logging
from typing import Dict, Any, List, Tuple
import base64
import os

# Configure logging
logger = logging.getLogger(__name__)

class OLLAMAService:
    """Service for interacting with local OLLAMA instance"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        """
        Initialize OLLAMA service
        
        Args:
            base_url: OLLAMA server URL (default: http://localhost:11434)
        """
        self.base_url = base_url
        self.model = "mistral"
        self.api_endpoint = f"{base_url}/api/generate"
        self.tags_endpoint = f"{base_url}/api/tags"
        
    def is_available(self) -> bool:
        """
        Check if OLLAMA server is running and accessible
        
        Returns:
            True if server is available, False otherwise
        """
        try:
            response = requests.get(self.tags_endpoint, timeout=2)
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            logger.warning(f"OLLAMA server not available: {e}")
            return False
    
    def get_available_models(self) -> List[str]:
        """
        Get list of available models
        
        Returns:
            List of model names
        """
        try:
            response = requests.get(self.tags_endpoint, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
        except Exception as e:
            logger.error(f"Error fetching models: {e}")
        return []
    
    def generate_text(self, prompt: str, model: str = None, temperature: float = 0.7) -> str:
        """
        Generate text using OLLAMA model (Mistral 7B)
        
        Args:
            prompt: Input prompt for text generation
            model: Model name (default: mistral)
            temperature: Creativity level (0.0-1.0, default: 0.7)
            
        Returns:
            Generated text response
        """
        if not self.is_available():
            logger.error("OLLAMA service not available for text generation")
            return ""
        
        try:
            model = model or "mistral"
            
            response = requests.post(
                self.api_endpoint,
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": temperature
                },
                timeout=60
            )
            
            if response.status_code != 200:
                logger.error(f"OLLAMA text generation error: {response.status_code}")
                return ""
            
            result = response.json()
            return result.get('response', '').strip()
            
        except Exception as e:
            logger.error(f"Error generating text with OLLAMA: {e}")
            return ""
    
    def verify_screen_content(self, 
                            screenshot_path: str, 
                            expected_content: str,
                            context: str = None) -> Dict[str, Any]:
        """
        Verify screen content matches expected content
        
        Args:
            screenshot_path: Path to screenshot file
            expected_content: Text or element expected to be on screen
            context: Additional context for verification
            
        Returns:
            Dictionary with verification result:
            {
                "verified": bool,
                "confidence": float (0-1),
                "message": str,
                "analysis": str,
                "timestamp": str
            }
        """
        if not self.is_available():
            return {
                "verified": False,
                "confidence": 0.0,
                "message": "OLLAMA service is not available",
                "analysis": "Server connection failed",
                "timestamp": None
            }
        
        try:
            # Read and encode image
            if not os.path.exists(screenshot_path):
                return {
                    "verified": False,
                    "confidence": 0.0,
                    "message": f"Screenshot not found: {screenshot_path}",
                    "analysis": "File not found",
                    "timestamp": None
                }
            
            with open(screenshot_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            # Prepare prompt for verification
            prompt = f"""Analyze this screenshot and verify if it contains: "{expected_content}"

{f'Additional context: {context}' if context else ''}

Respond with:
1. VERIFIED or NOT_VERIFIED
2. Confidence percentage (0-100)
3. Brief explanation of what you found

Be precise and concise."""
            
            # Call OLLAMA API
            response = requests.post(
                self.api_endpoint,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "images": [image_data]
                },
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"OLLAMA API error: {response.status_code} - {response.text}")
                return {
                    "verified": False,
                    "confidence": 0.0,
                    "message": f"API error: {response.status_code}",
                    "analysis": response.text[:200],
                    "timestamp": None
                }
            
            # Parse response
            result = response.json()
            analysis = result.get('response', '').strip()
            
            # Extract verification status and confidence
            verified = "VERIFIED" in analysis.upper()
            
            # Try to extract confidence percentage
            confidence = 0.0
            import re
            confidence_match = re.search(r'(\d+)%', analysis)
            if confidence_match:
                confidence = int(confidence_match.group(1)) / 100.0
            
            return {
                "verified": verified,
                "confidence": confidence,
                "message": f"Screen content {'verified' if verified else 'not verified'}",
                "analysis": analysis,
                "timestamp": str(datetime.now()) if 'datetime' in dir() else None
            }
            
        except Exception as e:
            logger.error(f"Error verifying screen content: {e}")
            return {
                "verified": False,
                "confidence": 0.0,
                "message": f"Verification error: {str(e)}",
                "analysis": str(e),
                "timestamp": None
            }
    
    def analyze_error_message(self, screenshot_path: str) -> Dict[str, Any]:
        """
        Analyze screenshot for error messages
        
        Args:
            screenshot_path: Path to screenshot file
            
        Returns:
            Dictionary with analysis:
            {
                "has_error": bool,
                "error_messages": List[str],
                "severity": str (low/medium/high),
                "analysis": str,
                "timestamp": str
            }
        """
        if not self.is_available():
            return {
                "has_error": False,
                "error_messages": [],
                "severity": "unknown",
                "analysis": "OLLAMA service not available",
                "timestamp": None
            }
        
        try:
            if not os.path.exists(screenshot_path):
                return {
                    "has_error": False,
                    "error_messages": [],
                    "severity": "unknown",
                    "analysis": "Screenshot not found",
                    "timestamp": None
                }
            
            with open(screenshot_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            prompt = """Analyze this screenshot for error messages or warnings.

Identify:
1. Any error or warning messages visible
2. Error type (validation, connection, permission, etc)
3. Severity (low, medium, high, critical)
4. Suggested action to resolve

Format your response as:
ERRORS FOUND: yes/no
ERROR LIST: [error1, error2, ...]
SEVERITY: [level]
RESOLUTION: [suggested fix]"""
            
            response = requests.post(
                self.api_endpoint,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "images": [image_data]
                },
                timeout=30
            )
            
            if response.status_code != 200:
                return {
                    "has_error": False,
                    "error_messages": [],
                    "severity": "unknown",
                    "analysis": f"API error: {response.status_code}",
                    "timestamp": None
                }
            
            result = response.json()
            analysis = result.get('response', '').strip()
            
            # Parse response
            has_error = "yes" in analysis.lower()
            
            # Extract error messages
            errors = []
            import re
            error_match = re.search(r'ERROR LIST:\s*\[(.*?)\]', analysis, re.IGNORECASE)
            if error_match:
                error_list = error_match.group(1)
                errors = [e.strip() for e in error_list.split(',')]
            
            # Extract severity
            severity_match = re.search(r'SEVERITY:\s*(\w+)', analysis, re.IGNORECASE)
            severity = severity_match.group(1).lower() if severity_match else "unknown"
            
            return {
                "has_error": has_error,
                "error_messages": errors,
                "severity": severity,
                "analysis": analysis,
                "timestamp": str(datetime.now()) if 'datetime' in dir() else None
            }
            
        except Exception as e:
            logger.error(f"Error analyzing error messages: {e}")
            return {
                "has_error": False,
                "error_messages": [],
                "severity": "unknown",
                "analysis": str(e),
                "timestamp": None
            }
    
    def validate_ui_elements(self, 
                            screenshot_path: str,
                            expected_elements: List[str]) -> Dict[str, Any]:
        """
        Validate presence of UI elements
        
        Args:
            screenshot_path: Path to screenshot file
            expected_elements: List of UI elements to verify
            
        Returns:
            Dictionary with validation results:
            {
                "all_found": bool,
                "found_elements": List[str],
                "missing_elements": List[str],
                "analysis": str,
                "timestamp": str
            }
        """
        if not self.is_available():
            return {
                "all_found": False,
                "found_elements": [],
                "missing_elements": expected_elements,
                "analysis": "OLLAMA service not available",
                "timestamp": None
            }
        
        try:
            if not os.path.exists(screenshot_path):
                return {
                    "all_found": False,
                    "found_elements": [],
                    "missing_elements": expected_elements,
                    "analysis": "Screenshot not found",
                    "timestamp": None
                }
            
            with open(screenshot_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            elements_str = ", ".join(expected_elements)
            prompt = f"""Analyze this screenshot and check if the following UI elements are present:
{elements_str}

For each element, indicate if it's:
- FOUND: Element is clearly visible
- NOT_FOUND: Element is not visible
- PARTIALLY_VISIBLE: Element is partially visible or obscured

List your findings as:
FOUND: [element1, element2, ...]
NOT_FOUND: [element3, element4, ...]
PARTIAL: [element5, ...]
ANALYSIS: Brief description of UI layout"""
            
            response = requests.post(
                self.api_endpoint,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "images": [image_data]
                },
                timeout=30
            )
            
            if response.status_code != 200:
                return {
                    "all_found": False,
                    "found_elements": [],
                    "missing_elements": expected_elements,
                    "analysis": f"API error: {response.status_code}",
                    "timestamp": None
                }
            
            result = response.json()
            analysis = result.get('response', '').strip()
            
            # Parse response
            found_elements = []
            missing_elements = []
            
            import re
            
            # Extract found elements
            found_match = re.search(r'FOUND:\s*\[(.*?)\]', analysis, re.IGNORECASE)
            if found_match:
                found_list = found_match.group(1)
                found_elements = [e.strip() for e in found_list.split(',') if e.strip()]
            
            # Extract not found elements
            not_found_match = re.search(r'NOT_FOUND:\s*\[(.*?)\]', analysis, re.IGNORECASE)
            if not_found_match:
                not_found_list = not_found_match.group(1)
                missing_elements = [e.strip() for e in not_found_list.split(',') if e.strip()]
            
            all_found = len(missing_elements) == 0 and len(found_elements) == len(expected_elements)
            
            return {
                "all_found": all_found,
                "found_elements": found_elements,
                "missing_elements": missing_elements,
                "analysis": analysis,
                "timestamp": str(datetime.now()) if 'datetime' in dir() else None
            }
            
        except Exception as e:
            logger.error(f"Error validating UI elements: {e}")
            return {
                "all_found": False,
                "found_elements": [],
                "missing_elements": expected_elements,
                "analysis": str(e),
                "timestamp": None
            }


# Global OLLAMA service instance
_ollama_service = None

def get_ollama_service() -> OLLAMAService:
    """Get or create OLLAMA service instance"""
    global _ollama_service
    if _ollama_service is None:
        _ollama_service = OLLAMAService()
    return _ollama_service


if __name__ == "__main__":
    # Test OLLAMA service
    service = OLLAMAService()
    
    if service.is_available():
        print("✓ OLLAMA service is available")
        print(f"✓ Available models: {service.get_available_models()}")
    else:
        print("✗ OLLAMA service is not available")
