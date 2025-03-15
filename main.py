# main.py
# This script allows the user to choose which script to run.
import os
import sys
import json
from logo import print_logo, version
from colorama import Fore, Style, init
import locale
import platform
import requests
import subprocess
from config import get_config  
import webbrowser
import tempfile
import time
from cursor_auth import CursorAuth
from oauth_auth import OAuthHandler
import keyring
from cursor_register_manual import CursorRegistration
from cursor_register_github import main as register_github
from cursor_register_google import main as register_google
from github_trial_reset import reset_trial

# Only import windll on Windows systems
if platform.system() == 'Windows':
    import ctypes
    # 只在 Windows 上导入 windll
    from ctypes import windll

# Initialize colorama
init()

# Define emoji and color constants
EMOJI = {
    "FILE": "📄",
    "BACKUP": "💾",
    "SUCCESS": "✅",
    "ERROR": "❌",
    "INFO": "ℹ️",
    "RESET": "🔄",
    "MENU": "📋",
    "ARROW": "➜",
    "LANG": "🌐",
    "UPDATE": "🔄",
    "ADMIN": "🔐"
}

# Function to check if running as frozen executable
def is_frozen():
    """Check if the script is running as a frozen executable."""
    return getattr(sys, 'frozen', False)

# Function to check admin privileges (Windows only)
def is_admin():
    """Check if the script is running with admin privileges (Windows only)."""
    if platform.system() == 'Windows':
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    # Always return True for non-Windows to avoid changing behavior
    return True

# Function to restart with admin privileges
def run_as_admin():
    """Restart the current script with admin privileges (Windows only)."""
    if platform.system() != 'Windows':
        return False
        
    try:
        args = [sys.executable] + sys.argv
        
        # Request elevation via ShellExecute
        print(f"{Fore.YELLOW}{EMOJI['ADMIN']} Requesting administrator privileges...{Style.RESET_ALL}")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", args[0], " ".join('"' + arg + '"' for arg in args[1:]), None, 1)
        return True
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} Failed to restart with admin privileges: {e}{Style.RESET_ALL}")
        return False

class Translator:
    def __init__(self):
        self.translations = {}
        self.current_language = self.detect_system_language()  # Use correct method name
        self.fallback_language = 'en'  # Fallback language if translation is missing
        self.load_translations()
    
    def detect_system_language(self):
        """Detect system language and return corresponding language code"""
        try:
            system = platform.system()
            
            if system == 'Windows':
                return self._detect_windows_language()
            else:
                return self._detect_unix_language()
                
        except Exception as e:
            print(f"{Fore.YELLOW}{EMOJI['INFO']} Failed to detect system language: {e}{Style.RESET_ALL}")
            return 'en'
    
    def _detect_windows_language(self):
        """Detect language on Windows systems"""
        try:
            # Ensure we are on Windows
            if platform.system() != 'Windows':
                return 'en'
                
            # Get keyboard layout
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            threadid = user32.GetWindowThreadProcessId(hwnd, 0)
            layout_id = user32.GetKeyboardLayout(threadid) & 0xFFFF
            
            # Map language ID to our language codes
            language_map = {
                0x0409: 'en',      # English
                0x0404: 'zh_tw',   # Traditional Chinese
                0x0804: 'zh_cn',   # Simplified Chinese
                0x0422: 'vi',      # Vietnamese
            }
            
            return language_map.get(layout_id, 'en')
        except:
            return self._detect_unix_language()
    
    def _detect_unix_language(self):
        """Detect language on Unix-like systems (Linux, macOS)"""
        try:
            # Get the system locale
            system_locale = locale.getdefaultlocale()[0]
            if not system_locale:
                return 'en'
            
            system_locale = system_locale.lower()
            
            # Map locale to our language codes
            if system_locale.startswith('zh_tw') or system_locale.startswith('zh_hk'):
                return 'zh_tw'
            elif system_locale.startswith('zh_cn'):
                return 'zh_cn'
            elif system_locale.startswith('en'):
                return 'en'
            elif system_locale.startswith('vi'):
                return 'vi'
            

            # Try to get language from LANG environment variable as fallback
            env_lang = os.getenv('LANG', '').lower()
            if 'tw' in env_lang or 'hk' in env_lang:
                return 'zh_tw'
            elif 'cn' in env_lang:
                return 'zh_cn'
            elif 'vi' in env_lang:
                return 'vi'
            

            return 'en'
        except:
            return 'en'
    
    def load_translations(self):
        """Load all available translations"""
        try:
            locales_dir = os.path.join(os.path.dirname(__file__), 'locales')
            if hasattr(sys, '_MEIPASS'):
                locales_dir = os.path.join(sys._MEIPASS, 'locales')
            
            if not os.path.exists(locales_dir):
                print(f"{Fore.RED}{EMOJI['ERROR']} Locales directory not found{Style.RESET_ALL}")
                return

            for file in os.listdir(locales_dir):
                if file.endswith('.json'):
                    lang_code = file[:-5]  # Remove .json
                    try:
                        with open(os.path.join(locales_dir, file), 'r', encoding='utf-8') as f:
                            self.translations[lang_code] = json.load(f)
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        print(f"{Fore.RED}{EMOJI['ERROR']} Error loading {file}: {e}{Style.RESET_ALL}")
                        continue
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} Failed to load translations: {e}{Style.RESET_ALL}")
    
    def get(self, key, **kwargs):
        """Get translated text with fallback support"""
        try:
            # Try current language
            result = self._get_translation(self.current_language, key)
            if result == key and self.current_language != self.fallback_language:
                # Try fallback language if translation not found
                result = self._get_translation(self.fallback_language, key)
            return result.format(**kwargs) if kwargs else result
        except Exception:
            return key
    
    def _get_translation(self, lang_code, key):
        """Get translation for a specific language"""
        try:
            keys = key.split('.')
            value = self.translations.get(lang_code, {})
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k, key)
                else:
                    return key
            return value
        except Exception:
            return key
    
    def set_language(self, lang_code):
        """Set current language with validation"""
        if lang_code in self.translations:
            self.current_language = lang_code
            return True
        return False

    def get_available_languages(self):
        """Get list of available languages"""
        return list(self.translations.keys())

# Create translator instance
translator = Translator()

def print_menu():
    """Print menu options"""
    print(f"\n{Fore.CYAN}{EMOJI['MENU']} {translator.get('menu.title')}:{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{'─' * 40}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}0{Style.RESET_ALL}. {EMOJI['ERROR']} {translator.get('menu.exit')}")
    print(f"{Fore.GREEN}1{Style.RESET_ALL}. {EMOJI['RESET']} {translator.get('menu.reset')}")
    print(f"{Fore.GREEN}2{Style.RESET_ALL}. 🔄 Reset Trial [GitHub]")
    print(f"{Fore.GREEN}3{Style.RESET_ALL}. {EMOJI['SUCCESS']} {translator.get('menu.register')}")
    print(f"{Fore.GREEN}4{Style.RESET_ALL}. 🌟 {translator.get('menu.register_google')}")
    print(f"{Fore.YELLOW}   ┗━━ 🔥 LIFETIME ACCESS ENABLED 🔥{Style.RESET_ALL}")
    print(f"{Fore.GREEN}5{Style.RESET_ALL}. ⭐ {translator.get('menu.register_github')}")
    print(f"{Fore.YELLOW}   ┗━━ 🚀 LIFETIME ACCESS ENABLED 🚀{Style.RESET_ALL}")
    print(f"{Fore.GREEN}6{Style.RESET_ALL}. {EMOJI['SUCCESS']} {translator.get('menu.register_manual')}")
    print(f"{Fore.GREEN}7{Style.RESET_ALL}. {EMOJI['ERROR']} {translator.get('menu.quit')}")
    print(f"{Fore.GREEN}8{Style.RESET_ALL}. {EMOJI['LANG']} {translator.get('menu.select_language')}")
    print(f"{Fore.GREEN}9{Style.RESET_ALL}. {EMOJI['UPDATE']} {translator.get('menu.disable_auto_update')}")
    print(f"{Fore.YELLOW}{'─' * 40}{Style.RESET_ALL}")

def select_language():
    """Language selection menu"""
    print(f"\n{Fore.CYAN}{EMOJI['LANG']} {translator.get('menu.select_language')}:{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{'─' * 40}{Style.RESET_ALL}")
    
    languages = translator.get_available_languages()
    for i, lang in enumerate(languages):
        lang_name = translator.get(f"languages.{lang}")
        print(f"{Fore.GREEN}{i}{Style.RESET_ALL}. {lang_name}")
    
    try:
        choice = input(f"\n{EMOJI['ARROW']} {Fore.CYAN}{translator.get('menu.input_choice', choices=f'0-{len(languages)-1}')}: {Style.RESET_ALL}")
        if choice.isdigit() and 0 <= int(choice) < len(languages):
            translator.set_language(languages[int(choice)])
            return True
        else:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('menu.invalid_choice')}{Style.RESET_ALL}")
            return False
    except (ValueError, IndexError):
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('menu.invalid_choice')}{Style.RESET_ALL}")
        return False

def check_latest_version():
    """Check if current version matches the latest release version"""
    try:
        print(f"\n{Fore.CYAN}{EMOJI['UPDATE']} {translator.get('updater.checking')}{Style.RESET_ALL}")
        
        # Get latest version from GitHub API with timeout and proper headers
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'CursorFreeVIP-Updater'
        }
        response = requests.get(
            "https://api.github.com/repos/yeongpin/cursor-free-vip/releases/latest",
            headers=headers,
            timeout=10
        )
        
        # Check if response is successful
        if response.status_code != 200:
            raise Exception(f"GitHub API returned status code {response.status_code}")
            
        response_data = response.json()
        if "tag_name" not in response_data:
            raise Exception("No version tag found in GitHub response")
            
        latest_version = response_data["tag_name"].lstrip('v')
        
        # Validate version format
        if not latest_version:
            raise Exception("Invalid version format received")
        
        if latest_version != version:
            print(f"\n{Fore.YELLOW}{EMOJI['INFO']} {translator.get('updater.new_version_available', current=version, latest=latest_version)}{Style.RESET_ALL}")
            
            # Ask user if they want to update
            while True:
                choice = input(f"\n{EMOJI['ARROW']} {Fore.CYAN}{translator.get('updater.update_confirm', choices='Y/n')}: {Style.RESET_ALL}").lower()
                if choice in ['', 'y', 'yes']:
                    break
                elif choice in ['n', 'no']:
                    print(f"\n{Fore.YELLOW}{EMOJI['INFO']} {translator.get('updater.update_skipped')}{Style.RESET_ALL}")
                    return
                else:
                    print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('menu.invalid_choice')}{Style.RESET_ALL}")
            
            try:
                # Execute update command based on platform
                if platform.system() == 'Windows':
                    update_command = 'irm https://raw.githubusercontent.com/yeongpin/cursor-free-vip/main/scripts/install.ps1 | iex'
                    subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', update_command], check=True)
                else:
                    # For Linux/Mac, download and execute the install script
                    install_script_url = 'https://raw.githubusercontent.com/yeongpin/cursor-free-vip/main/scripts/install.sh'
                    
                    # First verify the script exists
                    script_response = requests.get(install_script_url, timeout=5)
                    if script_response.status_code != 200:
                        raise Exception("Installation script not found")
                        
                    # Save and execute the script
                    with open('install.sh', 'wb') as f:
                        f.write(script_response.content)
                    
                    os.chmod('install.sh', 0o755)  # Make executable
                    subprocess.run(['./install.sh'], check=True)
                    
                    # Clean up
                    if os.path.exists('install.sh'):
                        os.remove('install.sh')
                
                print(f"\n{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('updater.updating')}{Style.RESET_ALL}")
                sys.exit(0)
                
            except Exception as update_error:
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('updater.update_failed', error=str(update_error))}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('updater.manual_update_required')}{Style.RESET_ALL}")
                return
        else:
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('updater.up_to_date')}{Style.RESET_ALL}")
            
    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('updater.network_error', error=str(e))}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('updater.continue_anyway')}{Style.RESET_ALL}")
        return
        
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('updater.check_failed', error=str(e))}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('updater.continue_anyway')}{Style.RESET_ALL}")
        return

def get_chrome_path():
    """Get the Chrome browser executable path based on the platform"""
    try:
        if platform.system() == 'Windows':
            # Check common Windows Chrome installation paths
            paths = [
                os.path.expandvars(r'%ProgramFiles%\Google\Chrome\Application\chrome.exe'),
                os.path.expandvars(r'%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe'),
                os.path.expandvars(r'%LocalAppData%\Google\Chrome\Application\chrome.exe')
            ]
        elif platform.system() == 'Darwin':  # macOS
            paths = [
                '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                '~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
            ]
        else:  # Linux
            paths = [
                '/usr/bin/google-chrome',
                '/usr/bin/google-chrome-stable',
                '/usr/bin/chromium',
                '/usr/bin/chromium-browser'
            ]

        # Return the first path that exists
        for path in paths:
            expanded_path = os.path.expanduser(path)
            if os.path.exists(expanded_path):
                return expanded_path
                
        return None  # Return None if Chrome is not found
        
    except Exception as e:
        print(f"Error finding Chrome path: {str(e)}")
        return None

def open_chrome_with_userscript():
    """Open Chrome and navigate to cursor.sh/settings with the reset trial script"""
    try:
        from DrissionPage import ChromiumOptions, ChromiumPage
        import time
        import random
        import getpass
        import keyring

        def get_random_wait_time(min_time=0.5, max_time=2.0):
            return random.uniform(min_time, max_time)

        def get_saved_credentials():
            try:
                email = keyring.get_password("cursor_reset", "github_email")
                password = keyring.get_password("cursor_reset", "github_password")
                return email, password
            except:
                return None, None

        def save_credentials(email, password):
            try:
                keyring.set_password("cursor_reset", "github_email", email)
                keyring.set_password("cursor_reset", "github_password", password)
                return True
            except:
                return False

        def clear_saved_credentials():
            try:
                keyring.delete_password("cursor_reset", "github_email")
                keyring.delete_password("cursor_reset", "github_password")
                return True
            except:
                return False

        def extract_auth_data(page, github_email=None):
            """Extract authentication data from page"""
            auth_token = None
            cursor_email = None
            
            print(f"{Fore.CYAN}{EMOJI['INFO']} Extracting authentication data...{Style.RESET_ALL}")
            
            # Get cookies
            cookies = page.cookies()
            for cookie in cookies:
                name = cookie.get("name", "")
                value = cookie.get("value", "")
                if name == "WorkosCursorSessionToken":
                    if "::" in value:
                        auth_token = value.split("::")[-1]
                    elif "%3A%3A" in value:
                        auth_token = value.split("%3A%3A")[-1]
                elif name == "cursor_email":
                    cursor_email = value

            # Try localStorage if token not found
            if not auth_token:
                try:
                    local_storage_token = page.run_js('''
                        return localStorage.getItem('WorkosCursorSessionToken') || 
                               localStorage.getItem('cursor_token') || 
                               localStorage.getItem('token');
                    ''')
                    if local_storage_token:
                        auth_token = local_storage_token
                except:
                    pass

            # Use GitHub email if cursor_email not found
            if not cursor_email and github_email:
                print(f"{Fore.YELLOW}Using GitHub email as fallback{Style.RESET_ALL}")
                cursor_email = github_email

            return auth_token, cursor_email

        print(f"{Fore.CYAN}{EMOJI['INFO']} Setting up automated browser...{Style.RESET_ALL}")

        # Get GitHub credentials
        github_email, github_password = get_saved_credentials()
        if not github_email or not github_password:
            print(f"\n{Fore.CYAN}{EMOJI['INFO']} No saved GitHub credentials found. Please enter them now:{Style.RESET_ALL}")
            github_email = input(f"{Fore.YELLOW}Enter GitHub email: {Style.RESET_ALL}")
            github_password = getpass.getpass(f"{Fore.YELLOW}Enter GitHub password: {Style.RESET_ALL}")
            
            if save_credentials(github_email, github_password):
                print(f"{Fore.GREEN}✅ Credentials saved securely{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}⚠️ Could not save credentials, but will continue with login{Style.RESET_ALL}")

        # Set up ChromiumOptions
        co = ChromiumOptions()
        chrome_path = get_chrome_path()
        if chrome_path:
            co.set_browser_path(chrome_path)

        # Other browser options
        co.set_argument("--no-sandbox")
        co.auto_port()
        co.headless(False)

        # Create browser instance
        page = ChromiumPage(co)
        
        print(f"{Fore.YELLOW}Opening browser and navigating to settings...{Style.RESET_ALL}")

        # Navigate to settings page
        page.get("https://cursor.sh/settings")
        time.sleep(get_random_wait_time())

        # First check if we need to log in
        max_attempts = 30
        attempt = 0
        logged_in = False

        while attempt < max_attempts:
            try:
                # Check if already logged in
                basic_info = page.ele("text=Basic Information", timeout=1)
                if basic_info:
                    print(f"{Fore.GREEN}✅ Already logged in{Style.RESET_ALL}")
                    logged_in = True
                    break

                # If not logged in, look for and click GitHub button
                github_button = page.ele("text=Continue with GitHub", timeout=1)
                if github_button:
                    print(f"{Fore.YELLOW}Clicking GitHub login button...{Style.RESET_ALL}")
                    github_button.click()
                    time.sleep(2)

                    # Handle GitHub login form
                    login_field = page.ele('@id=login_field', timeout=2) or page.ele('@name=login', timeout=2)
                    if login_field:
                        print(f"{Fore.YELLOW}Entering GitHub email...{Style.RESET_ALL}")
                        login_field.input(github_email)
                        time.sleep(1)

                        password_field = page.ele('@id=password', timeout=2) or page.ele('@name=password', timeout=2)
                        if password_field:
                            print(f"{Fore.YELLOW}Entering GitHub password...{Style.RESET_ALL}")
                            password_field.input(github_password)
                            time.sleep(1)

                            sign_in = page.ele('@name=commit', timeout=2) or page.ele("text=Sign in", timeout=2)
                            if sign_in:
                                print(f"{Fore.YELLOW}Clicking Sign in...{Style.RESET_ALL}")
                                sign_in.click()
                                time.sleep(3)

                    # Handle GitHub OAuth page if it appears
                    authorize = page.ele("text=Authorize", timeout=2) or page.ele("@id=js-oauth-authorize-btn", timeout=2)
                    if authorize:
                        print(f"{Fore.YELLOW}Authorizing Cursor access...{Style.RESET_ALL}")
                        authorize.click()
                        time.sleep(3)

                attempt += 1
                time.sleep(1)
            except Exception as e:
                print(f"{Fore.YELLOW}Waiting for page to load... ({attempt}/{max_attempts}){Style.RESET_ALL}")
                attempt += 1
                time.sleep(1)

        if not logged_in:
            print(f"{Fore.RED}{EMOJI['ERROR']} Failed to log in automatically{Style.RESET_ALL}")
            return False

        # Extract auth data before reset
        auth_token, cursor_email = extract_auth_data(page, github_email)
        if auth_token and cursor_email:
            print(f"{Fore.GREEN}✅ Successfully extracted authentication data before reset{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}⚠️ Could not extract complete auth data before reset{Style.RESET_ALL}")

        # Execute the reset
        print(f"{Fore.YELLOW}Executing reset...{Style.RESET_ALL}")
        page.run_js('''
            fetch("https://www.cursor.com/api/dashboard/delete-account", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Origin": "https://cursor.sh",
                    "Referer": "https://cursor.sh/settings"
                },
                credentials: "include"
            })
            .then(response => {
                if (response.ok) {
                    window.location.reload();
                } else {
                    console.error("Failed to reset trial");
                }
            })
            .catch(error => {
                console.error("Reset failed:", error);
            });
        ''')
        
        time.sleep(2)  # Wait for reload

        # Log in again after reset
        print(f"{Fore.YELLOW}Logging in again after reset...{Style.RESET_ALL}")
        attempt = 0
        logged_in = False

        while attempt < max_attempts:
            try:
                # Check if already logged in
                basic_info = page.ele("text=Basic Information", timeout=1)
                if basic_info:
                    print(f"{Fore.GREEN}✅ Successfully logged in after reset{Style.RESET_ALL}")
                    logged_in = True
                    break

                # If not logged in, look for and click GitHub button
                github_button = page.ele("text=Continue with GitHub", timeout=1)
                if github_button:
                    print(f"{Fore.YELLOW}Clicking GitHub login button...{Style.RESET_ALL}")
                    github_button.click()
                    time.sleep(2)

                    # Handle GitHub OAuth page if it appears (should auto-authorize)
                    authorize = page.ele("text=Authorize", timeout=2) or page.ele("@id=js-oauth-authorize-btn", timeout=2)
                    if authorize:
                        print(f"{Fore.YELLOW}Authorizing Cursor access...{Style.RESET_ALL}")
                        authorize.click()
                        time.sleep(3)

                attempt += 1
                time.sleep(1)
            except Exception as e:
                print(f"{Fore.YELLOW}Waiting for page to load... ({attempt}/{max_attempts}){Style.RESET_ALL}")
                attempt += 1
                time.sleep(1)

        if not logged_in:
            print(f"{Fore.RED}{EMOJI['ERROR']} Failed to log in after reset{Style.RESET_ALL}")
            return False

        # Extract auth data after reset and second login
        print(f"{Fore.YELLOW}Extracting final authentication data...{Style.RESET_ALL}")
        auth_token, cursor_email = extract_auth_data(page, github_email)
        
        if auth_token and cursor_email:
            try:
                print(f"{Fore.CYAN}{EMOJI['INFO']} Updating Cursor authentication data...{Style.RESET_ALL}")
                cursor_auth = CursorAuth(translator=translator)
                
                # Update the auth info in Cursor's database
                if cursor_auth.update_auth(
                    email=cursor_email,
                    access_token=auth_token,
                    refresh_token=auth_token  # Use same token for both
                ):
                    print(f"{Fore.GREEN}✅ Authentication data saved - Cursor will auto-login next time{Style.RESET_ALL}")
                    
                    # Reset machine ID after updating auth
                    from reset_machine_manual import MachineIDResetter
                    print(f"{Fore.CYAN}{EMOJI['INFO']} Resetting machine ID...{Style.RESET_ALL}")
                    resetter = MachineIDResetter(translator)
                    if resetter.reset_machine_ids():
                        print(f"{Fore.GREEN}✅ Machine ID reset successful{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.RED}❌ Failed to reset machine ID{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}❌ Failed to save authentication data{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}❌ Failed to save authentication data: {e}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}❌ Could not extract authentication data{Style.RESET_ALL}")
            print(f"Missing data: {' auth_token' if not auth_token else ''}{' cursor_email' if not cursor_email else ''}")
        
        print(f"{Fore.CYAN}ℹ️ Closing Chrome...{Style.RESET_ALL}")
        
        # Close the browser
        try:
            page.quit()
        except:
            pass

        return True

    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} Failed to automate the process: {e}{Style.RESET_ALL}")
        return False
    finally:
        try:
            page.quit()
        except:
            pass

    return True

def main():
    """Main function"""
    try:
        # Initialize translator
        translator = load_translator()
        
        while True:
            print_menu(translator)
            choice = input(f"\n{Fore.CYAN}{translator.get('menu.enter_choice')}{Style.RESET_ALL}")
            
            if choice == "0":
                print(f"\n{Fore.YELLOW}{EMOJI['EXIT']} {translator.get('menu.goodbye')}{Style.RESET_ALL}")
                break
            elif choice == "1":
                reset_machine_id(translator)
            elif choice == "2":
                reset_trial(translator)
            elif choice == "3":
                register_cursor(translator)
            elif choice == "4":
                register_github(translator)
            elif choice == "5":
                register_google(translator)
            else:
                print(f"\n{Fore.RED}{EMOJI['ERROR']} {translator.get('menu.invalid_choice')}{Style.RESET_ALL}")
            
            input(f"\n{Fore.CYAN}{translator.get('menu.press_enter')}{Style.RESET_ALL}")
            
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}{EMOJI['EXIT']} {translator.get('menu.goodbye')}{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}{EMOJI['ERROR']} {translator.get('menu.error', error=str(e))}{Style.RESET_ALL}")
        input(f"\n{Fore.CYAN}{translator.get('menu.press_enter')}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()