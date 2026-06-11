"""
Configuration for SSH/SFTP Connection Management and Performance Optimization

This file contains settings to prevent "EOF during negotiation" errors and connection exhaustion issues.
"""

# SSH Connection Pool Configuration
SSH_CONNECTION_POOL = {
    # Maximum number of concurrent SSH connections per device
    'max_connections_per_device': 10,
    
    # Global maximum connections across all devices
    'max_total_connections': 100,
    
    # Time in seconds before idle connection is closed
    'idle_timeout': 300,  # 5 minutes
    
    # Connection timeout for establishing new connections
    'connection_timeout': 15,
    
    # Minimum delay between rapid SSH operations (seconds)
    'operation_delay': 0.3,
    
    # Enable connection pooling and reuse
    'enable_pooling': True,
}

# SFTP Configuration
SFTP_CONFIG = {
    # Retry attempts for SFTP channel opening on EOF error
    'max_retries_on_eof': 3,
    
    # Delay between retries (seconds)
    'retry_delay': 1.0,
    
    # Timeout for SFTP operations (seconds)
    'operation_timeout': 30,
    
    # Use SSH fallback if SFTP fails
    'enable_ssh_fallback': True,
}

# SSH Command Batching (to reduce connection count)
SSH_COMMAND_BATCHING = {
    # Maximum commands per SSH session before reconnecting
    'max_commands_per_session': 20,
    
    # Batch multiple commands together
    'enable_command_batching': True,
    
    # Delay between batched commands (seconds)
    'batch_command_delay': 0.1,
}

# Navigate Inputs Specific Configuration
NAVIGATE_INPUTS_CONFIG = {
    # Delay between screenshot captures (seconds)
    'screenshot_delay': 0.5,
    
    # Maximum concurrent screenshot operations
    'max_concurrent_screenshots': 3,
    
    # Timeout for screenshot operations (seconds)
    'screenshot_timeout': 60,
    
    # Enable log collection on failure
    'collect_logs_on_failure': True,
    
    # Log collection timeout (seconds)
    'log_collection_timeout': 30,
}

# Device-Specific SSH Limits (for devices with resource constraints)
DEVICE_SPECIFIC_LIMITS = {
    '10.0.0.110': {  # PIONEER-UHD
        'max_concurrent_connections': 5,  # Lower limit for Pioneer
        'operation_delay': 0.5,  # Longer delay between operations
        'use_light_weight_sftp': True,  # Use SSH fallback first
    },
    # Add more devices as needed
}

# Logging and Debugging
DEBUG_CONFIG = {
    # Log connection pool statistics
    'log_pool_stats': True,
    
    # Log SFTP retry attempts
    'log_sftp_retries': True,
    
    # Log connection operations
    'log_connection_ops': True,
    
    # Log SSH command execution
    'log_command_execution': False,  # Set to True for verbose logging
}
