#!/usr/bin/env python3
"""
Heroku production configuration
"""

import os

# Heroku production settings
HEROKU_CONFIG = {
    'REQUEST_TIMEOUT': int(os.getenv('REQUEST_TIMEOUT', '60')),
    'MAX_RETRIES': int(os.getenv('MAX_RETRIES', '5')),
    'BACKOFF_FACTOR': float(os.getenv('BACKOFF_FACTOR', '0.5')),
    'SKIP_INSIGHTS': os.getenv('SKIP_INSIGHTS', 'false').lower() in ['1', 'true', 'yes'],
    'DYNO_TIMEOUT': int(os.getenv('DYNO_TIMEOUT', '300')),
    'WEB_CONCURRENCY': int(os.getenv('WEB_CONCURRENCY', '2')),
    'WORKER_CONNECTIONS': int(os.getenv('WORKER_CONNECTIONS', '1000')),
}

def get_heroku_config():
    """Get Heroku configuration"""
    return HEROKU_CONFIG

def is_heroku():
    """Check if running on Heroku"""
    return os.getenv('DYNO') is not None

def get_timeout_config():
    """Get timeout configuration based on environment"""
    if is_heroku():
        return {
            'request_timeout': HEROKU_CONFIG['REQUEST_TIMEOUT'],
            'max_retries': HEROKU_CONFIG['MAX_RETRIES'],
            'backoff_factor': HEROKU_CONFIG['BACKOFF_FACTOR']
        }
    else:
        return {
            'request_timeout': 30,
            'max_retries': 3,
            'backoff_factor': 0.3
        }
