"""
OLLAMA API Routes
REST endpoints for OLLAMA-powered screen validation and analysis

Endpoints:
- POST /api/ollama/verify-screen - Verify screen content
- POST /api/ollama/analyze-error - Analyze error messages
- POST /api/ollama/validate-elements - Validate UI elements
- GET /api/ollama/status - Check OLLAMA service status
- GET /api/ollama/models - List available models
"""

from __future__ import annotations
from flask import request, jsonify, Blueprint
from services.ollama_integration import get_ollama_service
import logging
import os
from werkzeug.utils import secure_filename

# Configure logging
logger = logging.getLogger(__name__)

# Create Blueprint
ollama_bp = Blueprint('ollama', __name__, url_prefix='/api/ollama')

# Allowed file extensions for uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@ollama_bp.route('/status', methods=['GET'])
def status():
    """
    Check OLLAMA service status
    
    Response:
    {
        "status": "available|unavailable",
        "models": ["mistral", ...],
        "base_url": "http://localhost:11434"
    }
    """
    try:
        service = get_ollama_service()
        is_available = service.is_available()
        
        return jsonify({
            "status": "available" if is_available else "unavailable",
            "models": service.get_available_models() if is_available else [],
            "base_url": service.base_url,
            "timestamp": str(__import__('datetime').datetime.now())
        }), 200
    except Exception as e:
        logger.error(f"Error checking OLLAMA status: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@ollama_bp.route('/models', methods=['GET'])
def models():
    """
    Get list of available OLLAMA models
    
    Response:
    {
        "models": ["mistral", "llama2", ...],
        "count": 2
    }
    """
    try:
        service = get_ollama_service()
        available_models = service.get_available_models()
        
        return jsonify({
            "models": available_models,
            "count": len(available_models),
            "timestamp": str(__import__('datetime').datetime.now())
        }), 200
    except Exception as e:
        logger.error(f"Error fetching models: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@ollama_bp.route('/verify-screen', methods=['POST'])
def verify_screen():
    """
    Verify screen content matches expected content
    
    Request:
    {
        "screenshot": "base64_encoded_image or file",
        "expected_content": "what to look for",
        "context": "optional additional context"
    }
    
    Response:
    {
        "verified": bool,
        "confidence": 0.0-1.0,
        "message": "string",
        "analysis": "detailed analysis",
        "timestamp": "ISO timestamp"
    }
    """
    try:
        # Get screenshot from request
        screenshot_path = None
        
        if 'file' in request.files:
            # File upload
            file = request.files['file']
            if file and allowed_file(file.filename):
                # Save temporarily
                filename = secure_filename(file.filename)
                temp_dir = '/tmp/ollama_uploads'
                os.makedirs(temp_dir, exist_ok=True)
                screenshot_path = os.path.join(temp_dir, filename)
                file.save(screenshot_path)
            else:
                return jsonify({
                    "verified": False,
                    "message": "Invalid file type. Allowed: png, jpg, jpeg, gif, bmp"
                }), 400
        
        elif 'screenshot_path' in request.json:
            # Direct path
            screenshot_path = request.json.get('screenshot_path')
        
        if not screenshot_path:
            return jsonify({
                "verified": False,
                "message": "No screenshot provided"
            }), 400
        
        # Get expected content
        expected_content = request.json.get('expected_content', '')
        context = request.json.get('context', None)
        
        if not expected_content:
            return jsonify({
                "verified": False,
                "message": "expected_content is required"
            }), 400
        
        # Verify screen content
        service = get_ollama_service()
        result = service.verify_screen_content(screenshot_path, expected_content, context)
        
        # Clean up temp file
        if 'file' in request.files and os.path.exists(screenshot_path):
            try:
                os.remove(screenshot_path)
            except:
                pass
        
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Error verifying screen content: {e}")
        return jsonify({
            "verified": False,
            "message": f"Error: {str(e)}"
        }), 500

@ollama_bp.route('/analyze-error', methods=['POST'])
def analyze_error():
    """
    Analyze screenshot for error messages
    
    Request:
    {
        "screenshot": "base64_encoded_image or file",
    }
    
    Response:
    {
        "has_error": bool,
        "error_messages": ["error1", "error2"],
        "severity": "low|medium|high|critical",
        "analysis": "detailed analysis",
        "timestamp": "ISO timestamp"
    }
    """
    try:
        # Get screenshot from request
        screenshot_path = None
        
        if 'file' in request.files:
            # File upload
            file = request.files['file']
            if file and allowed_file(file.filename):
                # Save temporarily
                filename = secure_filename(file.filename)
                temp_dir = '/tmp/ollama_uploads'
                os.makedirs(temp_dir, exist_ok=True)
                screenshot_path = os.path.join(temp_dir, filename)
                file.save(screenshot_path)
            else:
                return jsonify({
                    "has_error": False,
                    "message": "Invalid file type"
                }), 400
        
        elif 'screenshot_path' in request.json:
            screenshot_path = request.json.get('screenshot_path')
        
        if not screenshot_path:
            return jsonify({
                "has_error": False,
                "message": "No screenshot provided"
            }), 400
        
        # Analyze errors
        service = get_ollama_service()
        result = service.analyze_error_message(screenshot_path)
        
        # Clean up temp file
        if 'file' in request.files and os.path.exists(screenshot_path):
            try:
                os.remove(screenshot_path)
            except:
                pass
        
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Error analyzing error: {e}")
        return jsonify({
            "has_error": False,
            "message": f"Error: {str(e)}"
        }), 500

@ollama_bp.route('/validate-elements', methods=['POST'])
def validate_elements():
    """
    Validate presence of UI elements
    
    Request:
    {
        "screenshot": "base64_encoded_image or file",
        "elements": ["button", "input field", "error message", ...]
    }
    
    Response:
    {
        "all_found": bool,
        "found_elements": ["element1", ...],
        "missing_elements": ["element2", ...],
        "analysis": "detailed analysis",
        "timestamp": "ISO timestamp"
    }
    """
    try:
        # Get screenshot from request
        screenshot_path = None
        
        if 'file' in request.files:
            # File upload
            file = request.files['file']
            if file and allowed_file(file.filename):
                # Save temporarily
                filename = secure_filename(file.filename)
                temp_dir = '/tmp/ollama_uploads'
                os.makedirs(temp_dir, exist_ok=True)
                screenshot_path = os.path.join(temp_dir, filename)
                file.save(screenshot_path)
            else:
                return jsonify({
                    "all_found": False,
                    "message": "Invalid file type"
                }), 400
        
        elif 'screenshot_path' in request.json:
            screenshot_path = request.json.get('screenshot_path')
        
        if not screenshot_path:
            return jsonify({
                "all_found": False,
                "message": "No screenshot provided"
            }), 400
        
        # Get elements to validate
        elements = request.json.get('elements', [])
        if not elements:
            return jsonify({
                "all_found": False,
                "message": "elements list is required"
            }), 400
        
        # Validate elements
        service = get_ollama_service()
        result = service.validate_ui_elements(screenshot_path, elements)
        
        # Clean up temp file
        if 'file' in request.files and os.path.exists(screenshot_path):
            try:
                os.remove(screenshot_path)
            except:
                pass
        
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Error validating elements: {e}")
        return jsonify({
            "all_found": False,
            "message": f"Error: {str(e)}"
        }), 500
