"""
Screenshot Configuration
Based on Device-Reboot-DeepSleep-Wakeup_Updated.py
"""

# Screenshot server settings - Thunder server
upload_base_url = "https://thunderstrikes.stb.r53.xcal.tv:9443/cgi-bin/screenCaptureUpload.cgi"
download_base_url = "https://thunderstrikes.stb.r53.xcal.tv:9443/screenCapture/upload/"
listing_url = "https://thunderstrikes.stb.r53.xcal.tv:9443/screenCapture/upload/"
rpc_url = "http://127.0.0.1:9998/jsonrpc"  # RPC endpoint on the device

# Screenshot timeout settings
screenshot_upload_timeout = 20  # seconds to wait after upload command (increased from 10 to ensure screenshot captures completely)
screenshot_download_timeout = 30  # seconds to wait for download

# OCR configuration
# Note: Tesseract OCR must be installed on the system
# Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
# Linux: sudo apt-get install tesseract-ocr
# macOS: brew install tesseract

# Screen state detection keywords
HOME_SCREEN_KEYWORDS = ['home', 'sky', 'menu', 'apps', 'channels', 'View All']
NETWORK_ERROR_KEYWORDS = ['no connection', 'network error', 'try again', 'refresh your connection', 'check your connection']
LOADING_KEYWORDS = ['loading', 'please wait', 'buffering']
ERROR_KEYWORDS = ['error', 'failed', 'unable', 'cannot']

# Minimum text length to consider screen as non-blank
MIN_TEXT_LENGTH = 10
