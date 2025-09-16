import os
import shutil
import platform
import tempfile
import glob
import logging
from colorama import Fore, Style, init
import configparser
import sys
from datetime import datetime
from typing import Optional, Dict, List, Union, Tuple, Any
from pathlib import Path

from config import get_config

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
    "FILE": "📄",
    "BACKUP": "💾",
    "SUCCESS": "✅",
    "ERROR": "❌",
    "INFO": "ℹ️",
    "RESET": "🔄",
    "WARNING": "⚠️",
}

def get_user_documents_path() -> str:
    """Get user Documents folder path"""
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Shell Folders") as key:
                documents_path, _ = winreg.QueryValueEx(key, "Personal")
                return documents_path
        except Exception as e:
            logger.warning(f"Failed to get Documents path from registry: {e}")
            return os.path.join(os.path.expanduser("~"), "Documents")
    elif sys.platform == "darwin":
        return os.path.join(os.path.expanduser("~"), "Documents")
    else:  # Linux
        # Get actual user's home directory
        sudo_user = os.environ.get('SUDO_USER')
        if sudo_user:
            return os.path.join("/home", sudo_user, "Documents")
        return os.path.join(os.path.expanduser("~"), "Documents")


def get_workbench_cursor_path(translator: Any = None) -> str:
    """Get Cursor workbench.desktop.main.js path
    
    Args:
        translator: Optional translator for internationalization
        
    Returns:
        str: Path to the workbench.desktop.main.js file
        
    Raises:
        OSError: If the file is not found or the OS is not supported
    """
    system = platform.system()

    # Read configuration
    config = get_config(translator)
    
    # Define paths for different operating systems
    paths_map = {
        "Darwin": {  # macOS
            "base": "/Applications/Cursor.app/Contents/Resources/app",
            "main": "out/vs/workbench/workbench.desktop.main.js"
        },
        "Windows": {
            "main": "out\\vs\\workbench\\workbench.desktop.main.js"
        },
        "Linux": {
            "bases": [
                "/opt/Cursor/resources/app", 
                "/usr/share/cursor/resources/app", 
                "/usr/lib/cursor/app/"
            ],
            "main": "out/vs/workbench/workbench.desktop.main.js"
        }
    }
    
    # Add extracted AppImage paths for Linux
    if system == "Linux":
        extracted_usr_paths = glob.glob(os.path.expanduser("~/squashfs-root/usr/share/cursor/resources/app"))
        paths_map["Linux"]["bases"].extend(extracted_usr_paths)

    # Check if the system is supported
    if system not in paths_map:
        error_msg = f"Unsupported operating system: {system}"
        logger.error(error_msg)
        raise OSError(translator.get('reset.unsupported_os', system=system) if translator else error_msg)

    # For Linux, check all possible base paths
    if system == "Linux":
        for base in paths_map["Linux"]["bases"]:
            main_path = os.path.join(base, paths_map["Linux"]["main"])
            logger.info(f"Checking path: {main_path}")
            if os.path.exists(main_path):
                return main_path

    # For Windows and macOS, get the base path from config
    if system == "Windows":
        if config and config.has_section('WindowsPaths') and config.has_option('WindowsPaths', 'cursor_path'):
            base_path = config.get('WindowsPaths', 'cursor_path')
        else:
            logger.warning("WindowsPaths section or cursor_path option not found in config")
            base_path = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Cursor', 'resources', 'app')
    elif system == "Darwin":
        if config and config.has_section('MacPaths') and config.has_option('MacPaths', 'cursor_path'):
            base_path = config.get('MacPaths', 'cursor_path')
        else:
            base_path = paths_map[system]["base"]
    else:  # Linux (fallback if none of the bases worked)
        if config and config.has_section('LinuxPaths') and config.has_option('LinuxPaths', 'cursor_path'):
            base_path = config.get('LinuxPaths', 'cursor_path')
        else:
            base_path = paths_map[system]["bases"][0]

    # Construct the full path to the main.js file
    main_path = os.path.join(base_path, paths_map[system]["main"])
    
    # Check if the file exists
    if not os.path.exists(main_path):
        error_msg = f"Cursor main.js file not found: {main_path}"
        logger.error(error_msg)
        raise OSError(translator.get('reset.file_not_found', path=main_path) if translator else error_msg)
        
    return main_path


def modify_workbench_js(file_path: str, translator: Any = None) -> bool:
    """
    Modify workbench.desktop.main.js file to bypass token limit
    
    Args:
        file_path: Path to the workbench.desktop.main.js file
        translator: Optional translator for internationalization
        
    Returns:
        bool: True if the modification was successful, False otherwise
    """
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return False
            
        # Save original file permissions
        original_stat = os.stat(file_path)
        original_mode = original_stat.st_mode
        original_uid = original_stat.st_uid
        original_gid = original_stat.st_gid

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", errors="ignore", delete=False) as tmp_file:
            # Read original content
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as main_file:
                    content = main_file.read()
            except Exception as e:
                logger.error(f"Failed to read file: {e}")
                os.unlink(tmp_file.name)
                return False

            # Define patterns to replace
            patterns = {
                # Button replacement patterns
                r'B(k,D(Ln,{title:"Upgrade to Pro",size:"small",get codicon(){return A.rocket},get onClick(){return t.pay}}),null)': 
                    r'B(k,D(Ln,{title:"yeongpin GitHub",size:"small",get codicon(){return A.github},get onClick(){return function(){window.open("https://github.com/yeongpin/cursor-free-vip","_blank")}}}),null)',
                
                # Windows/Linux
                r'M(x,I(as,{title:"Upgrade to Pro",size:"small",get codicon(){return $.rocket},get onClick(){return t.pay}}),null)': 
                    r'M(x,I(as,{title:"yeongpin GitHub",size:"small",get codicon(){return $.github},get onClick(){return function(){window.open("https://github.com/yeongpin/cursor-free-vip","_blank")}}}),null)',
                
                # Mac button replacement pattern
                r'$(k,E(Ks,{title:"Upgrade to Pro",size:"small",get codicon(){return F.rocket},get onClick(){return t.pay}}),null)': 
                    r'$(k,E(Ks,{title:"yeongpin GitHub",size:"small",get codicon(){return F.rocket},get onClick(){return function(){window.open("https://github.com/yeongpin/cursor-free-vip","_blank")}}}),null)',
                
                # Badge replacement
                r'<div>Pro Trial': r'<div>Pro',

                r'py-1">Auto-select': r'py-1">Bypass-Version-Pin',
                
                # Token limit bypass
                r'async getEffectiveTokenLimit(e){const n=e.modelName;if(!n)return 2e5;':
                    r'async getEffectiveTokenLimit(e){return 9000000;const n=e.modelName;if(!n)return 9e5;',
                
                # Pro status
                r'var DWr=ne("<div class=settings__item_description>You are currently signed in with <strong></strong>.");': 
                    r'var DWr=ne("<div class=settings__item_description>You are currently signed in with <strong></strong>. <h1>Pro</h1>");',
                
                # Toast replacement
                r'notifications-toasts': r'notifications-toasts hidden'
            }

            # Apply replacements
            for old_pattern, new_pattern in patterns.items():
                content = content.replace(old_pattern, new_pattern)

            # Write to temporary file
            tmp_file.write(content)
            tmp_path = tmp_file.name

        # Backup original file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{file_path}.backup.{timestamp}"
        try:
            shutil.copy2(file_path, backup_path)
            logger.info(f"Backup created: {backup_path}")
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.backup_created', path=backup_path) if translator else f'Backup created: {backup_path}'}{Style.RESET_ALL}")
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            os.unlink(tmp_path)
            return False
        
        # Move temporary file to original position
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            shutil.move(tmp_path, file_path)
        except Exception as e:
            logger.error(f"Failed to replace original file: {e}")
            return False

        # Restore original permissions
        try:
            os.chmod(file_path, original_mode)
            if os.name != "nt":  # Not Windows
                os.chown(file_path, original_uid, original_gid)
        except Exception as e:
            logger.warning(f"Failed to restore original permissions: {e}")
            # Continue anyway as this is not critical

        logger.info("File modified successfully")
        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.file_modified') if translator else 'File modified successfully'}{Style.RESET_ALL}")
        return True

    except Exception as e:
        logger.error(f"Failed to modify file: {e}")
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.modify_file_failed', error=str(e)) if translator else f'Failed to modify file: {str(e)}'}{Style.RESET_ALL}")
        if "tmp_path" in locals():
            try:
                os.unlink(tmp_path)
            except:
                pass
        return False
    
def run(translator: Any = None) -> bool:
    """Run the token limit bypass
    
    Args:
        translator: Optional translator for internationalization
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        config = get_config(translator)
        if not config:
            logger.error("Failed to get configuration")
            return False
            
        print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{EMOJI['RESET']} {translator.get('bypass_token_limit.title') if translator else 'Bypass Token Limit'}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")

        # Get workbench.desktop.main.js path
        try:
            workbench_path = get_workbench_cursor_path(translator)
            logger.info(f"Found workbench.desktop.main.js at: {workbench_path}")
        except OSError as e:
            logger.error(f"Failed to get workbench path: {e}")
            print(f"{Fore.RED}{EMOJI['ERROR']} {str(e)}{Style.RESET_ALL}")
            return False

        # Modify the file
        success = modify_workbench_js(workbench_path, translator)
        
        print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        input(f"{EMOJI['INFO']} {translator.get('bypass_token_limit.press_enter') if translator else 'Press Enter to continue...'}")
        
        return success
    except Exception as e:
        logger.error(f"Error in run function: {e}")
        print(f"{Fore.RED}{EMOJI['ERROR']} An unexpected error occurred: {str(e)}{Style.RESET_ALL}")
        return False

if __name__ == "__main__":
    try:
        from main import translator as main_translator
        run(main_translator)
    except ImportError:
        logger.warning("Failed to import translator from main.py, running without translation")
        run(None)
    except Exception as e:
        logger.error(f"Error running bypass_token_limit.py: {e}")
        print(f"{Fore.RED}{EMOJI['ERROR']} An unexpected error occurred: {str(e)}{Style.RESET_ALL}")