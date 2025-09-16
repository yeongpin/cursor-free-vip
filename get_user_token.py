import requests
import json
import time
import logging
import os
from typing import Optional, Dict, Any, Union
from colorama import Fore, Style, init
from config import get_config

# Initialize colorama
init(autoreset=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Define emoji constants
EMOJI = {
    'START': '🚀',
    'OAUTH': '🔑',
    'SUCCESS': '✅',
    'ERROR': '❌',
    'WAIT': '⏳',
    'INFO': 'ℹ️',
    'WARNING': '⚠️',
    'TOKEN': '🔖',
    'REFRESH': '🔄'
}

def _get_message(translator: Any, key: str, fallback: str, **kwargs) -> str:
    """Get translated message or fallback.
    
    Args:
        translator: Translator object
        key: Translation key
        fallback: Fallback message if translation not available
        **kwargs: Format parameters for the message
        
    Returns:
        str: Translated or fallback message
    """
    if translator:
        return translator.get(key, **kwargs)
    return fallback.format(**kwargs) if kwargs else fallback

def refresh_token(token: str, translator: Any = None) -> str:
    """Refresh the token using the refresh server API.
    
    Args:
        token: The full WorkosCursorSessionToken cookie value
        translator: Optional translator object
        
    Returns:
        str: The refreshed access token or original token if refresh fails
    """
    try:
        logger.info("Attempting to refresh token")
        
        # Validate input
        if not token or not isinstance(token, str):
            logger.error("Invalid token provided")
            print(f"{Fore.RED}{EMOJI['ERROR']} {_get_message(translator, 'token.invalid_token', 'Invalid token provided')}{Style.RESET_ALL}")
            return token
            
        # Get configuration
        config = get_config(translator)
        
        # Check if token refresh is enabled
        if config.has_option('Token', 'enable_refresh') and not config.getboolean('Token', 'enable_refresh'):
            logger.info("Token refresh is disabled in configuration")
            print(f"{Fore.YELLOW}{EMOJI['INFO']} {_get_message(translator, 'token.refresh_disabled', 'Token refresh is disabled in configuration')}{Style.RESET_ALL}")
            return _extract_token_part(token)
            
        # Get refresh_server URL from config or use default
        refresh_server = config.get('Token', 'refresh_server', fallback='https://token.cursorpro.com.cn')
        logger.info(f"Using refresh server: {refresh_server}")
        
        # Ensure the token is URL encoded properly
        encoded_token = _ensure_token_encoded(token)
            
        # Make the request to the refresh server
        url = f"{refresh_server}/reftoken?token={encoded_token}"
        
        print(f"{Fore.CYAN}{EMOJI['REFRESH']} {_get_message(translator, 'token.refreshing', 'Refreshing token...')}{Style.RESET_ALL}")
        
        # Set timeout and headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json'
        }
        
        # Make request with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=headers, timeout=30)
                break
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Request attempt {attempt + 1} failed: {e}. Retrying...")
                    time.sleep(2)
                else:
                    raise
        
        if response.status_code == 200:
            try:
                data = response.json()
                
                if data.get('code') == 0 and data.get('msg') == "获取成功":
                    access_token = data.get('data', {}).get('accessToken')
                    days_left = data.get('data', {}).get('days_left', 0)
                    expire_time = data.get('data', {}).get('expire_time', 'Unknown')
                    
                    if access_token:
                        logger.info(f"Token refreshed successfully. Valid for {days_left} days")
                        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {_get_message(translator, 'token.refresh_success', 'Token refreshed successfully! Valid for {days} days (expires: {expire})', days=days_left, expire=expire_time)}{Style.RESET_ALL}")
                        return access_token
                    else:
                        logger.warning("No access token in response")
                        print(f"{Fore.YELLOW}{EMOJI['WARNING']} {_get_message(translator, 'token.no_access_token', 'No access token in response')}{Style.RESET_ALL}")
                else:
                    error_msg = data.get('msg', 'Unknown error')
                    logger.error(f"Token refresh failed: {error_msg}")
                    print(f"{Fore.RED}{EMOJI['ERROR']} {_get_message(translator, 'token.refresh_failed', 'Token refresh failed: {error}', error=error_msg)}{Style.RESET_ALL}")
            except json.JSONDecodeError:
                logger.error("Invalid JSON response from refresh server")
                print(f"{Fore.RED}{EMOJI['ERROR']} {_get_message(translator, 'token.invalid_response', 'Invalid JSON response from refresh server')}{Style.RESET_ALL}")
        else:
            logger.error(f"Refresh server error: HTTP {response.status_code}")
            print(f"{Fore.RED}{EMOJI['ERROR']} {_get_message(translator, 'token.server_error', 'Refresh server error: HTTP {status}', status=response.status_code)}{Style.RESET_ALL}")
    
    except requests.exceptions.Timeout:
        logger.error("Request to refresh server timed out")
        print(f"{Fore.RED}{EMOJI['ERROR']} {_get_message(translator, 'token.request_timeout', 'Request to refresh server timed out')}{Style.RESET_ALL}")
    except requests.exceptions.ConnectionError:
        logger.error("Connection error to refresh server")
        print(f"{Fore.RED}{EMOJI['ERROR']} {_get_message(translator, 'token.connection_error', 'Connection error to refresh server')}{Style.RESET_ALL}")
    except Exception as e:
        logger.error(f"Unexpected error during token refresh: {e}")
        print(f"{Fore.RED}{EMOJI['ERROR']} {_get_message(translator, 'token.unexpected_error', 'Unexpected error during token refresh: {error}', error=str(e))}{Style.RESET_ALL}")
    
    # Return extracted token part if refresh fails
    return _extract_token_part(token)

def _ensure_token_encoded(token: str) -> str:
    """Ensure the token is properly URL encoded.
    
    Args:
        token: The token to encode
        
    Returns:
        str: The properly encoded token
    """
    if '%3A%3A' not in token and '::' in token:
        # Replace :: with URL encoded version if needed
        return token.replace('::', '%3A%3A')
    return token

def _extract_token_part(token: str) -> str:
    """Extract the token part from the cookie value.
    
    Args:
        token: The full cookie value
        
    Returns:
        str: The extracted token part
    """
    if '%3A%3A' in token:
        return token.split('%3A%3A')[-1]
    elif '::' in token:
        return token.split('::')[-1]
    else:
        return token

def get_token_from_cookie(cookie_value: str, translator: Any = None) -> str:
    """Extract and process token from cookie value.
    
    Args:
        cookie_value: The WorkosCursorSessionToken cookie value
        translator: Optional translator object
        
    Returns:
        str: The processed token
    """
    try:
        logger.info("Processing token from cookie")
        
        # Validate input
        if not cookie_value or not isinstance(cookie_value, str):
            logger.error("Invalid cookie value provided")
            print(f"{Fore.RED}{EMOJI['ERROR']} {_get_message(translator, 'token.invalid_cookie', 'Invalid cookie value provided')}{Style.RESET_ALL}")
            return ""
            
        # Try to refresh the token with the API first
        print(f"{Fore.CYAN}{EMOJI['TOKEN']} {_get_message(translator, 'token.processing', 'Processing token...')}{Style.RESET_ALL}")
        refreshed_token = refresh_token(cookie_value, translator)
        
        # If refresh succeeded and returned a different token, use it
        original_token_part = _extract_token_part(cookie_value)
        if refreshed_token and refreshed_token != original_token_part and refreshed_token != cookie_value:
            logger.info("Using refreshed token")
            return refreshed_token
        
        # If refresh failed or returned same token, use traditional extraction method
        logger.info("Using extracted token part")
        return original_token_part
            
    except Exception as e:
        logger.error(f"Error extracting token: {e}")
        print(f"{Fore.RED}{EMOJI['ERROR']} {_get_message(translator, 'token.extraction_error', 'Error extracting token: {error}', error=str(e))}{Style.RESET_ALL}")
        # Fall back to original behavior
        return _extract_token_part(cookie_value)

def validate_token(token: str, translator: Any = None) -> bool:
    """Validate if the token looks legitimate.
    
    Args:
        token: The token to validate
        translator: Optional translator object
        
    Returns:
        bool: True if token looks valid, False otherwise
    """
    if not token:
        logger.warning("Empty token provided")
        print(f"{Fore.RED}{EMOJI['ERROR']} {_get_message(translator, 'token.empty_token', 'Empty token provided')}{Style.RESET_ALL}")
        return False
        
    # Basic validation - JWT tokens typically start with "eyJ"
    if token.startswith('eyJ') and len(token) > 100 and '.' in token:
        logger.info("Token appears to be in valid JWT format")
        return True
        
    logger.warning("Token does not appear to be in valid JWT format")
    print(f"{Fore.YELLOW}{EMOJI['WARNING']} {_get_message(translator, 'token.invalid_format', 'Token does not appear to be in valid JWT format')}{Style.RESET_ALL}")
    return False

if __name__ == "__main__":
    # Test functionality if run directly
    try:
        test_token = input(f"{Fore.CYAN}{EMOJI['TOKEN']} Enter a token to test: {Style.RESET_ALL}")
        processed_token = get_token_from_cookie(test_token)
        print(f"\n{Fore.GREEN}{EMOJI['INFO']} Processed token: {processed_token}{Style.RESET_ALL}")
        
        if validate_token(processed_token):
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} Token appears to be valid{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}{EMOJI['WARNING']} Token may not be valid{Style.RESET_ALL}")
    except Exception as e:
        logger.error(f"Error in test: {e}")
        print(f"{Fore.RED}{EMOJI['ERROR']} Test error: {str(e)}{Style.RESET_ALL}") 