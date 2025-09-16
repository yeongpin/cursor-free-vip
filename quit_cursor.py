import psutil
import time
import logging
import platform
import sys
import os
from colorama import Fore, Style, init
from typing import Optional, Dict, List, Any, Tuple, Union, Set

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
    "PROCESS": "⚙️",
    "SUCCESS": "✅",
    "ERROR": "❌",
    "INFO": "ℹ️",
    "WAIT": "⏳",
    "KILL": "🛑",
    "SEARCH": "🔍"
}

class CursorQuitter:
    """Class to handle termination of Cursor processes."""
    
    def __init__(self, timeout: int = 5, translator: Any = None):
        """Initialize CursorQuitter.
        
        Args:
            timeout: Maximum time to wait for processes to terminate naturally
            translator: Optional translator for internationalization
        """
        self.timeout = max(1, timeout)  # Ensure timeout is at least 1 second
        self.translator = translator
        
    def _get_message(self, key: str, fallback: str, **kwargs) -> str:
        """Get translated message or fallback.
        
        Args:
            key: Translation key
            fallback: Fallback message if translation not available
            **kwargs: Format parameters for the message
            
        Returns:
            str: Translated or fallback message
        """
        if self.translator:
            return self.translator.get(key, **kwargs)
        return fallback.format(**kwargs) if kwargs else fallback
        
    def _find_cursor_processes(self) -> List[psutil.Process]:
        """Find all Cursor processes.
        
        Returns:
            List[psutil.Process]: List of Cursor processes
        """
        cursor_processes = []
        cursor_names = {
            'windows': ['cursor.exe', 'cursor helper.exe', 'cursor crash handler.exe'],
            'darwin': ['Cursor', 'Cursor Helper', 'Cursor Crash Handler'],
            'linux': ['cursor', 'cursor-helper', 'cursor-crash-handler']
        }
        
        # Get platform-specific process names
        system = platform.system().lower()
        if system in cursor_names:
            target_names = cursor_names[system]
        else:
            # Fallback to all possible names
            target_names = [name for names in cursor_names.values() for name in names]
            
        logger.info(f"Looking for Cursor processes with names: {target_names}")
        print(f"{Fore.CYAN}{EMOJI['SEARCH']} {self._get_message('quit_cursor.searching', 'Searching for Cursor processes...')}{Style.RESET_ALL}")
            
        # Collect all Cursor processes
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                proc_name = proc.info['name'].lower() if proc.info['name'] else ""
                
                # Check process name
                if any(target.lower() in proc_name for target in target_names):
                    cursor_processes.append(proc)
                    continue
                    
                # Check command line for additional detection
                if proc.info['cmdline']:
                    cmdline = " ".join(proc.info['cmdline']).lower()
                    if 'cursor' in cmdline and ('electron' in cmdline or 'app' in cmdline):
                        cursor_processes.append(proc)
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied, Exception) as e:
                logger.warning(f"Error accessing process: {e}")
                continue
                
        return cursor_processes
        
    def quit_cursor(self) -> bool:
        """Gently close Cursor processes.
        
        Returns:
            bool: True if all processes were terminated successfully, False otherwise
        """
        try:
            msg = self._get_message('quit_cursor.start', 'Attempting to close Cursor processes')
            logger.info(msg)
            print(f"{Fore.CYAN}{EMOJI['PROCESS']} {msg}...{Style.RESET_ALL}")
            
            # Find Cursor processes
            cursor_processes = self._find_cursor_processes()
            
            if not cursor_processes:
                msg = self._get_message('quit_cursor.no_process', 'No Cursor processes found')
                logger.info(msg)
                print(f"{Fore.GREEN}{EMOJI['INFO']} {msg}{Style.RESET_ALL}")
                return True

            # Log found processes
            logger.info(f"Found {len(cursor_processes)} Cursor processes")
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self._get_message('quit_cursor.processes_found', 'Found {count} Cursor processes', count=len(cursor_processes))}{Style.RESET_ALL}")
            
            # Gently request processes to terminate
            for proc in cursor_processes:
                try:
                    if proc.is_running():
                        msg = self._get_message('quit_cursor.terminating', 'Terminating process {pid}', pid=proc.pid)
                        logger.info(f"Terminating process {proc.pid}")
                        print(f"{Fore.YELLOW}{EMOJI['PROCESS']} {msg}...{Style.RESET_ALL}")
                        proc.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied, Exception) as e:
                    logger.warning(f"Error terminating process {proc.pid}: {e}")
                    continue

            # Wait for processes to terminate naturally
            msg = self._get_message('quit_cursor.waiting', f'Waiting up to {self.timeout} seconds for processes to close')
            logger.info(f"Waiting up to {self.timeout} seconds for processes to close")
            print(f"{Fore.CYAN}{EMOJI['WAIT']} {msg}...{Style.RESET_ALL}")
            
            start_time = time.time()
            while time.time() - start_time < self.timeout:
                still_running = []
                for proc in cursor_processes:
                    try:
                        if proc.is_running():
                            still_running.append(proc)
                    except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
                        continue
                
                if not still_running:
                    msg = self._get_message('quit_cursor.success', 'All Cursor processes have been closed successfully')
                    logger.info("All Cursor processes have been closed successfully")
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {msg}{Style.RESET_ALL}")
                    return True
                    
                time.sleep(0.5)
                
            # If processes are still running after timeout, try to kill them
            if still_running:
                process_list = ", ".join([str(p.pid) for p in still_running])
                msg = self._get_message('quit_cursor.timeout', 'Timeout reached. Some processes are still running: {pids}', pids=process_list)
                logger.warning(f"Timeout reached. Still running: {process_list}")
                print(f"{Fore.YELLOW}{EMOJI['WAIT']} {msg}{Style.RESET_ALL}")
                
                # Try to kill remaining processes
                print(f"{Fore.RED}{EMOJI['KILL']} {self._get_message('quit_cursor.force_kill', 'Attempting to force kill remaining processes')}{Style.RESET_ALL}")
                for proc in still_running:
                    try:
                        if proc.is_running():
                            logger.info(f"Force killing process {proc.pid}")
                            proc.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied, Exception) as e:
                        logger.error(f"Error killing process {proc.pid}: {e}")
                        continue
                
                # Check if all processes are now killed
                time.sleep(1)
                final_check = [p for p in still_running if p.is_running()]
                if not final_check:
                    msg = self._get_message('quit_cursor.force_success', 'All Cursor processes have been forcefully terminated')
                    logger.info("All Cursor processes have been forcefully terminated")
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {msg}{Style.RESET_ALL}")
                    return True
                else:
                    failed_list = ", ".join([str(p.pid) for p in final_check])
                    msg = self._get_message('quit_cursor.force_failed', 'Failed to terminate some processes: {pids}', pids=failed_list)
                    logger.error(f"Failed to terminate processes: {failed_list}")
                    print(f"{Fore.RED}{EMOJI['ERROR']} {msg}{Style.RESET_ALL}")
                    return False
                
            return True

        except Exception as e:
            logger.error(f"Error in quit_cursor: {e}")
            msg = self._get_message('quit_cursor.error', 'An error occurred: {error}', error=str(e))
            print(f"{Fore.RED}{EMOJI['ERROR']} {msg}{Style.RESET_ALL}")
            return False

def quit_cursor(translator: Any = None, timeout: int = 5) -> bool:
    """Convenient function for directly calling the quit function.
    
    Args:
        translator: Optional translator for internationalization
        timeout: Maximum time to wait for processes to terminate naturally
        
    Returns:
        bool: True if all processes were terminated successfully, False otherwise
    """
    try:
        quitter = CursorQuitter(timeout, translator)
        return quitter.quit_cursor()
    except Exception as e:
        logger.error(f"Error in quit_cursor function: {e}")
        print(f"{Fore.RED}{EMOJI['ERROR']} An unexpected error occurred: {str(e)}{Style.RESET_ALL}")
        return False

if __name__ == "__main__":
    try:
        # If run directly, try to use the default translator
        try:
            from main import translator as main_translator
            result = quit_cursor(main_translator)
        except ImportError:
            logger.warning("Failed to import translator from main.py, running without translation")
            result = quit_cursor()
            
        # Exit with appropriate status code
        sys.exit(0 if result else 1)
    except Exception as e:
        logger.critical(f"Critical error: {e}")
        print(f"{Fore.RED}{EMOJI['ERROR']} Critical error: {str(e)}{Style.RESET_ALL}")
        sys.exit(1)