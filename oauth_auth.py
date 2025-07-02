# oauth_auth.py
import os
from colorama import Fore, Style, init
import time
import random
import webbrowser
import sys
import json
from DrissionPage import ChromiumPage, ChromiumOptions
from cursor_auth import CursorAuth
from utils import get_random_wait_time, get_default_browser_path
from config import get_config
import platform
from get_user_token import get_token_from_cookie

# Initialize colorama
init()

# Define emoji constants
EMOJI = {
    'START': '🚀',
    'OAUTH': '🔑',
    'SUCCESS': '✅',
    'ERROR': '❌',
    'WAIT': '⏳',
    'INFO': 'ℹ️',
    'WARNING': '⚠️'
}

class OAuthHandler:
    def __init__(self, translator=None, auth_type=None):
        self.translator = translator
        self.config = get_config(translator)
        self.auth_type = auth_type
        os.environ['BROWSER_HEADLESS'] = 'False'
        self.browser = None
        self.selected_profile = None
        
    def _get_available_profiles(self, user_data_dir):
        """Get list of available Chrome profiles with their names"""
        try:
            profiles = []
            profile_names = {}
            
            # Read Local State file to get profile names
            local_state_path = os.path.join(user_data_dir, 'Local State')
            if os.path.exists(local_state_path):
                with open(local_state_path, 'r', encoding='utf-8') as f:
                    local_state = json.load(f)
                    info_cache = local_state.get('profile', {}).get('info_cache', {})
                    for profile_dir, info in info_cache.items():
                        profile_dir = profile_dir.replace('\\', '/')
                        if profile_dir == 'Default':
                            profile_names['Default'] = info.get('name', 'Default')
                        elif profile_dir.startswith('Profile '):
                            profile_names[profile_dir] = info.get('name', profile_dir)

            # Get list of profile directories
            for item in os.listdir(user_data_dir):
                if item == 'Default' or (item.startswith('Profile ') and os.path.isdir(os.path.join(user_data_dir, item))):
                    profiles.append((item, profile_names.get(item, item)))
            return sorted(profiles)
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('chrome_profile.error_loading', error=str(e)) if self.translator else f'Error loading Chrome profiles: {e}'}{Style.RESET_ALL}")
            return []

    def _select_profile(self):
        """Allow user to select a browser profile to use"""
        try:
            # 从配置中获取浏览器类型
            config = get_config(self.translator)
            browser_type = config.get('Browser', 'default_browser', fallback='chrome')
            browser_type_display = browser_type.capitalize()
            
            if self.translator:
                # 动态使用浏览器类型
                print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.select_profile', browser=browser_type_display)}{Style.RESET_ALL}")
                print(f"{Fore.CYAN}{self.translator.get('oauth.profile_list', browser=browser_type_display)}{Style.RESET_ALL}")
            else:
                print(f"{Fore.CYAN}{EMOJI['INFO']} Select {browser_type_display} profile to use:{Style.RESET_ALL}")
                print(f"Available {browser_type_display} profiles:")
            
            # Get the user data directory for the browser type
            user_data_dir = self._get_user_data_directory()
            
            # Load available profiles from the selected browser type
            try:
                local_state_file = os.path.join(user_data_dir, "Local State")
                if os.path.exists(local_state_file):
                    with open(local_state_file, 'r', encoding='utf-8') as f:
                        state_data = json.load(f)
                    profiles_data = state_data.get('profile', {}).get('info_cache', {})
                    
                    # Create a list of available profiles
                    profiles = []
                    for profile_id, profile_info in profiles_data.items():
                        name = profile_info.get('name', profile_id)
                        # Mark the default profile
                        if profile_id.lower() == 'default':
                            name = f"{name} (Default)"
                        profiles.append((profile_id, name))
                    
                    # Sort profiles by name
                    profiles.sort(key=lambda x: x[1])
                    
                    # Show available profiles
                    if self.translator:
                        print(f"{Fore.CYAN}0. {self.translator.get('menu.exit')}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.CYAN}0. Exit{Style.RESET_ALL}")
                    
                    for i, (profile_id, name) in enumerate(profiles, 1):
                        print(f"{Fore.CYAN}{i}. {name}{Style.RESET_ALL}")
                    
                    # Get user's choice
                    max_choice = len(profiles)
                    choice_str = input(f"\n{Fore.CYAN}{self.translator.get('menu.input_choice', choices=f'0-{max_choice}') if self.translator else f'Please enter your choice (0-{max_choice})'}{Style.RESET_ALL}")
                    
                    try:
                        choice = int(choice_str)
                        if choice == 0:
                            return False
                        elif 1 <= choice <= max_choice:
                            selected_profile = profiles[choice-1][0]
                            self.selected_profile = selected_profile
                            
                            if self.translator:
                                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('oauth.profile_selected', profile=selected_profile)}{Style.RESET_ALL}")
                            else:
                                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} Selected profile: {selected_profile}{Style.RESET_ALL}")
                            return True
                        else:
                            if self.translator:
                                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.invalid_selection')}{Style.RESET_ALL}")
                            else:
                                print(f"{Fore.RED}{EMOJI['ERROR']} Invalid selection. Please try again.{Style.RESET_ALL}")
                            return self._select_profile()
                    except ValueError:
                        if self.translator:
                            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.invalid_selection')}{Style.RESET_ALL}")
                        else:
                            print(f"{Fore.RED}{EMOJI['ERROR']} Invalid selection. Please try again.{Style.RESET_ALL}")
                        return self._select_profile()
                else:
                    # No Local State file, use Default profile
                    print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('oauth.no_profiles', browser=browser_type_display) if self.translator else f'No {browser_type_display} profiles found'}{Style.RESET_ALL}")
                    self.selected_profile = "Default"
                    return True
                    
            except Exception as e:
                # Error loading profiles, use Default profile
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.error_loading', error=str(e), browser=browser_type_display) if self.translator else f'Error loading {browser_type_display} profiles: {str(e)}'}{Style.RESET_ALL}")
                self.selected_profile = "Default"
                return True
            
        except Exception as e:
            # General error, use Default profile
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.profile_selection_error', error=str(e)) if self.translator else f'Error during profile selection: {str(e)}'}{Style.RESET_ALL}")
            self.selected_profile = "Default"
            return True

    def setup_browser(self):
        """Setup browser for OAuth flow using selected profile"""
        try:
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.initializing_browser_setup') if self.translator else 'Initializing browser setup...'}{Style.RESET_ALL}")
            
            # Platform-specific initialization
            platform_name = platform.system().lower()
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.detected_platform', platform=platform_name) if self.translator else f'Detected platform: {platform_name}'}{Style.RESET_ALL}")
            
            # 从配置中获取浏览器类型
            config = get_config(self.translator)
            browser_type = config.get('Browser', 'default_browser', fallback='chrome')
            
            # Get browser paths and user data directory
            user_data_dir = self._get_user_data_directory()
            browser_path = self._get_browser_path()
            
            if not browser_path:
                error_msg = (
                    f"{self.translator.get('oauth.no_compatible_browser_found') if self.translator else 'No compatible browser found. Please install Google Chrome or Chromium.'}" + 
                    "\n" +
                    f"{self.translator.get('oauth.supported_browsers', platform=platform_name)}\n" + 
                    "- Windows: Google Chrome, Chromium\n" +
                    "- macOS: Google Chrome, Chromium\n" +
                    "- Linux: Google Chrome, Chromium, google-chrome-stable"
                )
                raise Exception(error_msg)
            
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.found_browser_data_directory', path=user_data_dir) if self.translator else f'Found browser data directory: {user_data_dir}'}{Style.RESET_ALL}")
            
            # Show warning about closing browser first - 使用动态提示
            if self.translator:
                warning_msg = self.translator.get('oauth.warning_browser_close', browser=browser_type)
            else:
                warning_msg = f'Warning: This will close all running {browser_type} processes'
            
            print(f"\n{Fore.YELLOW}{EMOJI['WARNING']} {warning_msg}{Style.RESET_ALL}")
            
            choice = input(f"{Fore.YELLOW} {self.translator.get('menu.continue_prompt', choices='y/N')} {Style.RESET_ALL}").lower()
            if choice != 'y':
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('menu.operation_cancelled_by_user') if self.translator else 'Operation cancelled by user'}{Style.RESET_ALL}")
                return False

            # Kill existing browser processes
            self._kill_browser_processes()
            
            # Let user select a profile
            if not self._select_profile():
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('menu.operation_cancelled_by_user') if self.translator else 'Operation cancelled by user'}{Style.RESET_ALL}")
                return False
            
            # Configure browser options
            co = self._configure_browser_options(browser_path, user_data_dir, self.selected_profile)
            
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.starting_browser', path=browser_path) if self.translator else f'Starting browser at: {browser_path}'}{Style.RESET_ALL}")
            self.browser = ChromiumPage(co)
            
            # Verify browser launched successfully
            if not self.browser:
                raise Exception(f"{self.translator.get('oauth.browser_failed_to_start', error=str(e)) if self.translator else 'Failed to initialize browser instance'}")
            
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('oauth.browser_setup_completed') if self.translator else 'Browser setup completed successfully'}{Style.RESET_ALL}")
            return True
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.browser_setup_failed', error=str(e)) if self.translator else f'Browser setup failed: {str(e)}'}{Style.RESET_ALL}")
            if "DevToolsActivePort file doesn't exist" in str(e):
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('oauth.try_running_without_sudo_admin') if self.translator else 'Try running without sudo/administrator privileges'}{Style.RESET_ALL}")
            elif "Chrome failed to start" in str(e):
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('oauth.make_sure_chrome_chromium_is_properly_installed') if self.translator else 'Make sure Chrome/Chromium is properly installed'}{Style.RESET_ALL}")
                if platform_name == 'linux':
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('oauth.try_install_chromium') if self.translator else 'Try: sudo apt install chromium-browser'}{Style.RESET_ALL}")
            return False

    def _kill_browser_processes(self):
        """Kill existing browser processes based on platform and browser type"""
        try:
            # 从配置中获取浏览器类型
            config = get_config(self.translator)
            browser_type = config.get('Browser', 'default_browser', fallback='chrome')
            browser_type = browser_type.lower()
            
            # 根据浏览器类型和平台定义要关闭的进程
            browser_processes = {
                'chrome': {
                    'win': ['chrome.exe', 'chromium.exe'],
                    'linux': ['chrome', 'chromium', 'chromium-browser', 'google-chrome-stable'],
                    'mac': ['Chrome', 'Chromium']
                },
                'brave': {
                    'win': ['brave.exe'],
                    'linux': ['brave', 'brave-browser'],
                    'mac': ['Brave Browser']
                },
                'edge': {
                    'win': ['msedge.exe'],
                    'linux': ['msedge'],
                    'mac': ['Microsoft Edge']
                },
                'firefox': {
                    'win': ['firefox.exe'],
                    'linux': ['firefox'],
                    'mac': ['Firefox']
                },
                'opera': {
                    'win': ['opera.exe', 'launcher.exe'],
                    'linux': ['opera'],
                    'mac': ['Opera']
                }
            }
            
            # 获取平台类型
            if os.name == 'nt':
                platform_type = 'win'
            elif sys.platform == 'darwin':
                platform_type = 'mac'
            else:
                platform_type = 'linux'
            
            # 获取要关闭的进程列表
            processes = browser_processes.get(browser_type, browser_processes['chrome']).get(platform_type, [])
            
            if self.translator:
                print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.killing_browser_processes', browser=browser_type) if self.translator else f'Killing {browser_type} processes...'}{Style.RESET_ALL}")
            
            # 根据平台关闭进程
            if os.name == 'nt':  # Windows
                for proc in processes:
                    os.system(f'taskkill /f /im {proc} >nul 2>&1')
            else:  # Linux/Mac
                for proc in processes:
                    os.system(f'pkill -f {proc} >/dev/null 2>&1')
            
            time.sleep(1)  # Wait for processes to close
        except Exception as e:
            print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('oauth.warning_could_not_kill_existing_browser_processes', error=str(e)) if self.translator else f'Warning: Could not kill existing browser processes: {e}'}{Style.RESET_ALL}")

    def _get_user_data_directory(self):
        """Get the default user data directory based on browser type and platform"""
        try:
            # 从配置中获取浏览器类型
            config = get_config(self.translator)
            browser_type = config.get('Browser', 'default_browser', fallback='chrome')
            browser_type = browser_type.lower()
            
            # 根据操作系统和浏览器类型获取用户数据目录
            if os.name == 'nt':  # Windows
                user_data_dirs = {
                    'chrome': os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'User Data'),
                    'brave': os.path.join(os.environ.get('LOCALAPPDATA', ''), 'BraveSoftware', 'Brave-Browser', 'User Data'),
                    'edge': os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Edge', 'User Data'),
                    'firefox': os.path.join(os.environ.get('APPDATA', ''), 'Mozilla', 'Firefox', 'Profiles'),
                    'opera': os.path.join(os.environ.get('APPDATA', ''), 'Opera Software', 'Opera Stable'),
                    'operagx': os.path.join(os.environ.get('APPDATA', ''), 'Opera Software', 'Opera GX Stable')
                }
            elif sys.platform == 'darwin':  # macOS
                user_data_dirs = {
                    'chrome': os.path.expanduser('~/Library/Application Support/Google/Chrome'),
                    'brave': os.path.expanduser('~/Library/Application Support/BraveSoftware/Brave-Browser'),
                    'edge': os.path.expanduser('~/Library/Application Support/Microsoft Edge'),
                    'firefox': os.path.expanduser('~/Library/Application Support/Firefox/Profiles'),
                    'opera': os.path.expanduser('~/Library/Application Support/com.operasoftware.Opera'),
                    'operagx': os.path.expanduser('~/Library/Application Support/com.operasoftware.OperaGX')
                }
            else:  # Linux
                user_data_dirs = {
                    'chrome': os.path.expanduser('~/.config/google-chrome'),
                    'brave': os.path.expanduser('~/.config/BraveSoftware/Brave-Browser'),
                    'edge': os.path.expanduser('~/.config/microsoft-edge'),
                    'firefox': os.path.expanduser('~/.mozilla/firefox'),
                    'opera': os.path.expanduser('~/.config/opera'),
                    'operagx': os.path.expanduser('~/.config/opera-gx')
                }
            
            # 获取选定浏览器的用户数据目录，如果找不到则使用 Chrome 的
            user_data_dir = user_data_dirs.get(browser_type)
            
            if user_data_dir and os.path.exists(user_data_dir):
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('oauth.found_browser_user_data_dir', browser=browser_type, path=user_data_dir) if self.translator else f'Found {browser_type} user data directory: {user_data_dir}'}{Style.RESET_ALL}")
                return user_data_dir
            else:
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('oauth.user_data_dir_not_found', browser=browser_type, path=user_data_dir) if self.translator else f'{browser_type} user data directory not found at {user_data_dir}, will try Chrome instead'}{Style.RESET_ALL}")
                return user_data_dirs['chrome']  # 回退到 Chrome 目录
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.error_getting_user_data_directory', error=str(e)) if self.translator else f'Error getting user data directory: {e}'}{Style.RESET_ALL}")
            # 在出错时提供一个默认目录
            if os.name == 'nt':
                return os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'User Data')
            elif sys.platform == 'darwin':
                return os.path.expanduser('~/Library/Application Support/Google/Chrome')
            else:
                return os.path.expanduser('~/.config/google-chrome')

    def _get_browser_path(self):
        """Get appropriate browser path based on platform and selected browser type"""
        try:
            # 从配置中获取浏览器类型
            config = get_config(self.translator)
            browser_type = config.get('Browser', 'default_browser', fallback='chrome')
            browser_type = browser_type.lower()
            
            # 首先检查配置中是否有明确指定的浏览器路径
            browser_path = config.get('Browser', f'{browser_type}_path', fallback=None)
            if browser_path and os.path.exists(browser_path):
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('oauth.using_configured_browser_path', browser=browser_type, path=browser_path) if self.translator else f'Using configured {browser_type} path: {browser_path}'}{Style.RESET_ALL}")
                return browser_path
            
            # 尝试获取默认路径
            browser_path = get_default_browser_path(browser_type)
            if browser_path and os.path.exists(browser_path):
                return browser_path
            
            print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('oauth.searching_for_alternative_browser_installations') if self.translator else 'Searching for alternative browser installations...'}{Style.RESET_ALL}")
            
            # 如果未找到配置中指定的浏览器，则尝试查找其他兼容浏览器
            if os.name == 'nt':  # Windows
                possible_paths = []
                if browser_type == 'brave':
                    possible_paths = [
                        os.path.join(os.environ.get('PROGRAMFILES', ''), 'BraveSoftware', 'Brave-Browser', 'Application', 'brave.exe'),
                        os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'BraveSoftware', 'Brave-Browser', 'Application', 'brave.exe'),
                        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'BraveSoftware', 'Brave-Browser', 'Application', 'brave.exe')
                    ]
                elif browser_type == 'edge':
                    possible_paths = [
                        os.path.join(os.environ.get('PROGRAMFILES', ''), 'Microsoft', 'Edge', 'Application', 'msedge.exe'),
                        os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Microsoft', 'Edge', 'Application', 'msedge.exe')
                    ]
                elif browser_type == 'firefox':
                    possible_paths = [
                        os.path.join(os.environ.get('PROGRAMFILES', ''), 'Mozilla Firefox', 'firefox.exe'),
                        os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Mozilla Firefox', 'firefox.exe')
                    ]
                elif browser_type == 'opera':
                    possible_paths = [
                        os.path.join(os.environ.get('PROGRAMFILES', ''), 'Opera', 'opera.exe'),
                        os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Opera', 'opera.exe'),
                        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Opera', 'launcher.exe'),
                        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Opera', 'opera.exe'),
                        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Opera GX', 'launcher.exe'),
                        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Opera GX', 'opera.exe')
                    ]
                else:  # 默认为 Chrome
                    possible_paths = [
                        os.path.join(os.environ.get('PROGRAMFILES', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
                        os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
                        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'Application', 'chrome.exe')
                    ]
                
            elif sys.platform == 'darwin':  # macOS
                possible_paths = []
                if browser_type == 'brave':
                    possible_paths = ['/Applications/Brave Browser.app/Contents/MacOS/Brave Browser']
                elif browser_type == 'edge':
                    possible_paths = ['/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge']
                elif browser_type == 'firefox':
                    possible_paths = ['/Applications/Firefox.app/Contents/MacOS/firefox']
                else:  # 默认为 Chrome
                    possible_paths = ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome']
                
            else:  # Linux
                possible_paths = []
                if browser_type == 'brave':
                    possible_paths = ['/usr/bin/brave-browser', '/usr/bin/brave']
                elif browser_type == 'edge':
                    possible_paths = ['/usr/bin/microsoft-edge']
                elif browser_type == 'firefox':
                    possible_paths = ['/usr/bin/firefox']
                else:  # 默认为 Chrome
                    possible_paths = [
                        '/usr/bin/google-chrome-stable',  # 优先检查 google-chrome-stable
                        '/usr/bin/google-chrome',
                        '/usr/bin/chromium',
                        '/usr/bin/chromium-browser'
                    ]
                
            # 检查每个可能的路径
            for path in possible_paths:
                if os.path.exists(path):
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('oauth.found_browser_at', path=path) if self.translator else f'Found browser at: {path}'}{Style.RESET_ALL}")
                    return path
            
            # 如果找不到指定浏览器，则尝试使用 Chrome
            if browser_type != 'chrome':
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('oauth.browser_not_found_trying_chrome', browser=browser_type) if self.translator else f'Could not find {browser_type}, trying Chrome instead'}{Style.RESET_ALL}")
                return self._get_chrome_path()
            
            return None
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.error_finding_browser_path', error=str(e)) if self.translator else f'Error finding browser path: {e}'}{Style.RESET_ALL}")
            return None

    def _configure_browser_options(self, browser_path, user_data_dir, active_profile):
        """Configure browser options based on platform"""
        try:
            co = ChromiumOptions()
            co.set_paths(browser_path=browser_path, user_data_path=user_data_dir)
            co.set_argument(f'--profile-directory={active_profile}')

            # 自动选择一个可用的端口，避免端口冲突
            co.auto_port()
            # Basic options
            co.set_argument('--no-first-run')
            co.set_argument('--no-default-browser-check')
            co.set_argument('--disable-gpu')
            
            # Platform-specific options
            if sys.platform.startswith('linux'):
                co.set_argument('--no-sandbox')
                co.set_argument('--disable-dev-shm-usage')
                co.set_argument('--disable-setuid-sandbox')
            elif sys.platform == 'darwin':
                co.set_argument('--disable-gpu-compositing')
            elif os.name == 'nt':
                co.set_argument('--disable-features=TranslateUI')
                co.set_argument('--disable-features=RendererCodeIntegrity')
            
            return co
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.error_configuring_browser_options', error=str(e)) if self.translator else f'Error configuring browser options: {e}'}{Style.RESET_ALL}")
            raise

    def _fix_chrome_permissions(self, user_data_dir):
        """Fix permissions for Chrome user data directory"""
        try:
            if sys.platform == 'darwin':  # macOS
                import subprocess
                import pwd
                
                # Get current user
                current_user = pwd.getpwuid(os.getuid()).pw_name
                
                # Fix permissions for Chrome directory
                chrome_dir = os.path.expanduser('~/Library/Application Support/Google/Chrome')
                if os.path.exists(chrome_dir):
                    subprocess.run(['chmod', '-R', 'u+rwX', chrome_dir])
                    subprocess.run(['chown', '-R', f'{current_user}:staff', chrome_dir])
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('oauth.chrome_permissions_fixed') if self.translator else 'Fixed Chrome user data directory permissions'}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('oauth.chrome_permissions_fix_failed', error=str(e)) if self.translator else f'Failed to fix Chrome permissions: {str(e)}'}{Style.RESET_ALL}")

    def handle_google_auth(self):
        """Handle Google OAuth authentication"""
        try:
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.google_start') if self.translator else 'Starting Google OAuth authentication...'}{Style.RESET_ALL}")
            
            # Setup browser
            if not self.setup_browser():
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.browser_failed') if self.translator else 'Browser failed to initialize'}{Style.RESET_ALL}")
                return False, None
            
            # Get user data directory for later use
            user_data_dir = self._get_user_data_directory()
            
            # Navigate to auth URL
            try:
                print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.navigating_to_authentication_page') if self.translator else 'Navigating to authentication page...'}{Style.RESET_ALL}")
                self.browser.get("https://authenticator.cursor.sh/sign-up")
                time.sleep(get_random_wait_time(self.config, 'page_load_wait'))
                
                # Look for Google auth button
                selectors = [
                    "//a[contains(@href,'GoogleOAuth')]",
                    "//a[contains(@class,'auth-method-button') and contains(@href,'GoogleOAuth')]",
                    "(//a[contains(@class,'auth-method-button')])[1]"  # First auth button as fallback
                ]
                
                auth_btn = None
                for selector in selectors:
                    try:
                        auth_btn = self.browser.ele(f"xpath:{selector}", timeout=12)
                        if auth_btn: #and auth_btn.is_displayed():
                            break
                    except:
                        continue
                
                if not auth_btn:
                    raise Exception("Could not find Google authentication button")
                
                # Click the button and wait for page load
                print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.starting_google_authentication') if self.translator else 'Starting Google authentication...'}{Style.RESET_ALL}")
                auth_btn.click()
                time.sleep(get_random_wait_time(self.config, 'page_load_wait'))
                
                # Check if we're on account selection page
                if "accounts.google.com" in self.browser.url:
                    print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.please_select_your_google_account_to_continue') if self.translator else 'Please select your Google account to continue...'}{Style.RESET_ALL}")
                    
                    # 获取配置中是否启用 alert 选项
                    config = get_config(self.translator)
                    show_alert = config.getboolean('OAuth', 'show_selection_alert', fallback=False)
                    
                    if show_alert:
                        alert_message = self.translator.get('oauth.please_select_your_google_account_to_continue') if self.translator else 'Please select your Google account to continue with Cursor authentication'
                        try:
                            self.browser.run_js(f"""
                            alert('{alert_message}');
                            """)
                        except:
                            pass  # Alert is optional
                
                # Wait for authentication to complete
                auth_info = self._wait_for_auth()
                if not auth_info:
                    print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.timeout') if self.translator else 'Timeout'}{Style.RESET_ALL}")
                    return False, None
                
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('oauth.success') if self.translator else 'Success'}{Style.RESET_ALL}")
                return True, auth_info
                
            except Exception as e:
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.authentication_error', error=str(e)) if self.translator else f'Authentication error: {str(e)}'}{Style.RESET_ALL}")
                return False, None
            finally:
                try:
                    if self.browser:
                        self.browser.quit()
                        # Fix Chrome permissions after browser is closed
                        self._fix_chrome_permissions(user_data_dir)
                except:
                    pass
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.failed', error=str(e))}{Style.RESET_ALL}")
            return False, None

    def _wait_for_auth(self):
        """Wait for authentication to complete and extract auth info"""
        try:
            max_wait = 300  # 5 minutes
            start_time = time.time()
            check_interval = 2  # Check every 2 seconds
            
            print(f"{Fore.CYAN}{EMOJI['WAIT']} {self.translator.get('oauth.waiting_for_authentication', timeout='5 minutes') if self.translator else 'Waiting for authentication (timeout: 5 minutes)'}{Style.RESET_ALL}")
            
            while time.time() - start_time < max_wait:
                try:
                    # Check for authentication cookies
                    cookies = self.browser.cookies()
                    
                    for cookie in cookies:
                        if cookie.get("name") == "WorkosCursorSessionToken":
                            value = cookie.get("value", "")
                            token = get_token_from_cookie(value, self.translator)
                            if token:
                                # Get email from settings page
                                print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.authentication_successful_getting_account_info') if self.translator else 'Authentication successful, getting account info...'}{Style.RESET_ALL}")
                                self.browser.get("https://www.cursor.com/settings")
                                time.sleep(3)
                                
                                email = None
                                try:
                                    email_element = self.browser.ele("css:div[class='flex w-full flex-col gap-2'] div:nth-child(2) p:nth-child(2)")
                                    if email_element:
                                        email = email_element.text
                                        print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.found_email', email=email) if self.translator else f'Found email: {email}'}{Style.RESET_ALL}")
                                except:
                                    email = "user@cursor.sh"  # Fallback email
                                
                                # Check usage count
                                try:
                                    usage_element = self.browser.ele("css:div[class='flex flex-col gap-4 lg:flex-row'] div:nth-child(1) div:nth-child(1) span:nth-child(2)")
                                    if usage_element:
                                        usage_text = usage_element.text
                                        print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.usage_count', usage=usage_text) if self.translator else f'Usage count: {usage_text}'}{Style.RESET_ALL}")
                                        
                                        def check_usage_limits(usage_str):
                                            try:
                                                parts = usage_str.split('/')
                                                if len(parts) != 2:
                                                    return False
                                                current = int(parts[0].strip())
                                                limit = int(parts[1].strip())
                                                return (limit == 50 and current >= 50) or (limit == 150 and current >= 150)
                                            except:
                                                return False

                                        if check_usage_limits(usage_text):
                                            print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('oauth.account_has_reached_maximum_usage', deleting='deleting') if self.translator else 'Account has reached maximum usage, deleting...'}{Style.RESET_ALL}")
                                            if self._delete_current_account():
                                                print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.starting_new_authentication_process') if self.translator else 'Starting new authentication process...'}{Style.RESET_ALL}")
                                                if self.auth_type == "google":
                                                    return self.handle_google_auth()
                                                else:
                                                    return self.handle_github_auth()
                                            else:
                                                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.failed_to_delete_expired_account') if self.translator else 'Failed to delete expired account'}{Style.RESET_ALL}")
                                        else:
                                            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('oauth.account_is_still_valid', usage=usage_text) if self.translator else f'Account is still valid (Usage: {usage_text})'}{Style.RESET_ALL}")
                                except Exception as e:
                                    print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('oauth.could_not_check_usage_count', error=str(e)) if self.translator else f'Could not check usage count: {str(e)}'}{Style.RESET_ALL}")
                                
                                return {"email": email, "token": token}
                    
                    # Also check URL as backup
                    if "cursor.com/settings" in self.browser.url:
                        print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.detected_successful_login') if self.translator else 'Detected successful login'}{Style.RESET_ALL}")
                    
                except Exception as e:
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('oauth.waiting_for_authentication', error=str(e)) if self.translator else f'Waiting for authentication... ({str(e)})'}{Style.RESET_ALL}")
                
                time.sleep(check_interval)
            
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.authentication_timeout') if self.translator else 'Authentication timeout'}{Style.RESET_ALL}")
            return None
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.error_waiting_for_authentication', error=str(e)) if self.translator else f'Error while waiting for authentication: {str(e)}'}{Style.RESET_ALL}")
            return None
        
    def handle_github_auth(self):
        """Handle GitHub OAuth authentication"""
        try:
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.github_start')}{Style.RESET_ALL}")
            
            # Setup browser
            if not self.setup_browser():
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.browser_failed', error=str(e)) if self.translator else 'Browser failed to initialize'}{Style.RESET_ALL}")
                return False, None
            
            # Navigate to auth URL
            try:
                print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.navigating_to_authentication_page') if self.translator else 'Navigating to authentication page...'}{Style.RESET_ALL}")
                self.browser.get("https://authenticator.cursor.sh/sign-up")
                time.sleep(get_random_wait_time(self.config, 'page_load_wait'))
                
                # Look for GitHub auth button
                selectors = [
                    "//a[contains(@href,'GitHubOAuth')]",
                    "//a[contains(@class,'auth-method-button') and contains(@href,'GitHubOAuth')]",
                    "(//a[contains(@class,'auth-method-button')])[2]"  # Second auth button as fallback
                ]
                
                auth_btn = None
                for selector in selectors:
                    try:
                        auth_btn = self.browser.ele(f"xpath:{selector}", timeout=2)
                        if auth_btn and auth_btn.is_displayed():
                            break
                    except:
                        continue
                
                if not auth_btn:
                    raise Exception("Could not find GitHub authentication button")
                
                # Click the button and wait for page load
                print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.starting_github_authentication') if self.translator else 'Starting GitHub authentication...'}{Style.RESET_ALL}")
                auth_btn.click()
                time.sleep(get_random_wait_time(self.config, 'page_load_wait'))
                
                # Wait for authentication to complete
                auth_info = self._wait_for_auth()
                if not auth_info:
                    print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.timeout') if self.translator else 'Timeout'}{Style.RESET_ALL}")
                    return False, None
                
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('oauth.success')}{Style.RESET_ALL}")
                return True, auth_info
                
            except Exception as e:
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.authentication_error', error=str(e)) if self.translator else f'Authentication error: {str(e)}'}{Style.RESET_ALL}")
                return False, None
            finally:
                try:
                    if self.browser:
                        self.browser.quit()
                except:
                    pass
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.failed', error=str(e))}{Style.RESET_ALL}")
            return False, None
        
    def _handle_oauth(self, auth_type):
        """Handle OAuth authentication for both Google and GitHub
        
        Args:
            auth_type (str): Type of authentication ('google' or 'github')
        """
        try:
            if not self.setup_browser():
                return False, None
                
            # Navigate to auth URL
            self.browser.get("https://authenticator.cursor.sh/sign-up")
            time.sleep(get_random_wait_time(self.config, 'page_load_wait'))
            
            # Set selectors based on auth type
            if auth_type == "google":
                selectors = [
                    "//a[@class='rt-reset rt-BaseButton rt-r-size-3 rt-variant-surface rt-high-contrast rt-Button auth-method-button_AuthMethodButton__irESX'][contains(@href,'GoogleOAuth')]",
                    "(//a[@class='rt-reset rt-BaseButton rt-r-size-3 rt-variant-surface rt-high-contrast rt-Button auth-method-button_AuthMethodButton__irESX'])[1]"
                ]
            else:  # github
                selectors = [
                    "(//a[@class='rt-reset rt-BaseButton rt-r-size-3 rt-variant-surface rt-high-contrast rt-Button auth-method-button_AuthMethodButton__irESX'])[2]"
                ]
            
            # Wait for the button to be available
            auth_btn = None
            max_button_wait = 30  # 30 seconds
            button_start_time = time.time()
            
            while time.time() - button_start_time < max_button_wait:
                for selector in selectors:
                    try:
                        auth_btn = self.browser.ele(f"xpath:{selector}", timeout=1)
                        if auth_btn and auth_btn.is_displayed():
                            break
                    except:
                        continue
                if auth_btn:
                    break
                time.sleep(1)
            
            if auth_btn:
                # Click the button and wait for page load
                auth_btn.click()
                time.sleep(get_random_wait_time(self.config, 'page_load_wait'))
                
                # Check if we're on account selection page
                if auth_type == "google" and "accounts.google.com" in self.browser.url:
                    alert_message = self.translator.get('oauth.please_select_your_google_account_to_continue') if self.translator else 'Please select your Google account to continue with Cursor authentication'
                    try:
                        self.browser.run_js(f"""
                        alert('{alert_message}');
                        """)
                    except Exception as e:
                        print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('oauth.alert_display_failed', error=str(e)) if self.translator else f'Alert display failed: {str(e)}'}{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.please_select_your_google_account_manually_to_continue_with_cursor_authentication') if self.translator else 'Please select your Google account manually to continue with Cursor authentication...'}{Style.RESET_ALL}")
                
                print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.waiting_for_authentication_to_complete') if self.translator else 'Waiting for authentication to complete...'}{Style.RESET_ALL}")
                
                # Wait for authentication to complete
                max_wait = 300  # 5 minutes
                start_time = time.time()
                last_url = self.browser.url
                
                print(f"{Fore.CYAN}{EMOJI['WAIT']} {self.translator.get('oauth.checking_authentication_status') if self.translator else 'Checking authentication status...'}{Style.RESET_ALL}")
                
                while time.time() - start_time < max_wait:
                    try:
                        # Check for authentication cookies
                        cookies = self.browser.cookies()
                        
                        for cookie in cookies:
                            if cookie.get("name") == "WorkosCursorSessionToken":
                                value = cookie.get("value", "")
                                token = get_token_from_cookie(value, self.translator)
                                if token:
                                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('oauth.authentication_successful') if self.translator else 'Authentication successful!'}{Style.RESET_ALL}")
                                    # Navigate to settings page
                                    print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.navigating_to_settings_page') if self.translator else 'Navigating to settings page...'}{Style.RESET_ALL}")
                                    self.browser.get("https://www.cursor.com/settings")
                                    time.sleep(3)  # Wait for settings page to load
                                    
                                    # Get email from settings page
                                    try:
                                        email_element = self.browser.ele("css:div[class='flex w-full flex-col gap-2'] div:nth-child(2) p:nth-child(2)")
                                        if email_element:
                                            actual_email = email_element.text
                                            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.found_email', email=actual_email) if self.translator else f'Found email: {actual_email}'}{Style.RESET_ALL}")
                                    except Exception as e:
                                        print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('oauth.could_not_find_email', error=str(e)) if self.translator else f'Could not find email: {str(e)}'}{Style.RESET_ALL}")
                                        actual_email = "user@cursor.sh"
                                    
                                    # Check usage count
                                    try:
                                        usage_element = self.browser.ele("css:div[class='flex flex-col gap-4 lg:flex-row'] div:nth-child(1) div:nth-child(1) span:nth-child(2)")
                                        if usage_element:
                                            usage_text = usage_element.text
                                            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.usage_count', usage=usage_text) if self.translator else f'Usage count: {usage_text}'}{Style.RESET_ALL}")
                                            
                                            def check_usage_limits(usage_str):
                                                try:
                                                    parts = usage_str.split('/')
                                                    if len(parts) != 2:
                                                        return False
                                                    current = int(parts[0].strip())
                                                    limit = int(parts[1].strip())
                                                    return (limit == 50 and current >= 50) or (limit == 150 and current >= 150)
                                                except:
                                                    return False

                                            if check_usage_limits(usage_text):
                                                print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('oauth.account_has_reached_maximum_usage', deleting='deleting') if self.translator else 'Account has reached maximum usage, deleting...'}{Style.RESET_ALL}")
                                                if self._delete_current_account():
                                                    print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.starting_new_authentication_process') if self.translator else 'Starting new authentication process...'}{Style.RESET_ALL}")
                                                    if self.auth_type == "google":
                                                        return self.handle_google_auth()
                                                    else:
                                                        return self.handle_github_auth()
                                                else:
                                                    print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.failed_to_delete_expired_account') if self.translator else 'Failed to delete expired account'}{Style.RESET_ALL}")
                                            else:
                                                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('oauth.account_is_still_valid', usage=usage_text) if self.translator else f'Account is still valid (Usage: {usage_text})'}{Style.RESET_ALL}")
                                    except Exception as e:
                                        print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('oauth.could_not_check_usage_count', error=str(e)) if self.translator else f'Could not check usage count: {str(e)}'}{Style.RESET_ALL}")
                                    
                                    # Remove the browser stay open prompt and input wait
                                    return True, {"email": actual_email, "token": token}
                        
                        # Also check URL as backup
                        current_url = self.browser.url
                        if "cursor.com/settings" in current_url:
                            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('oauth.already_on_settings_page') if self.translator else 'Already on settings page!'}{Style.RESET_ALL}")
                            time.sleep(1)
                            cookies = self.browser.cookies()
                            for cookie in cookies:
                                if cookie.get("name") == "WorkosCursorSessionToken":
                                    value = cookie.get("value", "")
                                    token = get_token_from_cookie(value, self.translator)
                                    if token:
                                        # Get email and check usage here too
                                        try:
                                            email_element = self.browser.ele("css:div[class='flex w-full flex-col gap-2'] div:nth-child(2) p:nth-child(2)")
                                            if email_element:
                                                actual_email = email_element.text
                                                print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.found_email', email=actual_email) if self.translator else f'Found email: {actual_email}'}{Style.RESET_ALL}")
                                        except Exception as e:
                                            print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('oauth.could_not_find_email', error=str(e)) if self.translator else f'Could not find email: {str(e)}'}{Style.RESET_ALL}")
                                            actual_email = "user@cursor.sh"
                                        
                                        # Check usage count
                                        try:
                                            usage_element = self.browser.ele("css:div[class='flex flex-col gap-4 lg:flex-row'] div:nth-child(1) div:nth-child(1) span:nth-child(2)")
                                            if usage_element:
                                                usage_text = usage_element.text
                                                print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.usage_count', usage=usage_text) if self.translator else f'Usage count: {usage_text}'}{Style.RESET_ALL}")
                                                
                                                def check_usage_limits(usage_str):
                                                    try:
                                                        parts = usage_str.split('/')
                                                        if len(parts) != 2:
                                                            return False
                                                        current = int(parts[0].strip())
                                                        limit = int(parts[1].strip())
                                                        return (limit == 50 and current >= 50) or (limit == 150 and current >= 150)
                                                    except:
                                                        return False

                                            if check_usage_limits(usage_text):
                                                print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('oauth.account_has_reached_maximum_usage', deleting='deleting') if self.translator else 'Account has reached maximum usage, deleting...'}{Style.RESET_ALL}")
                                                if self._delete_current_account():
                                                    print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.starting_new_authentication_process') if self.translator else 'Starting new authentication process...'}{Style.RESET_ALL}")
                                                    if self.auth_type == "google":
                                                        return self.handle_google_auth()
                                                    else:
                                                        return self.handle_github_auth()
                                                else:
                                                    print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.failed_to_delete_expired_account') if self.translator else 'Failed to delete expired account'}{Style.RESET_ALL}")
                                            else:
                                                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('oauth.account_is_still_valid', usage=usage_text) if self.translator else f'Account is still valid (Usage: {usage_text})'}{Style.RESET_ALL}")
                                        except Exception as e:
                                            print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('oauth.could_not_check_usage_count', error=str(e)) if self.translator else f'Could not check usage count: {str(e)}'}{Style.RESET_ALL}")
                                        
                                        # Remove the browser stay open prompt and input wait
                                        return True, {"email": actual_email, "token": token}
                        elif current_url != last_url:
                            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.page_changed_checking_auth') if self.translator else 'Page changed, checking auth...'}{Style.RESET_ALL}")
                            last_url = current_url
                            time.sleep(get_random_wait_time(self.config, 'page_load_wait'))
                    except Exception as e:
                        print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('oauth.status_check_error', error=str(e)) if self.translator else f'Status check error: {str(e)}'}{Style.RESET_ALL}")
                        time.sleep(1)
                        continue
                    time.sleep(1)
                    
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.authentication_timeout') if self.translator else 'Authentication timeout'}{Style.RESET_ALL}")
                return False, None
                
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.authentication_button_not_found') if self.translator else 'Authentication button not found'}{Style.RESET_ALL}")
            return False, None
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.authentication_failed', error=str(e)) if self.translator else f'Authentication failed: {str(e)}'}{Style.RESET_ALL}")
            return False, None
        finally:
            if self.browser:
                self.browser.quit()

    def _extract_auth_info(self):
        """Extract authentication information after successful OAuth"""
        try:
            # Get cookies with retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    cookies = self.browser.cookies()
                    if cookies:
                        break
                    time.sleep(1)
                except:
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(1)
            
            # Debug cookie information
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.found_cookies', count=len(cookies)) if self.translator else f'Found {len(cookies)} cookies'}{Style.RESET_ALL}")
            
            email = None
            token = None
            
            for cookie in cookies:
                name = cookie.get("name", "")
                if name == "WorkosCursorSessionToken":
                    try:
                        value = cookie.get("value", "")
                        token = get_token_from_cookie(value, self.translator)
                    except Exception as e:
                        error_message = f'Failed to extract auth info: {str(e)}' if not self.translator else self.translator.get('oauth.failed_to_extract_auth_info', error=str(e))
                        print(f"{Fore.RED}{EMOJI['ERROR']} {error_message}{Style.RESET_ALL}")
                elif name == "cursor_email":
                    email = cookie.get("value")
                    
            if email and token:
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('oauth.authentication_successful', email=email) if self.translator else f'Authentication successful - Email: {email}'}{Style.RESET_ALL}")
                return True, {"email": email, "token": token}
            else:
                missing = []
                if not email:
                    missing.append("email")
                if not token:
                    missing.append("token")
                error_message = f"Missing authentication data: {', '.join(missing)}" if not self.translator else self.translator.get('oauth.missing_authentication_data', data=', '.join(missing))
                print(f"{Fore.RED}{EMOJI['ERROR']} {error_message}{Style.RESET_ALL}")
                return False, None
            
        except Exception as e:
            error_message = f'Failed to extract auth info: {str(e)}' if not self.translator else self.translator.get('oauth.failed_to_extract_auth_info', error=str(e))
            print(f"{Fore.RED}{EMOJI['ERROR']} {error_message}{Style.RESET_ALL}")
            return False, None

    def _delete_current_account(self):
        """Delete the current account using the API"""
        try:
            delete_js = """
            function deleteAccount() {
                return new Promise((resolve, reject) => {
                    fetch('https://www.cursor.com/api/dashboard/delete-account', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        credentials: 'include'
                    })
                    .then(response => {
                        if (response.status === 200) {
                            resolve('Account deleted successfully');
                        } else {
                            reject('Failed to delete account: ' + response.status);
                        }
                    })
                    .catch(error => {
                        reject('Error: ' + error);
                    });
                });
            }
            return deleteAccount();
            """
            
            result = self.browser.run_js(delete_js)
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} Delete account result: {result}{Style.RESET_ALL}")
            
            # Navigate back to auth page
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.redirecting_to_authenticator_cursor_sh') if self.translator else 'Redirecting to authenticator.cursor.sh...'}{Style.RESET_ALL}")
            self.browser.get("https://authenticator.cursor.sh/sign-up")
            time.sleep(get_random_wait_time(self.config, 'page_load_wait'))
            
            return True
            
        except Exception as e:
            error_message = f'Failed to delete account: {str(e)}' if not self.translator else self.translator.get('oauth.failed_to_delete_account', error=str(e))
            print(f"{Fore.RED}{EMOJI['ERROR']} {error_message}{Style.RESET_ALL}")
            return False

def main(auth_type, translator=None):
    """Main function to handle OAuth authentication
    
    Args:
        auth_type (str): Type of authentication ('google' or 'github')
        translator: Translator instance for internationalization
    """
    handler = OAuthHandler(translator, auth_type)
    
    if auth_type.lower() == 'google':
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('oauth.google_start') if translator else 'Google start'}{Style.RESET_ALL}")
        success, auth_info = handler.handle_google_auth()
    elif auth_type.lower() == 'github':
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('oauth.github_start') if translator else 'Github start'}{Style.RESET_ALL}")
        success, auth_info = handler.handle_github_auth()
    else:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('oauth.invalid_authentication_type') if translator else 'Invalid authentication type'}{Style.RESET_ALL}")
        return False
        
    if success and auth_info:
        # Update Cursor authentication
        auth_manager = CursorAuth(translator)
        if auth_manager.update_auth(
            email=auth_info["email"],
            access_token=auth_info["token"],
            refresh_token=auth_info["token"],
            auth_type=auth_type
        ):
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('oauth.auth_update_success') if translator else 'Auth update success'}{Style.RESET_ALL}")
            # Close the browser after successful authentication
            if handler.browser:
                handler.browser.quit()
                print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('oauth.browser_closed') if translator else 'Browser closed'}{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('oauth.auth_update_failed') if translator else 'Auth update failed'}{Style.RESET_ALL}")
            
    return False 