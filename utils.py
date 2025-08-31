import os
import sys
import platform
import random
import shutil
import logging
from typing import Optional, Dict, List, Union, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

def get_user_documents_path() -> str:
    """Get user documents path across different operating systems.
    
    Returns:
        str: Path to user's Documents directory
    """
    if platform.system() == "Windows":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Shell Folders") as key:
                documents_path, _ = winreg.QueryValueEx(key, "Personal")
                return documents_path
        except Exception as e:
            logger.warning(f"Failed to get Documents path from registry: {e}")
            return os.path.expanduser("~\\Documents")
    elif platform.system() == "Darwin":  # macOS
        return os.path.expanduser("~/Documents")
    else:  # Linux and other Unix-like systems
        # Check for XDG user directories
        try:
            with open(os.path.expanduser("~/.config/user-dirs.dirs"), "r") as f:
                for line in f:
                    if line.startswith("XDG_DOCUMENTS_DIR"):
                        path = line.split("=")[1].strip().strip('"').replace("$HOME", os.path.expanduser("~"))
                        if os.path.exists(path):
                            return path
        except (FileNotFoundError, IOError):
            pass
        
        # Fallback to ~/Documents
        return os.path.expanduser("~/Documents")

def find_executable(executable_names: List[str]) -> Optional[str]:
    """Find executable in PATH by trying multiple possible names.
    
    Args:
        executable_names: List of possible executable names to try
        
    Returns:
        Path to the executable if found, None otherwise
    """
    for name in executable_names:
        try:
            path = shutil.which(name)
            if path:
                return path
        except Exception:
            continue
    return None

def get_default_driver_path(browser_type: str = 'chrome') -> str:
    """Get default driver path based on browser type.
    
    Args:
        browser_type: Type of browser ('chrome', 'edge', 'firefox', 'brave')
        
    Returns:
        str: Path to the browser driver
    """
    browser_type = browser_type.lower()
    driver_map = {
        'chrome': get_default_chrome_driver_path,
        'edge': get_default_edge_driver_path,
        'firefox': get_default_firefox_driver_path,
        'brave': get_default_chrome_driver_path,  # Brave uses Chrome driver
        'opera': get_default_chrome_driver_path,  # Opera uses Chrome driver
        'operagx': get_default_chrome_driver_path  # OperaGX uses Chrome driver
    }
    
    driver_func = driver_map.get(browser_type, get_default_chrome_driver_path)
    return driver_func()

def get_default_chrome_driver_path() -> str:
    """Get default Chrome driver path based on platform."""
    if sys.platform == "win32":
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "drivers", "chromedriver.exe")
    elif sys.platform == "darwin":
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "drivers", "chromedriver")
    else:  # Linux and other Unix-like systems
        # Try to find chromedriver in PATH first
        path = find_executable(["chromedriver"])
        if path:
            return path
        return "/usr/local/bin/chromedriver"

def get_default_edge_driver_path() -> str:
    """Get default Edge driver path based on platform."""
    if sys.platform == "win32":
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "drivers", "msedgedriver.exe")
    elif sys.platform == "darwin":
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "drivers", "msedgedriver")
    else:  # Linux and other Unix-like systems
        path = find_executable(["msedgedriver"])
        if path:
            return path
        return "/usr/local/bin/msedgedriver"
        
def get_default_firefox_driver_path() -> str:
    """Get default Firefox driver path based on platform."""
    if sys.platform == "win32":
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "drivers", "geckodriver.exe")
    elif sys.platform == "darwin":
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "drivers", "geckodriver")
    else:  # Linux and other Unix-like systems
        path = find_executable(["geckodriver"])
        if path:
            return path
        return "/usr/local/bin/geckodriver"

def get_default_browser_path(browser_type: str = 'chrome') -> str:
    """Get default browser executable path based on platform and browser type.
    
    Args:
        browser_type: Type of browser ('chrome', 'edge', 'firefox', 'brave', 'opera', 'operagx')
        
    Returns:
        str: Path to the browser executable
    """
    browser_type = browser_type.lower()
    
    # Platform-specific browser paths
    if sys.platform == "win32":
        return _get_windows_browser_path(browser_type)
    elif sys.platform == "darwin":
        return _get_macos_browser_path(browser_type)
    else:  # Linux and other Unix-like systems
        return _get_linux_browser_path(browser_type)

def _get_windows_browser_path(browser_type: str) -> str:
    """Get browser path for Windows."""
    browser_paths = {
        'chrome': [
            shutil.which("chrome"),
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'Application', 'chrome.exe')
        ],
        'edge': [
            shutil.which("msedge"),
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        ],
        'firefox': [
            shutil.which("firefox"),
            r"C:\Program Files\Mozilla Firefox\firefox.exe",
            r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe"
        ],
        'opera': [
            shutil.which("opera"),
            r"C:\Program Files\Opera\opera.exe",
            r"C:\Program Files (x86)\Opera\opera.exe",
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Opera', 'launcher.exe'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Opera', 'opera.exe')
        ],
        'operagx': [
            shutil.which("opera"),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Opera GX', 'launcher.exe'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Opera GX', 'opera.exe'),
            r"C:\Program Files\Opera GX\opera.exe",
            r"C:\Program Files (x86)\Opera GX\opera.exe"
        ],
        'brave': [
            shutil.which("brave"),
            os.path.join(os.environ.get('PROGRAMFILES', ''), 'BraveSoftware', 'Brave-Browser', 'Application', 'brave.exe'),
            os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'BraveSoftware', 'Brave-Browser', 'Application', 'brave.exe'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'BraveSoftware', 'Brave-Browser', 'Application', 'brave.exe')
        ]
    }
    
    # Return first existing path
    paths = browser_paths.get(browser_type, browser_paths['chrome'])
    for path in paths:
        if path and os.path.exists(path):
            return path
    
    # Return first path as fallback
    return next((p for p in paths if p), r"C:\Program Files\Google\Chrome\Application\chrome.exe")

def _get_macos_browser_path(browser_type: str) -> str:
    """Get browser path for macOS."""
    browser_paths = {
        'chrome': [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        ],
        'edge': [
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "~/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
        ],
        'firefox': [
            "/Applications/Firefox.app/Contents/MacOS/firefox",
            "~/Applications/Firefox.app/Contents/MacOS/firefox"
        ],
        'brave': [
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            "~/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
        ],
        'opera': [
            "/Applications/Opera.app/Contents/MacOS/Opera",
            "~/Applications/Opera.app/Contents/MacOS/Opera"
        ],
        'operagx': [
            "/Applications/Opera GX.app/Contents/MacOS/Opera",
            "~/Applications/Opera GX.app/Contents/MacOS/Opera"
        ]
    }
    
    # Return first existing path
    paths = browser_paths.get(browser_type, browser_paths['chrome'])
    for path in paths:
        expanded_path = os.path.expanduser(path)
        if os.path.exists(expanded_path):
            return expanded_path
    
    # Return first path as fallback
    return os.path.expanduser(paths[0])

def _get_linux_browser_path(browser_type: str) -> str:
    """Get browser path for Linux."""
    browser_executables = {
        'chrome': ["google-chrome", "chrome", "chromium", "chromium-browser"],
        'edge': ["microsoft-edge", "msedge"],
        'firefox': ["firefox", "firefox-esr"],
        'opera': ["opera"],
        'operagx': ["opera-gx", "opera"],
        'brave': ["brave-browser", "brave"]
    }
    
    # Try to find executable in PATH
    executables = browser_executables.get(browser_type, browser_executables['chrome'])
    path = find_executable(executables)
    if path:
        return path
    
    # Fallback to common locations
    common_locations = {
        'chrome': "/usr/bin/google-chrome",
        'edge': "/usr/bin/microsoft-edge",
        'firefox': "/usr/bin/firefox",
        'opera': "/usr/bin/opera",
        'operagx': "/usr/bin/opera",
        'brave': "/usr/bin/brave-browser"
    }
    
    return common_locations.get(browser_type, common_locations['chrome'])

def get_linux_cursor_path() -> str:
    """Get Linux Cursor path by checking multiple possible locations."""
    possible_paths = [
        "/opt/Cursor/resources/app",
        "/usr/share/cursor/resources/app",
        "/opt/cursor-bin/resources/app",
        "/usr/lib/cursor/resources/app",
        os.path.expanduser("~/.local/share/cursor/resources/app"),
        # Add extracted AppImage paths
        *[p for p in [os.path.expanduser("~/squashfs-root/usr/share/cursor/resources/app")] if os.path.exists(p)]
    ]
    
    # Return first existing path or default if none exists
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # Log warning if no path found
    logger.warning("No Cursor installation found in common Linux paths")
    return possible_paths[0]

def parse_time_range(time_str: str) -> Tuple[float, float]:
    """Parse a time range string into min and max values.
    
    Args:
        time_str: String representing time range (e.g., "0.5-1.5" or "0.5,1.5")
        
    Returns:
        Tuple of (min_time, max_time)
    """
    try:
        if isinstance(time_str, (int, float)):
            return float(time_str), float(time_str)
            
        if '-' in time_str:
            min_time, max_time = map(float, time_str.split('-'))
        elif ',' in time_str:
            min_time, max_time = map(float, time_str.split(','))
        else:
            min_time = max_time = float(time_str)
            
        return min_time, max_time
    except (ValueError, TypeError):
        return 0.5, 1.5

def get_random_wait_time(config: Dict, timing_key: str, default_range: Tuple[float, float] = (0.5, 1.5)) -> float:
    """Get random wait time based on configuration timing settings.
    
    Args:
        config: Configuration dictionary containing timing settings
        timing_key: Key to look up in the timing settings
        default_range: Default time range to use if config value is invalid
        
    Returns:
        float: Random wait time in seconds
    """
    try:
        # Get timing value from config
        if not config or 'Timing' not in config:
            return random.uniform(*default_range)
            
        timing = config.get('Timing', {}).get(timing_key)
        if not timing:
            return random.uniform(*default_range)
            
        min_time, max_time = parse_time_range(timing)
        return random.uniform(min_time, max_time)
        
    except Exception as e:
        logger.warning(f"Error getting wait time for {timing_key}: {e}")
        return random.uniform(*default_range) 