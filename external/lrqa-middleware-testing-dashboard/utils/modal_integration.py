"""
Phase 3 Modal UI Integration Module
Ensures all modals are included in the application and properly initialized
"""

import os
import logging

logger = logging.getLogger(__name__)

def include_modals_in_base_template():
    """
    Returns the HTML string to include all modals in the base layout.html template
    Should be added in layout.html after <body> tag
    """
    modals_html = '''
    <!-- ============================================================ -->
    <!-- PHASE 3 MODAL UI SYSTEM - PRODUCTION READY -->
    <!-- ============================================================ -->

    <!-- BASE MODAL COMPONENTS (Reusable templates) -->
    {% include "modals/base/modal_base.html" %}

    <!-- AUTHENTICATION MODALS -->
    {% include "modals/auth/auth_login.html" %}

    <!-- DEVICE MANAGEMENT MODALS -->
    {% include "modals/device_management/device_management_add.html" %}

    <!-- METHOD EXECUTION MODALS -->
    {% include "modals/method_execution/method_execution_select.html" %}

    <!-- SEQUENCE MANAGEMENT MODALS -->
    {% include "modals/sequence_management/sequence_create.html" %}

    <!-- EXECUTION CONTEXT MODALS -->
    {% include "modals/execution_context/execution_context_capture.html" %}

    <!-- Alert container for notifications -->
    <div id="alertContainer"></div>

    <!-- ============================================================ -->
    <!-- END PHASE 3 MODAL UI SYSTEM -->
    <!-- ============================================================ -->
    '''
    return modals_html

def get_required_assets():
    """
    Returns list of required CSS and JS files for modal system
    """
    return {
        'css': [
            '/static/css/modals.css',  # Main modal styling
        ],
        'js': [
            '/static/js/modal-handlers.js',  # Main modal handlers
        ]
    }

def inject_modal_assets(app):
    """
    Injects modal CSS and JS into Flask app template context
    Should be called in app.py after app initialization
    """
    @app.context_processor
    def inject_modal_assets():
        return {
            'modal_css_files': get_required_assets()['css'],
            'modal_js_files': get_required_assets()['js'],
            'include_modals': include_modals_in_base_template()
        }
    
    logger.info("✅ Modal assets injected into Flask app context")

# For use in base template
MODALS_HTML_SNIPPET = '''
<!-- Include this in your base layout.html template -->
{# Phase 3 Modal UI System #}
<link rel="stylesheet" href="/static/css/modals.css">
<script src="/static/js/modal-handlers.js"></script>

{# Include all modal templates #}
{% include "modals/auth/auth_login.html" %}
{% include "modals/device_management/device_management_add.html" %}
{% include "modals/method_execution/method_execution_select.html" %}
{% include "modals/sequence_management/sequence_create.html" %}
{% include "modals/execution_context/execution_context_capture.html" %}

{# Alert notification container #}
<div id="alertContainer"></div>
'''

# For use in app.py
APP_INITIALIZATION_SNIPPET = '''
# In app.py, after app initialization:

from controllers.modal_routes import register_modal_routes
from utils.modal_integration import inject_modal_assets

# Register modal API routes
register_modal_routes(app)

# Inject modal assets into template context
inject_modal_assets(app)

print("✅ Phase 3 Modal UI System initialized")
'''
