import os
import shutil
import platform
import tempfile
import glob
from colorama import Fore, Style, init
import configparser
import sys
from config import get_config
from datetime import datetime

# Initialize colorama
init()

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

def get_user_documents_path():
    """Get user Documents folder path"""
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Shell Folders") as key:
                documents_path, _ = winreg.QueryValueEx(key, "Personal")
                return documents_path
        except Exception:
            return os.path.join(os.path.expanduser("~"), "Documents")
    elif sys.platform == "darwin":
        return os.path.join(os.path.expanduser("~"), "Documents")
    else:  # Linux
        sudo_user = os.environ.get('SUDO_USER')
        if sudo_user:
            return os.path.join("/home", sudo_user, "Documents")
        return os.path.join(os.path.expanduser("~"), "Documents")


def get_workbench_windsurf_path(translator=None) -> str:
    """Get Windsurf workbench.desktop.main.js path"""
    system = platform.system()

    # Read configuration
    config_dir = os.path.join(get_user_documents_path(), ".windsurf-free-vip")
    config_file = os.path.join(config_dir, "config.ini")
    config = configparser.ConfigParser()

    if os.path.exists(config_file):
        config.read(config_file)
    
    paths_map = {
        "Darwin": {  # macOS
            "base": "/Applications/Windsurf.app/Contents/Resources/app",
            "main": "out/vs/workbench/workbench.desktop.main.js"
        },
        "Windows": {
            "bases": [
                os.path.expandvars(r"%LOCALAPPDATA%\\Programs\\Windsurf\\resources\\app"),
                os.path.expandvars(r"%USERPROFILE%\\AppData\\Local\\Programs\\Windsurf\\resources\\app")
            ],
            "main": os.path.join("out", "vs", "workbench", "workbench.desktop.main.js")
        },
        "Linux": {
            "bases": [
                "/usr/share/windsurf/resources/app",
                "/opt/windsurf/resources/app",
                "/usr/lib/windsurf/resources/app"
            ],
            "main": "out/vs/workbench/workbench.desktop.main.js"
        }
    }
    
    if system == "Linux":
        extracted_paths = glob.glob(os.path.expanduser("~/squashfs-root/usr/share/windsurf/resources/app"))
        paths_map["Linux"]["bases"].extend(extracted_paths)

    if system not in paths_map:
        raise OSError(translator.get('reset.unsupported_os', system=system)
                      if translator else f"Unsupported OS: {system}")

    # Search for Linux and Windows bases
    if system in ("Linux", "Windows"):
        for base in paths_map[system]["bases"]:
            main_path = os.path.join(base, paths_map[system]["main"])
            print(f"{Fore.CYAN}{EMOJI['INFO']} Checking path: {main_path}{Style.RESET_ALL}")
            if os.path.exists(main_path):
                return main_path

    # macOS has a single base
    if system == "Darwin":
        base = paths_map[system]["base"]
        if config.has_section('MacPaths') and config.has_option('MacPaths', 'windsurf_path'):
            base = config.get('MacPaths', 'windsurf_path')
        main_path = os.path.join(base, paths_map[system]["main"])
        if os.path.exists(main_path):
            return main_path

    # Fallback: error
    raise OSError(translator.get('reset.file_not_found', path=main_path)
                  if translator else f"File not found: {main_path}")


def modify_workbench_js(file_path: str, translator=None) -> bool:
    """
    Modify file content
    """
    try:
        original_stat = os.stat(file_path)
        original_mode = original_stat.st_mode
        original_uid = original_stat.st_uid
        original_gid = original_stat.st_gid

        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", errors="ignore", delete=False) as tmp_file:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as main_file:
                content = main_file.read()

            patterns = {
                # Bypass Upgrade prompt patterns
                r'async getEffectiveTokenLimit\(e\)\{const n=e.modelName;if\(!n\)return 2e5;':
                  r'async getEffectiveTokenLimit(e){return 9000000;const n=e.modelName;if(!n)return 9e5;',
                r'notifications-toasts': r'notifications-toasts hidden',
            }

            for old, new in patterns.items():
                content = content.replace(old, new)

            tmp_file.write(content)
            tmp_path = tmp_file.name

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{file_path}.backup.{timestamp}"
        shutil.copy2(file_path, backup_path)
        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} Backup created at: {backup_path}{Style.RESET_ALL}")
        
        os.remove(file_path)
        shutil.move(tmp_path, file_path)

        os.chmod(file_path, original_mode)
        if os.name != "nt":
            os.chown(file_path, original_uid, original_gid)

        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} File modified successfully.{Style.RESET_ALL}")
        return True

    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} Modification failed: {e}{Style.RESET_ALL}")
        if 'tmp_path' in locals():
            try:
                os.unlink(tmp_path)
            except:
                pass
        return False
    

def run(translator=None):
    config = get_config(translator)
    if not config:
        return False
    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{EMOJI['RESET']} Bypass Windsurf token limits{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}\n")

    js_path = get_workbench_windsurf_path(translator)
    modify_workbench_js(js_path, translator)

    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    input(f"{EMOJI['INFO']} Press Enter to exit...")

if __name__ == "__main__":
    from main import translator as main_translator
    run(main_translator)
