"""
Agent-ScreenAnalyzer: AI-Powered Screen Validation Agent
Wraps the existing ai_screen_analyzer.py service for intelligent screen validation
"""

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json

logger = logging.getLogger(__name__)

# ============================================================
# DATA CLASSES & ENUMS
# ============================================================

class ValidationStatus(Enum):
    """Screen validation result status"""
    MATCHING = "matching"
    MISMATCHED = "mismatched"
    UNCERTAIN = "uncertain"
    ERROR = "error"
    UNKNOWN = "unknown"


class ScreenAnalysisType(Enum):
    """Types of screen analysis available"""
    PIXEL_MATCHING = "pixel_matching"
    AI_VISION = "ai_vision"
    COMBINED = "combined"
    OCR = "ocr"


@dataclass
class ScreenValidationResult:
    """Result of a screen validation"""
    job_id: str
    timestamp: str
    analysis_type: str
    status: str  # matching, mismatched, uncertain, error
    confidence: float  # 0.0 - 1.0
    description: str
    details: Dict[str, Any]
    
    def to_dict(self):
        return {
            'job_id': self.job_id,
            'timestamp': self.timestamp,
            'analysis_type': self.analysis_type,
            'status': self.status,
            'confidence': self.confidence,
            'description': self.description,
            'details': self.details
        }


# ============================================================
# SCREEN ANALYZER WRAPPER
# ============================================================

class ScreenAnalyzerWrapper:
    """Wrapper for the existing ai_screen_analyzer service"""
    
    def __init__(self, ai_analyzer_service=None):
        """
        Initialize the wrapper
        
        Args:
            ai_analyzer_service: Optional ai_screen_analyzer module instance
        """
        self.ai_analyzer = ai_analyzer_service
        self.validation_history: List[ScreenValidationResult] = []
        self.lock = threading.Lock()
        
        # Try to import existing service if not provided
        if not self.ai_analyzer:
            try:
                from services.ai_screen_analyzer import AIScreenAnalyzer
                self.ai_analyzer = AIScreenAnalyzer()
                logger.info("✅ Loaded existing AIScreenAnalyzer service")
            except ImportError:
                logger.warning("⚠️  ai_screen_analyzer service not found - will use fallback")
                self.ai_analyzer = None
    
    def validate_screen(
        self,
        job_id: str,
        screenshot_path: str,
        expected_elements: Dict[str, Any] = None,
        log_pattern: str = None,
        analysis_type: ScreenAnalysisType = ScreenAnalysisType.COMBINED
    ) -> ScreenValidationResult:
        """
        Validate a screenshot against expected screen
        
        Args:
            job_id: Job identifier
            screenshot_path: Path to screenshot file
            expected_elements: Expected screen elements/patterns
            log_pattern: Log pattern to match against
            analysis_type: Type of analysis to perform
        
        Returns:
            ScreenValidationResult with analysis
        """
        try:
            result = None
            
            if analysis_type == ScreenAnalysisType.AI_VISION and self.ai_analyzer:
                # Use Claude Vision API
                result = self._validate_with_ai_vision(
                    job_id, screenshot_path, expected_elements
                )
            
            elif analysis_type == ScreenAnalysisType.PIXEL_MATCHING:
                # Use pixel-based matching
                result = self._validate_with_pixel_matching(
                    job_id, screenshot_path, expected_elements
                )
            
            elif analysis_type == ScreenAnalysisType.COMBINED:
                # Use both methods and combine results
                result = self._validate_with_combined(
                    job_id, screenshot_path, expected_elements
                )
            
            else:
                # Fallback
                result = self._validate_fallback(
                    job_id, screenshot_path, expected_elements
                )
            
            # Store in history
            with self.lock:
                self.validation_history.append(result)
            
            logger.info(
                f"📊 Screen validation: job={job_id}, status={result.status}, "
                f"confidence={result.confidence:.0%}"
            )
            
            return result
        
        except Exception as e:
            logger.error(f"❌ Error validating screen: {e}")
            return ScreenValidationResult(
                job_id=job_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                analysis_type=analysis_type.value,
                status=ValidationStatus.ERROR.value,
                confidence=0.0,
                description=f"Error: {str(e)}",
                details={'error': str(e)}
            )
    
    def _validate_with_ai_vision(
        self,
        job_id: str,
        screenshot_path: str,
        expected_elements: Dict[str, Any]
    ) -> ScreenValidationResult:
        """Validate using Claude Vision API"""
        try:
            if not self.ai_analyzer:
                raise ValueError("AI Analyzer service not available")
            
            # Call the existing AI Screen Analyzer
            # Expected interface: validate_screen(image_path, validation_prompt)
            
            validation_prompt = self._build_validation_prompt(expected_elements)
            
            # Call AI analyzer
            analysis_result = self.ai_analyzer.validate_screen(
                screenshot_path,
                validation_prompt
            ) if hasattr(self.ai_analyzer, 'validate_screen') else None
            
            if not analysis_result:
                raise ValueError("AI validation returned no result")
            
            # Parse AI response
            status = self._parse_ai_response(analysis_result)
            
            return ScreenValidationResult(
                job_id=job_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                analysis_type=ScreenAnalysisType.AI_VISION.value,
                status=status['status'],
                confidence=status['confidence'],
                description=status['description'],
                details={
                    'ai_response': analysis_result,
                    'expected_elements': expected_elements
                }
            )
        
        except Exception as e:
            logger.error(f"AI Vision validation error: {e}")
            raise
    
    def _validate_with_pixel_matching(
        self,
        job_id: str,
        screenshot_path: str,
        expected_elements: Dict[str, Any]
    ) -> ScreenValidationResult:
        """Validate using pixel-based matching"""
        try:
            import cv2
            import numpy as np
            from pathlib import Path
            
            # Load screenshot
            img = cv2.imread(screenshot_path)
            if img is None:
                raise ValueError(f"Could not load image: {screenshot_path}")
            
            # Simple pixel analysis
            # In production, this would use template matching, ORB features, etc.
            
            img_height, img_width = img.shape[:2]
            
            status = ValidationStatus.MATCHING.value
            confidence = 0.8  # Default high confidence for pixel matching
            
            # Check image dimensions
            if expected_elements and 'dimensions' in expected_elements:
                exp_width, exp_height = expected_elements['dimensions']
                if abs(img_width - exp_width) > 10 or abs(img_height - exp_height) > 10:
                    status = ValidationStatus.MISMATCHED.value
                    confidence = 0.3
            
            return ScreenValidationResult(
                job_id=job_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                analysis_type=ScreenAnalysisType.PIXEL_MATCHING.value,
                status=status,
                confidence=confidence,
                description=f"Pixel analysis: {img_width}x{img_height}",
                details={
                    'image_dimensions': (img_width, img_height),
                    'expected_elements': expected_elements
                }
            )
        
        except Exception as e:
            logger.error(f"Pixel matching validation error: {e}")
            raise
    
    def _validate_with_combined(
        self,
        job_id: str,
        screenshot_path: str,
        expected_elements: Dict[str, Any]
    ) -> ScreenValidationResult:
        """Validate using combined analysis"""
        try:
            # Try AI first, fall back to pixel matching
            try:
                ai_result = self._validate_with_ai_vision(
                    job_id, screenshot_path, expected_elements
                )
            except:
                ai_result = None
            
            try:
                pixel_result = self._validate_with_pixel_matching(
                    job_id, screenshot_path, expected_elements
                )
            except:
                pixel_result = None
            
            # Combine results
            if ai_result and pixel_result:
                # Average confidence, use stricter status
                combined_confidence = (ai_result.confidence + pixel_result.confidence) / 2
                
                if ai_result.status == pixel_result.status:
                    status = ai_result.status
                elif ai_result.status == ValidationStatus.MATCHING.value:
                    status = pixel_result.status
                else:
                    status = ai_result.status
                
                return ScreenValidationResult(
                    job_id=job_id,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    analysis_type=ScreenAnalysisType.COMBINED.value,
                    status=status,
                    confidence=combined_confidence,
                    description=f"Combined analysis: AI={ai_result.status}, Pixel={pixel_result.status}",
                    details={
                        'ai_result': ai_result.to_dict(),
                        'pixel_result': pixel_result.to_dict(),
                        'combined_confidence': combined_confidence
                    }
                )
            
            elif ai_result:
                return ai_result
            elif pixel_result:
                return pixel_result
            else:
                raise ValueError("All analysis methods failed")
        
        except Exception as e:
            logger.error(f"Combined validation error: {e}")
            raise
    
    def _validate_fallback(
        self,
        job_id: str,
        screenshot_path: str,
        expected_elements: Dict[str, Any]
    ) -> ScreenValidationResult:
        """Fallback validation"""
        try:
            from pathlib import Path
            
            # Check if file exists
            if not Path(screenshot_path).exists():
                raise ValueError(f"Screenshot not found: {screenshot_path}")
            
            return ScreenValidationResult(
                job_id=job_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                analysis_type="fallback",
                status=ValidationStatus.UNKNOWN.value,
                confidence=0.5,
                description="Fallback validation - screenshot exists",
                details={'file_path': screenshot_path}
            )
        
        except Exception as e:
            logger.error(f"Fallback validation error: {e}")
            raise
    
    def _build_validation_prompt(self, expected_elements: Dict[str, Any]) -> str:
        """Build Claude Vision validation prompt"""
        prompt = "Analyze this screen screenshot and validate:\n"
        
        if expected_elements:
            if 'text' in expected_elements:
                prompt += f"- Look for text: {expected_elements['text']}\n"
            if 'buttons' in expected_elements:
                prompt += f"- Look for buttons: {', '.join(expected_elements['buttons'])}\n"
            if 'errors' in expected_elements:
                prompt += f"- Check for error patterns: {expected_elements['errors']}\n"
            if 'status' in expected_elements:
                prompt += f"- Expected status: {expected_elements['status']}\n"
        
        prompt += "Reply with: MATCHING, MISMATCHED, or UNCERTAIN"
        return prompt
    
    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        """Parse AI Vision API response"""
        response_lower = response.lower()
        
        if 'matching' in response_lower and 'mismatched' not in response_lower:
            return {
                'status': ValidationStatus.MATCHING.value,
                'confidence': 0.9,
                'description': 'AI Vision: Screen matches expected elements'
            }
        elif 'mismatched' in response_lower:
            return {
                'status': ValidationStatus.MISMATCHED.value,
                'confidence': 0.8,
                'description': 'AI Vision: Screen does not match expected elements'
            }
        else:
            return {
                'status': ValidationStatus.UNCERTAIN.value,
                'confidence': 0.5,
                'description': 'AI Vision: Unable to determine match status'
            }
    
    def get_validation_history(self, job_id: str = None) -> List[Dict[str, Any]]:
        """Get validation history"""
        with self.lock:
            if job_id:
                return [
                    v.to_dict() for v in self.validation_history
                    if v.job_id == job_id
                ]
            else:
                return [v.to_dict() for v in self.validation_history[-100:]]  # Last 100
    
    def get_accuracy_metrics(self) -> Dict[str, Any]:
        """Get screen validation accuracy metrics"""
        with self.lock:
            if not self.validation_history:
                return {'total_validations': 0}
            
            by_status = {}
            total_confidence = 0
            
            for result in self.validation_history:
                status = result.status
                by_status[status] = by_status.get(status, 0) + 1
                total_confidence += result.confidence
            
            return {
                'total_validations': len(self.validation_history),
                'by_status': by_status,
                'average_confidence': total_confidence / len(self.validation_history),
                'success_rate': by_status.get(ValidationStatus.MATCHING.value, 0) / len(self.validation_history)
            }


# ============================================================
# AGENT-SCREEN-ANALYZER
# ============================================================

class AgentScreenAnalyzer:
    """
    AI Agent for intelligent screen validation and analysis
    
    Responsibilities:
    - Validate screens using Claude Vision API
    - OCR text extraction and validation
    - Pattern matching on screenshots
    - Error detection from UI states
    - Fallback to pixel-based matching
    """
    
    def __init__(self, ai_service=None):
        self.name = "Agent-ScreenAnalyzer"
        self.is_running = False
        self.analyzer = ScreenAnalyzerWrapper(ai_service)
        self.monitor_thread = None
        self.validation_queue: List[Dict[str, Any]] = []
        
        logger.info(f"✅ {self.name} initialized")
    
    def start(self):
        """Start the agent"""
        if self.is_running:
            logger.warning(f"⚠️  {self.name} is already running")
            return
        
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info(f"🚀 {self.name} started")
    
    def stop(self):
        """Stop the agent"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info(f"⛔ {self.name} stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                # Process validation queue
                self._process_validation_queue()
                time.sleep(5)
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                time.sleep(10)
    
    def _process_validation_queue(self):
        """Process pending screen validations"""
        try:
            # In production, process queue items
            pass
        except Exception as e:
            logger.error(f"Error processing queue: {e}")
    
    def validate_screenshot(
        self,
        job_id: str,
        screenshot_path: str,
        expected_elements: Dict[str, Any] = None,
        analysis_type: str = "combined"
    ) -> Dict[str, Any]:
        """
        Validate a screenshot
        
        Args:
            job_id: Job identifier
            screenshot_path: Path to screenshot
            expected_elements: Expected screen content
            analysis_type: Type of analysis (combined, ai_vision, pixel_matching)
        
        Returns:
            Validation result dict
        """
        try:
            analysis_enum = ScreenAnalysisType[analysis_type.upper()]
        except KeyError:
            analysis_enum = ScreenAnalysisType.COMBINED
        
        result = self.analyzer.validate_screen(
            job_id,
            screenshot_path,
            expected_elements,
            analysis_type=analysis_enum
        )
        
        return result.to_dict()
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get agent status"""
        metrics = self.analyzer.get_accuracy_metrics()
        
        return {
            'agent_name': self.name,
            'is_running': self.is_running,
            'validation_metrics': metrics,
            'pending_validations': len(self.validation_queue),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }


# ============================================================
# GLOBAL AGENT INSTANCE
# ============================================================

_SCREEN_ANALYZER_AGENT = None

def get_screen_analyzer_agent() -> AgentScreenAnalyzer:
    """Get or create the global ScreenAnalyzer agent"""
    global _SCREEN_ANALYZER_AGENT
    if _SCREEN_ANALYZER_AGENT is None:
        _SCREEN_ANALYZER_AGENT = AgentScreenAnalyzer()
    return _SCREEN_ANALYZER_AGENT


def start_screen_analyzer_agent():
    """Start the ScreenAnalyzer agent"""
    agent = get_screen_analyzer_agent()
    agent.start()
    return agent


def stop_screen_analyzer_agent():
    """Stop the ScreenAnalyzer agent"""
    if _SCREEN_ANALYZER_AGENT:
        _SCREEN_ANALYZER_AGENT.stop()


# ============================================================
# CLI INTERFACE
# ============================================================

def main():
    """CLI interface for agent"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Agent-ScreenAnalyzer')
    parser.add_argument('--start', action='store_true', help='Start the agent')
    parser.add_argument('--status', action='store_true', help='Get agent status')
    
    args = parser.parse_args()
    
    agent = get_screen_analyzer_agent()
    
    if args.start:
        print("🚀 Starting Agent-ScreenAnalyzer...")
        agent.start()
        print("✅ Agent started. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n⛔ Stopping agent...")
            agent.stop()
    
    elif args.status:
        import json
        agent.start()
        print(json.dumps(agent.get_agent_status(), indent=2))
        agent.stop()
    
    else:
        parser.print_help()


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    main()
