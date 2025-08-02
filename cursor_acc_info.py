import os
import sys
import json
import requests
import sqlite3
import platform
import logging
import time
import re
from typing import Dict, Optional, Any, List, Tuple
from pathlib import Path
from colorama import Fore, Style, init
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin

# Initialize colorama
init()

# Setup logger
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cursor_api.log')
    ]
)
logger = logging.getLogger(__name__)

# Define emoji constants
EMOJI = {
    "USER": "👤",
    "USAGE": "📊",
    "PREMIUM": "⭐",
    "BASIC": "📝",
    "SUBSCRIPTION": "💳",
    "INFO": "ℹ️",
    "ERROR": "❌",
    "SUCCESS": "✅",
    "WARNING": "⚠️",
    "TIME": "🕒"
}

class Config:
    """Configuration class"""
    NAME_LOWER = "cursor"
    NAME_CAPITALIZE = "Cursor"
    BASE_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36 Cursor/0.10.0",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

class UsageManager:
    """Manages Cursor API usage and subscription information"""
    
    @staticmethod
    def get_proxy() -> Optional[Dict[str, str]]:
        """Get proxy configuration from environment variables"""
        proxy = os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")
        if proxy:
            return {"http": proxy, "https": proxy}
        return None
        
    @staticmethod
    def get_usage(token: str) -> Optional[Dict]:
        """Get usage information from Cursor API"""
        from config import API_BASE_URL, USAGE_ENDPOINT, ALTERNATE_ENDPOINTS, REQUEST_TIMEOUT, USER_AGENT
        
        # Start with the primary endpoint and add alternates
        endpoints_to_try = [USAGE_ENDPOINT] + [e for e in ALTERNATE_ENDPOINTS if 'usage' in e or 'billing' in e]
        
        for endpoint in endpoints_to_try:
            url = f"{API_BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"  # Ensure clean URL
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
                "Accept": "application/json"
            }
            
            try:
                proxies = UsageManager.get_proxy()
                logger.info(f"Trying usage endpoint: {url}")
                
                response = requests.get(
                    url, 
                    headers=headers, 
                    timeout=REQUEST_TIMEOUT, 
                    proxies=proxies,
                    allow_redirects=True
                )
                
                # Handle redirects
                if response.history:
                    url = response.url
                    response = requests.get(
                        url,
                        headers=headers,
                        timeout=REQUEST_TIMEOUT,
                        proxies=proxies,
                        allow_redirects=False
                    )
                
                response.raise_for_status()
                data = response.json()
                
                # Log successful response
                logger.debug(f"API Response from {url}: {data}")
                
                # Handle different response formats
                response_data = data.get('data', data)
                
                # Extract usage information with flexible field names
                premium_usage = response_data.get('premium_usage') or response_data.get('gpt4_usage') or response_data.get('usage', {}).get('premium', 0)
                max_premium_usage = response_data.get('max_premium_usage') or response_data.get('gpt4_limit') or response_data.get('limits', {}).get('premium', 999)
                basic_usage = response_data.get('basic_usage') or response_data.get('gpt35_usage') or response_data.get('usage', {}).get('basic', 0)
                
                result = {
                    'premium_usage': premium_usage,
                    'max_premium_usage': max_premium_usage,
                    'basic_usage': basic_usage,
                    'max_basic_usage': response_data.get('max_basic_usage', "No Limit"),
                    'endpoint_used': url
                }
                
                logger.info(f"Successfully retrieved usage info from {url}")
                return result
                
            except requests.RequestException as e:
                if hasattr(e, 'response') and e.response is not None:
                    if e.response.status_code == 404:
                        logger.debug(f"Endpoint not found: {url}")
                        continue  # Try next endpoint
                    logger.error(f"Error from {url}: {e.response.status_code} - {e.response.text}")
                else:
                    logger.debug(f"Request failed for {url}: {str(e)}")
                continue  # Try next endpoint
            except Exception as e:
                logger.error(f"Unexpected error with {url}: {str(e)}")
                continue  # Try next endpoint
        
        logger.error("All endpoints failed for get_usage")
        return None
        
    @staticmethod
    def get_stripe_profile(token: str) -> Optional[Dict]:
        """Get subscription information from Cursor API"""
        from config import API_BASE_URL, SUBSCRIPTION_ENDPOINT, ALTERNATE_ENDPOINTS, REQUEST_TIMEOUT, USER_AGENT
        
        # Start with the primary endpoint and add alternates
        endpoints_to_try = [SUBSCRIPTION_ENDPOINT] + \
                         [e for e in ALTERNATE_ENDPOINTS if 'subscription' in e or 'billing' in e or 'user' in e or 'auth/me' in e]
        
        for endpoint in endpoints_to_try:
            url = f"{API_BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"  # Ensure clean URL
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
                "Accept": "application/json"
            }
            
            try:
                proxies = UsageManager.get_proxy()
                logger.info(f"Trying subscription endpoint: {url}")
                
                response = requests.get(
                    url, 
                    headers=headers, 
                    timeout=REQUEST_TIMEOUT, 
                    proxies=proxies,
                    allow_redirects=True
                )
                
                # Handle redirects
                if response.history:
                    url = response.url
                    response = requests.get(
                        url,
                        headers=headers,
                        timeout=REQUEST_TIMEOUT,
                        proxies=proxies,
                        allow_redirects=False
                    )
                
                response.raise_for_status()
                data = response.json()
                
                # Log successful response
                logger.debug(f"Subscription API Response from {url}: {data}")
                
                # Handle different response formats
                response_data = data.get('data', data)
                
                # Extract subscription information with flexible field names
                subscription = response_data.get('subscription')
                if not subscription and isinstance(response_data, dict):
                    # Try to construct subscription info from available fields
                    subscription = {
                        'status': 'active' if response_data.get('has_active_subscription') else 'inactive',
                        'plan': response_data.get('plan', {}).get('name', 'Free')
                    }
                
                result = {
                    'subscription': subscription,
                    'endpoint_used': url
                }
                
                logger.info(f"Successfully retrieved subscription info from {url}")
                return result
                
            except requests.RequestException as e:
                if hasattr(e, 'response') and e.response is not None:
                    if e.response.status_code == 404:
                        logger.debug(f"Endpoint not found: {url}")
                        continue  # Try next endpoint
                    logger.error(f"Error from {url}: {e.response.status_code} - {e.response.text}")
                else:
                    logger.debug(f"Request failed for {url}: {str(e)}")
                continue  # Try next endpoint
            except Exception as e:
                logger.error(f"Unexpected error with {url}: {str(e)}")
                continue  # Try next endpoint
        
        logger.error("All endpoints failed for get_stripe_profile")
        return None
        
    @staticmethod
    def test_api_endpoints(token: str) -> Dict[str, Any]:
        """Test various API endpoints to find working ones"""
        import requests
        from urllib.parse import urljoin
        
        base_urls = [
            "https://www.cursor.com/api",
            "https://api.cursor.sh",
            "https://api2.cursor.sh",
            "https://platform.cursor.com/api",
        ]
        
        endpoints = [
            "/user/me",
            "/v1/user/me",
            "/auth/me",
            "/v1/auth/me",
            "/billing/usage",
            "/v1/billing/usage",
            "/billing/subscription",
            "/v1/billing/subscription",
        ]
        
        results = {}
        
        for base_url in base_urls:
            for endpoint in endpoints:
                url = urljoin(base_url, endpoint)
                headers = {
                    "Authorization": f"Bearer {token}",
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36 Cursor/0.10.0",
                    "Accept": "application/json"
                }
                
                try:
                    response = requests.get(
                        url, 
                        headers=headers, 
                        timeout=10,
                        allow_redirects=True
                    )
                    
                    # Store the result
                    results[url] = {
                        'status_code': response.status_code,
                        'content_type': response.headers.get('content-type'),
                        'content_length': len(response.content) if response.content else 0,
                        'is_json': 'application/json' in response.headers.get('content-type', '').lower()
                    }
                    
                    # If we got JSON, include a sample of the response
                    if results[url]['is_json'] and response.content:
                        try:
                            json_data = response.json()
                            results[url]['data'] = json_data
                        except:
                            results[url]['data'] = "Could not parse JSON"
                    
                except Exception as e:
                    results[url] = {
                        'error': str(e)
                    }
                
                # Be nice to the API
                import time
                time.sleep(0.5)
        
        # Save results to a file
        import json
        with open('api_test_results.json', 'w') as f:
            json.dump(results, f, indent=2)
            
        return results

    @staticmethod
    def check_local_storage():
        """Check local storage for API-related information"""
        import json
        import os
        import platform
        from pathlib import Path

        # Get the user's home directory
        home = str(Path.home())
        
        # Determine the Cursor storage location based on the OS
        if platform.system() == 'Darwin':  # macOS
            storage_path = os.path.join(home, 'Library', 'Application Support', 'Cursor')
        elif platform.system() == 'Windows':
            storage_path = os.path.join(os.getenv('APPDATA', ''), 'Cursor')
        else:  # Linux
            storage_path = os.path.join(home, '.config', 'Cursor')
        
        # Check if the storage directory exists
        if not os.path.exists(storage_path):
            logger.warning(f"Cursor storage path not found: {storage_path}")
            return None
        
        # Look for storage.json or similar files
        storage_files = [
            'storage.json',
            'Local Storage/leveldb',
            'Local Storage/leveldb-v1',
            'Local Storage/leveldb-v2',
            'Local Storage/leveldb-v3',
            'Local Storage/leveldb-v4',
            'Local Storage/leveldb-v5',
            'Local Storage/leveldb-v6',
            'Local Storage/leveldb-v7',
            'Local Storage/leveldb-v8',
            'Local Storage/leveldb-v9',
            'Local Storage/leveldb-v10'
        ]
        
        found_data = {}
        
        for file_name in storage_files:
            file_path = os.path.join(storage_path, file_name)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Try to parse as JSON if it's a JSON file
                        if file_name.endswith('.json'):
                            try:
                                data = json.loads(content)
                                if data:  # Only add non-empty data
                                    found_data[file_name] = data
                            except json.JSONDecodeError:
                                # If not valid JSON, add as text
                                found_data[file_name] = content[:1000] + '...'  # Limit size
                        else:
                            # For non-JSON files, just add a portion of the content
                            found_data[file_name] = content[:1000] + '...'  # Limit size
                except Exception as e:
                    logger.warning(f"Error reading {file_path}: {str(e)}")
        
        return found_data

    @staticmethod
    def get_stripe_profile(token: str) -> Optional[Dict]:
        """get stripe profile information"""
        from config import API_BASE_URL, SUBSCRIPTION_ENDPOINT, ALTERNATE_ENDPOINTS, REQUEST_TIMEOUT, USER_AGENT
        
        # Start with the primary endpoint
        endpoints_to_try = [SUBSCRIPTION_ENDPOINT] + \
                         [e for e in ALTERNATE_ENDPOINTS if 'subscription' in e or 'billing' in e or 'user' in e or 'auth/me' in e]
        
        for endpoint in endpoints_to_try:
            url = f"{API_BASE_URL}{endpoint}"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
                "Accept": "application/json"
            }
            
            try:
                response = requests.get(
                    url, 
                    headers=headers, 
                    timeout=REQUEST_TIMEOUT, 
                    proxies=None,
                    allow_redirects=True
                )
                
                # If we get redirected, update the URL and try again
                if response.history:
                    url = response.url
                    response = requests.get(
                        url,
                        headers=headers,
                        timeout=REQUEST_TIMEOUT,
                        proxies=None,
                        allow_redirects=False
                    )
                
                response.raise_for_status()
                data = response.json()
                
                # Debug: Print the API response
                logger.debug(f"API Response from {url}: {data}")
                
                # Try to extract subscription information with different response formats
                response_data = data.get('data', data)  # Handle both wrapped and unwrapped responses
                
                # Try different possible field names for subscription data
                subscription = response_data.get('subscription') or response_data.get('subscription', {}).get('data')
                
                result = {
                    'subscription': subscription,
                    'endpoint_used': url
                }
                
                logger.info(f"Successfully retrieved subscription info from {url}")
                return result
                
            except requests.RequestException as e:
                if hasattr(e, 'response') and e.response is not None:
                    if e.response.status_code == 404:
                        logger.debug(f"Endpoint not found: {url}")
                        continue  # Try next endpoint
                    logger.error(f"Error from {url}: {e.response.status_code} - {e.response.text}")
                else:
                    logger.debug(f"Request failed for {url}: {str(e)}")
                continue  # Try next endpoint
            except Exception as e:
                logger.error(f"Unexpected error with {url}: {str(e)}")
                continue  # Try next endpoint
        
        logger.error("All endpoints failed for get_stripe_profile")
        return None
    def get_token_from_config():
        """get path from config"""
        import configparser
        import os
        import platform
        from pathlib import Path

        try:
            # Get the user's home directory
            home = str(Path.home())
            
            # Determine the config file location based on the OS
            if platform.system() == 'Darwin':  # macOS
                config_path = os.path.join(home, 'Library', 'Preferences', 'cursor.ini')
            elif platform.system() == 'Windows':
                config_path = os.path.join(os.getenv('APPDATA', ''), 'cursor', 'cursor.ini')
            else:  # Linux
                config_path = os.path.join(home, '.config', 'cursor', 'cursor.ini')
            
            # Check if the config file exists
            if not os.path.exists(config_path):
                logger.warning(f"Config file not found: {config_path}")
                return None
            
            config = configparser.ConfigParser()
            config.read(config_path)
            
            system = platform.system()
            if system == "Windows" and config.has_section('WindowsPaths'):
                return {
                    'storage_path': config.get('WindowsPaths', 'storage_path'),
                    'sqlite_path': config.get('WindowsPaths', 'sqlite_path'),
                    'session_path': os.path.join(os.getenv("APPDATA"), "Cursor", "Session Storage")
                }
            elif system == "Darwin" and config.has_section('MacPaths'):  # macOS
                return {
                    'storage_path': config.get('MacPaths', 'storage_path'),
                    'sqlite_path': config.get('MacPaths', 'sqlite_path'),
                    'session_path': os.path.expanduser("~/Library/Application Support/Cursor/Session Storage")
                }
            elif system == "Linux" and config.has_section('LinuxPaths'):
                return {
                    'storage_path': config.get('LinuxPaths', 'storage_path'),
                    'sqlite_path': config.get('LinuxPaths', 'sqlite_path'),
                    'session_path': os.path.expanduser("~/.config/Cursor/Session Storage")
                }
        except Exception as e:
            logger.error(f"Get config path failed: {str(e)}")
        
        return None

def get_token_from_storage(storage_path):
    """get token from storage.json"""
    if not os.path.exists(storage_path):
        return None
        
    try:
        with open(storage_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # try to get accessToken
            if 'cursorAuth/accessToken' in data:
                return data['cursorAuth/accessToken']
            
            # try other possible keys
            for key in data:
                if 'token' in key.lower() and isinstance(data[key], str) and len(data[key]) > 20:
                    return data[key]
    except Exception as e:
        logger.error(f"get token from storage.json failed: {str(e)}")
    
    return None

def get_token_from_sqlite(sqlite_path):
    """get token from sqlite"""
    if not os.path.exists(sqlite_path):
        return None
        
    try:
        conn = sqlite3.connect(sqlite_path)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM ItemTable WHERE key LIKE '%token%'")
        rows = cursor.fetchall()
        conn.close()
        
        for row in rows:
            try:
                value = row[0]
                if isinstance(value, str) and len(value) > 20:
                    return value
                # try to parse JSON
                data = json.loads(value)
                if isinstance(data, dict) and 'token' in data:
                    return data['token']
            except:
                continue
    except Exception as e:
        logger.error(f"get token from sqlite failed: {str(e)}")
    
    return None

def get_token_from_session(session_path):
    """get token from session"""
    if not os.path.exists(session_path):
        return None
        
    try:
        # try to find all possible session files
        for file in os.listdir(session_path):
            if file.endswith('.log'):
                file_path = os.path.join(session_path, file)
                try:
                    with open(file_path, 'rb') as f:
                        content = f.read().decode('utf-8', errors='ignore')
                        # find token pattern
                        token_match = re.search(r'"token":"([^"]+)"', content)
                        if token_match:
                            return token_match.group(1)
                except:
                    continue
    except Exception as e:
        logger.error(f"get token from session failed: {str(e)}")
    
    return None

def get_token():
    """get Cursor token"""
    # get path from config
    paths = get_token_from_config()
    if not paths:
        return None
    
    # try to get token from different locations
    token = get_token_from_storage(paths['storage_path'])
    if token:
        return token
        
    token = get_token_from_sqlite(paths['sqlite_path'])
    if token:
        return token
        
    token = get_token_from_session(paths['session_path'])
    if token:
        return token
    
    return None

def format_subscription_type(subscription_data: Dict) -> str:
    """format subscription type"""
    if not subscription_data:
        return "Free"
    
    # handle new API response format
    if "membershipType" in subscription_data:
        membership_type = subscription_data.get("membershipType", "").lower()
        subscription_status = subscription_data.get("subscriptionStatus", "").lower()
        
        if subscription_status == "active":
            if membership_type == "pro":
                return "Pro"
            elif membership_type == "free_trial":
                return "Free Trial"
            elif membership_type == "pro_trial":
                return "Pro Trial"
            elif membership_type == "team":
                return "Team"
            elif membership_type == "enterprise":
                return "Enterprise"
            elif membership_type:
                return membership_type.capitalize()
            else:
                return "Active Subscription"
        elif subscription_status:
            return f"{membership_type.capitalize()} ({subscription_status})"
    
    # compatible with old API response format
    subscription = subscription_data.get("subscription")
    if subscription:
        plan = subscription.get("plan", {}).get("nickname", "Unknown")
        status = subscription.get("status", "unknown")
        
        if status == "active":
            if "pro" in plan.lower():
                return "Pro"
            elif "pro_trial" in plan.lower():
                return "Pro Trial"
            elif "free_trial" in plan.lower():
                return "Free Trial"
            elif "team" in plan.lower():
                return "Team"
            elif "enterprise" in plan.lower():
                return "Enterprise"
            else:
                return plan
        else:
            return f"{plan} ({status})"
    
    return "Free"

def get_email_from_storage(storage_path):
    """get email from storage.json"""
    if not os.path.exists(storage_path):
        return None
        
    try:
        with open(storage_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # try to get email
            if 'cursorAuth/cachedEmail' in data:
                return data['cursorAuth/cachedEmail']
            
            # try other possible keys
            for key in data:
                if 'email' in key.lower() and isinstance(data[key], str) and '@' in data[key]:
                    return data[key]
    except Exception as e:
        logger.error(f"get email from storage.json failed: {str(e)}")
    
    return None

def get_email_from_sqlite(sqlite_path):
    """get email from sqlite"""
    if not os.path.exists(sqlite_path):
        return None
        
    try:
        conn = sqlite3.connect(sqlite_path)
        cursor = conn.cursor()
        # try to query records containing email
        cursor.execute("SELECT value FROM ItemTable WHERE key LIKE '%email%' OR key LIKE '%cursorAuth%'")
        rows = cursor.fetchall()
        conn.close()
        
        for row in rows:
            try:
                value = row[0]
                # if it's a string and contains @, it might be an email
                if isinstance(value, str) and '@' in value:
                    return value
                
                # try to parse JSON
                try:
                    data = json.loads(value)
                    if isinstance(data, dict):
                        # check if there's an email field
                        if 'email' in data:
                            return data['email']
                        # check if there's a cachedEmail field
                        if 'cachedEmail' in data:
                            return data['cachedEmail']
                except:
                    pass
            except:
                continue
    except Exception as e:
        logger.error(f"get email from sqlite failed: {str(e)}")
    
    return None

def display_account_info(translator=None):
    """display account info"""
    print(f"\n{Fore.CYAN}{'─' * 70}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{EMOJI['USER']} {translator.get('account_info.title') if translator else 'Cursor Account Information'}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'─' * 70}{Style.RESET_ALL}")
    
    # First, check local storage for any API-related information
    print(f"{Fore.YELLOW}Checking local storage for API information...{Style.RESET_ALL}")
    storage_data = UsageManager.check_local_storage()
    
    if storage_data:
        print(f"{Fore.GREEN}Found local storage data. Analyzing...{Style.RESET_ALL}")
        # Save the storage data to a file for debugging
        import json
        with open('cursor_storage_debug.json', 'w') as f:
            json.dump(storage_data, f, indent=2)
        print(f"{Fore.GREEN}Debug information saved to cursor_storage_debug.json{Style.RESET_ALL}")
    
    # get token
    token = get_token()
    if not token:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('account_info.token_not_found') if translator else 'Token not found. Please login to Cursor first.'}{Style.RESET_ALL}")
        return
    
    # Print token info for debugging (first 10 and last 10 characters)
    token_display = f"{token[:10]}...{token[-10:]}" if token and len(token) > 20 else token
    print(f"{Fore.GREEN}Token found: {token_display}{Style.RESET_ALL}")
    
    # Test API endpoints
    print(f"{Fore.YELLOW}Testing API endpoints...{Style.RESET_ALL}")
    api_results = UsageManager.test_api_endpoints(token)
    print(f"{Fore.GREEN}API endpoint testing complete. Results saved to api_test_results.json{Style.RESET_ALL}")
    
    # get path info
    paths = get_token_from_config()
    if not paths:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('account_info.config_not_found') if translator else 'Configuration not found.'}{Style.RESET_ALL}")
        return
    
    # get email info - try multiple sources
    email = get_email_from_storage(paths['storage_path'])
    
    # if not found in storage, try from sqlite
    if not email:
        email = get_email_from_sqlite(paths['sqlite_path'])
    
    # get subscription info
    print(f"{Fore.YELLOW}Fetching subscription information...{Style.RESET_ALL}")
    try:
        subscription_info = UsageManager.get_stripe_profile(token)
        if subscription_info:
            print(f"{Fore.GREEN}Subscription information retrieved successfully{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}No subscription information found{Style.RESET_ALL}")
    except Exception as e:
        logger.error(f"Get subscription info failed: {str(e)}")
        print(f"{Fore.RED}Failed to get subscription info: {str(e)}{Style.RESET_ALL}")
        subscription_info = None
    
    # if not found in storage and sqlite, try from subscription info
    if not email and subscription_info:
        # try to get email from subscription info
        if 'customer' in subscription_info and 'email' in subscription_info['customer']:
            email = subscription_info['customer']['email']
    
    # get usage info - silently handle errors
    print(f"{Fore.YELLOW}Fetching usage information...{Style.RESET_ALL}")
    try:
        usage_info = UsageManager.get_usage(token)
        if usage_info:
            print(f"{Fore.GREEN}Usage information retrieved successfully{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}No usage information found{Style.RESET_ALL}")
    except Exception as e:
        logger.error(f"Get usage info failed: {str(e)}")
        print(f"{Fore.RED}Failed to get usage info: {str(e)}{Style.RESET_ALL}")
        usage_info = None
    
    # Prepare left and right info
    left_info = []
    right_info = []
    
    # Left side shows account info
    if email:
        left_info.append(f"{Fore.GREEN}{EMOJI['USER']} {translator.get('account_info.email') if translator else 'Email'}: {Fore.WHITE}{email}{Style.RESET_ALL}")
    else:
        left_info.append(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('account_info.email_not_found') if translator else 'Email not found'}{Style.RESET_ALL}")
    
    # Add token info for debugging
    left_info.append(f"{Fore.CYAN}Token: {token_display}{Style.RESET_ALL}")
    
    # Add storage info if available
    if storage_data:
        left_info.append(f"{Fore.GREEN}Found {len(storage_data)} storage items{Style.RESET_ALL}")
    # left_info.append("")
    
    # Show subscription type
    if subscription_info:
        subscription_type = format_subscription_type(subscription_info)
        left_info.append(f"{Fore.GREEN}{EMOJI['SUBSCRIPTION']} {translator.get('account_info.subscription') if translator else 'Subscription'}: {Fore.WHITE}{subscription_type}{Style.RESET_ALL}")
        
        # Show remaining trial days
        days_remaining = subscription_info.get("daysRemainingOnTrial")
        if days_remaining is not None and days_remaining > 0:
            left_info.append(f"{Fore.GREEN}{EMOJI['TIME']} {translator.get('account_info.trial_remaining') if translator else 'Remaining Pro Trial'}: {Fore.WHITE}{days_remaining} {translator.get('account_info.days') if translator else 'days'}{Style.RESET_ALL}")
    else:
        left_info.append(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('account_info.subscription_not_found') if translator else 'Subscription information not found'}{Style.RESET_ALL}")
    
    # Right side shows usage info - only if available
    if usage_info:
        right_info.append(f"{Fore.GREEN}{EMOJI['USAGE']} {translator.get('account_info.usage') if translator else 'Usage Statistics'}:{Style.RESET_ALL}")
        
        # Premium usage
        premium_usage = usage_info.get('premium_usage', 0)
        max_premium_usage = usage_info.get('max_premium_usage', "No Limit")
        
        #  make sure the value is not None
        if premium_usage is None:
            premium_usage = 0
        
        # handle "No Limit" case
        if isinstance(max_premium_usage, str) and max_premium_usage == "No Limit":
            premium_color = Fore.GREEN  # when there is no limit, use green
            premium_display = f"{premium_usage}/{max_premium_usage}"
        else:
            # calculate percentage when the value is a number
            if max_premium_usage is None or max_premium_usage == 0:
                max_premium_usage = 999
                premium_percentage = 0
            else:
                premium_percentage = (premium_usage / max_premium_usage) * 100
            
            # select color based on usage percentage
            premium_color = Fore.GREEN
            if premium_percentage > 70:
                premium_color = Fore.YELLOW
            if premium_percentage > 90:
                premium_color = Fore.RED
            
            premium_display = f"{premium_usage}/{max_premium_usage} ({premium_percentage:.1f}%)"
        
        right_info.append(f"{Fore.YELLOW}{EMOJI['PREMIUM']} {translator.get('account_info.premium_usage') if translator else 'Fast Response'}: {premium_color}{premium_display}{Style.RESET_ALL}")
        
        # Slow Response
        basic_usage = usage_info.get('basic_usage', 0)
        max_basic_usage = usage_info.get('max_basic_usage', "No Limit")
        
        # make sure the value is not None
        if basic_usage is None:
            basic_usage = 0
        
        # handle "No Limit" case
        if isinstance(max_basic_usage, str) and max_basic_usage == "No Limit":
            basic_color = Fore.GREEN  # when there is no limit, use green
            basic_display = f"{basic_usage}/{max_basic_usage}"
        else:
            # calculate percentage when the value is a number
            if max_basic_usage is None or max_basic_usage == 0:
                max_basic_usage = 999
                basic_percentage = 0
            else:
                basic_percentage = (basic_usage / max_basic_usage) * 100
            
            # select color based on usage percentage
            basic_color = Fore.GREEN
            if basic_percentage > 70:
                basic_color = Fore.YELLOW
            if basic_percentage > 90:
                basic_color = Fore.RED
            
            basic_display = f"{basic_usage}/{max_basic_usage} ({basic_percentage:.1f}%)"
        
        right_info.append(f"{Fore.BLUE}{EMOJI['BASIC']} {translator.get('account_info.basic_usage') if translator else 'Slow Response'}: {basic_color}{basic_display}{Style.RESET_ALL}")
    else:
        # if get usage info failed, only log in log, not show in interface
        # you can choose to not show any usage info, or show a simple prompt
        # right_info.append(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('account_info.usage_unavailable') if translator else 'Usage information unavailable'}{Style.RESET_ALL}")
        pass  # not show any usage info
    
    # Calculate the maximum display width of left info
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    
    def get_display_width(s):
        """Calculate the display width of a string, considering Chinese characters and emojis"""
        # Remove ANSI color codes
        clean_s = ansi_escape.sub('', s)
        width = 0
        for c in clean_s:
            # Chinese characters and some emojis occupy two character widths
            if ord(c) > 127:
                width += 2
            else:
                width += 1
        return width
    
    max_left_width = 0
    for item in left_info:
        width = get_display_width(item)
        max_left_width = max(max_left_width, width)
    
    # Set the starting position of right info
    fixed_spacing = 4  # Fixed spacing
    right_start = max_left_width + fixed_spacing
    
    # Calculate the number of spaces needed for right info
    spaces_list = []
    for i in range(len(left_info)):
        if i < len(left_info):
            left_item = left_info[i]
            left_width = get_display_width(left_item)
            spaces = right_start - left_width
            spaces_list.append(spaces)
    
    # Print info
    max_rows = max(len(left_info), len(right_info))
    
    for i in range(max_rows):
        # Print left info
        if i < len(left_info):
            left_item = left_info[i]
            print(left_item, end='')
            
            # Use pre-calculated spaces
            spaces = spaces_list[i]
        else:
            # If left side has no items, print only spaces
            spaces = right_start
            print('', end='')
        
        # Print right info
        if i < len(right_info):
            print(' ' * spaces + right_info[i])
        else:
            print()  # Change line
    
    print(f"{Fore.CYAN}{'─' * 70}{Style.RESET_ALL}")

def main(translator=None):
    """main function"""
    try:
        display_account_info(translator)
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('account_info.error') if translator else 'Error'}: {str(e)}{Style.RESET_ALL}")

if __name__ == "__main__":
    main() 