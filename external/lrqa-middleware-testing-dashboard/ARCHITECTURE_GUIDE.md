# 🏗️ Independent AI Architecture - Visual Guide

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   Your Test Methods                             │
│  (method_reboot.py, method_navigate_inputs_xumo.py, etc.)      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ↓ (use)
┌─────────────────────────────────────────────────────────────────┐
│         Unified Screen Validator                                │
│    (services/unified_screen_validator.py)                       │
│                                                                 │
│  ✓ Provider detection  ✓ Fallback logic  ✓ Logging            │
└──────────────┬──────────────────────────┬──────────────────────┘
               │ (selects)                 │
               ↓                           ↓
    ┌──────────────────┐        ┌──────────────────┐
    │   OLLAMA         │        │    GEMINI        │
    │   (Local)        │        │    (Cloud)       │
    │                  │        │                  │
    │ ✓ Free           │        │ ✓ Faster         │
    │ ✓ Private        │        │ ✓ More Accurate  │
    │ ✓ Offline        │        │ ✗ Requires key   │
    │ ✓ Independent    │        │ ✗ Network needed │
    └────────┬─────────┘        └────────┬─────────┘
             │                          │
             ↓                          ↓
    ┌──────────────────┐        ┌──────────────────┐
    │  LLaVA Model     │        │  Gemini API      │
    │  (Your PC)       │        │  (Google Servers)│
    │                  │        │                  │
    │ llama-2-7b       │        │ gemini-2.0-flash │
    │ Vision Weights   │        │ Vision API       │
    └──────────────────┘        └──────────────────┘
```

---

## Configuration Flow

```
.env file
    │
    ├─ SCREEN_VALIDATION_PROVIDER = 'ollama' ────┐
    │                                              ↓
    │  config_screen_validation_provider.py ──→ UnifiedScreenValidator
    │                                              │
    ├─ OLLAMA_BASE_URL = 'http://localhost:11434'┤
    │                                              │
    ├─ GOOGLE_API_KEY = 'xxxxx' (optional) ──────┤
    │                                              ↓
    ├─ SCREEN_MATCH_CONFIDENCE_THRESHOLD = 0.6 ─┤ Creates instance
    │                                              │
    └─ DEBUG_SCREEN_VALIDATION = false ──────────┴→ validator = UnifiedScreenValidator()
```

---

## Usage Flow

```
Method Code
    │
    ├─ from services.unified_screen_validator import validate_screen
    │
    ├─ is_valid = validate_screen(
    │       screenshot_path="screenshot.png",
    │       expected_screen="HOME"
    │   )
    │
    ↓
UnifiedScreenValidator.validate_screen()
    │
    ├─ Checks SCREEN_VALIDATION_PROVIDER config
    │
    ├─ If 'ollama':  ─────┐
    │                      ├──→ OllamaScreenValidator.validate_screen()
    │                      │       │
    │                      │       ├─ Send image to http://localhost:11434
    │                      │       ├─ LLaVA analyzes image
    │                      │       ├─ Extract confidence score
    │                      │       └─ Return match & confidence
    │                      │
    ├─ If 'gemini': ──┐   │
    │                 ├───→ AIScreenAnalyzer.validate_screenshot()
    │                 │       │
    │                 │       ├─ Send image to Google API
    │ ┌────────────┐  │       ├─ Gemini analyzes image
    │ │ Available: │  │       ├─ Extract confidence score
    │ │ Ollama? ✓  │  │       └─ Return match & confidence
    │ │ Gemini? ?  │  │
    │ └────────────┘  │
    │                 │
    ├─ If 'hybrid': ──┤
    │                 ├───→ Try Ollama first
    │                 │     If confidence < threshold:
    │                 │       └─ Fall back to Gemini
    │                 │
    └─ If 'legacy': ──→ Return False (fallback to legacy validation)
```

---

## Example: OllamaScreenValidator Inner Workings

```
OllamaScreenValidator.validate_screen_detailed()
    │
    ├─ Check: Is Ollama service running?
    │   curl http://localhost:11434/api/tags
    │   ✓ Yes → Continue
    │   ✗ No  → Return {error: "Ollama not available"}
    │
    ├─ Encode image to base64
    │   screenshot.png → Base64 string
    │
    ├─ Create prompt
    │   "Analyze this TV screenshot. Is this the HOME screen?"
    │
    ├─ Send request to Ollama API
    │   POST http://localhost:11434/api/generate
    │   {
    │     "model": "llava",
    │     "prompt": "...",
    │     "images": [base64_image]
    │   }
    │
    ├─ LLaVA processes request
    │   1. Load model (5-15s first time, cached after)
    │   2. Analyze image with vision weights
    │   3. Generate response
    │   4. Return text analysis
    │
    ├─ Parse response
    │   Extract confidence score (0-100%)
    │   Extract match decision (Yes/No)
    │
    └─ Return result
        {
          'match': True,
          'confidence': 87,
          'analysis': '...',
          'provider': 'ollama'
        }
```

---

## Confidence Scoring Logic

```
LLaVA Response Analysis
    │
    ├─ Look for explicit confidence:
    │   "confidence: 85%" ──→ Extract: 85
    │   "90% confident"   ──→ Extract: 90
    │
    ├─ Fall back to keyword scoring:
    │   Count positive keywords (yes, match, correct, etc.)
    │   Count negative keywords (no, wrong, different, etc.)
    │   
    │   Positive > Negative  ──→ Score: 85%
    │   Positive = Negative  ──→ Score: 50%
    │   Positive < Negative  ──→ Score: 20%
    │
    └─ Final: Confidence from 0-100%
        
        Match Decision:
        ├─ If confidence >= THRESHOLD (default 0.6)
        │   └─ Return: match = True
        └─ If confidence < THRESHOLD
            └─ Return: match = False
```

---

## Fallback Chain (Hybrid Mode)

```
validate_screen(screenshot, "HOME")
    │
    ├─ Try Ollama
    │   │
    │   ├─ Is Ollama running? ✗ → Skip to Gemini
    │   │
    │   └─ Get confidence (e.g., 75%)
    │       │
    │       ├─ Confidence >= 50%? ✓ → Use this result, return match
    │       └─ Confidence < 50%? → Try Gemini
    │
    ├─ Try Gemini (fallback)
    │   │
    │   ├─ Is Gemini configured? ✗ → Skip to legacy
    │   │
    │   └─ Get confidence (e.g., 92%)
    │       │
    │       └─ Return this result, mark as "fallback_used": True
    │
    └─ Legacy validation (last resort)
        └─ Return False, log warning
```

---

## File Structure

```
services/
├── unified_screen_validator.py          ← Main interface (everyone uses this)
├── ai_screen_analyzer.py                ← Existing Gemini validator
├── ai_screen_validation_bridge.py       ← Existing bridge
├── screen_validation_service.py         ← Existing service
└── ai_vision/
    ├── ai_integration_universal.py      ← Existing universal validator
    ├── ai_vision_ocr.py                 ← Existing OCR module
    └── ai_screen_validator_ollama.py    ← NEW: Ollama-based validator

config/
├── config_ai_screen_analyzer.py         ← Existing Gemini config
├── config_ai_vision.py                  ← Existing vision config
└── config_screen_validation_provider.py ← NEW: Provider selection config

(root)
├── INDEPENDENT_AI_SETUP.md              ← NEW: Complete setup guide
├── IMPLEMENTATION_SUMMARY.md            ← NEW: This summary
└── .env.example.ollama                  ← NEW: Configuration template
```

---

## Integration Checklist

### For Existing Methods:

- [ ] **Option 1: No code change (recommended)**
  - Existing validation code continues working
  - Set `SCREEN_VALIDATION_PROVIDER=ollama` in `.env`
  - System auto-detects and uses Ollama

- [ ] **Option 2: Update to unified validator (optional)**
  - Replace: `from services.ai_screen_analyzer import AIScreenAnalyzer`
  - With: `from services.unified_screen_validator import validate_screen`
  - Benefits: Better error handling, cleaner code

### For New Methods:

- [ ] Use unified validator from the start
  ```python
  from services.unified_screen_validator import validate_screen
  is_valid = validate_screen(screenshot_path, expected_screen)
  ```

---

## Monitoring & Debugging

### Enable debug logging
```bash
export DEBUG_SCREEN_VALIDATION=true
```

### Check which provider is active
```python
from services.unified_screen_validator import UnifiedScreenValidator
v = UnifiedScreenValidator()
info = v.get_provider_info()
print(f"Configured: {info['configured']}")  # What .env says
print(f"Actual: {info['actual']}")          # What's running
print(f"Available: {info['available']}")    # Is it working?
```

### View Ollama logs
```bash
# Terminal where ollama serve is running
# Shows all API calls and processing
```

### Test a screenshot
```python
from services.unified_screen_validator import validate_screen_detailed

result = validate_screen_detailed(
    screenshot_path="/path/to/screenshot.png",
    expected_screen="HOME"
)

print(f"Match: {result['match']}")
print(f"Confidence: {result['confidence']}%")
print(f"Provider: {result['provider']}")
print(f"Analysis: {result['analysis'][:200]}...")  # First 200 chars
```

---

## Migration Timeline

```
Week 1:
├─ Install Ollama
├─ Pull llava model
└─ Start ollama serve (keep running)

Week 2:
├─ Set SCREEN_VALIDATION_PROVIDER=ollama in .env
└─ Run existing tests (should work unchanged)

Week 3:
├─ Monitor: Check confidence scores are good (>60%)
├─ Optional: Update methods to use unified_screen_validator
└─ Celebrate: 100% independent AI now! 🎉

Week 4+:
├─ Consider hybrid mode for critical tests
├─ Fine-tune SCREEN_MATCH_CONFIDENCE_THRESHOLD
└─ Collect performance metrics
```

---

## Success Metrics

After implementing independent AI (Ollama):

| Metric | Current | Target |
|--------|---------|--------|
| **External Dependencies** | 1 (Gemini) | 0 ✅ |
| **API Key Required** | Yes | No ✅ |
| **Works Offline** | No | Yes ✅ |
| **Network Calls** | Every validation | Never ✅ |
| **Cost** | Potentially paid | Free forever ✅ |
| **Privacy** | Images to Google | Stays on machine ✅ |
| **Setup Time** | 2 min | 10 min |
| **Accuracy** | 95%+ | 85-92% |

**Trade-off:** Slightly lower accuracy for complete independence & privacy ✓

