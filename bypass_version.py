import os
import json
import shutil
import platform
import configparser
import time
import logging
from colorama import Fore, Style, init
import sys
import traceback
from pathlib import Path
from typing import Optional, Dict, List, Union, Tuple, Any
from utils import get_user_documents_path

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
    'INFO': 'ℹ️',
    'SUCCESS': '✅',
    'ERROR': '❌',
    'WARNING': '⚠️',
    'FILE': '📄',
    'BACKUP': '💾',
    'RESET': '🔄',
    'VERSION': '🏷️'
}

def get_product_json_path(translator: Any = None) -> str:
    """Get Cursor product.json path based on the operating system.
    
    Args:
        translator: Optional translator for internationalization
        
    Returns:
        str: Path to the product.json file
        
    Raises:
        OSError: If the file is not found or the OS is not supported
    """
    system = platform.system()
    
    # Read configuration
    config_dir = os.path.join(get_user_documents_path(), ".cursor-free-vip")
    config_file = os.path.join(config_dir, "config.ini")
    config = configparser.ConfigParser()
    
    if os.path.exists(config_file):
        config.read(config_file)
    
    # Define paths for different operating systems
    if system == "Windows":
        localappdata = os.environ.get("LOCALAPPDATA")
        if not localappdata:
            error_msg = "LOCALAPPDATA environment variable not found"
            logger.error(error_msg)
            raise OSError(translator.get('bypass.localappdata_not_found') if translator else error_msg)
        
        product_json_path = os.path.join(localappdata, "Programs", "Cursor", "resources", "app", "product.json")
        
        # Check if path exists in config
        if 'WindowsPaths' in config and 'cursor_path' in config['WindowsPaths']:
            cursor_path = config.get('WindowsPaths', 'cursor_path')
            product_json_path = os.path.join(cursor_path, "product.json")
    
    elif system == "Darwin":  # macOS
        product_json_path = "/Applications/Cursor.app/Contents/Resources/app/product.json"
        if config.has_section('MacPaths') and config.has_option('MacPaths', 'product_json_path'):
            product_json_path = config.get('MacPaths', 'product_json_path')
    
    elif system == "Linux":
        # Try multiple common paths
        possible_paths = [
            "/opt/Cursor/resources/app/product.json",
            "/usr/share/cursor/resources/app/product.json",
            "/usr/lib/cursor/app/product.json"
        ]
        
        # Add extracted AppImage paths
        extracted_usr_paths = os.path.expanduser("~/squashfs-root/usr/share/cursor/resources/app/product.json")
        if os.path.exists(extracted_usr_paths):
            possible_paths.append(extracted_usr_paths)
        
        # Find first existing path
        for path in possible_paths:
            if os.path.exists(path):
                product_json_path = path
                break
        else:
            error_msg = "product.json not found in common Linux paths"
            logger.error(error_msg)
            raise OSError(translator.get('bypass.product_json_not_found') if translator else error_msg)
    
    else:
        error_msg = f"Unsupported operating system: {system}"
        logger.error(error_msg)
        raise OSError(translator.get('bypass.unsupported_os', system=system) if translator else error_msg)
    
    # Verify that the file exists
    if not os.path.exists(product_json_path):
        error_msg = f"File not found: {product_json_path}"
        logger.error(error_msg)
        raise OSError(translator.get('bypass.file_not_found', path=product_json_path) if translator else error_msg)
    
    logger.info(f"Found product.json at: {product_json_path}")
    return product_json_path

def compare_versions(version1: str, version2: str) -> int:
    """Compare two version strings.
    
    Args:
        version1: First version string (e.g., "0.48.7")
        version2: Second version string (e.g., "0.46.0")
        
    Returns:
        int: -1 if version1 < version2, 0 if version1 == version2, 1 if version1 > version2
    """
    try:
        v1_parts = [int(x) for x in version1.split('.')]
        v2_parts = [int(x) for x in version2.split('.')]
        
        for i in range(max(len(v1_parts), len(v2_parts))):
            v1 = v1_parts[i] if i < len(v1_parts) else 0
            v2 = v2_parts[i] if i < len(v2_parts) else 0
            if v1 < v2:
                return -1
            elif v1 > v2:
                return 1
        
        return 0
    except (ValueError, TypeError) as e:
        logger.warning(f"Error comparing versions {version1} and {version2}: {e}")
        # Fall back to string comparison if numeric comparison fails
        if version1 < version2:
            return -1
        elif version1 > version2:
            return 1
        else:
            return 0

def bypass_version(translator: Any = None) -> bool:
    """Bypass Cursor version check by modifying product.json.
    
    Args:
        translator: Optional translator for internationalization
        
    Returns:
        bool: True if the version was successfully bypassed, False otherwise
    """
    try:
        print(f"\n{Fore.CYAN}{EMOJI['INFO']} {translator.get('bypass.starting') if translator else 'Starting Cursor version bypass...'}{Style.RESET_ALL}")
        
        # Get product.json path
        product_json_path = get_product_json_path(translator)
        print(f"{Fore.CYAN}{EMOJI['FILE']} {translator.get('bypass.found_product_json', path=product_json_path) if translator else f'Found product.json: {product_json_path}'}{Style.RESET_ALL}")
        
        # Check file permissions
        if not os.access(product_json_path, os.W_OK):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('bypass.no_write_permission', path=product_json_path) if translator else f'No write permission for file: {product_json_path}'}{Style.RESET_ALL}")
            return False
        
        # Read product.json
        try:
            with open(product_json_path, "r", encoding="utf-8") as f:
                product_data = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in product.json: {e}")
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('bypass.invalid_json', error=str(e)) if translator else f'Invalid JSON in product.json: {str(e)}'}{Style.RESET_ALL}")
            return False
        except Exception as e:
            logger.error(f"Failed to read product.json: {e}")
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('bypass.read_failed', error=str(e)) if translator else f'Failed to read product.json: {str(e)}'}{Style.RESET_ALL}")
            return False
        
        # Get current version
        current_version = product_data.get("version", "0.0.0")
        print(f"{Fore.CYAN}{EMOJI['VERSION']} {translator.get('bypass.current_version', version=current_version) if translator else f'Current version: {current_version}'}{Style.RESET_ALL}")
        
        # Target version to set
        new_version = "0.48.7"
        
        # Check if version needs to be modified
        if compare_versions(current_version, "0.46.0") < 0:
            # Create backup
            timestamp = time.strftime("%Y%m%d%H%M%S")
            backup_path = f"{product_json_path}.{timestamp}"
            try:
                shutil.copy2(product_json_path, backup_path)
                print(f"{Fore.GREEN}{EMOJI['BACKUP']} {translator.get('bypass.backup_created', path=backup_path) if translator else f'Backup created: {backup_path}'}{Style.RESET_ALL}")
            except Exception as e:
                logger.error(f"Failed to create backup: {e}")
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('bypass.backup_failed', error=str(e)) if translator else f'Failed to create backup: {str(e)}'}{Style.RESET_ALL}")
                return False
            
            # Modify version
            product_data["version"] = new_version
            
            # Save modified product.json
            try:
                with open(product_json_path, "w", encoding="utf-8") as f:
                    json.dump(product_data, f, indent=2)
                logger.info(f"Version updated from {current_version} to {new_version}")
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('bypass.version_updated', old=current_version, new=new_version) if translator else f'Version updated from {current_version} to {new_version}'}{Style.RESET_ALL}")
                return True
            except Exception as e:
                logger.error(f"Failed to write product.json: {e}")
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('bypass.write_failed', error=str(e)) if translator else f'Failed to write product.json: {str(e)}'}{Style.RESET_ALL}")
                
                # Try to restore from backup if write fails
                try:
                    if os.path.exists(backup_path):
                        shutil.copy2(backup_path, product_json_path)
                        print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('bypass.restored_from_backup') if translator else 'Restored from backup'}{Style.RESET_ALL}")
                except Exception as restore_error:
                    logger.error(f"Failed to restore from backup: {restore_error}")
                
                return False
        else:
            print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('bypass.no_update_needed', version=current_version) if translator else f'No update needed. Current version {current_version} is already >= 0.46.0'}{Style.RESET_ALL}")
            return True
    
    except Exception as e:
        logger.error(f"Version bypass failed: {e}")
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('bypass.bypass_failed', error=str(e)) if translator else f'Version bypass failed: {str(e)}'}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('bypass.stack_trace') if translator else 'Stack trace'}: {traceback.format_exc()}{Style.RESET_ALL}")
        return False

def run(translator: Any = None) -> bool:
    """Main function to run the version bypass.
    
    Args:
        translator: Optional translator for internationalization
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{EMOJI['RESET']} {translator.get('bypass_version.title') if translator else 'Bypass Version Check'}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        
        success = bypass_version(translator)
        
        print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        input(f"{EMOJI['INFO']} {translator.get('bypass_version.press_enter') if translator else 'Press Enter to continue...'}")
        
        return success
    except Exception as e:
        logger.error(f"Error in run function: {e}")
        print(f"{Fore.RED}{EMOJI['ERROR']} An unexpected error occurred: {str(e)}{Style.RESET_ALL}")
        return False

def main(translator: Any = None) -> bool:
    """Entry point when called directly.
    
    Args:
        translator: Optional translator for internationalization
        
    Returns:
        bool: True if successful, False otherwise
    """
    return run(translator)

if __name__ == "__main__":
    try:
        from main import translator as main_translator
        main(main_translator)
    except ImportError:
        logger.warning("Failed to import translator from main.py, running without translation")
        main(None)
    except Exception as e:
        logger.error(f"Error running bypass_version.py: {e}")
        print(f"{Fore.RED}{EMOJI['ERROR']} An unexpected error occurred: {str(e)}{Style.RESET_ALL}") 