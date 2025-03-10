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

# 只在 Windows 系统上导入 windll
if platform.system() == 'Windows':
    import ctypes
    # 只在 Windows 上导入 windll
    from ctypes import windll

# 初始化colorama
init()

# 定义emoji和颜色常量
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
    "UPDATE": "🔄"
}

class Translator:
    def __init__(self):
        self.translations = {}
        self.current_language = self.detect_system_language()  # 使用正确的方法名
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
            # 确保我们在 Windows 上
            if platform.system() != 'Windows':
                return 'en'
                
            # 获取键盘布局
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            threadid = user32.GetWindowThreadProcessId(hwnd, 0)
            layout_id = user32.GetKeyboardLayout(threadid) & 0xFFFF
            
            # Map language ID to our language codes
            language_map = {
                0x0409: 'en',      # English
                0x0404: 'zh_tw',   # Traditional Chinese
                0x0804: 'zh_cn',   # Simplified Chinese
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
            
            # Try to get language from LANG environment variable as fallback
            env_lang = os.getenv('LANG', '').lower()
            if 'tw' in env_lang or 'hk' in env_lang:
                return 'zh_tw'
            elif 'cn' in env_lang:
                return 'zh_cn'
            
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

# 创建翻译器实例
translator = Translator()

def print_menu():
    """打印菜单选项"""
    print(f"\n{Fore.CYAN}{EMOJI['MENU']} {translator.get('menu.title')}:{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{'─' * 40}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}0{Style.RESET_ALL}. {EMOJI['ERROR']} {translator.get('menu.exit')}")
    print(f"{Fore.GREEN}1{Style.RESET_ALL}. {EMOJI['RESET']} {translator.get('menu.reset')}")
    print(f"{Fore.GREEN}2{Style.RESET_ALL}. {EMOJI['SUCCESS']} {translator.get('menu.register')}")
    print(f"{Fore.GREEN}3{Style.RESET_ALL}. {EMOJI['SUCCESS']} {translator.get('menu.register_manual')}")
    print(f"{Fore.GREEN}4{Style.RESET_ALL}. {EMOJI['ERROR']} {translator.get('menu.quit')}")
    print(f"{Fore.GREEN}5{Style.RESET_ALL}. {EMOJI['LANG']} {translator.get('menu.select_language')}")
    print(f"{Fore.GREEN}6{Style.RESET_ALL}. {EMOJI['UPDATE']} {translator.get('menu.disable_auto_update')}")
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

def check_latest_version(auto_update=True):
    """Check if current version matches the latest release version"""
    try:
        print(f"\n{Fore.CYAN}{EMOJI['UPDATE']} {translator.get('updater.checking')}{Style.RESET_ALL}")
        
        # Get latest version from GitHub API with timeout and proper headers
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'CursorFreeVIP-Updater'
        }
        response = requests.get(
            "https://api.github.com/repos/qing-turnaround/cursor-free-vip/releases/latest",
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
        
        # 正确比较版本号
        def parse_version(version_str):
            return [int(x) for x in version_str.split('.')]
            
        current_parts = parse_version(version)
        latest_parts = parse_version(latest_version)
        
        # 检查是否需要更新（只有当最新版本真的大于当前版本时）
        needs_update = False
        for i in range(max(len(current_parts), len(latest_parts))):
            current_part = current_parts[i] if i < len(current_parts) else 0
            latest_part = latest_parts[i] if i < len(latest_parts) else 0
            
            if latest_part > current_part:
                needs_update = True
                break
            elif current_part > latest_part:
                needs_update = False
                break
        
        if needs_update:
            print(f"\n{Fore.YELLOW}{EMOJI['INFO']} {translator.get('updater.new_version_available', current=version, latest=latest_version)}{Style.RESET_ALL}")
            
            # 只有auto_update为True时才自动更新
            if auto_update:
                choice = input(f"\n{EMOJI['ARROW']} {Fore.CYAN}{translator.get('updater.prompt_update')}: (Y/n): {Style.RESET_ALL}")
                
                if choice.lower() not in ["n", "no"]:
                    try:
                        # 获取有效下载路径并提示用户
                        downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
                        download_file = f"CursorFreeVIP_{latest_version}_windows.exe"
                        download_path = os.path.join(downloads_path, download_file)
                        
                        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('updater.downloading_to', path=download_path)}{Style.RESET_ALL}")
                        
                        # Execute update command based on platform
                        if platform.system() == 'Windows':
                            update_command = 'irm https://raw.githubusercontent.com/qing-turnaround/cursor-free-vip/main/scripts/install.ps1 | iex -SkipVersionCheck'
                            print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('updater.running_command', command=update_command)}{Style.RESET_ALL}")
                            subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', update_command], check=True)
                        else:
                            # For Linux/Mac, download and execute the install script
                            install_script_url = 'https://raw.githubusercontent.com/qing-turnaround/cursor-free-vip/main/scripts/install.sh'
                            
                            # First verify the script exists
                            script_response = requests.get(install_script_url, timeout=5)
                            if script_response.status_code != 200:
                                raise Exception("Installation script not found")
                                
                            # Save and execute the script
                            with open('install.sh', 'wb') as f:
                                f.write(script_response.content)
                            
                            os.chmod('install.sh', 0o755)  # Make executable
                            subprocess.run(['./install.sh'], check=True)
                        
                        print(f"\n{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('updater.updating')}{Style.RESET_ALL}")
                        return True
                    except Exception as e:
                        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('updater.update_failed', error=str(e))}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('updater.update_skipped')}{Style.RESET_ALL}")
        else:
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('updater.latest_version')}{Style.RESET_ALL}")
            
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('updater.network_error', error=str(e))}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('updater.continue_anyway')}{Style.RESET_ALL}")
        return
        
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('updater.check_failed', error=str(e))}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('updater.continue_anyway')}{Style.RESET_ALL}")
        return

def main():
    print_logo()
    
    # 初始化配置
    from new_signup import setup_config
    config = setup_config(translator)
    if not config:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('menu.config_init_failed')}{Style.RESET_ALL}")
        return
        
    check_latest_version()  # Add version check before showing menu
    print_menu()
    
    while True:
        try:
            choice = input(f"\n{EMOJI['ARROW']} {Fore.CYAN}{translator.get('menu.input_choice', choices='0-6')}: {Style.RESET_ALL}")

            if choice == "0":
                print(f"\n{Fore.YELLOW}{EMOJI['INFO']} {translator.get('menu.exit')}...{Style.RESET_ALL}")
                print(f"{Fore.CYAN}{'═' * 50}{Style.RESET_ALL}")
                return
            elif choice == "1":
                import reset_machine_manual
                reset_machine_manual.run(translator)
                print_menu()
            elif choice == "2":
                import cursor_register
                cursor_register.main(translator)
                print_menu()
            elif choice == "3":
                import cursor_register_manual
                cursor_register_manual.main(translator)
                print_menu()
            elif choice == "4":
                import quit_cursor
                quit_cursor.quit_cursor(translator)
                print_menu()
            elif choice == "5":
                if select_language():
                    print_menu()
                continue
            elif choice == "6":
                import disable_auto_update
                disable_auto_update.run(translator)
                print_menu()
            else:
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('menu.invalid_choice')}{Style.RESET_ALL}")
                print_menu()

        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}{EMOJI['INFO']} {translator.get('menu.program_terminated')}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'═' * 50}{Style.RESET_ALL}")
            return
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('menu.error_occurred', error=str(e))}{Style.RESET_ALL}")
            print_menu()

if __name__ == "__main__":
    main()