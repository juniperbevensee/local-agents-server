"""
Configuration file for the Flask Agent
Adjust these settings to match your LM Studio setup
"""

import os

# LM Studio API Configuration
LM_STUDIO_HOST = os.getenv('LM_STUDIO_HOST', 'localhost')
LM_STUDIO_PORT = os.getenv('LM_STUDIO_PORT', '1234')
LM_STUDIO_URL = f"http://{LM_STUDIO_HOST}:{LM_STUDIO_PORT}/v1/chat/completions"

# Model name (LM Studio typically uses "local-model" or the actual model name)
LM_STUDIO_MODEL = os.getenv('LM_STUDIO_MODEL', 'local-model')

# Flask Server Configuration
FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
FLASK_PORT = int(os.getenv('FLASK_PORT', '5000'))
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() in ('true', '1', 't')

# Content Fetching Configuration
MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', '4000'))
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '10'))

# Summarization Configuration
SUMMARY_MAX_TOKENS = int(os.getenv('SUMMARY_MAX_TOKENS', '500'))
SUMMARY_TEMPERATURE = float(os.getenv('SUMMARY_TEMPERATURE', '0.7'))
