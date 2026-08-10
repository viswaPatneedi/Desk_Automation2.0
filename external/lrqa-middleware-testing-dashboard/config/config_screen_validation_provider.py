"""
Screen Validation Provider Configuration
Controls which AI provider is used for screen validation

CURRENT STATUS: OLLAMA EXCLUSIVE MODE
- All screen validation uses OLLAMA (local, free, no API keys)
- No cloud dependencies (Google Gemini disabled)
- No hybrid mode or fallbacks to external services
- 100% self-contained AI execution
"""

import os

# ============================================================
# SCREEN VALIDATION PROVIDER SELECTION
# ============================================================

# FORCED TO OLLAMA ONLY - No alternatives
# This ensures 100% local AI execution with no cloud dependencies
SCREEN_VALIDATION_PROVIDER = 'ollama'  # HARDCODED - DO NOT CHANGE

# Detailed provider configuration

# Ollama Configuration (100% INDEPENDENT - No external services)
OLLAMA_SCREEN_VALIDATOR_ENABLED = True  # Always enabled
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llava')  # Vision model
OLLAMA_TIMEOUT = int(os.getenv('OLLAMA_TIMEOUT', '60'))

# Cloud providers DISABLED
GEMINI_SCREEN_VALIDATOR_ENABLED = False  # DISABLED - Using OLLAMA only
GOOGLE_API_KEY = ''  # NOT USED
GEMINI_MODEL = '' # NOT USED

# Hybrid Mode DISABLED
HYBRID_TRY_OLLAMA_FIRST = False
HYBRID_FALLBACK_TO_GEMINI = False
HYBRID_FALLBACK_CONFIDENCE_THRESHOLD = 0.0

# ============================================================
# VALIDATION SETTINGS
# ============================================================

# Confidence threshold for screen matching (0.0-1.0)
SCREEN_MATCH_CONFIDENCE_THRESHOLD = float(os.getenv('SCREEN_MATCH_CONFIDENCE_THRESHOLD', '0.6'))

# Fallback to legacy pixel-based validation if AI fails (OLLAMA only fallback)
FALLBACK_TO_LEGACY_VALIDATION = os.getenv('FALLBACK_TO_LEGACY_VALIDATION', 'true').lower() == 'true'

# ============================================================
# DEBUG & LOGGING
# ============================================================

DEBUG_SCREEN_VALIDATION = os.getenv('DEBUG_SCREEN_VALIDATION', 'false').lower() == 'true'
SAVE_VALIDATION_REPORTS = os.getenv('SAVE_VALIDATION_REPORTS', 'false').lower() == 'true'
VALIDATION_REPORT_DIR = os.getenv('VALIDATION_REPORT_DIR', 'Enhancement_output/validation_reports')

# ============================================================
# SETUP INSTRUCTIONS
# ============================================================

"""
OLLAMA-EXCLUSIVE MODE (No alternatives)

1. Ensure OLLAMA is running:
   ollama serve
   
2. Verify OLLAMA is accessible:
   curl http://localhost:11434/api/tags
   
3. Models should include:
   - mistral:latest (for text generation)
   - llava:latest (for vision/screen analysis)
   
4. No configuration needed:
   - System auto-detects OLLAMA
   - No API keys required
   - No environment variables needed
   - Works out-of-the-box with defaults

5. Verify it's working:
   python -c "from services.ollama_integration import get_ollama_service; s = get_ollama_service(); print('READY' if s.is_available() else 'NOT AVAILABLE')"
"""

2. Set environment variable:
   export SCREEN_VALIDATION_PROVIDER='hybrid'
   export GOOGLE_API_KEY='your-key-here'

3. System will:
   - Try Ollama first (local, fast, free)
   - Fall back to Gemini if Ollama confidence is low
   - Fall back to legacy pixel validation if both fail
"""
