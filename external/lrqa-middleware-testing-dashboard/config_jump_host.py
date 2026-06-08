"""
Jump Host Configuration
Centralized configuration for jump host connections
"""

# Jump host configurations by location
JUMP_HOSTS = {
    'usa_philadelphia': {
        'host': '96.118.26.235',
        'port': 22,
        'name': 'acrylic-platco-only-lab',
        'description': 'GRRE Jumphost - Philadelphia USA Lab'
    },
    'india_bangalore': {
        'host': '',  # To be filled when India jump host is available
        'port': 22,
        'name': '',
        'description': 'GRRE Jumphost - Bangalore India Lab'
    }
}

# Default jump host for cloud deployment
DEFAULT_JUMP_HOST = 'usa_philadelphia'

def get_jump_host_config(location: str = None) -> dict:
    """
    Get jump host configuration for a specific location
    
    Args:
        location: Location key (e.g., 'usa_philadelphia', 'india_bangalore')
                 If None, returns default jump host
    
    Returns:
        Dictionary with jump host configuration
    """
    if location is None:
        location = DEFAULT_JUMP_HOST
    
    return JUMP_HOSTS.get(location, JUMP_HOSTS[DEFAULT_JUMP_HOST])

def get_available_jump_hosts() -> list:
    """
    Get list of available jump hosts
    
    Returns:
        List of tuples (key, name, description)
    """
    return [
        (key, config['name'], config['description'])
        for key, config in JUMP_HOSTS.items()
        if config['host']  # Only include configured jump hosts
    ]

# Connection settings
JUMP_HOST_CONNECTION_TIMEOUT = 10  # seconds
JUMP_HOST_COMMAND_TIMEOUT = 30  # seconds
JUMP_HOST_MENU_TIMEOUT = 5  # seconds

# Enable/disable jump host globally
JUMP_HOST_ENABLED = False  # Set to True to enable jump host connections globally

def is_jump_host_enabled() -> bool:
    """Check if jump host is enabled globally"""
    return JUMP_HOST_ENABLED
