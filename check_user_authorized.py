import os
import requests
import time
import hashlib
import base64
import struct
import logging
from colorama import Fore, Style, init
from typing import Optional, Dict, Union, Any, Tuple

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
    "SUCCESS": "✅",
    "ERROR": "❌",
    "INFO": "ℹ️",
    "WARNING": "⚠️",
    "KEY": "🔑",
    "CHECK": "🔍"
}

def generate_hashed64_hex(input_str: str, salt: str = '') -> str:
    """Generate a SHA-256 hash of input + salt and return as hex.
    
    Args:
        input_str: The input string to hash
        salt: Optional salt to add to the input string
        
    Returns:
        str: Hexadecimal representation of the hash
    """
    if not input_str:
        logger.warning("Empty input string provided for hashing")
        return ""
        
    hash_obj = hashlib.sha256()
    hash_obj.update((input_str + salt).encode('utf-8'))
    return hash_obj.hexdigest()

def obfuscate_bytes(byte_array: bytearray) -> bytearray:
    """Obfuscate bytes using the algorithm from utils.js.
    
    Args:
        byte_array: The byte array to obfuscate
        
    Returns:
        bytearray: The obfuscated byte array
    """
    if not byte_array:
        return bytearray()
        
    t = 165
    for r in range(len(byte_array)):
        byte_array[r] = ((byte_array[r] ^ t) + (r % 256)) & 0xFF
        t = byte_array[r]
    return byte_array

def generate_cursor_checksum(token: str, translator: Any = None) -> str:
    """Generate Cursor checksum from token using the algorithm.
    
    Args:
        token: The authentication token
        translator: Optional translator for internationalization
        
    Returns:
        str: The generated checksum
    """
    try:
        # Validate input
        if not token or not isinstance(token, str):
            logger.error("Invalid token provided")
            return ""
            
        # Clean the token
        clean_token = token.strip()
        
        # Generate machineId and macMachineId
        machine_id = generate_hashed64_hex(clean_token, 'machineId')
        mac_machine_id = generate_hashed64_hex(clean_token, 'macMachineId')
        
        # Get timestamp and convert to byte array
        timestamp = int(time.time() * 1000) // 1000000
        byte_array = bytearray(struct.pack('>Q', timestamp)[-6:])  # Take last 6 bytes
        
        # Obfuscate bytes and encode as base64
        obfuscated_bytes = obfuscate_bytes(byte_array)
        encoded_checksum = base64.b64encode(obfuscated_bytes).decode('utf-8')
        
        # Combine final checksum
        return f"{encoded_checksum}{machine_id}/{mac_machine_id}"
    except Exception as e:
        logger.error(f"Error generating checksum: {e}")
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('auth_check.error_generating_checksum', error=str(e)) if translator else f'Error generating checksum: {str(e)}'}{Style.RESET_ALL}")
        return ""

def check_user_authorized(token: str, translator: Any = None) -> bool:
    """
    Check if the user is authorized with the given token.
    
    Args:
        token: The authorization token
        translator: Optional translator for internationalization
    
    Returns:
        bool: True if authorized, False otherwise
    """
    try:
        print(f"{Fore.CYAN}{EMOJI['CHECK']} {translator.get('auth_check.checking_authorization') if translator else 'Checking authorization...'}{Style.RESET_ALL}")
        
        # Validate input
        if not token or not isinstance(token, str):
            logger.error("Invalid token provided")
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('auth_check.invalid_token') if translator else 'Invalid token'}{Style.RESET_ALL}")
            return False
            
        # Clean the token
        if token and '%3A%3A' in token:
            token = token.split('%3A%3A')[1]
        elif token and '::' in token:
            token = token.split('::')[1]
        
        # Remove any whitespace
        token = token.strip()
        
        if not token or len(token) < 10:  # Add a basic validation for token length
            logger.error("Token too short or empty after cleaning")
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('auth_check.invalid_token') if translator else 'Invalid token'}{Style.RESET_ALL}")
            return False
        
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('auth_check.token_length', length=len(token)) if translator else f'Token length: {len(token)} characters'}{Style.RESET_ALL}")
        
        # Try to get usage info using the DashboardService API
        try:
            # Generate checksum
            checksum = generate_cursor_checksum(token, translator)
            if not checksum:
                logger.error("Failed to generate checksum")
                return False
                
            # Create request headers
            headers = {
                'accept-encoding': 'gzip',
                'authorization': f'Bearer {token}',
                'connect-protocol-version': '1',
                'content-type': 'application/proto',
                'user-agent': 'connect-es/1.6.1',
                'x-cursor-checksum': checksum,
                'x-cursor-client-version': '0.48.7',
                'x-cursor-timezone': 'Asia/Shanghai',
                'x-ghost-mode': 'false',
                'Host': 'api2.cursor.sh'
            }
            
            print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('auth_check.checking_usage_information') if translator else 'Checking usage information...'}{Style.RESET_ALL}")
            
            # Make the request with timeout and retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    usage_response = requests.post(
                        'https://api2.cursor.sh/aiserver.v1.DashboardService/GetUsageBasedPremiumRequests',
                        headers=headers,
                        data=b'',  # Empty body
                        timeout=10
                    )
                    break
                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"Request attempt {attempt + 1} failed: {e}. Retrying...")
                        time.sleep(2)
                    else:
                        raise
            
            print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('auth_check.usage_response', response=usage_response.status_code) if translator else f'Usage response status: {usage_response.status_code}'}{Style.RESET_ALL}")
            
            if usage_response.status_code == 200:
                logger.info("User is authorized")
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('auth_check.user_authorized') if translator else 'User is authorized'}{Style.RESET_ALL}")
                return True
            elif usage_response.status_code == 401 or usage_response.status_code == 403:
                logger.warning("User is unauthorized")
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('auth_check.user_unauthorized') if translator else 'User is unauthorized'}{Style.RESET_ALL}")
                return False
            else:
                logger.warning(f"Unexpected status code: {usage_response.status_code}")
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('auth_check.unexpected_status_code', code=usage_response.status_code) if translator else f'Unexpected status code: {usage_response.status_code}'}{Style.RESET_ALL}")
                
                # If the token at least looks like a valid JWT, consider it valid
                if token.startswith('eyJ') and '.' in token and len(token) > 100:
                    logger.info("Token appears to be in JWT format, but API check returned an unexpected status code")
                    print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('auth_check.jwt_token_warning') if translator else 'Token appears to be in JWT format, but API check returned an unexpected status code. The token might be valid but API access is restricted.'}{Style.RESET_ALL}")
                    return True
                
                return False
        except requests.exceptions.Timeout:
            logger.error("Request timed out")
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('auth_check.request_timeout') if translator else 'Request timed out'}{Style.RESET_ALL}")
            
            # If the token at least looks like a valid JWT, consider it valid even if the API check fails
            if token.startswith('eyJ') and '.' in token and len(token) > 100:
                logger.info("Token appears to be in JWT format, but request timed out")
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('auth_check.jwt_token_warning') if translator else 'Token appears to be in JWT format, but API check timed out. The token might be valid but API access is restricted.'}{Style.RESET_ALL}")
                return True
                
            return False
        except requests.exceptions.ConnectionError:
            logger.error("Connection error")
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('auth_check.connection_error') if translator else 'Connection error'}{Style.RESET_ALL}")
            
            # If the token at least looks like a valid JWT, consider it valid even if the API check fails
            if token.startswith('eyJ') and '.' in token and len(token) > 100:
                logger.info("Token appears to be in JWT format, but connection failed")
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('auth_check.jwt_token_warning') if translator else 'Token appears to be in JWT format, but API connection failed. The token might be valid but API access is restricted.'}{Style.RESET_ALL}")
                return True
                
            return False
        except Exception as e:
            logger.error(f"Error checking usage: {e}")
            print(f"{Fore.YELLOW}{EMOJI['WARNING']} Error checking usage: {str(e)}{Style.RESET_ALL}")
            
            # If the token at least looks like a valid JWT, consider it valid even if the API check fails
            if token.startswith('eyJ') and '.' in token and len(token) > 100:
                logger.info("Token appears to be in JWT format, but API check failed")
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('auth_check.jwt_token_warning') if translator else 'Token appears to be in JWT format, but API check failed. The token might be valid but API access is restricted.'}{Style.RESET_ALL}")
                return True
            
            return False
            
    except requests.exceptions.Timeout:
        logger.error("Request timed out")
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('auth_check.request_timeout') if translator else 'Request timed out'}{Style.RESET_ALL}")
        return False
    except requests.exceptions.ConnectionError:
        logger.error("Connection error")
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('auth_check.connection_error') if translator else 'Connection error'}{Style.RESET_ALL}")
        return False
    except Exception as e:
        logger.error(f"Error checking authorization: {e}")
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('auth_check.check_error', error=str(e)) if translator else f'Error checking authorization: {str(e)}'}{Style.RESET_ALL}")
        return False

def get_token_from_database(translator: Any = None) -> str:
    """
    Get token from database using cursor_acc_info.py.
    
    Args:
        translator: Optional translator for internationalization
        
    Returns:
        str: The token if found, empty string otherwise
    """
    try:
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('auth_check.getting_token_from_db') if translator else 'Getting token from database...'}{Style.RESET_ALL}")
        
        # Import functions from cursor_acc_info.py
        from cursor_acc_info import get_token
        
        # Get token using the get_token function
        token = get_token()
        
        if token:
            logger.info("Token found in database")
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('auth_check.token_found_in_db') if translator else 'Token found in database'}{Style.RESET_ALL}")
            return token
        else:
            logger.warning("Token not found in database")
            print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('auth_check.token_not_found_in_db') if translator else 'Token not found in database'}{Style.RESET_ALL}")
            return ""
    except ImportError:
        logger.error("cursor_acc_info.py not found")
        print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('auth_check.cursor_acc_info_not_found') if translator else 'cursor_acc_info.py not found'}{Style.RESET_ALL}")
        return ""
    except Exception as e:
        logger.error(f"Error getting token from database: {e}")
        print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('auth_check.error_getting_token_from_db', error=str(e)) if translator else f'Error getting token from database: {str(e)}'}{Style.RESET_ALL}")
        return ""

def run(translator: Any = None) -> bool:
    """Run function to be called from main.py.
    
    Args:
        translator: Optional translator for internationalization
        
    Returns:
        bool: True if authorization successful, False otherwise
    """
    try:
        # Ask user if they want to get token from database or input manually
        choice = input(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('auth_check.token_source') if translator else 'Get token from database or input manually? (d/m, default: d): '}{Style.RESET_ALL}").strip().lower()
        
        token = None
        
        # If user chooses database or default
        if not choice or choice == 'd':
            token = get_token_from_database(translator)
        
        # If token not found in database or user chooses manual input
        if not token:
            # Try to get token from environment
            token = os.environ.get('CURSOR_TOKEN')
            
            # If not in environment, ask user to input
            if not token:
                token = input(f"{Fore.CYAN}{EMOJI['KEY']} {translator.get('auth_check.enter_token') if translator else 'Enter your Cursor token: '}{Style.RESET_ALL}")
        
        # Check authorization
        is_authorized = check_user_authorized(token, translator)
        
        if is_authorized:
            logger.info("Authorization successful")
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('auth_check.authorization_successful') if translator else 'Authorization successful!'}{Style.RESET_ALL}")
        else:
            logger.warning("Authorization failed")
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('auth_check.authorization_failed') if translator else 'Authorization failed!'}{Style.RESET_ALL}")
        
        return is_authorized
    except Exception as e:
        logger.error(f"Error in run function: {e}")
        print(f"{Fore.RED}{EMOJI['ERROR']} An unexpected error occurred: {str(e)}{Style.RESET_ALL}")
        return False

def main(translator: Any = None) -> bool:
    """Main function to be called when script is run directly.
    
    Args:
        translator: Optional translator for internationalization
        
    Returns:
        bool: True if authorization successful, False otherwise
    """
    try:
        print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{EMOJI['CHECK']} {translator.get('auth_check.title') if translator else 'Check User Authorization'}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        
        result = run(translator)
        
        print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        input(f"{EMOJI['INFO']} {translator.get('auth_check.press_enter') if translator else 'Press Enter to continue...'}")
        
        return result
    except Exception as e:
        logger.error(f"Error in main function: {e}")
        print(f"{Fore.RED}{EMOJI['ERROR']} An unexpected error occurred: {str(e)}{Style.RESET_ALL}")
        return False

if __name__ == "__main__":
    try:
        from main import translator as main_translator
        main(main_translator)
    except ImportError:
        logger.warning("Failed to import translator from main.py, running without translation")
        main(None)
    except Exception as e:
        logger.error(f"Error running check_user_authorized.py: {e}")
        print(f"{Fore.RED}{EMOJI['ERROR']} An unexpected error occurred: {str(e)}{Style.RESET_ALL}")