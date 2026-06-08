# AI Screen Analyzer - Intelligent Screen Validation System

## Overview

The **AI Screen Analyzer** is a standalone AI agent system that uses Claude Vision API to intelligently analyze device screenshots and provide:

- ✅ **Accurate Screen Matching** - Determine if device is on expected screen
- 🎯 **Focus Detection** - Identify what elements are currently in focus
- 📊 **UI Element Analysis** - Recognize all visible UI components
- 🔍 **Anomaly Detection** - Detect errors, unexpected states, or visual glitches
- 📈 **Transition Analysis** - Compare before/after screenshots to detect changes
- 📱 **Device Status** - Overall device health and responsiveness assessment

## Why Replace Current Image Validation?

### Current Approach Issues:
- ❌ Limited to pixel/feature matching (unreliable with visual variations)
- ❌ Struggles with different device orientations or resolutions
- ❌ Cannot understand context or semantic meaning
- ❌ Requires manual reference images for every screen
- ❌ False positives/negatives with minor UI changes
- ❌ No information about what's actually in focus

### AI Screen Analyzer Advantages:
- ✅ **Semantic Understanding** - Understands screen meaning and context
- ✅ **Natural Language** - Can describe what it sees in human terms
- ✅ **Focus Awareness** - Identifies prominent and secondary elements
- ✅ **No Reference Images** - Works without pre-captured reference screens
- ✅ **Robust** - Handles variations in UI, resolution, orientation
- ✅ **Detailed Analysis** - Provides actionable insights about layout and state
- ✅ **Anomaly Detection** - Identifies unexpected or error states

## Quick Start

### 1. Get Anthropic API Key

```bash
# Visit https://console.anthropic.com/account/keys
# Create new API key
# Copy the key (starts with sk-ant-)
```

### 2. Set Environment Variable

```bash
# Linux/macOS
export ANTHROPIC_API_KEY='sk-ant-xxxxx'

# Windows PowerShell
$env:ANTHROPIC_API_KEY='sk-ant-xxxxx'

# Or in Python
import os
os.environ['ANTHROPIC_API_KEY'] = 'sk-ant-xxxxx'
```

### 3. Verify Setup

```bash
python -c "from services.ai_screen_analyzer import get_analyzer; \
           a = get_analyzer(); \
           print('✅ Ready' if a.client else '❌ Not configured')"
```

### 4. Use in Your Code

```python
from services.ai_screen_validation_bridge import validate_screen_with_ai

# Validate a screenshot
result = validate_screen_with_ai(
    screenshot_path="/path/to/screenshot.png",
    expected_screen="HOME",
    device_name="STB-Device-01"
)

# Check results
if result['device_matched']:
    print(f"✅ Device is on {result['detected_screen']}")
    print(f"   Focus: {result['focus_elements']}")
    print(f"   Confidence: {result['confidence']:.1%}")
else:
    print(f"❌ Device not on {result['expected_screen']}")
    print(f"   Actually on: {result['detected_screen']}")
    print(f"   Anomalies: {result['anomalies']}")
```

## Integration with Existing Methods

### Integrating with method_deepsleep.py

```python
# In method_deepsleep.py
from services.ai_screen_validation_bridge import get_validation_bridge

def execute_deepsleep_process(...):
    bridge = get_validation_bridge()
    
    # ... existing code ...
    
    # After capturing screenshot, validate using AI
    result = bridge.validate_screen(
        screenshot_path=screenshot_path,
        expected_screen="HOME",
        device_name=device_name
    )
    
    if result['is_valid']:
        log_message(f"✅ HOME screen validated using AI")
        log_message(f"   Focus: {result['focus_elements']}")
    else:
        log_message(f"❌ Not on HOME screen")
        log_message(f"   Detected: {result['detected_screen']}")
        log_message(f"   Issues: {result['anomalies']}")
    
    return result['is_valid']
```

### Integrating with method_reboot_perf_v2_optimized.py

```python
from services.ai_screen_validation_bridge import get_validation_bridge

def validate_home_screen(screenshot_path, device_name):
    bridge = get_validation_bridge()
    
    result = bridge.validate_screen(
        screenshot_path=screenshot_path,
        expected_screen="HOME",
        device_name=device_name
    )
    
    return {
        'passed': result['is_valid'],
        'detected_screen': result['detected_screen'],
        'confidence': result['confidence'],
        'focus_elements': result['focus_elements'],
        'anomalies': result['anomalies']
    }
```

### Integrating with method_screen_validation.py

```python
from services.ai_screen_validation_bridge import analyze_screen_focus

def validate_custom_screen(screenshot_path, expected_screen):
    # Get detailed focus analysis
    focus_result = analyze_screen_focus(screenshot_path)
    
    print(f"Screen: {focus_result['detected_screen']}")
    print(f"Primary Focus: {focus_result['primary_focus']}")
    print(f"Secondary Focus: {focus_result['secondary_focus']}")
    print(f"UI Elements: {focus_result['ui_elements']}")
    
    return focus_result['detected_screen'] == expected_screen
```

## API Reference

### Core Method: `analyze_screenshot()`

Analyze a screenshot and get comprehensive analysis.

```python
result = analyzer.analyze_screenshot(
    screenshot_path="/path/to/screenshot.png",
    expected_screen="HOME",         # Optional
    device_name="STB-Device-01",    # Optional
    detailed=True                   # Optional
)
```

**Response Structure:**
```python
{
    'timestamp': '2026-05-07T10:30:45.123456',
    'success': True,
    'detected_screen': 'HOME',           # Detected screen name
    'screen_description': '...',         # Description
    'device_matched': True,              # Matches expected screen?
    'focus_elements': ['App Grid', ...], # What's in focus
    'ui_elements': ['Status Bar', ...],  # All visible elements
    'anomalies': [],                     # Issues detected
    'confidence': 0.95,                  # Confidence (0-1)
    'analysis_text': '...',              # Full AI response
    'error': None
}
```

### Method: `validate_screen_match()`

Quick validation with confidence threshold.

```python
result = analyzer.validate_screen_match(
    screenshot_path="/path/to/screenshot.png",
    expected_screen="HOME",
    device_name="STB-Device-01",
    confidence_threshold=0.7
)

# result['is_valid'] - Whether validation passed
# result['confidence'] - Confidence level
```

### Method: `get_focus_analysis()`

Detailed focus element analysis.

```python
result = analyzer.get_focus_analysis(
    screenshot_path="/path/to/screenshot.png",
    device_name="STB-Device-01"
)

# result['focus_elements'] - List of focused elements
# result['primary_focus'] - Main focused element
# result['secondary_focus'] - Other focus elements
```

### Method: `compare_screenshots()`

Compare two screenshots to detect changes.

```python
result = analyzer.compare_screenshots(
    before_path="/path/to/before.png",
    after_path="/path/to/after.png",
    device_name="STB-Device-01"
)

# result['changed'] - Whether screen changed
# result['before_screen'] - Detected before screen
# result['after_screen'] - Detected after screen
# result['major_changes'] - List of significant changes
```

## Configuration

Edit `config_ai_screen_analyzer.py` to customize:

```python
# Enable/Disable AI analyzer
AI_SCREEN_ANALYZER_ENABLED = True

# Confidence threshold for validation (0-1)
AI_CONFIDENCE_THRESHOLD = 0.7

# Detail level ('minimal', 'standard', 'detailed')
ANALYSIS_DETAIL_LEVEL = 'standard'

# Fallback to legacy validation on failure
AI_FALLBACK_TO_LEGACY = True

# Cache results for 1 hour
AI_CACHE_RESULTS = True
AI_CACHE_DURATION = 3600

# Debug logging
AI_DEBUG_LOGGING = False
```

## Usage Examples

### Example 1: Basic Validation in Test Method

```python
from services.ai_screen_validation_bridge import validate_screen_with_ai

def test_home_screen(device, screenshot_path):
    result = validate_screen_with_ai(
        screenshot_path=screenshot_path,
        expected_screen="HOME"
    )
    
    if result['device_matched']:
        print(f"✅ Test passed - Device on HOME")
        return True
    else:
        print(f"❌ Test failed - Device on {result['detected_screen']}")
        return False
```

### Example 2: Detailed Focus Analysis

```python
from services.ai_screen_analyzer import get_analyzer

analyzer = get_analyzer()

result = analyzer.analyze_screenshot(
    screenshot_path="screenshot.png",
    expected_screen="NETFLIX",
    detailed=True
)

print(f"Screen: {result['detected_screen']}")
print(f"Primary Focus: {result['focus_elements'][0]}")
print(f"All Elements: {result['ui_elements']}")
print(f"Issues: {result['anomalies']}")
```

### Example 3: Transition Verification

```python
from services.ai_screen_analyzer import get_analyzer

analyzer = get_analyzer()

result = analyzer.compare_screenshots(
    before_path="before.png",
    after_path="after.png"
)

if result['screen_transitioned']:
    print(f"Transition: {result['before_screen']} → {result['after_screen']}")
    print(f"Changes: {result['major_changes']}")
else:
    print("No screen transition detected")
```

### Example 4: Batch Analysis

```python
from services.ai_screen_analyzer import get_analyzer

analyzer = get_analyzer()

screenshots = ["screen1.png", "screen2.png", "screen3.png"]
results = analyzer.batch_analyze_screenshots(
    screenshot_paths=screenshots,
    expected_screen="HOME"
)

for i, result in enumerate(results):
    print(f"[{i+1}] {result['detected_screen']} - {result['confidence']:.1%}")
```

## Performance & Costs

### Processing Time
- First request: ~3-5 seconds (API call)
- Cached request: <100ms (from cache)

### API Costs
- **Model**: Claude 3.5 Sonnet
- **Input Cost**: $3 per 1M tokens
- **Output Cost**: $15 per 1M tokens
- **Typical Cost Per Screenshot**: $0.01-0.02 (~2-5k tokens)
- **Daily Quota**: 50,000 requests (generous for testing)

### Optimization Tips
1. **Enable Caching** - Avoid re-analyzing same screenshot
2. **Use Minimal Detail** - When focus not needed
3. **Batch Processing** - If analyzing multiple screenshots
4. **Fallback to Legacy** - For critical operations if API fails

## Troubleshooting

### Issue: "API key not configured"

**Solution:**
```bash
export ANTHROPIC_API_KEY='sk-ant-xxxxx'
python your_script.py
```

### Issue: "Screenshot not found"

**Solution:**
```python
import os
screenshot_path = "path/to/screenshot.png"
if not os.path.exists(screenshot_path):
    print("Screenshot file not found")
```

### Issue: "Timeout or slow response"

**Solution:**
- API might be slow, retry in a few seconds
- Image might be too large, compress before sending
- Check internet connection

### Issue: "Low confidence score"

**Solutions:**
- Image quality might be poor
- Screen might be partially loading
- Try with detailed=True for more accurate analysis

### Issue: "API rate limit exceeded"

**Solution:**
- Wait a few minutes before retrying
- Consider using caching to reduce requests
- Upgrade API plan if needed

## API Key Security

### Best Practices
✅ Use environment variables only
✅ Never commit API key to git
✅ Use .gitignore to exclude config files
✅ Rotate keys periodically
✅ Use different keys for dev/prod/test

### Add to .gitignore
```bash
echo "ANTHROPIC_API_KEY" >> .gitignore
echo ".env" >> .gitignore
echo "*.key" >> .gitignore
```

## Support & Documentation

- **Anthropic Docs**: https://docs.anthropic.com/
- **Claude Vision Guide**: https://docs.anthropic.com/en/docs/vision/vision-intro
- **API Reference**: https://docs.anthropic.com/en/api/

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-05-07 | Initial release with screen validation, focus detection, and transition analysis |

## License

Same as parent project

## Questions?

For issues or questions about AI Screen Analyzer:
1. Check `config_ai_screen_analyzer.py` for configuration options
2. Review `AI_SCREEN_ANALYZER_USAGE_EXAMPLES.py` for usage patterns
3. Check `services/ai_screen_analyzer.py` source code
4. Review Anthropic API documentation
