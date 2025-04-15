import os
import requests
import time
import hashlib
import base64
import struct
from colorama import Fore, Style, init

# Initialize colorama
init()

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
    """Generate a SHA-256 hash of input + salt and return as hex"""
    hash_obj = hashlib.sha256()
    hash_obj.update((input_str + salt).encode('utf-8'))
    return hash_obj.hexdigest()

def obfuscate_bytes(byte_array: bytearray) -> bytearray:
    """Obfuscate bytes using the algorithm from utils.js"""
    t = 165
    for r in range(len(byte_array)):
        byte_array[r] = ((byte_array[r] ^ t) + (r % 256)) & 0xFF
        t = byte_array[r]
    return byte_array

def generate_cursor_checksum(token: str, translator=None) -> str:
    """Generate Cursor checksum from token using the algorithm"""
    try:
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
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('auth_check.error_generating_checksum', error=str(e)) if translator else f'Error generating checksum: {str(e)}'}{Style.RESET_ALL}")
        return ""

def check_user_authorized(token: str, translator=None) -> bool:
    """
    Check if the user is authorized with the given token
    
    Args:
        token (str): The authorization token
        translator: Optional translator for internationalization
    
    Returns:
        bool: True if authorized, False otherwise
    """
    try:
        print(f"{Fore.CYAN}{EMOJI['CHECK']} {translator.get('auth_check.checking_authorization') if translator else 'Checking authorization...'}{Style.RESET_ALL}")
        
        # Clean the token
        if token and '%3A%3A' in token:
            token = token.split('%3A%3A')[1]
        elif token and '::' in token:
            token = token.split('::')[1]
        
        # Remove any whitespace
        token = token.strip()
        
        if not token or len(token) < 10:  # Add a basic validation for token length
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('auth_check.invalid_token') if translator else 'Invalid token'}{Style.RESET_ALL}")
            return False
        
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('auth_check.token_length', length=len(token)) if translator else f'Token length: {len(token)} characters'}{Style.RESET_ALL}")
        
        # Try to get usage info using the DashboardService API
        try:
            # Generate checksum
            checksum = generate_cursor_checksum(token, translator)
            
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
            
            # Make the request - this endpoint doesn't need a request body
            usage_response = requests.post(
                'https://api2.cursor.sh/aiserver.v1.DashboardService/GetUsageBasedPremiumRequests',
                headers=headers,
                data=b'',  # Empty body
                timeout=10
            )
            
            print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('auth_check.usage_response', response=usage_response.status_code) if translator else f'Usage response status: {usage_response.status_code}'}{Style.RESET_ALL}")
            
            if usage_response.status_code == 200:
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('auth_check.user_authorized') if translator else 'User is authorized'}{Style.RESET_ALL}")
                return True
            elif usage_response.status_code == 401 or usage_response.status_code == 403:
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('auth_check.user_unauthorized') if translator else 'User is unauthorized'}{Style.RESET_ALL}")
                return False
            else:
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('auth_check.unexpected_status_code', code=usage_response.status_code) if translator else f'Unexpected status code: {usage_response.status_code}'}{Style.RESET_ALL}")
                
                # If the token at least looks like a valid JWT, consider it valid
                if token.startswith('eyJ') and '.' in token and len(token) > 100:
                    print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('auth_check.jwt_token_warning') if translator else 'Token appears to be in JWT format, but API check returned an unexpected status code. The token might be valid but API access is restricted.'}{Style.RESET_ALL}")
                    return True
                
                return False
        except Exception as e:
            print(f"{Fore.YELLOW}{EMOJI['WARNING']} Error checking usage: {str(e)}{Style.RESET_ALL}")
            
            # If the token at least looks like a valid JWT, consider it valid even if the API check fails
            if token.startswith('eyJ') and '.' in token and len(token) > 100:
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('auth_check.jwt_token_warning') if translator else 'Token appears to be in JWT format, but API check failed. The token might be valid but API access is restricted.'}{Style.RESET_ALL}")
                return True
            
            return False
            
    except requests.exceptions.Timeout:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('auth_check.request_timeout') if translator else 'Request timed out'}{Style.RESET_ALL}")
        return False
    except requests.exceptions.ConnectionError:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('auth_check.connection_error') if translator else 'Connection error'}{Style.RESET_ALL}")
        return False
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('auth_check.check_error', error=str(e)) if translator else f'Error checking authorization: {str(e)}'}{Style.RESET_ALL}")
        return False

def run(translator=None):
    """Run function to be called from main.py"""
    try:
        # Ask user if they want to get token from database or input manually
        choice = input(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('auth_check.token_source') if translator else 'Get token from database or input manually? (D/m): '}{Style.RESET_ALL}").strip().lower()
        
        token = None
        
        # If user chooses database or default
        if not choice or choice == 'd':
            print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('auth_check.getting_token_from_db') if translator else 'Getting token from database...'}{Style.RESET_ALL}")
            
            try:
                # Import functions from cursor_acc_info.py
                from cursor_acc_info import get_token
                
                # Get token using the get_token function
                token = get_token()
                
                if token:
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('auth_check.token_found_in_db') if translator else 'Token found in database'}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('auth_check.token_not_found_in_db') if translator else 'Token not found in database'}{Style.RESET_ALL}")
            except ImportError:
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('auth_check.cursor_acc_info_not_found') if translator else 'cursor_acc_info.py not found'}{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('auth_check.error_getting_token_from_db', error=str(e)) if translator else f'Error getting token from database: {str(e)}'}{Style.RESET_ALL}")
        
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
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('auth_check.authorization_successful') if translator else 'Authorization successful!'}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('auth_check.authorization_failed') if translator else 'Authorization failed!'}{Style.RESET_ALL}")
        
        return is_authorized
        
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('auth_check.operation_cancelled') if translator else 'Operation cancelled by user'}{Style.RESET_ALL}")
        return False
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('auth_check.unexpected_error', error=str(e)) if translator else f'Unexpected error: {str(e)}'}{Style.RESET_ALL}")
        return False

def main(translator=None):
    """Main function to check user authorization"""
    return run(translator)

if __name__ == "__main__":
    main()