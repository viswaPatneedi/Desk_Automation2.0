"""
AI Screen Analyzer - Usage Guide and Examples

This file demonstrates how to use the AI Screen Analyzer for intelligent
screen validation, focus detection, and transition analysis.

Author: Enhanced Testing Framework
Date: 2026-05-07
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from services.ai_screen_analyzer import AIScreenAnalyzer, get_analyzer
from services.ai_screen_validation_bridge import (
    validate_screen_with_ai,
    analyze_screen_focus,
    get_validation_bridge
)


class AIScreenAnalyzerExamples:
    """Examples demonstrating AI Screen Analyzer usage"""
    
    @staticmethod
    def example_1_basic_validation():
        """Example 1: Basic screen validation"""
        print("\n" + "="*60)
        print("Example 1: Basic Screen Validation")
        print("="*60)
        
        # Initialize analyzer
        analyzer = get_analyzer()
        
        if not analyzer.client:
            print("❌ AI Screen Analyzer not configured")
            print("   Set ANTHROPIC_API_KEY environment variable")
            return
        
        # Validate a screenshot
        screenshot_path = "path/to/screenshot.png"
        
        if not os.path.exists(screenshot_path):
            print(f"⚠️  Screenshot not found: {screenshot_path}")
            print("   Please provide a valid screenshot path")
            return
        
        result = analyzer.validate_screen_match(
            screenshot_path=screenshot_path,
            expected_screen="HOME",
            device_name="STB-Device-01",
            confidence_threshold=0.7
        )
        
        print(f"\n✅ Validation Result:")
        print(f"   Device Matched: {result['device_matched']}")
        print(f"   Detected Screen: {result['detected_screen']}")
        print(f"   Confidence: {result['confidence']:.1%}")
        print(f"   Valid: {result['is_valid']}")
    
    @staticmethod
    def example_2_focus_detection():
        """Example 2: Detect what's in focus"""
        print("\n" + "="*60)
        print("Example 2: Focus Detection")
        print("="*60)
        
        analyzer = get_analyzer()
        
        if not analyzer.client:
            print("❌ AI Screen Analyzer not configured")
            return
        
        screenshot_path = "path/to/screenshot.png"
        
        if not os.path.exists(screenshot_path):
            print(f"⚠️  Screenshot not found: {screenshot_path}")
            return
        
        # Get focus analysis
        result = analyzer.get_focus_analysis(screenshot_path, device_name="STB-Device-01")
        
        print(f"\n✅ Focus Analysis:")
        print(f"   Primary Focus: {result['primary_focus']}")
        print(f"   Secondary Focus: {result['secondary_focus']}")
        print(f"   Detected Screen: {result['detected_screen']}")
        print(f"   UI Elements: {result['ui_elements']}")
        print(f"   Anomalies: {result['anomalies']}")
    
    @staticmethod
    def example_3_transition_analysis():
        """Example 3: Analyze screen transitions"""
        print("\n" + "="*60)
        print("Example 3: Screen Transition Analysis")
        print("="*60)
        
        analyzer = get_analyzer()
        
        if not analyzer.client:
            print("❌ AI Screen Analyzer not configured")
            return
        
        before_path = "path/to/before_screenshot.png"
        after_path = "path/to/after_screenshot.png"
        
        if not os.path.exists(before_path) or not os.path.exists(after_path):
            print("⚠️  Screenshot files not found")
            return
        
        # Compare screens
        result = analyzer.compare_screenshots(before_path, after_path, device_name="STB-Device-01")
        
        print(f"\n✅ Transition Analysis:")
        print(f"   Changed: {result.get('changed')}")
        print(f"   Change Type: {result.get('change_type')}")
        print(f"   Before Screen: {result.get('before_screen')}")
        print(f"   After Screen: {result.get('after_screen')}")
        print(f"   Major Changes: {result.get('major_changes')}")
        print(f"   Navigation Success: {result.get('navigation_success')}")
    
    @staticmethod
    def example_4_batch_validation():
        """Example 4: Validate multiple screenshots"""
        print("\n" + "="*60)
        print("Example 4: Batch Validation")
        print("="*60)
        
        analyzer = get_analyzer()
        
        if not analyzer.client:
            print("❌ AI Screen Analyzer not configured")
            return
        
        screenshots = [
            "path/to/screenshot1.png",
            "path/to/screenshot2.png",
            "path/to/screenshot3.png"
        ]
        
        print(f"\nValidating {len(screenshots)} screenshots...")
        
        results = analyzer.batch_analyze_screenshots(
            screenshot_paths=screenshots,
            expected_screen="HOME",
            device_name="STB-Device-01"
        )
        
        print(f"\n✅ Batch Validation Results:")
        for i, result in enumerate(results, 1):
            if result['success']:
                print(f"   [{i}] {result['detected_screen']} - Confidence: {result['confidence']:.1%}")
            else:
                print(f"   [{i}] Error: {result.get('error')}")
    
    @staticmethod
    def example_5_integration_with_methods():
        """Example 5: Use AI validator in method execution"""
        print("\n" + "="*60)
        print("Example 5: Integration with Test Methods")
        print("="*60)
        
        print("\nUsage in method_deepsleep.py or other methods:")
        print("""
# In your test method:
from services.ai_screen_validation_bridge import get_validation_bridge

bridge = get_validation_bridge()

# Validate screenshot
result = bridge.validate_screen(
    screenshot_path="path/to/screenshot.png",
    expected_screen="HOME",
    device_name=device.name
)

if result['is_valid']:
    print(f"✅ Device validated on {result['detected_screen']}")
    print(f"   Focus elements: {result['focus_elements']}")
else:
    print(f"❌ Validation failed")
    print(f"   Expected: {result['expected_screen']}")
    print(f"   Detected: {result['detected_screen']}")
    print(f"   Anomalies: {result['anomalies']}")
        """)
    
    @staticmethod
    def example_6_convenience_functions():
        """Example 6: Using convenience functions"""
        print("\n" + "="*60)
        print("Example 6: Convenience Functions")
        print("="*60)
        
        print("\n# Quick validation:")
        print("""
result = validate_screen_with_ai(
    screenshot_path="path/to/screenshot.png",
    expected_screen="HOME"
)
print(f"Match: {result['device_matched']}")
        """)
        
        print("\n# Quick focus analysis:")
        print("""
result = analyze_screen_focus("path/to/screenshot.png")
print(f"In Focus: {result['focus_elements']}")
        """)


def setup_ai_screen_analyzer():
    """Setup instructions for AI Screen Analyzer"""
    print("\n" + "="*70)
    print("AI SCREEN ANALYZER - SETUP INSTRUCTIONS")
    print("="*70)
    
    print("""
1. GET ANTHROPIC API KEY:
   - Visit: https://console.anthropic.com/account/keys
   - Create a new API key
   - Copy the full key (starts with sk-ant-)

2. SET ENVIRONMENT VARIABLE:
   
   On Linux/macOS:
   export ANTHROPIC_API_KEY='sk-ant-xxxxxxxxxxxxxxxxxxxxxx'
   
   On Windows PowerShell:
   $env:ANTHROPIC_API_KEY='sk-ant-xxxxxxxxxxxxxxxxxxxxxx'
   
   In Python:
   import os
   os.environ['ANTHROPIC_API_KEY'] = 'sk-ant-xxxxxxxxxxxxxxxxxxxxxx'

3. OPTIONAL CONFIGURATION:
   export AI_SCREEN_ANALYZER_ENABLED='true'
   export AI_VISION_MODEL='claude-3-5-sonnet-20241022'
   export AI_CONFIDENCE_THRESHOLD='0.7'
   export AI_FALLBACK_TO_LEGACY='true'
   export AI_DEBUG_LOGGING='true'

4. VERIFY INSTALLATION:
   python -c "from services.ai_screen_analyzer import get_analyzer; 
              a = get_analyzer(); 
              print('✅ AI Screen Analyzer Ready' if a.client else '❌ Not configured')"

5. TEST WITH EXAMPLE:
   python AI_SCREEN_ANALYZER_USAGE_EXAMPLES.py

PRICING:
- Claude 3.5 Sonnet: ~$0.01-0.02 per screenshot
- Rate limit: Generous for testing (50,000 requests per day)
- No minimum spend

FEATURES:
✅ Intelligent screen matching
✅ Focus element detection
✅ UI element identification
✅ Transition analysis
✅ Anomaly detection
✅ Confidence scoring
✅ Natural language analysis
✅ Batch processing
✅ Legacy fallback support

LIMITATIONS:
- Requires internet connection
- API rate limits apply
- Processing time: 2-5 seconds per image
- Costs vary with image complexity
    """)


def main():
    """Run usage examples"""
    print("\n" + "="*70)
    print("AI SCREEN ANALYZER - USAGE EXAMPLES")
    print("="*70)
    
    # Check if API key is configured
    if not os.environ.get('ANTHROPIC_API_KEY'):
        print("\n⚠️  ANTHROPIC_API_KEY not set!")
        setup_ai_screen_analyzer()
        print("\nAfter setting up the API key, run this script again:")
        print("  export ANTHROPIC_API_KEY='sk-ant-....'")
        print("  python AI_SCREEN_ANALYZER_USAGE_EXAMPLES.py")
        return
    
    # Run examples
    examples = AIScreenAnalyzerExamples()
    
    try:
        examples.example_1_basic_validation()
    except Exception as e:
        print(f"❌ Example 1 error: {e}")
    
    examples.example_2_focus_detection()
    examples.example_3_transition_analysis()
    examples.example_4_batch_validation()
    examples.example_5_integration_with_methods()
    examples.example_6_convenience_functions()
    
    print("\n" + "="*70)
    print("✅ EXAMPLES COMPLETE")
    print("="*70)
    print("\nNext steps:")
    print("1. Review the examples above")
    print("2. Integrate get_validation_bridge() into your test methods")
    print("3. Replace legacy validation with AI-powered validation")
    print("4. Monitor analysis results and adjust confidence thresholds as needed")
    print("\nDocumentation:")
    print("- config_ai_screen_analyzer.py: Configuration options")
    print("- services/ai_screen_analyzer.py: Core implementation")
    print("- services/ai_screen_validation_bridge.py: Integration bridge")


if __name__ == '__main__':
    main()
