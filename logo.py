from colorama import Fore, Style, init
from dotenv import load_dotenv
import os

# Get the current script directory
current_dir = os.path.dirname(os.path.abspath(__file__))
# Build the full path to the .env file
env_path = os.path.join(current_dir, '.env')

# Load environment variables, specifying the .env file path
load_dotenv(env_path)
# Get the version number, using the default value if not found
version = os.getenv('VERSION', '1.0.0')

# Initialize colorama
init()

CURSOR_LOGO = f"""
{Fore.CYAN}
   ██████╗██╗   ██╗██████╗ ███████╗ ██████╗ ██████╗      ██████╗ ██████╗  ██████╗   
  ██╔════╝██║   ██║██╔══██╗██╔════╝██╔═══██╗██╔══██╗     ██╔══██╗██╔══██╗██╔═══██╗  
  ██║     ██║   ██║██████╔╝███████╗██║   ██║██████╔╝     ██████╔╝██████╔╝██║   ██║  
  ██║     ██║   ██║██╔══██╗╚════██║██║   ██║██╔══██╗     ██╔═══╝ ██╔══██╗██║   ██║  
  ╚██████╗╚██████╔╝██║  ██║███████║╚██████╔╝██║  ██║     ██║     ██║  ██║╚██████╔╝  
   ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝     ╚═╝     ╚═╝  ╚═╝ ╚═════╝  
{Fore.YELLOW}
                Pro Version Activator v{version}
{Fore.GREEN}
                Author: Pin Studios | qing-turnaround

      Github: https://github.com/qing-turnaround/cursor-free-vip
{Fore.RED}
        Press 5 to change language | 按下 5 键切换语言
{Style.RESET_ALL}
    """

def print_logo():
    print(CURSOR_LOGO)

if __name__ == "__main__":
    print_logo()