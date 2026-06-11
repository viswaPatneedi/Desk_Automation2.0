# AI Screen Analyzer Configuration

import os

# ============================================================
# AI SCREEN ANALYZER SETTINGS
# ============================================================

# Enable/Disable AI Screen Analyzer
AI_SCREEN_ANALYZER_ENABLED = os.environ.get('AI_SCREEN_ANALYZER_ENABLED', 'true').lower() == 'true'

# Anthropic API Configuration
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

# Claude Model to use for screen analysis
# Recommended: claude-3-5-sonnet-20241022 (fastest, cost-effective)
# Options: claude-3-opus, claude-3-sonnet, claude-3-haiku
AI_VISION_MODEL = os.environ.get('AI_VISION_MODEL', 'claude-3-5-sonnet-20241022')

# Confidence threshold for screen matching (0.0 - 1.0)
# Higher values require more confidence in the AI's assessment
AI_CONFIDENCE_THRESHOLD = float(os.environ.get('AI_CONFIDENCE_THRESHOLD', '0.7'))

# Cache analysis results (speeds up repeated checks of same screenshot)
AI_CACHE_RESULTS = os.environ.get('AI_CACHE_RESULTS', 'true').lower() == 'true'

# Cache duration in seconds
AI_CACHE_DURATION = int(os.environ.get('AI_CACHE_DURATION', '3600'))

# Fallback to legacy validation if AI fails
AI_FALLBACK_TO_LEGACY = os.environ.get('AI_FALLBACK_TO_LEGACY', 'true').lower() == 'true'

# ============================================================
# LOGGING & DEBUG
# ============================================================

# Log AI responses for debugging
AI_DEBUG_LOGGING = os.environ.get('AI_DEBUG_LOGGING', 'false').lower() == 'true'

# Save analysis reports
AI_SAVE_ANALYSIS_REPORTS = os.environ.get('AI_SAVE_ANALYSIS_REPORTS', 'true').lower() == 'true'

# Analysis report directory
AI_ANALYSIS_REPORT_DIR = os.environ.get(
    'AI_ANALYSIS_REPORT_DIR',
    'Enhancement_output/ai_analysis_reports'
)

# ============================================================
# VALIDATION SETTINGS
# ============================================================

# Expected screens for validation
EXPECTED_SCREENS = {
    'HOME': 'Device home screen with app grid',
    'NETFLIX': 'Netflix app interface',
    'YOUTUBE': 'YouTube app interface',
    'YOUTUBE_SIGNIN': 'YouTube sign-in page',
    'SETTINGS': 'Device settings',
    'MENU': 'Main menu navigation',
    'LOADING': 'Loading state',
    'ERROR': 'Error screen',
}

# Focus detection settings
FOCUS_DETECTION_ENABLED = os.environ.get('FOCUS_DETECTION_ENABLED', 'true').lower() == 'true'

# Detail level for analysis ('minimal', 'standard', 'detailed')
ANALYSIS_DETAIL_LEVEL = os.environ.get('ANALYSIS_DETAIL_LEVEL', 'standard')

# ============================================================
# SETUP INSTRUCTIONS
# ============================================================

"""
To enable AI Screen Analyzer, set the following environment variables:

1. Get Anthropic API Key:
   - Go to https://console.anthropic.com
   - Create new API key
   - Copy the key

2. Set environment variable:
   export ANTHROPIC_API_KEY='sk-ant-...'

3. Optional configuration:
   export AI_SCREEN_ANALYZER_ENABLED='true'
   export AI_VISION_MODEL='claude-3-5-sonnet-20241022'
   export AI_CONFIDENCE_THRESHOLD='0.7'
   export AI_FALLBACK_TO_LEGACY='true'
   export AI_DEBUG_LOGGING='true'

4. Verify setup:
   python -c "from services.ai_screen_analyzer import get_analyzer; a = get_analyzer(); print('✅ Ready' if a.client else '❌ Not configured')"

5. Example usage in Python:
   from services.ai_screen_validation_bridge import validate_screen_with_ai
   
   result = validate_screen_with_ai(
       screenshot_path='/path/to/screenshot.png',
       expected_screen='HOME',
       device_name='STB-Device-01'
   )
   
   print(f"Match: {result['device_matched']}")
   print(f"Confidence: {result['confidence']}")
   print(f"Focus: {result['focus_elements']}")
   print(f"UI Elements: {result['ui_elements']}")
"""

# ============================================================
# VALIDATION RESULT STRUCTURE
# ============================================================

"""
Result format from AI Screen Analyzer:

{
    'timestamp': '2026-05-07T10:30:45.123456',
    'success': True,
    'device_matched': True,           # Is device on expected screen?
    'expected_screen': 'HOME',        # What we expected
    'detected_screen': 'HOME',        # What was actually shown
    'focus_elements': [
        'App Grid',                   # Primary element in focus
        'Navigation Bar'              # Secondary elements
    ],
    'ui_elements': [                  # All visible elements
        'Status Bar',
        'App Icons',
        'Navigation Bar',
        'Settings Button'
    ],
    'anomalies': [],                  # Any issues detected
    'confidence': 0.95,               # Confidence level (0-1)
    'analysis_text': '...',           # Full AI analysis
    'error': None                     # Error message if any
}
"""

# ============================================================
# COST CONSIDERATIONS
# ============================================================

"""
API Costs:
- Claude 3.5 Sonnet: $3 per 1M input tokens, $15 per 1M output tokens
- Typical screenshot analysis: ~2,000-5,000 tokens per image
- Cost per screenshot: ~$0.01-0.02

Optimization:
- Use caching to avoid repeated analyses of same screenshot
- Use AI_DETAIL_LEVEL='minimal' for faster processing
- Batch multiple screenshots if possible
"""
