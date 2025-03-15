import os
import time
from colorama import Fore, Style, init
from DrissionPage import ChromiumPage
from cursor_auth import CursorAuth
from reset_machine_manual import MachineIDResetter
from keyring import get_password, set_password
import json

# Initialize colorama
init()

# Define emoji constants
EMOJI = {
    'START': '🚀',
    'FORM': '📝',
    'VERIFY': '🔄',
    'PASSWORD': '🔑',
    'CODE': '📱',
    'DONE': '✨',
    'ERROR': '❌',
    'WAIT': '⏳',
    'SUCCESS': '✅',
    'MAIL': '📧',
    'KEY': '🔐',
    'UPDATE': '🔄',
    'INFO': 'ℹ️'
}

def get_saved_credentials():
    """Get saved GitHub credentials from keyring"""
    try:
        email = get_password('cursor_github', 'email')
        password = get_password('cursor_github', 'password')
        return email, password
    except:
        return None, None

def save_credentials(email, password):
    """Save GitHub credentials to keyring"""
    try:
        set_password('cursor_github', 'email', email)
        set_password('cursor_github', 'password', password)
        return True
    except:
        return False

def extract_auth_data(page, github_email=None):
    """Extract authentication data from page"""
    auth_token = None
    cursor_email = None
    
    print(f"{Fore.CYAN}{EMOJI['INFO']} Extracting authentication data...{Style.RESET_ALL}")
    
    # Get cookies
    cookies = page.cookies()
    for cookie in cookies:
        name = cookie.get("name", "")
        value = cookie.get("value", "")
        if name == "WorkosCursorSessionToken":
            if "::" in value:
                auth_token = value.split("::")[-1]
            elif "%3A%3A" in value:
                auth_token = value.split("%3A%3A")[-1]
        elif name == "cursor_email":
            cursor_email = value

    # Try localStorage if token not found
    if not auth_token:
        try:
            local_storage_token = page.run_js('''
                return localStorage.getItem('WorkosCursorSessionToken') || 
                       localStorage.getItem('cursor_token') || 
                       localStorage.getItem('token');
            ''')
            if local_storage_token:
                auth_token = local_storage_token
        except:
            pass

    # Use GitHub email if cursor_email not found
    if not cursor_email and github_email:
        print(f"{Fore.YELLOW}Using GitHub email as fallback{Style.RESET_ALL}")
        cursor_email = github_email

    return auth_token, cursor_email

def reset_trial(translator=None):
    """Reset trial using GitHub authentication"""
    try:
        print(f"{Fore.CYAN}{EMOJI['INFO']} Setting up automated browser...{Style.RESET_ALL}")

        # Get GitHub credentials
        github_email, github_password = get_saved_credentials()
        if not github_email or not github_password:
            print(f"{Fore.YELLOW}{EMOJI['INFO']} No saved credentials found. Please enter GitHub details:{Style.RESET_ALL}")
            github_email = input(f"{Fore.CYAN}GitHub Email: {Style.RESET_ALL}")
            github_password = input(f"{Fore.CYAN}GitHub Password: {Style.RESET_ALL}")
            
            # Save credentials if user agrees
            if input(f"{Fore.YELLOW}Save credentials for future use? (y/n): {Style.RESET_ALL}").lower() == 'y':
                if save_credentials(github_email, github_password):
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} Credentials saved{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}{EMOJI['ERROR']} Failed to save credentials{Style.RESET_ALL}")

        # Create browser instance
        page = ChromiumPage()
        
        # Navigate to settings page
        print(f"{Fore.CYAN}{EMOJI['INFO']} Navigating to settings page...{Style.RESET_ALL}")
        page.get("https://cursor.sh/settings")
        time.sleep(2)

        # Extract initial auth data
        auth_token, cursor_email = extract_auth_data(page, github_email)
        if not auth_token or not cursor_email:
            print(f"{Fore.RED}{EMOJI['ERROR']} Could not extract authentication data{Style.RESET_ALL}")
            return False

        # Execute reset trial
        print(f"{Fore.CYAN}{EMOJI['INFO']} Executing trial reset...{Style.RESET_ALL}")
        page.run_js('''
            fetch("https://www.cursor.com/api/dashboard/delete-account", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Origin": "https://cursor.sh",
                    "Referer": "https://cursor.sh/settings"
                },
                credentials: "include"
            })
            .then(response => {
                if (response.ok) {
                    window.location.reload();
                } else {
                    console.error("Failed to reset trial");
                }
            })
            .catch(error => {
                console.error("Reset failed:", error);
            });
        ''')

        # Wait for page reload and re-extract auth data
        time.sleep(3)
        auth_token, cursor_email = extract_auth_data(page, github_email)
        
        if auth_token and cursor_email:
            try:
                print(f"{Fore.CYAN}{EMOJI['INFO']} Updating Cursor authentication data...{Style.RESET_ALL}")
                cursor_auth = CursorAuth(translator=translator)
                
                # Update the auth info in Cursor's database
                if cursor_auth.update_auth(
                    email=cursor_email,
                    access_token=auth_token,
                    refresh_token=auth_token  # Use same token for both
                ):
                    print(f"{Fore.GREEN}✅ Authentication data saved - Cursor will auto-login next time{Style.RESET_ALL}")
                    
                    # Reset machine ID after updating auth
                    print(f"{Fore.CYAN}{EMOJI['INFO']} Resetting machine ID...{Style.RESET_ALL}")
                    resetter = MachineIDResetter(translator)
                    if resetter.reset_machine_ids():
                        print(f"{Fore.GREEN}✅ Machine ID reset successful{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.RED}❌ Failed to reset machine ID{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}❌ Failed to save authentication data{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}❌ Failed to save authentication data: {e}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}❌ Could not extract authentication data{Style.RESET_ALL}")
            print(f"Missing data: {' auth_token' if not auth_token else ''}{' cursor_email' if not cursor_email else ''}")
        
        print(f"{Fore.CYAN}ℹ️ Closing Chrome...{Style.RESET_ALL}")
        
        # Close the browser
        try:
            page.quit()
        except:
            pass

        return True

    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} Error during trial reset: {str(e)}{Style.RESET_ALL}")
        return False 