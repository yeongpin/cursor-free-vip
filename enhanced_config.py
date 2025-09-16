

import os
import sys
import configparser
import logging
import tempfile
import datetime
import platform
import json
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, Union, List, Tuple, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum
from colorama import Fore, Style, init
import yaml

# Initialize colorama
init(autoreset=True)

# Configure enhanced logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("cursor_free_vip.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Enhanced emoji constants
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
    "CONFIG": "📝",
    "VALIDATION": "🔍",
    "BACKUP": "💾",
    "RESTORE": "🔄",
    "SECURITY": "🔐",
    "PERFORMANCE": "⚡"
}

class ConfigFormat(Enum):
    INI = "ini"
    JSON = "json"
    YAML = "yaml"

class ValidationError(Exception):
    pass

@dataclass
class BrowserConfig:
    default_browser: str = "chrome"
    chrome_path: str = ""
    chrome_driver_path: str = ""
    edge_path: str = ""
    edge_driver_path: str = ""
    firefox_path: str = ""
    firefox_driver_path: str = ""
    brave_path: str = ""
    brave_driver_path: str = ""
    opera_path: str = ""
    opera_driver_path: str = ""
    operagx_path: str = ""
    operagx_driver_path: str = ""

@dataclass
class TimingConfig:
    min_random_time: float = 0.1
    max_random_time: float = 0.8
    page_load_wait: str = "0.1-0.8"
    input_wait: str = "0.3-0.8"
    submit_wait: str = "0.5-1.5"
    verification_code_input: str = "0.1-0.3"
    verification_success_wait: str = "2-3"
    verification_retry_wait: str = "2-3"
    email_check_initial_wait: str = "4-6"
    email_refresh_wait: str = "2-4"
    settings_page_load_wait: str = "1-2"
    failed_retry_time: str = "0.5-1"
    retry_interval: str = "8-12"
    max_timeout: int = 160

@dataclass
class SecurityConfig:
    enable_encryption: bool = True
    encryption_key: str = ""
    enable_backup: bool = True
    backup_retention_days: int = 30
    enable_audit_log: bool = True
    sensitive_fields: List[str] = field(default_factory=lambda: ["password", "token", "key"])

class EnhancedConfigManager:
    
    def __init__(self, translator: Any = None, config_format: ConfigFormat = ConfigFormat.INI):
        self.translator = translator
        self.config_format = config_format
        self.config_dir = None
        self.config_file = None
        self.backup_dir = None
        self.audit_log_file = None
        self._config_cache = {}
        self._validation_schema = self._load_validation_schema()
        
    def _get_message(self, key: str, fallback: str, **kwargs) -> str:
        """Get translated message or fallback with enhanced error handling"""
        try:
            if self.translator:
                return self.translator.get(key, fallback=fallback, **kwargs)
        except Exception as e:
            logger.warning(f"Translation error for key '{key}': {e}")
        return fallback.format(**kwargs) if kwargs else fallback
    
    def _load_validation_schema(self) -> Dict[str, Any]:
        """Load configuration validation schema"""
        return {
            "Browser": {
                "default_browser": {"type": "str", "allowed": ["chrome", "edge", "firefox", "brave", "opera", "operagx"]},
                "chrome_path": {"type": "str", "required": False},
                "chrome_driver_path": {"type": "str", "required": False}
            },
            "Timing": {
                "min_random_time": {"type": "float", "min": 0.0, "max": 10.0},
                "max_random_time": {"type": "float", "min": 0.0, "max": 10.0},
                "max_timeout": {"type": "int", "min": 10, "max": 600}
            },
            "Security": {
                "enable_encryption": {"type": "bool"},
                "backup_retention_days": {"type": "int", "min": 1, "max": 365}
            }
        }
    
    def setup_config_directory(self) -> Tuple[str, str]:
        """Setup configuration directory with enhanced error handling"""
        try:
            # Get documents path with fallback
            docs_path = self._get_documents_path()
            config_dir = os.path.normpath(os.path.join(docs_path, ".cursor-free-vip"))
            config_file = os.path.normpath(os.path.join(config_dir, self._get_config_filename()))
            
            # Create directory structure
            self._create_directory_structure(config_dir)
            
            self.config_dir = config_dir
            self.config_file = config_file
            self.backup_dir = os.path.join(config_dir, "backups")
            self.audit_log_file = os.path.join(config_dir, "audit.log")
            
            return config_dir, config_file
            
        except Exception as e:
            logger.error(f"Failed to setup config directory: {e}")
            raise ValidationError(f"Configuration setup failed: {e}")
    
    def _get_documents_path(self) -> str:
        """Get documents path with enhanced platform detection"""
        try:
            if platform.system() == "Windows":
                import winreg
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                   "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Shell Folders") as key:
                    documents_path, _ = winreg.QueryValueEx(key, "Personal")
                    return documents_path
            elif platform.system() == "Darwin":  # macOS
                return os.path.expanduser("~/Documents")
            else:  # Linux
                # Try XDG user directories
                xdg_config = os.path.expanduser("~/.config/user-dirs.dirs")
                if os.path.exists(xdg_config):
                    with open(xdg_config, "r") as f:
                        for line in f:
                            if line.startswith("XDG_DOCUMENTS_DIR"):
                                path = line.split("=")[1].strip().strip('"').replace("$HOME", os.path.expanduser("~"))
                                if os.path.exists(path):
                                    return path
                return os.path.expanduser("~/Documents")
        except Exception as e:
            logger.warning(f"Failed to get documents path: {e}")
            return os.path.abspath('.')
    
    def _get_config_filename(self) -> str:
        """Get configuration filename based on format"""
        format_extensions = {
            ConfigFormat.INI: "config.ini",
            ConfigFormat.JSON: "config.json",
            ConfigFormat.YAML: "config.yaml"
        }
        return format_extensions.get(self.config_format, "config.ini")
    
    def _create_directory_structure(self, config_dir: str) -> None:
        """Create directory structure with proper permissions"""
        try:
            os.makedirs(config_dir, exist_ok=True)
            
            # Create subdirectories
            subdirs = ["backups", "logs", "cache", "temp"]
            for subdir in subdirs:
                subdir_path = os.path.join(config_dir, subdir)
                os.makedirs(subdir_path, exist_ok=True)
                
            # Set proper permissions on Unix systems
            if platform.system() != "Windows":
                os.chmod(config_dir, 0o700)
                
        except Exception as e:
            logger.error(f"Failed to create directory structure: {e}")
            raise
    
    def validate_config(self, config_data: Dict[str, Any]) -> List[str]:
        """Validate configuration data against schema"""
        errors = []
        
        for section, section_schema in self._validation_schema.items():
            if section not in config_data:
                continue
                
            section_data = config_data[section]
            for key, validation in section_schema.items():
                if key not in section_data:
                    if validation.get("required", False):
                        errors.append(f"Missing required field: {section}.{key}")
                    continue
                
                value = section_data[key]
                value_type = validation.get("type")
                
                # Type validation
                if value_type == "str" and not isinstance(value, str):
                    errors.append(f"Invalid type for {section}.{key}: expected str, got {type(value)}")
                elif value_type == "int" and not isinstance(value, int):
                    errors.append(f"Invalid type for {section}.{key}: expected int, got {type(value)}")
                elif value_type == "float" and not isinstance(value, (int, float)):
                    errors.append(f"Invalid type for {section}.{key}: expected float, got {type(value)}")
                elif value_type == "bool" and not isinstance(value, bool):
                    errors.append(f"Invalid type for {section}.{key}: expected bool, got {type(value)}")
                
                # Range validation
                if "min" in validation and value < validation["min"]:
                    errors.append(f"Value too small for {section}.{key}: {value} < {validation['min']}")
                if "max" in validation and value > validation["max"]:
                    errors.append(f"Value too large for {section}.{key}: {value} > {validation['max']}")
                
                # Allowed values validation
                if "allowed" in validation and value not in validation["allowed"]:
                    errors.append(f"Invalid value for {section}.{key}: {value} not in {validation['allowed']}")
        
        return errors
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get enhanced default configuration"""
        from utils import get_default_browser_path, get_default_driver_path
        
        config_dir = self.config_dir or os.path.join(self._get_documents_path(), ".cursor-free-vip")
        
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
                'operagx_driver_path': get_default_driver_path('chrome')
            },
            'Timing': {
                'min_random_time': 0.1,
                'max_random_time': 0.8,
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
                'max_timeout': 160
            },
            'Security': {
                'enable_encryption': True,
                'encryption_key': '',
                'enable_backup': True,
                'backup_retention_days': 30,
                'enable_audit_log': True,
                'sensitive_fields': ['password', 'token', 'key', 'secret']
            },
            'Performance': {
                'enable_caching': True,
                'cache_ttl': 3600,
                'max_concurrent_operations': 5,
                'enable_compression': True
            },
            'Logging': {
                'log_level': 'INFO',
                'log_file': 'cursor_free_vip.log',
                'max_log_size': 10485760,  # 10MB
                'log_rotation': 5
            }
        }
        
        # Add system-specific paths
        self._add_system_paths(default_config)
        
        return default_config
    
    def _add_system_paths(self, config: Dict[str, Any]) -> None:
        system = platform.system()
        
        if system == "Windows":
            self._add_windows_paths(config)
        elif system == "Darwin":
            self._add_macos_paths(config)
        else:
            self._add_linux_paths(config)
    
    def _add_windows_paths(self, config: Dict[str, Any]) -> None:
        username = os.getenv('USERNAME', 'user')
        config['WindowsPaths'] = {
            'storage_path': f"C:\\Users\\{username}\\AppData\\Roaming\\Cursor\\User\\globalStorage\\storage.json",
            'sqlite_path': f"C:\\Users\\{username}\\AppData\\Roaming\\Cursor\\User\\globalStorage\\state.vscdb",
            'machine_id_path': f"C:\\Users\\{username}\\AppData\\Roaming\\Cursor\\machineId",
            'cursor_path': f"C:\\Users\\{username}\\AppData\\Local\\Programs\\Cursor\\resources\\app",
            'updater_path': f"C:\\Users\\{username}\\AppData\\Local\\cursor-updater",
            'update_yml_path': f"C:\\Users\\{username}\\AppData\\Local\\Programs\\Cursor\\resources\\app-update.yml",
            'product_json_path': f"C:\\Users\\{username}\\AppData\\Local\\Programs\\Cursor\\resources\\app\\product.json"
        }
    
    def _add_macos_paths(self, config: Dict[str, Any]) -> None:
        username = os.getenv('USER', 'user')
        config['MacOSPaths'] = {
            'storage_path': f"/Users/{username}/Library/Application Support/Cursor/User/globalStorage/storage.json",
            'sqlite_path': f"/Users/{username}/Library/Application Support/Cursor/User/globalStorage/state.vscdb",
            'machine_id_path': f"/Users/{username}/Library/Application Support/Cursor/machineId",
            'cursor_path': f"/Applications/Cursor.app/Contents/Resources/app",
            'updater_path': f"/Users/{username}/Library/Application Support/cursor-updater",
            'update_yml_path': f"/Applications/Cursor.app/Contents/Resources/app-update.yml",
            'product_json_path': f"/Applications/Cursor.app/Contents/Resources/app/product.json"
        }
    
    def _add_linux_paths(self, config: Dict[str, Any]) -> None:
        username = os.getenv('USER', 'user')
        config['LinuxPaths'] = {
            'storage_path': f"/home/{username}/.config/Cursor/User/globalStorage/storage.json",
            'sqlite_path': f"/home/{username}/.config/Cursor/User/globalStorage/state.vscdb",
            'machine_id_path': f"/home/{username}/.config/Cursor/machineid",
            'cursor_path': "/opt/Cursor/resources/app",
            'updater_path': f"/home/{username}/.config/cursor-updater",
            'update_yml_path': "/opt/Cursor/resources/app-update.yml",
            'product_json_path': "/opt/Cursor/resources/app/product.json"
        }
    
    def save_config(self, config_data: Dict[str, Any], backup: bool = True) -> None:
        try:
            errors = self.validate_config(config_data)
            if errors:
                raise ValidationError(f"Configuration validation failed:\n" + "\n".join(errors))
            
            if backup and self.backup_dir:
                self._create_backup()
            
            if self.config_format == ConfigFormat.JSON:
                self._save_json_config(config_data)
            elif self.config_format == ConfigFormat.YAML:
                self._save_yaml_config(config_data)
            else:
                self._save_ini_config(config_data)
            
            self._log_config_change("Configuration saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise
    
    def _create_backup(self) -> None:
        try:
            if not self.config_file or not os.path.exists(self.config_file):
                return
            
            if not self.backup_dir:
                return
                
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"config_backup_{timestamp}.{self.config_format.value}"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            shutil.copy2(self.config_file, backup_path)
            
            self._cleanup_old_backups()
            
            logger.info(f"Configuration backup created: {backup_path}")
            
        except Exception as e:
            logger.warning(f"Failed to create backup: {e}")
    
    def _cleanup_old_backups(self) -> None:
        try:
            if not self.backup_dir:
                return
            
            retention_days = 30
            cutoff_time = datetime.datetime.now() - datetime.timedelta(days=retention_days)
            
            for filename in os.listdir(self.backup_dir):
                if filename.startswith("config_backup_"):
                    file_path = os.path.join(self.backup_dir, filename)
                    file_time = datetime.datetime.fromtimestamp(os.path.getctime(file_path))
                    
                    if file_time < cutoff_time:
                        os.remove(file_path)
                        logger.info(f"Removed old backup: {filename}")
                        
        except Exception as e:
            logger.warning(f"Failed to cleanup old backups: {e}")
    
    def _save_json_config(self, config_data: Dict[str, Any]) -> None:
        if self.config_file:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
    
    def _save_yaml_config(self, config_data: Dict[str, Any]) -> None:
        if self.config_file:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
    
    def _save_ini_config(self, config_data: Dict[str, Any]) -> None:
        config = configparser.ConfigParser()
        
        for section, items in config_data.items():
            config.add_section(section)
            for key, value in items.items():
                config.set(section, key, str(value))
        
        if self.config_file:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                config.write(f)
    
    def _log_config_change(self, message: str) -> None:
        try:
            if self.audit_log_file:
                timestamp = datetime.datetime.now().isoformat()
                log_entry = f"{timestamp} - {message}\n"
                
                with open(self.audit_log_file, 'a', encoding='utf-8') as f:
                    f.write(log_entry)
                    
        except Exception as e:
            logger.warning(f"Failed to log configuration change: {e}")

def create_config_manager(translator: Any = None, format_type: str = "ini") -> EnhancedConfigManager:
    format_map = {
        "ini": ConfigFormat.INI,
        "json": ConfigFormat.JSON,
        "yaml": ConfigFormat.YAML
    }
    
    config_format = format_map.get(format_type.lower(), ConfigFormat.INI)
    return EnhancedConfigManager(translator, config_format) 