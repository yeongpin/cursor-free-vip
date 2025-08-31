# main.py
# This script allows the user to choose which script to run.
import os
import sys
import locale
import platform
import requests
import subprocess
import logging
from colorama import Fore, Style, init
from typing import Optional, Dict, List, Any, Tuple, Union
from pathlib import Path

# Initialize colorama
init(autoreset=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Import local modules
from logo import print_logo, version
from config import get_config, force_update_config
from utils import get_user_documents_path

# Add these imports for Arabic support
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
except ImportError:
    logger.warning("Arabic support modules not found")
    arabic_reshaper = None
    get_display = None

# Only import windll on Windows systems
if platform.system() == 'Windows':
    try:
        import ctypes
        from ctypes import windll
    except ImportError:
        logger.warning("Windows-specific modules not found")
        ctypes = None
        windll = None

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
    "ADMIN": "🔐",
    "AIRDROP": "💰",
    "ROCKET": "🚀",
    "STAR": "⭐",
    "SUN": "🌟",
    "CONTRIBUTE": "🤝",
    "SETTINGS": "⚙️"
}

# Function to check if running as frozen executable
def is_frozen() -> bool:
    """Check if the script is running as a frozen executable."""
    return getattr(sys, 'frozen', False)

# Function to check admin privileges (Windows only)
def is_admin() -> bool:
    """Check if the script is running with admin privileges (Windows only)."""
    if platform.system() == 'Windows' and ctypes and windll:
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception as e:
            logger.error(f"Error checking admin privileges: {e}")
            return False
    # Always return True for non-Windows to avoid changing behavior
    return True

# Function to restart with admin privileges
def run_as_admin() -> bool:
    """Restart the current script with admin privileges (Windows only)."""
    if platform.system() != 'Windows' or not ctypes or not windll:
        return False
        
    try:
        args = [sys.executable] + sys.argv
        
        # Request elevation via ShellExecute
        print(f"{Fore.YELLOW}{EMOJI['ADMIN']} {translator.get('admin.requesting_privileges') if translator else 'Requesting administrator privileges...'}{Style.RESET_ALL}")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", args[0], " ".join('"' + arg + '"' for arg in args[1:]), None, 1)
        return True
    except Exception as e:
        logger.error(f"Failed to restart with admin privileges: {e}")
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('admin.restart_failed', error=str(e)) if translator else f'Failed to restart with admin privileges: {e}'}{Style.RESET_ALL}")
        return False

class Translator:
    def __init__(self):
        self.translations = {}
        self.config = get_config()
        
        # Create language cache directory if it doesn't exist
        if self.config and self.config.has_section('Language'):
            self.language_cache_dir = self.config.get('Language', 'language_cache_dir')
            os.makedirs(self.language_cache_dir, exist_ok=True)
        else:
            self.language_cache_dir = None
        
        # Set fallback language from config if available
        self.fallback_language = 'en'
        if self.config and self.config.has_section('Language') and self.config.has_option('Language', 'fallback_language'):
            self.fallback_language = self.config.get('Language', 'fallback_language')
        
        # Load saved language from config if available, otherwise detect system language
        if self.config and self.config.has_section('Language') and self.config.has_option('Language', 'current_language'):
            saved_language = self.config.get('Language', 'current_language')
            if saved_language and saved_language.strip():
                self.current_language = saved_language
            else:
                self.current_language = self.detect_system_language()
                # Save detected language to config
                if self.config.has_section('Language'):
                    self.config.set('Language', 'current_language', self.current_language)
                    config_dir = os.path.join(get_user_documents_path(), ".cursor-free-vip")
                    config_file = os.path.join(config_dir, "config.ini")
                    with open(config_file, 'w', encoding='utf-8') as f:
                        self.config.write(f)
        else:
            self.current_language = self.detect_system_language()
        
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
            
            # Map language ID to our language codes using match-case
            match layout_id:
                case 0x0409:
                    return 'en'      # English
                case 0x0404:
                    return 'zh_tw'   # Traditional Chinese
                case 0x0804:
                    return 'zh_cn'   # Simplified Chinese
                case 0x0422:
                    return 'vi'      # Vietnamese
                case 0x0419:
                    return 'ru'      # Russian
                case 0x0415:
                    return 'tr'      # Turkish
                case 0x0402:
                    return 'bg'      # Bulgarian
                case 0x0401:
                    return 'ar'      # Arabic
                case _:
                    return 'en'       # Default to English
        except:
            return self._detect_unix_language()
    
    def _detect_unix_language(self):
        """Detect language on Unix-like systems (Linux, macOS)"""
        try:
            # Get the system locale
            locale.setlocale(locale.LC_ALL, '')
            system_locale = locale.getlocale()[0]
            if not system_locale:
                return 'en'
            
            system_locale = system_locale.lower()
            
            # Map locale to our language codes using match-case
            match system_locale:
                case s if s.startswith('zh_tw') or s.startswith('zh_hk'):
                    return 'zh_tw'
                case s if s.startswith('zh_cn'):
                    return 'zh_cn'
                case s if s.startswith('en'):
                    return 'en'
                case s if s.startswith('vi'):
                    return 'vi'
                case s if s.startswith('nl'):
                    return 'nl'
                case s if s.startswith('de'):
                    return 'de'
                case s if s.startswith('fr'):
                    return 'fr'
                case s if s.startswith('pt'):
                    return 'pt'
                case s if s.startswith('ru'):
                    return 'ru'
                case s if s.startswith('tr'):
                    return 'tr'
                case s if s.startswith('bg'):
                    return 'bg'
                case s if s.startswith('ar'):
                    return 'ar'
                case _:
                    # Try to get language from LANG environment variable as fallback
                    env_lang = os.getenv('LANG', '').lower()
                    match env_lang:
                        case s if 'tw' in s or 'hk' in s:
                            return 'zh_tw'
                        case s if 'cn' in s:
                            return 'zh_cn'
                        case s if 'vi' in s:
                            return 'vi'
                        case s if 'nl' in s:
                            return 'nl'
                        case s if 'de' in s:
                            return 'de'
                        case s if 'fr' in s:
                            return 'fr'
                        case s if 'pt' in s:
                            return 'pt'
                        case s if 'ru' in s:
                            return 'ru'
                        case s if 'tr' in s:
                            return 'tr'
                        case s if 'bg' in s:
                            return 'bg'
                        case s if 'ar' in s:
                            return 'ar'
                        case _:
                            return 'en'
        except:
            return 'en'
    
    def download_language_file(self, lang_code):
        """Method kept for compatibility but now returns False as language files are integrated"""
        print(f"{Fore.YELLOW}{EMOJI['INFO']} Languages are now integrated into the package, no need to download.{Style.RESET_ALL}")
        return False
            
    def load_translations(self):
        """Load all available translations from the integrated package"""
        try:
            # Collection of languages we've successfully loaded
            loaded_languages = set()
            
            locales_paths = []
            
            # Check for PyInstaller bundle first
            if hasattr(sys, '_MEIPASS'):
                locales_paths.append(os.path.join(sys._MEIPASS, 'locales'))
            
            # Check script directory next
            script_dir = os.path.dirname(os.path.abspath(__file__))
            locales_paths.append(os.path.join(script_dir, 'locales'))
            
            # Also check current working directory
            locales_paths.append(os.path.join(os.getcwd(), 'locales'))
            
            for locales_dir in locales_paths:
                if os.path.exists(locales_dir) and os.path.isdir(locales_dir):
                    for file in os.listdir(locales_dir):
                        if file.endswith('.json'):
                            lang_code = file[:-5]  # Remove .json
                            try:
                                with open(os.path.join(locales_dir, file), 'r', encoding='utf-8') as f:
                                    self.translations[lang_code] = json.load(f)
                                    loaded_languages.add(lang_code)
                                    loaded_any = True
                            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                                print(f"{Fore.RED}{EMOJI['ERROR']} Error loading {file}: {e}{Style.RESET_ALL}")
                                continue

        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} Failed to load translations: {e}{Style.RESET_ALL}")
            # Create at least minimal English translations for basic functionality
            self.translations['en'] = {"menu": {"title": "Menu", "exit": "Exit", "invalid_choice": "Invalid choice"}}
    
    def fix_arabic(self, text):
        if self.current_language == 'ar' and arabic_reshaper and get_display:
            try:
                reshaped_text = arabic_reshaper.reshape(text)
                bidi_text = get_display(reshaped_text)
                return bidi_text
            except Exception:
                return text
        return text

    def get(self, key, **kwargs):
        """Get translated text with fallback support"""
        try:
            # Try current language
            result = self._get_translation(self.current_language, key)
            if result == key and self.current_language != self.fallback_language:
                # Try fallback language if translation not found
                result = self._get_translation(self.fallback_language, key)
            formatted = result.format(**kwargs) if kwargs else result
            return self.fix_arabic(formatted)
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
        # Get currently loaded languages
        available_languages = list(self.translations.keys())
        
        # Sort languages alphabetically for better display
        return sorted(available_languages)

# Create translator instance
translator = Translator()

def print_menu():
    """Print menu options"""
    try:
        config = get_config()
        if config.getboolean('Utils', 'enabled_account_info'):
            import cursor_acc_info
            cursor_acc_info.display_account_info(translator)
    except Exception as e:
        print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('menu.account_info_error', error=str(e))}{Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}{EMOJI['MENU']} {translator.get('menu.title')}:{Style.RESET_ALL}")
    if translator.current_language == 'zh_cn' or translator.current_language == 'zh_tw':
        print(f"{Fore.YELLOW}{'─' * 70}{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}{'─' * 110}{Style.RESET_ALL}")
    
    # Get terminal width
    try:
        terminal_width = shutil.get_terminal_size().columns
    except:
        terminal_width = 80  # Default width
    
    # Define all menu items
    menu_items = {
        0: f"{Fore.GREEN}0{Style.RESET_ALL}. {EMOJI['ERROR']} {translator.get('menu.exit')}",
        1: f"{Fore.GREEN}1{Style.RESET_ALL}. {EMOJI['RESET']} {translator.get('menu.reset')}",
        2: f"{Fore.GREEN}2{Style.RESET_ALL}. {EMOJI['SUCCESS']} {translator.get('menu.register_manual')}",
        3: f"{Fore.GREEN}3{Style.RESET_ALL}. {EMOJI['ERROR']} {translator.get('menu.quit')}",
        4: f"{Fore.GREEN}4{Style.RESET_ALL}. {EMOJI['LANG']} {translator.get('menu.select_language')}",
        5: f"{Fore.GREEN}5{Style.RESET_ALL}. {EMOJI['SUN']} {translator.get('menu.register_google')}",
        6: f"{Fore.GREEN}6{Style.RESET_ALL}. {EMOJI['STAR']} {translator.get('menu.register_github')}",
        7: f"{Fore.GREEN}7{Style.RESET_ALL}. {EMOJI['UPDATE']} {translator.get('menu.disable_auto_update')}",
        8: f"{Fore.GREEN}8{Style.RESET_ALL}. {EMOJI['RESET']} {translator.get('menu.totally_reset')}",
        9: f"{Fore.GREEN}9{Style.RESET_ALL}. {EMOJI['CONTRIBUTE']} {translator.get('menu.contribute')}",
        10: f"{Fore.GREEN}10{Style.RESET_ALL}. {EMOJI['SETTINGS']}  {translator.get('menu.config')}",
        11: f"{Fore.GREEN}11{Style.RESET_ALL}. {EMOJI['UPDATE']}  {translator.get('menu.bypass_version_check')}",
        12: f"{Fore.GREEN}12{Style.RESET_ALL}. {EMOJI['UPDATE']}  {translator.get('menu.check_user_authorized')}",
        13: f"{Fore.GREEN}13{Style.RESET_ALL}. {EMOJI['UPDATE']}  {translator.get('menu.bypass_token_limit')}",
        14: f"{Fore.GREEN}14{Style.RESET_ALL}. {EMOJI['BACKUP']}  {translator.get('menu.restore_machine_id')}",
        15: f"{Fore.GREEN}15{Style.RESET_ALL}. {EMOJI['ERROR']}  {translator.get('menu.delete_google_account')}",
        16: f"{Fore.GREEN}16{Style.RESET_ALL}. {EMOJI['SETTINGS']}  {translator.get('menu.select_chrome_profile')}",
        17: f"{Fore.GREEN}17{Style.RESET_ALL}. {EMOJI['UPDATE']}  {translator.get('menu.manual_custom_auth')}"
    }
    
    # Automatically calculate the number of menu items in the left and right columns
    total_items = len(menu_items)
    left_column_count = (total_items + 1) // 2  # The number of options displayed on the left (rounded up)
    
    # Build left and right columns of menus
    sorted_indices = sorted(menu_items.keys())
    left_menu = [menu_items[i] for i in sorted_indices[:left_column_count]]
    right_menu = [menu_items[i] for i in sorted_indices[left_column_count:]]
    
    # Calculate the maximum display width of left menu items
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
    for item in left_menu:
        width = get_display_width(item)
        max_left_width = max(max_left_width, width)
    
    # Set the starting position of right menu
    fixed_spacing = 4  # Fixed spacing
    right_start = max_left_width + fixed_spacing
    
    # Calculate the number of spaces needed for right menu items
    spaces_list = []
    for i in range(len(left_menu)):
        if i < len(left_menu):
            left_item = left_menu[i]
            left_width = get_display_width(left_item)
            spaces = right_start - left_width
            spaces_list.append(spaces)
    
    # Print menu items
    max_rows = max(len(left_menu), len(right_menu))
    
    for i in range(max_rows):
        # Print left menu items
        if i < len(left_menu):
            left_item = left_menu[i]
            print(left_item, end='')
            
            # Use pre-calculated spaces
            spaces = spaces_list[i]
        else:
            # If left side has no items, print only spaces
            spaces = right_start
            print('', end='')
        
        # Print right menu items
        if i < len(right_menu):
            print(' ' * spaces + right_menu[i])
        else:
            print()  # Change line
    if translator.current_language == 'zh_cn' or translator.current_language == 'zh_tw':
        print(f"{Fore.YELLOW}{'─' * 70}{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}{'─' * 110}{Style.RESET_ALL}")

def select_language():
    """Language selection menu"""
    print(f"\n{Fore.CYAN}{EMOJI['LANG']} {translator.get('menu.select_language')}:{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{'─' * 40}{Style.RESET_ALL}")
    
    # Get available languages either from local directory or GitHub
    languages = translator.get_available_languages()
    languages_count = len(languages)
    
    # Display all available languages with proper indices
    for i, lang in enumerate(languages):
        lang_name = translator.get(f"languages.{lang}", fallback=lang)
        print(f"{Fore.GREEN}{i}{Style.RESET_ALL}. {lang_name}")
    
    try:
        # Use the actual number of languages in the prompt
        choice = input(f"\n{EMOJI['ARROW']} {Fore.CYAN}{translator.get('menu.input_choice', choices=f'0-{languages_count-1}')}: {Style.RESET_ALL}")
        
        if choice.isdigit() and 0 <= int(choice) < languages_count:
            selected_language = languages[int(choice)]
            translator.set_language(selected_language)
            
            # Save selected language to config
            config = get_config()
            if config and config.has_section('Language'):
                config.set('Language', 'current_language', selected_language)
                
                # Get config path from user documents
                config_dir = os.path.join(get_user_documents_path(), ".cursor-free-vip")
                config_file = os.path.join(config_dir, "config.ini")
                
                # Write updated config
                with open(config_file, 'w', encoding='utf-8') as f:
                    config.write(f)
                
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('menu.language_config_saved', language=translator.get(f'languages.{selected_language}', fallback=selected_language))}{Style.RESET_ALL}")
            
            return True
        else:
            # Show invalid choice message with the correct range
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('menu.lang_invalid_choice', lang_choices=f'0-{languages_count-1}')}{Style.RESET_ALL}")
            return False
    except (ValueError, IndexError) as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('menu.lang_invalid_choice', lang_choices=f'0-{languages_count-1}')}{Style.RESET_ALL}")
        return False

def check_latest_version():
    """Check if current version matches the latest release version"""
    try:
        print(f"\n{Fore.CYAN}{EMOJI['UPDATE']} {translator.get('updater.checking')}{Style.RESET_ALL}")
        
        # First try GitHub API
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'CursorFreeVIP-Updater'
        }
        
        latest_version = None
        github_error = None
        
        # Try GitHub API first
        try:
            github_response = requests.get(
                "https://api.github.com/repos/yeongpin/cursor-free-vip/releases/latest",
                headers=headers,
                timeout=10
            )
            
            # Check if rate limit exceeded
            if github_response.status_code == 403 and "rate limit exceeded" in github_response.text.lower():
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('updater.rate_limit_exceeded', fallback='GitHub API rate limit exceeded. Trying backup API...')}{Style.RESET_ALL}")
                raise Exception("Rate limit exceeded")
                
            # Check if response is successful
            if github_response.status_code != 200:
                raise Exception(f"GitHub API returned status code {github_response.status_code}")
                
            github_data = github_response.json()
            if "tag_name" not in github_data:
                raise Exception("No version tag found in GitHub response")
                
            latest_version = github_data["tag_name"].lstrip('v')
            
        except Exception as e:
            github_error = str(e)
            print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('updater.github_api_failed', fallback='GitHub API failed, trying backup API...')}{Style.RESET_ALL}")
            
            # If GitHub API fails, try backup API
            try:
                backup_headers = {
                    'Accept': 'application/json',
                    'User-Agent': 'CursorFreeVIP-Updater'
                }
                backup_response = requests.get(
                    "https://pinnumber.rr.nu/badges/release/yeongpin/cursor-free-vip",
                    headers=backup_headers,
                    timeout=10
                )
                
                # Check if response is successful
                if backup_response.status_code != 200:
                    raise Exception(f"Backup API returned status code {backup_response.status_code}")
                    
                backup_data = backup_response.json()
                if "message" not in backup_data:
                    raise Exception("No version tag found in backup API response")
                    
                latest_version = backup_data["message"].lstrip('v')
                
            except Exception as backup_e:
                # If both APIs fail, raise the original GitHub error
                raise Exception(f"Both APIs failed. GitHub error: {github_error}, Backup error: {str(backup_e)}")
        
        # Validate version format
        if not latest_version:
            raise Exception("Invalid version format received")
        
        # Parse versions for proper comparison
        def parse_version(version_str):
            """Parse version string into tuple for proper comparison"""
            try:
                return tuple(map(int, version_str.split('.')))
            except ValueError:
                # Fallback to string comparison if parsing fails
                return version_str
                
        current_version_tuple = parse_version(version)
        latest_version_tuple = parse_version(latest_version)
        
        # Compare versions properly
        is_newer_version_available = False
        if isinstance(current_version_tuple, tuple) and isinstance(latest_version_tuple, tuple):
            is_newer_version_available = current_version_tuple < latest_version_tuple
        else:
            # Fallback to string comparison
            is_newer_version_available = version != latest_version
        
        if is_newer_version_available:
            print(f"\n{Fore.YELLOW}{EMOJI['INFO']} {translator.get('updater.new_version_available', current=version, latest=latest_version)}{Style.RESET_ALL}")
            
            # get and show changelog
            try:
                changelog_url = "https://raw.githubusercontent.com/yeongpin/cursor-free-vip/main/CHANGELOG.md"
                changelog_response = requests.get(changelog_url, timeout=10)
                
                if changelog_response.status_code == 200:
                    changelog_content = changelog_response.text
                    
                    # get latest version changelog
                    latest_version_pattern = f"## v{latest_version}"
                    changelog_sections = changelog_content.split("## v")
                    
                    latest_changes = None
                    for section in changelog_sections:
                        if section.startswith(latest_version):
                            latest_changes = section
                            break
                    
                    if latest_changes:
                        print(f"\n{Fore.CYAN}{'─' * 40}{Style.RESET_ALL}")
                        print(f"{Fore.CYAN}{translator.get('updater.changelog_title')}:{Style.RESET_ALL}")
                        
                        # show changelog content (max 10 lines)
                        changes_lines = latest_changes.strip().split('\n')
                        for i, line in enumerate(changes_lines[1:11]):  # skip version number line, max 10 lines
                            if line.strip():
                                print(f"{Fore.WHITE}{line.strip()}{Style.RESET_ALL}")
                        
                        # if changelog more than 10 lines, show ellipsis
                        if len(changes_lines) > 11:
                            print(f"{Fore.WHITE}...{Style.RESET_ALL}")
                        
                        print(f"{Fore.CYAN}{'─' * 40}{Style.RESET_ALL}")
            except Exception as changelog_error:
                # get changelog failed
                pass
            
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
            # If current version is newer or equal to latest version
            if current_version_tuple > latest_version_tuple:
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('updater.development_version', current=version, latest=latest_version)}{Style.RESET_ALL}")
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

def main() -> None:
    """Main entry point for the application."""
    try:
        # Check for admin privileges if running as executable on Windows only
        if platform.system() == 'Windows' and is_frozen() and not is_admin():
            logger.warning("Running without admin privileges on Windows")
            print(f"{Fore.YELLOW}{EMOJI['ADMIN']} {translator.get('menu.admin_required') if translator else 'Administrator privileges are required for some features'}{Style.RESET_ALL}")
            if run_as_admin():
                sys.exit(0)  # Exit after requesting admin privileges
            else:
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('menu.admin_required_continue') if translator else 'Continuing without administrator privileges. Some features may not work correctly.'}{Style.RESET_ALL}")
        
        # Display logo
        print_logo()
        
        # Initialize configuration
        logger.info("Initializing configuration")
        config = get_config(translator)
        if not config:
            logger.error("Failed to initialize configuration")
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('menu.config_init_failed') if translator else 'Failed to initialize configuration'}{Style.RESET_ALL}")
            return
            
        # Update configuration
        force_update_config(translator)
    
        # Check for updates
        if config.has_option('Utils', 'enabled_update_check') and config.getboolean('Utils', 'enabled_update_check'):
            logger.info("Checking for updates")
            check_latest_version()
            
        # Display menu
        print_menu()
        
        # Main menu loop
        while True:
            try:
                choice_num = 17
                choice = input(f"\n{EMOJI['ARROW']} {Fore.CYAN}{translator.get('menu.input_choice', choices=f'0-{choice_num}') if translator else f'Enter your choice (0-{choice_num})'}: {Style.RESET_ALL}")
    
                # Process menu choice
                process_menu_choice(choice)
                
            except KeyboardInterrupt:
                logger.info("Program terminated by user (KeyboardInterrupt)")
                print(f"\n{Fore.YELLOW}{EMOJI['INFO']} {translator.get('menu.program_terminated') if translator else 'Program terminated by user'}{Style.RESET_ALL}")
                print(f"{Fore.CYAN}{'═' * 50}{Style.RESET_ALL}")
                return
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}")
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('menu.unexpected_error', error=str(e)) if translator else f'An unexpected error occurred: {e}'}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('menu.please_try_again') if translator else 'Please try again'}{Style.RESET_ALL}")
                
    except Exception as e:
        logger.critical(f"Critical error in main function: {e}")
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('menu.critical_error', error=str(e)) if translator else f'A critical error occurred: {e}'}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('menu.please_restart') if translator else 'Please restart the application'}{Style.RESET_ALL}")
        return

def process_menu_choice(choice: str) -> None:
    """Process menu choice and execute corresponding action.
    
    Args:
        choice: User's menu choice
    """
    try:
        match choice:
            case "0":
                logger.info("User selected to exit")
                print(f"\n{Fore.YELLOW}{EMOJI['INFO']} {translator.get('menu.exit') if translator else 'Exiting'}...{Style.RESET_ALL}")
                print(f"{Fore.CYAN}{'═' * 50}{Style.RESET_ALL}")
                sys.exit(0)
            case "1":
                logger.info("User selected reset machine manual")
                import reset_machine_manual
                reset_machine_manual.run(translator)
                print_menu()   
            case "2":
                logger.info("User selected cursor register manual")
                import cursor_register_manual
                cursor_register_manual.main(translator)
                print_menu()    
            case "3":
                logger.info("User selected quit cursor")
                import quit_cursor
                quit_cursor.quit_cursor(translator)
                print_menu()
            case "4":
                logger.info("User selected language settings")
                if select_language():
                    print_menu()
                return
            case "5":
                logger.info("User selected Google OAuth")
                from oauth_auth import main as oauth_main
                oauth_main('google', translator)
                print_menu()
            case "6":
                logger.info("User selected GitHub OAuth")
                from oauth_auth import main as oauth_main
                oauth_main('github', translator)
                print_menu()
            case "7":
                logger.info("User selected disable auto update")
                import disable_auto_update
                disable_auto_update.run(translator)
                print_menu()
            case "8":
                logger.info("User selected totally reset cursor")
                import totally_reset_cursor
                totally_reset_cursor.run(translator)
                print_menu()
            case "9":
                logger.info("User selected view contributors")
                import logo
                print(logo.CURSOR_CONTRIBUTORS)
                print_menu()
            case "10":
                logger.info("User selected view config")
                from config import print_config
                print_config(get_config(), translator)
                print_menu()
            case "11":
                logger.info("User selected bypass version")
                import bypass_version
                bypass_version.main(translator)
                print_menu()
            case "12":
                logger.info("User selected check user authorized")
                import check_user_authorized
                check_user_authorized.main(translator)
                print_menu()
            case "13":
                logger.info("User selected bypass token limit")
                import bypass_token_limit
                bypass_token_limit.run(translator)
                print_menu()
            case "14":
                logger.info("User selected restore machine ID")
                import restore_machine_id
                restore_machine_id.run(translator)
                print_menu()
            case "15":
                logger.info("User selected delete cursor Google")
                import delete_cursor_google
                delete_cursor_google.main(translator)
                print_menu()
            case "16":
                logger.info("User selected select profile")
                from oauth_auth import OAuthHandler
                oauth = OAuthHandler(translator)
                oauth._select_profile()
                print_menu()
            case "17":
                logger.info("User selected manual custom auth")
                import manual_custom_auth
                manual_custom_auth.main(translator)
                print_menu()
            case _:
                logger.warning(f"Invalid choice: {choice}")
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('menu.invalid_choice') if translator else 'Invalid choice'}{Style.RESET_ALL}")
                print_menu()
    except ImportError as e:
        logger.error(f"Failed to import module: {e}")
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('menu.module_not_found', error=str(e)) if translator else f'Module not found: {e}'}{Style.RESET_ALL}")
        print_menu()
    except Exception as e:
        logger.error(f"Error processing menu choice: {e}")
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('menu.action_failed', error=str(e)) if translator else f'Action failed: {e}'}{Style.RESET_ALL}")
        print_menu()

if __name__ == "__main__":
    # Initialize translator
    translator = Translator()
    
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}{EMOJI['INFO']} {translator.get('menu.program_terminated') if translator else 'Program terminated by user'}{Style.RESET_ALL}")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}")
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('menu.unhandled_exception', error=str(e)) if translator else f'Unhandled exception: {e}'}{Style.RESET_ALL}")
        sys.exit(1)