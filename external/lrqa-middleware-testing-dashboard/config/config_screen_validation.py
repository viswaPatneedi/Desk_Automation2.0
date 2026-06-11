"""
Configuration for AI-powered Screen Validation using SAM-CD

This configuration defines screen validation settings and reference mappings
for different device states (HOME, Netflix, YouTube, etc.)
"""

# Screen validation settings
SCREEN_VALIDATION_CONFIG = {
    'enabled': True,  # Set to False to disable AI validation
    'change_ratio_threshold': 0.0005,  # Lower = more strict matching
    'use_aspect_ratio': True,  # Maintain aspect ratio during comparison
    'cleanup_temp_files': True,  # Clean up temporary mask files after validation
}

# Screen type definitions and their validation regions
# Region format: [x1, x2, y1, y2] - leave None for full screen comparison
SCREEN_DEFINITIONS = {
    'HOME': {
        'description': 'Device home screen with main menu',
        'region': None,  # Full screen comparison
        'change_ratio': 0.0005,
    },
    'NETFLIX_HOME': {
        'description': 'Netflix home screen with content browsing',
        'region': [0, 100, 0, 512],  # Focus on top menu area
        'change_ratio': 0.001,
    },
    'NETFLIX_SIGNIN': {
        'description': 'Netflix sign-in page',
        'region': None,
        'change_ratio': 0.0005,
    },
    'YOUTUBE_HOME': {
        'description': 'YouTube home screen',
        'region': None,
        'change_ratio': 0.0005,
    },
    'YOUTUBE_SIGNIN': {
        'description': 'YouTube sign-in page',
        'region': None,
        'change_ratio': 0.0005,
    },
    'PRIME_HOME': {
        'description': 'Amazon Prime Video home screen',
        'region': None,
        'change_ratio': 0.001,
    },
    'PRIME_SIGNIN': {
        'description': 'Amazon Prime Video sign-in page',
        'region': None,
        'change_ratio': 0.0005,
    },
    'DISNEY_HOME': {
        'description': 'Disney+ home screen',
        'region': None,
        'change_ratio': 0.001,
    },
    'SPOTIFY_HOME': {
        'description': 'Spotify home screen',
        'region': None,
        'change_ratio': 0.001,
    },
    'BOOT_SCREEN': {
        'description': 'Device boot/loading screen',
        'region': None,
        'change_ratio': 0.0005,
    },
    'ERROR_SCREEN': {
        'description': 'Error or crash screen',
        'region': None,
        'change_ratio': 0.001,
    },
}

# Method to expected screen mapping
# Maps test methods to their expected final screen state
METHOD_EXPECTED_SCREENS = {
    'reboot': 'HOME',
    'deepsleep': 'HOME',
    'voice_command': 'HOME',  # Or specific screen based on command
    'remote_keys': 'HOME',  # Or specific screen based on keys pressed
    'ir_test': 'HOME',
}

# Device-specific screen mappings (override defaults)
DEVICE_SCREEN_OVERRIDES = {
    'Element-A4K-DESK': {
        'HOME': {
            'change_ratio': 0.0008,  # Element devices might need slightly relaxed threshold
        }
    },
    'SHARP-HARDIK-DESK': {
        'HOME': {
            'change_ratio': 0.0006,
        }
    },
    # Add more device-specific overrides as needed
}

def get_screen_config(screen_name, device_name=None):
    """
    Get screen validation configuration with device-specific overrides
    
    Args:
        screen_name (str): Screen identifier (e.g., 'HOME', 'NETFLIX_HOME')
        device_name (str): Optional device name for device-specific settings
        
    Returns:
        dict: Screen configuration with all settings
    """
    if screen_name not in SCREEN_DEFINITIONS:
        return None
    
    config = SCREEN_DEFINITIONS[screen_name].copy()
    
    # Apply device-specific overrides
    if device_name and device_name in DEVICE_SCREEN_OVERRIDES:
        device_overrides = DEVICE_SCREEN_OVERRIDES[device_name]
        if screen_name in device_overrides:
            config.update(device_overrides[screen_name])
    
    return config

def get_expected_screen_for_method(method_name):
    """
    Get the expected screen state after executing a method
    
    Args:
        method_name (str): Method name (e.g., 'reboot', 'deepsleep')
        
    Returns:
        str: Expected screen name
    """
    return METHOD_EXPECTED_SCREENS.get(method_name, 'HOME')
