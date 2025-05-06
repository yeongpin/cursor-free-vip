from colorama import Fore, Style, init
import os
import shutil
import re
from project_info import VERSION as version

# Initialize colorama
init()

# get terminal width
def get_terminal_width():
    try:
        columns, _ = shutil.get_terminal_size()/2
        return columns
    except:
        return 80  # default width

# center display text (not handling Chinese characters)
def center_multiline_text(text, handle_chinese=False):
    width = get_terminal_width()
    lines = text.split('\n')
    centered_lines = []
    
    for line in lines:
        # calculate actual display width (remove ANSI color codes)
        clean_line = line
        for color in [Fore.CYAN, Fore.YELLOW, Fore.GREEN, Fore.RED, Fore.BLUE, Style.RESET_ALL]:
            clean_line = clean_line.replace(color, '')
        
        # remove all ANSI escape sequences to get the actual length
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        clean_line = ansi_escape.sub('', clean_line)
        
        # calculate display width
        if handle_chinese:
            # consider Chinese characters occupying two positions
            display_width = 0
            for char in clean_line:
                if ord(char) > 127:  # non-ASCII characters
                    display_width += 2
                else:
                    display_width += 1
        else:
            # not handling Chinese characters
            display_width = len(clean_line)
        
        # calculate the number of spaces to add
        padding = max(0, (width - display_width) // 2)
        centered_lines.append(' ' * padding + line)
    
    return '\n'.join(centered_lines)

# original LOGO text
LOGO_TEXT = f"""{Fore.CYAN}
   ██████╗██╗   ██╗██████╗ ███████╗ ██████╗ ██████╗      ██████╗ ██████╗  ██████╗   
  ██╔════╝██║   ██║██╔══██╗██╔════╝██╔═══██╗██╔══██╗     ██╔══██╗██╔══██╗██╔═══██╗  
  ██║     ██║   ██║██████╔╝███████╗██║   ██║██████╔╝     ██████╔╝██████╔╝██║   ██║  
  ██║     ██║   ██║██╔══██╗╚════██║██║   ██║██╔══██╗     ██╔═══╝ ██╔══██╗██║   ██║  
  ╚██████╗╚██████╔╝██║  ██║███████║╚██████╔╝██║  ██║     ██║     ██║  ██║╚██████╔╝  
   ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝     ╚═╝     ╚═╝  ╚═╝ ╚═════╝  
{Style.RESET_ALL}"""

DESCRIPTION_TEXT = f"""{Fore.YELLOW}
Pro Version Activator v{version}{Fore.GREEN}
Author: Pin Studios (yeongpin)"""

CONTRIBUTORS_TEXT = f"""{Fore.BLUE}
Contributors:
BasaiCorp  aliensb  handwerk2016  Nigel1992
UntaDotMy  RenjiYuusei  imbajin  ahmed98Osama
bingoohuang  mALIk-sHAHId  MFaiqKhan  httpmerak
muhammedfurkan plamkatawe Lucaszmv
"""
OTHER_INFO_TEXT = f"""{Fore.YELLOW}
Github: https://github.com/yeongpin/cursor-free-vip{Fore.RED}
Press 4 to change language | 按下 4 键切换语言{Style.RESET_ALL}"""

# center display LOGO and DESCRIPTION
CURSOR_LOGO = center_multiline_text(LOGO_TEXT, handle_chinese=False)
CURSOR_DESCRIPTION = center_multiline_text(DESCRIPTION_TEXT, handle_chinese=False)
CURSOR_CONTRIBUTORS = center_multiline_text(CONTRIBUTORS_TEXT, handle_chinese=False)
CURSOR_OTHER_INFO = center_multiline_text(OTHER_INFO_TEXT, handle_chinese=True)

def print_logo():
    print(CURSOR_LOGO)
    print(CURSOR_DESCRIPTION)
    # print(CURSOR_CONTRIBUTORS)
    print(CURSOR_OTHER_INFO)

if __name__ == "__main__":
    print_logo()
