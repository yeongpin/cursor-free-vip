

import os
import sys
import platform
import random
import shutil
import logging
import subprocess
import threading
import time
import hashlib
import json
from typing import Optional, Dict, List, Union, Tuple, Any, Callable
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import psutil
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure enhanced logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

class ProcessStatus(Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    NOT_FOUND = "not_found"
    ERROR = "error"

@dataclass
class ProcessInfo:
    pid: int
    name: str
    status: ProcessStatus
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    start_time: float = 0.0
    command_line: str = ""

@dataclass
class SystemInfo:
    platform: str
    architecture: str
    python_version: str
    total_memory: float
    available_memory: float
    cpu_count: int
    disk_usage: Dict[str, float]

class EnhancedPathManager:
    
    def __init__(self):
        self._path_cache = {}
        self._executable_cache = {}
        self._browser_cache = {}
    
    def get_user_documents_path(self) -> str:
        """Get user documents path with enhanced error handling"""
        cache_key = "documents_path"
        if cache_key in self._path_cache:
            return self._path_cache[cache_key]
        
        try:
            if platform.system() == "Windows":
                path = self._get_windows_documents_path()
            elif platform.system() == "Darwin":
                path = self._get_macos_documents_path()
            else:
                path = self._get_linux_documents_path()
            
            # Validate path exists
            if not os.path.exists(path):
                logger.warning(f"Documents path does not exist: {path}")
                path = os.path.expanduser("~/Documents")
            
            self._path_cache[cache_key] = path
            return path
            
        except Exception as e:
            logger.error(f"Failed to get documents path: {e}")
            fallback = os.path.expanduser("~/Documents")
            self._path_cache[cache_key] = fallback
            return fallback
    
    def _get_windows_documents_path(self) -> str:
        """Get Windows documents path from registry"""
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                               "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Shell Folders") as key:
                documents_path, _ = winreg.QueryValueEx(key, "Personal")
                return documents_path
        except Exception as e:
            logger.warning(f"Failed to get Windows documents path from registry: {e}")
            return os.path.expanduser("~\\Documents")
    
    def _get_macos_documents_path(self) -> str:
        """Get macOS documents path"""
        return os.path.expanduser("~/Documents")
    
    def _get_linux_documents_path(self) -> str:
        """Get Linux documents path with XDG support"""
        try:
            xdg_config = os.path.expanduser("~/.config/user-dirs.dirs")
            if os.path.exists(xdg_config):
                with open(xdg_config, "r") as f:
                    for line in f:
                        if line.startswith("XDG_DOCUMENTS_DIR"):
                            path = line.split("=")[1].strip().strip('"').replace("$HOME", os.path.expanduser("~"))
                            if os.path.exists(path):
                                return path
        except Exception as e:
            logger.warning(f"Failed to read XDG config: {e}")
        
        return os.path.expanduser("~/Documents")
    
    def find_executable(self, executable_names: List[str], validate: bool = True) -> Optional[str]:
        """Find executable with enhanced validation"""
        cache_key = tuple(sorted(executable_names))
        if cache_key in self._executable_cache:
            return self._executable_cache[cache_key]
        
        for name in executable_names:
            try:
                path = shutil.which(name)
                if path and (not validate or self._validate_executable(path)):
                    self._executable_cache[cache_key] = path
                    return path
            except Exception as e:
                logger.debug(f"Failed to find executable {name}: {e}")
                continue
        
        self._executable_cache[cache_key] = None
        return None
    
    def _validate_executable(self, path: str) -> bool:
        """Validate executable file"""
        try:
            if not os.path.exists(path):
                return False
            
            # Check if file is executable
            if platform.system() != "Windows":
                if not os.access(path, os.X_OK):
                    return False
            
            # Check file size (should not be 0)
            if os.path.getsize(path) == 0:
                return False
            
            return True
            
        except Exception as e:
            logger.debug(f"Executable validation failed for {path}: {e}")
            return False

class EnhancedBrowserManager:
    """Enhanced browser management with automatic detection and validation"""
    
    def __init__(self):
        self.path_manager = EnhancedPathManager()
        self._browser_paths = {}
        self._driver_paths = {}
    
    def get_browser_path(self, browser_type: str) -> str:
        """Get browser path with enhanced detection"""
        browser_type = browser_type.lower()
        
        if browser_type in self._browser_paths:
            return self._browser_paths[browser_type]
        
        try:
            if platform.system() == "Windows":
                path = self._get_windows_browser_path(browser_type)
            elif platform.system() == "Darwin":
                path = self._get_macos_browser_path(browser_type)
            else:
                path = self._get_linux_browser_path(browser_type)
            
            self._browser_paths[browser_type] = path
            return path
            
        except Exception as e:
            logger.error(f"Failed to get browser path for {browser_type}: {e}")
            return ""
    
    def get_driver_path(self, browser_type: str) -> str:
        """Get driver path with enhanced detection"""
        browser_type = browser_type.lower()
        
        if browser_type in self._driver_paths:
            return self._driver_paths[browser_type]
        
        try:
            # Map browser types to driver types
            driver_map = {
                'chrome': 'chromedriver',
                'edge': 'msedgedriver',
                'firefox': 'geckodriver',
                'brave': 'chromedriver',
                'opera': 'chromedriver',
                'operagx': 'chromedriver'
            }
            
            driver_name = driver_map.get(browser_type, 'chromedriver')
            path = self._find_driver_path(driver_name)
            
            self._driver_paths[browser_type] = path
            return path
            
        except Exception as e:
            logger.error(f"Failed to get driver path for {browser_type}: {e}")
            return ""
    
    def _get_windows_browser_path(self, browser_type: str) -> str:
        """Get Windows browser path"""
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
                os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Opera', 'launcher.exe')
            ],
            'operagx': [
                os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Opera GX', 'launcher.exe'),
                r"C:\Program Files\Opera GX\opera.exe",
                r"C:\Program Files (x86)\Opera GX\opera.exe"
            ],
            'brave': [
                shutil.which("brave"),
                os.path.join(os.environ.get('PROGRAMFILES', ''), 'BraveSoftware', 'Brave-Browser', 'Application', 'brave.exe'),
                os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'BraveSoftware', 'Brave-Browser', 'Application', 'brave.exe')
            ]
        }
        
        paths = browser_paths.get(browser_type, [])
        for path in paths:
            if path and os.path.exists(path):
                return path
        
        return ""
    
    def _get_macos_browser_path(self, browser_type: str) -> str:
        """Get macOS browser path"""
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
            'opera': [
                "/Applications/Opera.app/Contents/MacOS/Opera",
                "~/Applications/Opera.app/Contents/MacOS/Opera"
            ],
            'operagx': [
                "/Applications/Opera GX.app/Contents/MacOS/Opera GX",
                "~/Applications/Opera GX.app/Contents/MacOS/Opera GX"
            ],
            'brave': [
                "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
                "~/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
            ]
        }
        
        paths = browser_paths.get(browser_type, [])
        for path in paths:
            expanded_path = os.path.expanduser(path)
            if os.path.exists(expanded_path):
                return expanded_path
        
        return ""
    
    def _get_linux_browser_path(self, browser_type: str) -> str:
        """Get Linux browser path"""
        browser_names = {
            'chrome': ['google-chrome', 'chrome', 'chromium-browser', 'chromium'],
            'edge': ['microsoft-edge', 'msedge', 'edge'],
            'firefox': ['firefox', 'firefox-esr'],
            'opera': ['opera', 'opera-stable'],
            'operagx': ['opera-gx'],
            'brave': ['brave-browser', 'brave']
        }
        
        names = browser_names.get(browser_type, [browser_type])
        return self.path_manager.find_executable(names) or ""
    
    def _find_driver_path(self, driver_name: str) -> str:
        """Find driver executable path"""
        # Try to find in PATH first
        path = self.path_manager.find_executable([driver_name])
        if path:
            return path
        
        # Try common installation paths
        if platform.system() == "Windows":
            driver_paths = [
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "drivers", f"{driver_name}.exe"),
                os.path.join(os.environ.get('LOCALAPPDATA', ''), 'WebDriver', f"{driver_name}.exe"),
                f"C:\\Program Files\\{driver_name}\\{driver_name}.exe"
            ]
        elif platform.system() == "Darwin":
            driver_paths = [
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "drivers", driver_name),
                f"/usr/local/bin/{driver_name}",
                f"/opt/homebrew/bin/{driver_name}"
            ]
        else:
            driver_paths = [
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "drivers", driver_name),
                f"/usr/local/bin/{driver_name}",
                f"/usr/bin/{driver_name}"
            ]
        
        for driver_path in driver_paths:
            if os.path.exists(driver_path):
                return driver_path
        
        return ""

class EnhancedProcessManager:
    """Enhanced process management with monitoring and control"""
    
    def __init__(self):
        self._process_cache = {}
        self._monitoring_threads = {}
    
    def find_cursor_processes(self) -> List[ProcessInfo]:
        """Find all Cursor processes with detailed information"""
        processes = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info', 'cpu_percent', 'create_time']):
                try:
                    if self._is_cursor_process(proc.info['name']):
                        process_info = ProcessInfo(
                            pid=proc.info['pid'],
                            name=proc.info['name'],
                            status=ProcessStatus.RUNNING,
                            memory_usage=proc.info['memory_info'].rss / 1024 / 1024,  # MB
                            cpu_usage=proc.info['cpu_percent'],
                            start_time=proc.info['create_time'],
                            command_line=' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                        )
                        processes.append(process_info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except Exception as e:
            logger.error(f"Failed to find Cursor processes: {e}")
        
        return processes
    
    def _is_cursor_process(self, process_name: str) -> bool:
        """Check if process is related to Cursor"""
        cursor_names = ['cursor', 'Cursor', 'CURSOR']
        return any(name in process_name for name in cursor_names)
    
    def kill_cursor_processes(self, force: bool = False) -> bool:
        """Kill all Cursor processes"""
        processes = self.find_cursor_processes()
        success = True
        
        for process_info in processes:
            try:
                proc = psutil.Process(process_info.pid)
                if force:
                    proc.kill()
                else:
                    proc.terminate()
                
                logger.info(f"Terminated Cursor process: {process_info.name} (PID: {process_info.pid})")
                
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                logger.warning(f"Failed to terminate process {process_info.pid}: {e}")
                success = False
        
        return success
    
    def wait_for_process_termination(self, pids: List[int], timeout: int = 30) -> bool:
        """Wait for processes to terminate"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            remaining_pids = []
            
            for pid in pids:
                try:
                    if psutil.pid_exists(pid):
                        remaining_pids.append(pid)
                except Exception:
                    continue
            
            if not remaining_pids:
                return True
            
            time.sleep(0.5)
        
        logger.warning(f"Timeout waiting for process termination: {remaining_pids}")
        return False
    
    def monitor_process(self, pid: int, callback: Callable[[ProcessInfo], None]) -> None:
        """Monitor process and call callback with updates"""
        def monitor():
            try:
                proc = psutil.Process(pid)
                while proc.is_running():
                    try:
                        process_info = ProcessInfo(
                            pid=proc.pid,
                            name=proc.name(),
                            status=ProcessStatus.RUNNING,
                            memory_usage=proc.memory_info().rss / 1024 / 1024,
                            cpu_usage=proc.cpu_percent(),
                            start_time=proc.create_time(),
                            command_line=' '.join(proc.cmdline()) if proc.cmdline() else ''
                        )
                        callback(process_info)
                        time.sleep(1)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        break
            except Exception as e:
                logger.error(f"Process monitoring failed for PID {pid}: {e}")
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        self._monitoring_threads[pid] = thread

class EnhancedSystemManager:
    """Enhanced system information and management"""
    
    def __init__(self):
        self._system_info = None
    
    def get_system_info(self) -> SystemInfo:
        """Get comprehensive system information"""
        if self._system_info is None:
            try:
                cpu_count = psutil.cpu_count()
                if cpu_count is None:
                    cpu_count = 1
                    
                self._system_info = SystemInfo(
                    platform=platform.system(),
                    architecture=platform.machine(),
                    python_version=sys.version,
                    total_memory=psutil.virtual_memory().total / 1024 / 1024 / 1024,
                    available_memory=psutil.virtual_memory().available / 1024 / 1024 / 1024,
                    cpu_count=cpu_count,
                    disk_usage=self._get_disk_usage()
                )
            except Exception as e:
                logger.error(f"Failed to get system info: {e}")
                # Return basic info
                self._system_info = SystemInfo(
                    platform=platform.system(),
                    architecture=platform.machine(),
                    python_version=sys.version,
                    total_memory=0.0,
                    available_memory=0.0,
                    cpu_count=1,
                    disk_usage={}
                )
        
        return self._system_info
    
    def _get_disk_usage(self) -> Dict[str, float]:
        disk_usage = {}
        
        try:
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_usage[partition.mountpoint] = {
                        'total': usage.total / 1024 / 1024 / 1024,
                        'used': usage.used / 1024 / 1024 / 1024,
                        'free': usage.free / 1024 / 1024 / 1024,
                        'percent': usage.percent
                    }
                except (OSError, PermissionError):
                    continue
        except Exception as e:
            logger.warning(f"Failed to get disk usage: {e}")
        
        return disk_usage
    
    def check_system_requirements(self) -> Dict[str, bool]:
        requirements = {
            'python_version': sys.version_info >= (3, 8),
            'memory_available': self.get_system_info().available_memory >= 2.0,
            'disk_space': self._check_disk_space(),
            'permissions': self._check_permissions()
        }
        
        return requirements
    
    def _check_disk_space(self) -> bool:
        try:
            check_path = os.path.expanduser("~")
            usage = psutil.disk_usage(check_path)
            free_gb = usage.free / 1024 / 1024 / 1024
            return free_gb >= 1.0
        except Exception:
            return True
    
    def _check_permissions(self) -> bool:
        try:
            test_file = os.path.join(os.path.expanduser("~"), ".cursor_free_vip_test")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            return True
        except Exception:
            return False

class EnhancedNetworkManager:
    def __init__(self, timeout: int = 30, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Cursor-Free-VIP/1.0'
        })
    
    def make_request(self, url: str, method: str = 'GET', **kwargs) -> Optional[requests.Response]:
        for attempt in range(self.max_retries):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    timeout=self.timeout,
                    **kwargs
                )
                response.raise_for_status()
                return response
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    logger.error(f"All request attempts failed for {url}")
                    return None
                
                time.sleep(2 ** attempt)
        
        return None
    
    def check_connectivity(self, urls: Optional[List[str]] = None) -> Dict[str, bool]:
        if urls is None:
            urls = [
                'https://www.google.com',
                'https://github.com',
                'https://cursor.sh'
            ]
        
        results = {}
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_url = {
                executor.submit(self._check_single_url, url): url 
                for url in urls
            }
            
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    results[url] = future.result()
                except Exception as e:
                    logger.error(f"Failed to check {url}: {e}")
                    results[url] = False
        
        return results
    
    def _check_single_url(self, url: str) -> bool:
        try:
            response = self.make_request(url, timeout=10)
            return response is not None and response.status_code == 200
        except Exception:
            return False

path_manager = EnhancedPathManager()
browser_manager = EnhancedBrowserManager()
process_manager = EnhancedProcessManager()
system_manager = EnhancedSystemManager()
network_manager = EnhancedNetworkManager()

def get_user_documents_path() -> str:
    return path_manager.get_user_documents_path()

def find_executable(executable_names: List[str]) -> Optional[str]:
    return path_manager.find_executable(executable_names)

def get_default_browser_path(browser_type: str = 'chrome') -> str:
    return browser_manager.get_browser_path(browser_type)

def get_default_driver_path(browser_type: str = 'chrome') -> str:
    return browser_manager.get_driver_path(browser_type)

def parse_time_range(time_str: str) -> Tuple[float, float]:
    try:
        if '-' in time_str:
            parts = time_str.split('-')
            if len(parts) == 2:
                return float(parts[0].strip()), float(parts[1].strip())
        else:
            value = float(time_str.strip())
            return value, value
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to parse time range '{time_str}': {e}")
    
    return 0.5, 1.5

def get_random_wait_time(config: Dict, timing_key: str, default_range: Tuple[float, float] = (0.5, 1.5)) -> float:
    try:
        if timing_key in config:
            time_range = parse_time_range(config[timing_key])
            return random.uniform(time_range[0], time_range[1])
        else:
            return random.uniform(default_range[0], default_range[1])
    except Exception as e:
        logger.warning(f"Failed to get random wait time for {timing_key}: {e}")
        return random.uniform(default_range[0], default_range[1])

def get_linux_cursor_path() -> str:
    possible_paths = [
        "/opt/Cursor/resources/app",
        "/usr/share/cursor/resources/app",
        "/usr/local/share/cursor/resources/app",
        os.path.expanduser("~/.local/share/cursor/resources/app"),
        os.path.expanduser("~/snap/cursor/current/usr/share/cursor/resources/app")
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    cursor_executable = path_manager.find_executable(['cursor'])
    if cursor_executable:
        exec_dir = os.path.dirname(cursor_executable)
        possible_resource_paths = [
            os.path.join(exec_dir, "resources", "app"),
            os.path.join(os.path.dirname(exec_dir), "resources", "app"),
            os.path.join(exec_dir, "..", "resources", "app")
        ]
        
        for path in possible_resource_paths:
            if os.path.exists(path):
                return os.path.abspath(path)
    
    return "" 