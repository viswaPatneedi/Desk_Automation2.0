"""
AI Vision Configuration for Screenshot Text Extraction
Supports multiple AI vision providers with fallback to Tesseract OCR
"""

import os

# AI Vision Provider Selection
# Options: 'ollama', 'openai', 'google', 'azure', 'tesseract'
AI_VISION_PROVIDER = os.getenv('AI_VISION_PROVIDER', 'ollama')  # Default to OLLAMA (local, free, no API keys)

# Ollama Configuration (FREE - runs locally)
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llava')  # llava, bakllava, or llava-phi3

# OpenAI Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')  # Set via environment variable
OPENAI_MODEL = 'gpt-4o'  # gpt-4o has vision capabilities
OPENAI_MAX_TOKENS = 1000

# Google Cloud Vision Configuration
GOOGLE_CREDENTIALS_PATH = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')

# Azure Computer Vision Configuration
AZURE_VISION_KEY = os.getenv('AZURE_VISION_KEY', '')
AZURE_VISION_ENDPOINT = os.getenv('AZURE_VISION_ENDPOINT', '')

# AI Vision Settings
AI_VISION_TIMEOUT = 30  # seconds
AI_VISION_RETRY_COUNT = 2

# Fallback Strategy
# If True, falls back to Tesseract if AI vision fails
FALLBACK_TO_TESSERACT = True

# Enable/Disable AI Vision
USE_AI_VISION = AI_VISION_PROVIDER != 'tesseract' and (
    (AI_VISION_PROVIDER == 'ollama') or  # Ollama is always available if running
    (AI_VISION_PROVIDER == 'openai' and OPENAI_API_KEY) or
    (AI_VISION_PROVIDER == 'google' and GOOGLE_CREDENTIALS_PATH) or
    (AI_VISION_PROVIDER == 'azure' and AZURE_VISION_KEY)
)
