import sys
import platform
import logging
from colorama import Fore, Style, init
from typing import Optional, Dict, List, Any, Tuple, Union

# Initialize colorama
init(autoreset=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Current version
version = "1.9.9"

# ASCII art logo
LOGO = f"""
{Fore.CYAN}
 ██████╗██╗   ██╗██████╗ ███████╗ ██████╗ ██████╗     ███████╗██████╗ ███████╗███████╗    ██╗   ██╗██╗██████╗ 
██╔════╝██║   ██║██╔══██╗██╔════╝██╔═══██╗██╔══██╗    ██╔════╝██╔══██╗██╔════╝██╔════╝    ██║   ██║██║██╔══██╗
██║     ██║   ██║██████╔╝███████╗██║   ██║██████╔╝    █████╗  ██████╔╝█████╗  █████╗      ██║   ██║██║██████╔╝
██║     ██║   ██║██╔══██╗╚════██║██║   ██║██╔══██╗    ██╔══╝  ██╔══██╗██╔══╝  ██╔══╝      ╚██╗ ██╔╝██║██╔═══╝ 
╚██████╗╚██████╔╝██║  ██║███████║╚██████╔╝██║  ██║    ██║     ██║  ██║███████╗███████╗     ╚████╔╝ ██║██║     
 ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝    ╚═╝     ╚═╝  ╚═╝╚══════╝╚══════╝      ╚═══╝  ╚═╝╚═╝     
{Style.RESET_ALL}"""

# Simplified logo for terminals with limited width
SIMPLIFIED_LOGO = f"""
{Fore.CYAN}
 ██████╗██╗   ██╗██████╗ ███████╗ ██████╗ ██████╗ 
██╔════╝██║   ██║██╔══██╗██╔════╝██╔═══██╗██╔══██╗
██║     ██║   ██║██████╔╝███████╗██║   ██║██████╔╝
██║     ██║   ██║██╔══██╗╚════██║██║   ██║██╔══██╗
╚██████╗╚██████╔╝██║  ██║███████║╚██████╔╝██║  ██║
 ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝
{Fore.GREEN}FREE VIP {version}{Style.RESET_ALL}
{Style.RESET_ALL}"""

# Contributors info
CURSOR_CONTRIBUTORS = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════════════╗
║                        {Fore.YELLOW}CURSOR FREE VIP{Fore.CYAN}                          ║
╠══════════════════════════════════════════════════════════════════╣
║ {Fore.GREEN}Author:{Fore.WHITE}  yeongpin                                            {Fore.CYAN}║
║ {Fore.GREEN}GitHub:{Fore.WHITE}  https://github.com/yeongpin/cursor-free-vip         {Fore.CYAN}║
║ {Fore.GREEN}Version:{Fore.WHITE} {version}                                            {Fore.CYAN}║
╚══════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""

def get_terminal_width() -> int:
    """Get terminal width with fallback for different platforms.
    
    Returns:
        int: Terminal width in characters
    """
    try:
        # Try to get terminal size using different methods based on platform
        if platform.system() == "Windows":
            from shutil import get_terminal_size
            columns = get_terminal_size().columns
        else:
            import os
            columns = os.get_terminal_size().columns
        
        return columns
    except Exception as e:
        logger.warning(f"Failed to get terminal width: {e}")
        # Default width if detection fails
        return 80

def print_logo() -> None:
    """Print logo with version information based on terminal width."""
    try:
        # Get terminal width
        terminal_width = get_terminal_width()
        
        # Choose logo based on terminal width
        if terminal_width < 100:
            logo = SIMPLIFIED_LOGO
        else:
            logo = LOGO
            
        # Print logo
        print(logo)
        
        # Print version info
        print(f"{Fore.GREEN}Version: {version}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'═' * min(80, terminal_width)}{Style.RESET_ALL}")
        
    except Exception as e:
        logger.error(f"Error printing logo: {e}")
        # Fallback to simplified version if any error occurs
        print(SIMPLIFIED_LOGO)
        print(f"{Fore.GREEN}Version: {version}{Style.RESET_ALL}")

if __name__ == "__main__":
    print_logo()
    print(CURSOR_CONTRIBUTORS)
