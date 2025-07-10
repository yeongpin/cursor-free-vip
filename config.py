import os
import sys
import configparser
import logging
import tempfile
import datetime
import platform
from pathlib import Path
from typing import Optional, Dict, Any, Union, List, Tuple
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Import utils after logging setup to avoid circular imports
from utils import get_user_documents_path, get_linux_cursor_path, get_default_driver_path, get_default_browser_path

# Define emoji constants
EMOJI = {
    "INFO": "ℹ️",
    "WARNING": "⚠️",
    "ERROR": "❌",
    "SUCCESS": "✅",
    "ADMIN": "🔒",
    "ARROW": "➡️",
    "USER": "👤",
    "KEY": "🔑",
    "SETTINGS": "⚙️",
    "CONFIG": "📝"
}

# Global config cache
_config_cache = None

class ConfigManager:
    """Class to manage configuration operations"""
    
    def __init__(self, translator: Any = None):
        """Initialize ConfigManager
        
        Args:
            translator: Optional translator for internationalization
        """
        self.translator = translator
        self.config = configparser.ConfigParser()
        self.config_dir = None
        self.config_file = None
        
    def _get_message(self, key: str, fallback: str, **kwargs) -> str:
        """Get translated message or fallback
        
        Args:
            key: Translation key
            fallback: Fallback message if translation not available
            **kwargs: Format parameters for the message
            
        Returns:
            str: Translated or fallback message
        """
        if self.translator:
            return self.translator.get(key, fallback=fallback, **kwargs)
        return fallback.format(**kwargs) if kwargs else fallback
        
    def setup_config_directory(self) -> Tuple[str, str]:
        """Setup configuration directory
        
        Returns:
            Tuple[str, str]: Configuration directory and file paths
        """
        # Get documents path
        docs_path = get_user_documents_path()
        if not docs_path or not os.path.exists(docs_path):
            # If documents path not found, use current directory
            msg = self._get_message('config.documents_path_not_found', 
                                   'Documents path not found, using current directory')
            logger.warning(msg)
            print(f"{Fore.YELLOW}{EMOJI['WARNING']} {msg}{Style.RESET_ALL}")
            docs_path = os.path.abspath('.')
        
        # Normalize path
        config_dir = os.path.normpath(os.path.join(docs_path, ".cursor-free-vip"))
        config_file = os.path.normpath(os.path.join(config_dir, "config.ini"))
        
        # Create config directory
        dir_exists = os.path.exists(config_dir)
        try:
            os.makedirs(config_dir, exist_ok=True)
            if not dir_exists:
                msg = self._get_message('config.config_dir_created', 
                                       'Config directory created: {path}', path=config_dir)
                logger.info(f"Config directory created: {config_dir}")
                print(f"{Fore.CYAN}{EMOJI['INFO']} {msg}{Style.RESET_ALL}")
        except Exception as e:
            # If cannot create directory, use temporary directory
            logger.warning(f"Failed to create config directory: {e}")
            temp_dir = os.path.normpath(os.path.join(tempfile.gettempdir(), ".cursor-free-vip"))
            temp_exists = os.path.exists(temp_dir)
            config_dir = temp_dir
            config_file = os.path.normpath(os.path.join(config_dir, "config.ini"))
            
            try:
                os.makedirs(config_dir, exist_ok=True)
                if not temp_exists:
                    msg = self._get_message('config.using_temp_dir', 
                                           'Using temporary directory due to error: {path} (Error: {error})', 
                                           path=config_dir, error=str(e))
                    print(f"{Fore.YELLOW}{EMOJI['WARNING']} {msg}{Style.RESET_ALL}")
            except Exception as inner_e:
                logger.error(f"Failed to create temporary config directory: {inner_e}")
                # Last resort: use current directory
                config_dir = os.path.abspath('.')
                config_file = os.path.join(config_dir, "config.ini")
                
        self.config_dir = config_dir
        self.config_file = config_file
        return config_dir, config_file
    
    def get_default_config(self) -> Dict[str, Dict[str, Any]]:
        """Get default configuration
        
        Returns:
            Dict[str, Dict[str, Any]]: Default configuration dictionary
        """
        config_dir = self.config_dir or os.path.join(get_user_documents_path(), ".cursor-free-vip")
        
        # Default configuration
        default_config = {
            'Browser': {
                'default_browser': 'chrome',
                'chrome_path': get_default_browser_path('chrome'),
                'chrome_driver_path': get_default_driver_path('chrome'),
                'edge_path': get_default_browser_path('edge'),
                'edge_driver_path': get_default_driver_path('edge'),
                'firefox_path': get_default_browser_path('firefox'),
                'firefox_driver_path': get_default_driver_path('firefox'),
                'brave_path': get_default_browser_path('brave'),
                'brave_driver_path': get_default_driver_path('brave'),
                'opera_path': get_default_browser_path('opera'),
                'opera_driver_path': get_default_driver_path('opera'),
                'operagx_path': get_default_browser_path('operagx'),
                'operagx_driver_path': get_default_driver_path('chrome')  # Opera GX uses Chrome driver
            },
            'Turnstile': {
                'handle_turnstile_time': '2',
                'handle_turnstile_random_time': '1-3'
            },
            'Timing': {
                'min_random_time': '0.1',
                'max_random_time': '0.8',
                'page_load_wait': '0.1-0.8',
                'input_wait': '0.3-0.8',
                'submit_wait': '0.5-1.5',
                'verification_code_input': '0.1-0.3',
                'verification_success_wait': '2-3',
                'verification_retry_wait': '2-3',
                'email_check_initial_wait': '4-6',
                'email_refresh_wait': '2-4',
                'settings_page_load_wait': '1-2',
                'failed_retry_time': '0.5-1',
                'retry_interval': '8-12',
                'max_timeout': '160'
            },
            'Utils': {
                'enabled_update_check': 'True',
                'enabled_force_update': 'False',
                'enabled_account_info': 'True'
            },
            'OAuth': {
                'show_selection_alert': 'False',
                'timeout': '120',
                'max_attempts': '3'
            },
            'Token': {
                'refresh_server': 'https://token.cursorpro.com.cn',
                'enable_refresh': 'True'
            },
            'Language': {
                'current_language': '',  # Set by local system detection if empty
                'fallback_language': 'en',
                'auto_update_languages': 'True',
                'language_cache_dir': os.path.join(config_dir, "language_cache")
            }
        }

        # Add system-specific path configuration
        self._add_system_paths(default_config)
        
        return default_config
        
    def _add_system_paths(self, default_config: Dict[str, Dict[str, Any]]) -> None:
        """Add system-specific paths to the default configuration
        
        Args:
            default_config: Default configuration dictionary to update
        """
        if sys.platform == "win32":
            self._add_windows_paths(default_config)
        elif sys.platform == "darwin":
            self._add_macos_paths(default_config)
        elif sys.platform == "linux":
            self._add_linux_paths(default_config)
    
    def _add_windows_paths(self, default_config: Dict[str, Dict[str, Any]]) -> None:
        """Add Windows-specific paths to the default configuration
        
        Args:
            default_config: Default configuration dictionary to update
        """
        appdata = os.getenv("APPDATA", "")
        localappdata = os.getenv("LOCALAPPDATA", "")
        
        if not appdata or not localappdata:
            logger.warning("APPDATA or LOCALAPPDATA environment variables not found")
            appdata = os.path.expanduser("~\\AppData\\Roaming")
            localappdata = os.path.expanduser("~\\AppData\\Local")
            
        default_config['WindowsPaths'] = {
            'storage_path': os.path.join(appdata, "Cursor", "User", "globalStorage", "storage.json"),
            'sqlite_path': os.path.join(appdata, "Cursor", "User", "globalStorage", "state.vscdb"),
            'machine_id_path': os.path.join(appdata, "Cursor", "machineId"),
            'cursor_path': os.path.join(localappdata, "Programs", "Cursor", "resources", "app"),
            'updater_path': os.path.join(localappdata, "cursor-updater"),
            'update_yml_path': os.path.join(localappdata, "Programs", "Cursor", "resources", "app-update.yml"),
            'product_json_path': os.path.join(localappdata, "Programs", "Cursor", "resources", "app", "product.json")
        }
        
        # Create storage directory
        try:
            storage_dir = os.path.dirname(default_config['WindowsPaths']['storage_path'])
            os.makedirs(storage_dir, exist_ok=True)
        except Exception as e:
            logger.warning(f"Failed to create storage directory: {e}")
    
    def _add_macos_paths(self, default_config: Dict[str, Dict[str, Any]]) -> None:
        """Add macOS-specific paths to the default configuration
        
        Args:
            default_config: Default configuration dictionary to update
        """
        default_config['MacPaths'] = {
            'storage_path': os.path.abspath(os.path.expanduser("~/Library/Application Support/Cursor/User/globalStorage/storage.json")),
            'sqlite_path': os.path.abspath(os.path.expanduser("~/Library/Application Support/Cursor/User/globalStorage/state.vscdb")),
            'machine_id_path': os.path.expanduser("~/Library/Application Support/Cursor/machineId"),
            'cursor_path': "/Applications/Cursor.app/Contents/Resources/app",
            'updater_path': os.path.expanduser("~/Library/Application Support/cursor-updater"),
            'update_yml_path': "/Applications/Cursor.app/Contents/Resources/app-update.yml",
            'product_json_path': "/Applications/Cursor.app/Contents/Resources/app/product.json"
        }
        
        # Create storage directory
        try:
            storage_dir = os.path.dirname(default_config['MacPaths']['storage_path'])
            os.makedirs(storage_dir, exist_ok=True)
        except Exception as e:
            logger.warning(f"Failed to create storage directory: {e}")
    
    def _add_linux_paths(self, default_config: Dict[str, Dict[str, Any]]) -> None:
        """Add Linux-specific paths to the default configuration
        
        Args:
            default_config: Default configuration dictionary to update
        """
        # Get the actual user's home directory, handling both sudo and normal cases
        sudo_user = os.environ.get('SUDO_USER')
        current_user = sudo_user if sudo_user else (os.getenv('USER') or os.getenv('USERNAME'))
        
        if not current_user:
            current_user = os.path.expanduser('~').split('/')[-1]
        
        # Handle sudo case
        if sudo_user:
            actual_home = f"/home/{sudo_user}"
            root_home = "/root"
        else:
            actual_home = f"/home/{current_user}"
            root_home = None
        
        if not os.path.exists(actual_home):
            actual_home = os.path.expanduser("~")
        
        # Define base config directory
        config_base = os.path.join(actual_home, ".config")
        
        # Try both "Cursor" and "cursor" directory names in both user and root locations
        cursor_dir = None
        possible_paths = [
            os.path.join(config_base, "Cursor"),
            os.path.join(config_base, "cursor"),
            os.path.join(root_home, ".config", "Cursor") if root_home else None,
            os.path.join(root_home, ".config", "cursor") if root_home else None
        ]
        
        for path in possible_paths:
            if path and os.path.exists(path):
                cursor_dir = path
                break
        
        if not cursor_dir:
            msg = self._get_message('config.neither_cursor_nor_cursor_directory_found', 
                                   'Neither Cursor nor cursor directory found in {config_base}', 
                                   config_base=config_base)
            logger.warning(f"Cursor directory not found in {config_base}")
            print(f"{Fore.YELLOW}{EMOJI['WARNING']} {msg}{Style.RESET_ALL}")
            
            if root_home:
                msg = self._get_message('config.also_checked', 
                                       'Also checked {path}', 
                                       path=f'{root_home}/.config')
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {msg}{Style.RESET_ALL}")
                
            msg = self._get_message('config.please_make_sure_cursor_is_installed_and_has_been_run_at_least_once', 
                                   'Please make sure Cursor is installed and has been run at least once')
            print(f"{Fore.YELLOW}{EMOJI['INFO']} {msg}{Style.RESET_ALL}")
        
        # Define Linux paths using the found cursor directory
        storage_path = os.path.abspath(os.path.join(cursor_dir, "User/globalStorage/storage.json")) if cursor_dir else ""
        storage_dir = os.path.dirname(storage_path) if storage_path else ""
        
        # Set default Linux paths
        default_config['LinuxPaths'] = {
            'storage_path': storage_path,
            'sqlite_path': os.path.abspath(os.path.join(cursor_dir, "User/globalStorage/state.vscdb")) if cursor_dir else "",
            'machine_id_path': os.path.join(cursor_dir, "machineid") if cursor_dir else "",
            'cursor_path': get_linux_cursor_path(),
            'updater_path': os.path.join(config_base, "cursor-updater"),
            'update_yml_path': os.path.join(cursor_dir, "resources/app-update.yml") if cursor_dir else "",
            'product_json_path': os.path.join(cursor_dir, "resources/app/product.json") if cursor_dir else ""
        }
        
        # Verify paths and permissions
        self._verify_linux_paths(storage_path, storage_dir)
    
    def _verify_linux_paths(self, storage_path: str, storage_dir: str) -> None:
        """Verify Linux paths and permissions
        
        Args:
            storage_path: Path to the storage.json file
            storage_dir: Directory containing the storage.json file
        """
        try:
            # Check storage directory
            if storage_dir and not os.path.exists(storage_dir):
                msg = self._get_message('config.storage_directory_not_found', 
                                       'Storage directory not found: {storage_dir}', 
                                       storage_dir=storage_dir)
                logger.warning(f"Storage directory not found: {storage_dir}")
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {msg}{Style.RESET_ALL}")
                
                msg = self._get_message('config.please_make_sure_cursor_is_installed_and_has_been_run_at_least_once', 
                                       'Please make sure Cursor is installed and has been run at least once')
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {msg}{Style.RESET_ALL}")
            
            # Check storage.json with more detailed verification
            if storage_path and os.path.exists(storage_path):
                # Get file stats
                try:
                    stat = os.stat(storage_path)
                    msg = self._get_message('config.storage_file_found', 
                                           'Storage file found: {storage_path}', 
                                           storage_path=storage_path)
                    print(f"{Fore.GREEN}{EMOJI['INFO']} {msg}{Style.RESET_ALL}")
                    
                    # Log file details
                    file_details = [
                        ('config.file_size', 'File size: {size} bytes', {'size': stat.st_size}),
                        ('config.file_permissions', 'File permissions: {permissions}', {'permissions': oct(stat.st_mode & 0o777)}),
                        ('config.file_owner', 'File owner: {owner}', {'owner': stat.st_uid}),
                        ('config.file_group', 'File group: {group}', {'group': stat.st_gid})
                    ]
                    
                    for key, fallback, kwargs in file_details:
                        msg = self._get_message(key, fallback, **kwargs)
                        print(f"{Fore.GREEN}{EMOJI['INFO']} {msg}{Style.RESET_ALL}")
                        
                except Exception as e:
                    logger.error(f"Error getting file stats: {e}")
                    msg = self._get_message('config.error_getting_file_stats', 
                                           'Error getting file stats: {error}', 
                                           error=str(e))
                    print(f"{Fore.RED}{EMOJI['ERROR']} {msg}{Style.RESET_ALL}")
                
                # Check if file is readable and writable
                if not os.access(storage_path, os.R_OK | os.W_OK):
                    msg = self._get_message('config.permission_denied', 
                                           'Permission denied: {storage_path}', 
                                           storage_path=storage_path)
                    logger.warning(f"Permission denied: {storage_path}")
                    print(f"{Fore.RED}{EMOJI['ERROR']} {msg}{Style.RESET_ALL}")
                    
                    sudo_user = os.environ.get('SUDO_USER')
                    current_user = sudo_user if sudo_user else (os.getenv('USER') or os.getenv('USERNAME'))
                    
                    if sudo_user:
                        cmd = f"chown {sudo_user}:{sudo_user} {storage_path}"
                    else:
                        cmd = f"chown {current_user}:{current_user} {storage_path}"
                        
                    msg = self._get_message('config.try_running', 
                                           'Try running: {command}', 
                                           command=cmd)
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} {msg}{Style.RESET_ALL}")
                    
                    msg = self._get_message('config.and', 'And')
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} {msg}: chmod 644 {storage_path}{Style.RESET_ALL}")
                
                # Try to read the file to verify it's not corrupted
                try:
                    with open(storage_path, 'r') as f:
                        content = f.read()
                        if not content.strip():
                            msg = self._get_message('config.storage_file_is_empty', 
                                                   'Storage file is empty: {storage_path}', 
                                                   storage_path=storage_path)
                            logger.warning(f"Storage file is empty: {storage_path}")
                            print(f"{Fore.YELLOW}{EMOJI['WARNING']} {msg}{Style.RESET_ALL}")
                            
                            msg = self._get_message('config.the_file_might_be_corrupted_please_reinstall_cursor', 
                                                   'The file might be corrupted, please reinstall Cursor')
                            print(f"{Fore.YELLOW}{EMOJI['INFO']} {msg}{Style.RESET_ALL}")
                        else:
                            msg = self._get_message('config.storage_file_is_valid_and_contains_data', 
                                                   'Storage file is valid and contains data')
                            logger.info("Storage file is valid and contains data")
                            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {msg}{Style.RESET_ALL}")
                except Exception as e:
                    logger.error(f"Error reading storage file: {e}")
                    msg = self._get_message('config.error_reading_storage_file', 
                                           'Error reading storage file: {error}', 
                                           error=str(e))
                    print(f"{Fore.RED}{EMOJI['ERROR']} {msg}{Style.RESET_ALL}")
                    
                    msg = self._get_message('config.the_file_might_be_corrupted_please_reinstall_cursor', 
                                           'The file might be corrupted. Please reinstall Cursor')
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} {msg}{Style.RESET_ALL}")
            elif storage_path:
                msg = self._get_message('config.storage_file_not_found', 
                                       'Storage file not found: {storage_path}', 
                                       storage_path=storage_path)
                logger.warning(f"Storage file not found: {storage_path}")
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {msg}{Style.RESET_ALL}")
                
                msg = self._get_message('config.please_make_sure_cursor_is_installed_and_has_been_run_at_least_once', 
                                       'Please make sure Cursor is installed and has been run at least once')
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {msg}{Style.RESET_ALL}")
            
        except (OSError, IOError) as e:
            logger.error(f"Error checking Linux paths: {e}")
            msg = self._get_message('config.error_checking_linux_paths', 
                                   'Error checking Linux paths: {error}', 
                                   error=str(e))
            print(f"{Fore.RED}{EMOJI['ERROR']} {msg}{Style.RESET_ALL}")
    
    def setup(self) -> configparser.ConfigParser:
        """Setup configuration
        
        Returns:
            configparser.ConfigParser: Configured ConfigParser object
        """
        # Setup config directory
        self.setup_config_directory()
        
        # Get default configuration
        default_config = self.get_default_config()
        
        # Read existing config if it exists
        if os.path.exists(self.config_file):
            try:
                self.config.read(self.config_file)
                logger.info(f"Read existing configuration from {self.config_file}")
            except Exception as e:
                logger.error(f"Error reading config file: {e}")
                # Continue with default config
        
        # Update config with default values for missing sections/options
        for section, options in default_config.items():
            if not self.config.has_section(section):
                self.config.add_section(section)
                
            for option, value in options.items():
                if not self.config.has_option(section, option):
                    self.config.set(section, option, str(value))
        
        # Save config
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
            logger.info(f"Configuration saved to {self.config_file}")
        except Exception as e:
            logger.error(f"Error saving config file: {e}")
        
        return self.config

def setup_config(translator: Any = None) -> configparser.ConfigParser:
    """Setup configuration file and return config object
    
    Args:
        translator: Optional translator for internationalization
        
    Returns:
        configparser.ConfigParser: Configured ConfigParser object
    """
    try:
        config_manager = ConfigManager(translator)
        return config_manager.setup()
    except Exception as e:
        logger.error(f"Error setting up configuration: {e}")
        # Return empty config as fallback
        return configparser.ConfigParser()

def print_config(config: configparser.ConfigParser, translator: Any = None) -> None:
    """Print configuration
    
    Args:
        config: ConfigParser object
        translator: Optional translator for internationalization
    """
    if not config:
        print(f"{Fore.RED}{EMOJI['ERROR']} Configuration not available{Style.RESET_ALL}")
        return
        
    print(f"\n{Fore.CYAN}{EMOJI['CONFIG']} Configuration:{Style.RESET_ALL}")
    
    for section in config.sections():
        print(f"\n{Fore.CYAN}[{section}]{Style.RESET_ALL}")
        for option in config.options(section):
            value = config.get(section, option)
            # Mask sensitive information
            if 'token' in option.lower() or 'password' in option.lower() or 'key' in option.lower():
                value = '*' * 8
            print(f"  {option} = {value}")

def force_update_config(translator: Any = None) -> configparser.ConfigParser:
    """Force update configuration
    
    Args:
        translator: Optional translator for internationalization
        
    Returns:
        configparser.ConfigParser: Updated ConfigParser object
    """
    global _config_cache
    _config_cache = None
    
    # Create backup of existing config
    try:
        config_dir = os.path.join(get_user_documents_path(), ".cursor-free-vip")
        config_file = os.path.join(config_dir, "config.ini")
        
        if os.path.exists(config_file):
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            backup_file = f"{config_file}.{timestamp}.bak"
            
            import shutil
            shutil.copy2(config_file, backup_file)
            
            msg = translator.get('config.backup_created', fallback='Backup created: {path}', path=backup_file) if translator else f"Backup created: {backup_file}"
            logger.info(f"Config backup created: {backup_file}")
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {msg}{Style.RESET_ALL}")
    except Exception as e:
        logger.error(f"Error creating config backup: {e}")
    
    # Setup new config
    return setup_config(translator)

def get_config(translator: Any = None) -> configparser.ConfigParser:
    """Get configuration
    
    Args:
        translator: Optional translator for internationalization
        
    Returns:
        configparser.ConfigParser: ConfigParser object
    """
    global _config_cache
    
    if _config_cache is not None:
        return _config_cache
        
    try:
        config_dir = os.path.join(get_user_documents_path(), ".cursor-free-vip")
        config_file = os.path.join(config_dir, "config.ini")
        
        if os.path.exists(config_file):
            config = configparser.ConfigParser()
            config.read(config_file)
            _config_cache = config
            return config
        else:
            _config_cache = setup_config(translator)
            return _config_cache
    except Exception as e:
        logger.error(f"Error getting configuration: {e}")
        return configparser.ConfigParser()