"""
AI Vision OCR Module
Provides text extraction from images using AI vision APIs
with fallback to Tesseract OCR
"""

import base64
import io
from PIL import Image
from config_ai_vision import *

def extract_text_with_ollama(image, log_callback=None):
    """
    Extract text from image using Ollama with LLaVA (FREE - runs locally)
    
    Args:
        image: PIL Image object
        log_callback: Optional function to call for logging
    
    Returns:
        str: Extracted text
    """
    def log(message):
        if log_callback:
            log_callback(message)
    
    try:
        import requests
        
        # Convert image to base64
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        # Call Ollama API
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": """Extract ALL visible text from this TV screenshot. 
                Include: menu items, buttons, titles, descriptions, app names, and any other readable text.
                Organize the text as it appears on screen from top to bottom.
                Return only the extracted text without any additional commentary.""",
                "images": [img_base64],
                "stream": False
            },
            timeout=AI_VISION_TIMEOUT
        )
        
        if response.status_code == 200:
            result = response.json()
            text = result.get('response', '').strip()
            
            if log_callback:
                log(f"✓ Ollama Vision extracted {len(text)} characters")
            
            return text
        else:
            if log_callback:
                log(f"⚠ Ollama API returned status {response.status_code}")
            return None
            
    except requests.exceptions.ConnectionError:
        if log_callback:
            log("⚠ Ollama not running. Start with: ollama serve")
        return None
    except Exception as e:
        if log_callback:
            log(f"⚠ Ollama Vision error: {str(e)}")
        return None

def extract_text_with_openai(image, log_callback=None):
    """
    Extract text from image using OpenAI GPT-4 Vision
    
    Args:
        image: PIL Image object
        log_callback: Optional function to call for logging
    
    Returns:
        str: Extracted text
    """
    def log(message):
        if log_callback:
            log_callback(message)
    
    try:
        import openai
        from openai import OpenAI
        
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Convert image to base64
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        # Call OpenAI Vision API
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Extract ALL visible text from this TV screenshot. 
                            Include: menu items, buttons, titles, descriptions, app names, and any other readable text.
                            Organize the text as it appears on screen from top to bottom.
                            Return only the extracted text without any additional commentary."""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=OPENAI_MAX_TOKENS,
            timeout=AI_VISION_TIMEOUT
        )
        
        text = response.choices[0].message.content.strip()
        
        if log_callback:
            log(f"✓ OpenAI Vision extracted {len(text)} characters")
        
        return text
        
    except ImportError:
        if log_callback:
            log("⚠ OpenAI package not installed. Run: pip install openai")
        return None
    except Exception as e:
        if log_callback:
            log(f"⚠ OpenAI Vision error: {str(e)}")
        return None

def extract_text_with_ai_vision(image, log_callback=None):
    """
    Extract text from image using configured AI vision provider
    with fallback to Tesseract OCR
    
    Args:
        image: PIL Image object
        log_callback: Optional function to call for logging
    
    Returns:
        str: Extracted text
    """
    def log(message):
        if log_callback:
            log_callback(message)
    
    text = None
    
    # Try AI vision if enabled
    if USE_AI_VISION:
        if log_callback:
            log(f"Using AI Vision provider: {AI_VISION_PROVIDER}")
        
        if AI_VISION_PROVIDER == 'ollama':
            text = extract_text_with_ollama(image, log_callback)
        elif AI_VISION_PROVIDER == 'openai':
            text = extract_text_with_openai(image, log_callback)
        # Add other providers here as needed
        # elif AI_VISION_PROVIDER == 'google':
        #     text = extract_text_with_google(image, log_callback)
        # elif AI_VISION_PROVIDER == 'azure':
        #     text = extract_text_with_azure(image, log_callback)
    
    # Fallback to Tesseract if AI vision failed or not configured
    if text is None and FALLBACK_TO_TESSERACT:
        if log_callback:
            log("Falling back to Tesseract OCR...")
        from screenshot_utils import extract_text_with_preprocessing
        text = extract_text_with_preprocessing(image, log_callback)
    
    return text if text else ""
