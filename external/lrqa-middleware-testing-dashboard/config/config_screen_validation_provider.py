"""
Screen Validation Provider Configuration
Controls which AI provider is used for screen validation

Options:
    'ollama'  -> Local, free, no API keys needed (RECOMMENDED for independence)
    'gemini'  -> Cloud-based, requires API key, faster but external dependency
    'hybrid'  -> Try Ollama first, fallback to Gemini if needed
"""

import os

# ============================================================
# SCREEN VALIDATION PROVIDER SELECTION
# ============================================================

# DEFAULT: Use Ollama (local, free, independent)
# Set to: 'ollama', 'gemini', 'hybrid', 'legacy'
SCREEN_VALIDATION_PROVIDER = os.getenv('SCREEN_VALIDATION_PROVIDER', 'ollama')

# Detailed provider configuration

# Ollama Configuration (100% INDEPENDENT - No external services)
OLLAMA_SCREEN_VALIDATOR_ENABLED = (SCREEN_VALIDATION_PROVIDER in ['ollama', 'hybrid'])
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llava')  # Vision model
OLLAMA_TIMEOUT = int(os.getenv('OLLAMA_TIMEOUT', '60'))

# Gemini Configuration (Cloud-based - Requires API key)
GEMINI_SCREEN_VALIDATOR_ENABLED = (SCREEN_VALIDATION_PROVIDER in ['gemini', 'hybrid'])
GEMINI_API_KEY = os.getenv('GOOGLE_API_KEY', '')
GEMINI_MODEL = os.getenv('GEMINI_VISION_MODEL', 'gemini-2.0-flash')

# Hybrid Mode Settings
HYBRID_TRY_OLLAMA_FIRST = (SCREEN_VALIDATION_PROVIDER == 'hybrid')
HYBRID_FALLBACK_TO_GEMINI = (SCREEN_VALIDATION_PROVIDER == 'hybrid')
HYBRID_FALLBACK_CONFIDENCE_THRESHOLD = float(os.getenv('HYBRID_FALLBACK_THRESHOLD', '0.5'))

# ============================================================
# VALIDATION SETTINGS
# ============================================================

# Confidence threshold for screen matching (0.0-1.0)
SCREEN_MATCH_CONFIDENCE_THRESHOLD = float(os.getenv('SCREEN_MATCH_CONFIDENCE_THRESHOLD', '0.6'))

# Fallback to legacy pixel-based validation if AI fails
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
QUICK START - Use Local Ollama (100% Independent, NO API keys):

1. Install Ollama:
   - macOS: brew install ollama
   - Linux: curl https://ollama.ai/install.sh | sh
   - Windows: Download from https://ollama.ai

2. Pull vision model:
   ollama pull llava
   
3. Start Ollama server:
   ollama serve
   
4. Set environment variable:
   export SCREEN_VALIDATION_PROVIDER='ollama'

5. Test it works:
   python -c "from services.ai_vision.ai_screen_validator_ollama import OllamaScreenValidator; v = OllamaScreenValidator(); print('✅ Ready' if v.available else '❌ Ollama not running')"


ALTERNATIVE - Use Cloud Gemini (Requires API key):

1. Get Google Gemini API key:
   - Go to https://makersuite.google.com/app/apikey
   - Create new API key
   - Copy the key

2. Set environment variables:
   export GOOGLE_API_KEY='your-key-here'
   export SCREEN_VALIDATION_PROVIDER='gemini'

3. Verify:
   python -c "from services.ai_screen_analyzer import AIScreenAnalyzer; a = AIScreenAnalyzer(); print('✅ Ready' if a.client else '❌ Not configured')"


HYBRID MODE - Try Local First, Cloud Fallback:

1. Install both Ollama (local) and get Gemini API key (cloud)

2. Set environment variable:
   export SCREEN_VALIDATION_PROVIDER='hybrid'
   export GOOGLE_API_KEY='your-key-here'

3. System will:
   - Try Ollama first (local, fast, free)
   - Fall back to Gemini if Ollama confidence is low
   - Fall back to legacy pixel validation if both fail
"""
