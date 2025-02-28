import os
from colorama import Fore, Style, init
import time
import random
from browser import BrowserManager
from control import BrowserControl
from cursor_auth import CursorAuth
from reset_machine_manual import MachineIDResetter

os.environ["PYTHONVERBOSE"] = "0"
os.environ["PYINSTALLER_VERBOSE"] = "0"

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

class CursorRegistration:
    def __init__(self, translator=None):
        self.translator = translator
        # Set to display mode
        os.environ['BROWSER_HEADLESS'] = 'False'
        self.browser_manager = BrowserManager()
        self.browser = None
        self.controller = None
        self.sign_up_url = "https://authenticator.cursor.sh/sign-up"
        self.settings_url = "https://www.cursor.com/settings"
        self.email_address = None
        self.signup_tab = None
        self.email_tab = None
        
        # Account information
        self.password = self._generate_password()
        self.first_name = self._generate_name()
        self.last_name = self._generate_name()
        print(f"Password: {self.password}\n")
        print(f"First Name: {self.first_name}\n")
        print(f"Last Name: {self.last_name}\n")

    def _generate_password(self, length=12):
        """Generate Random Password"""
        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
        return ''.join(random.choices(chars, k=length))

    def _generate_name(self, length=6):
        """Generate Random Name"""
        first_letter = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        rest_letters = ''.join(random.choices("abcdefghijklmnopqrstuvwxyz", k=length-1))
        return first_letter + rest_letters

    def setup_email(self):
        """Setup Email"""
        try:
            print(f"{Fore.CYAN}{EMOJI['START']} {self.translator.get('register.manual_email_input') if self.translator else 'Please enter your email address:'}")
            self.email_address = input().strip()
            
            if '@' not in self.email_address:
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('register.invalid_email') if self.translator else '无效的邮箱地址'}{Style.RESET_ALL}")
                return False
                
            print(f"Email Address: {self.email_address}\n")
            return True
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('register.email_setup_failed', error=str(e))}{Style.RESET_ALL}")
            return False

    def get_verification_code(self):
        """Manually Get Verification Code"""
        try:
            print(f"{Fore.CYAN}{EMOJI['CODE']} {self.translator.get('register.manual_code_input') if self.translator else 'Please enter the verification code:'}")
            code = input().strip()
            
            if not code.isdigit() or len(code) != 6:
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('register.invalid_code') if self.translator else '无效的验证码'}{Style.RESET_ALL}")
                return None
                
            return code
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('register.code_input_failed', error=str(e))}{Style.RESET_ALL}")
            return None

    def register_cursor(self):
        """Register Cursor"""
        browser_tab = None
        try:
            print(f"{Fore.CYAN}{EMOJI['START']} {self.translator.get('register.register_start')}...{Style.RESET_ALL}")
            
            # Use new_signup.py directly for registration
            from new_signup import main as new_signup_main
            
            # Execute new registration process, passing translator
            result, browser_tab = new_signup_main(
                email=self.email_address,
                password=self.password,
                first_name=self.first_name,
                last_name=self.last_name,
                email_tab=None,  # No email tab needed
                controller=self,  # Pass self instead of self.controller
                translator=self.translator
            )
            
            if result:
                # Use the returned browser instance to get account information
                self.signup_tab = browser_tab  # Save browser instance
                success = self._get_account_info()
                
                # Close browser after getting information
                if browser_tab:
                    try:
                        browser_tab.quit()
                    except:
                        pass
                
                return success
            
            return False
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('register.register_process_error', error=str(e))}{Style.RESET_ALL}")
            return False
        finally:
            # Ensure browser is closed in any case
            if browser_tab:
                try:
                    browser_tab.quit()
                except:
                    pass
                
    def _get_account_info(self):
        """Get Account Information and Token"""
        try:
            self.signup_tab.get(self.settings_url)
            time.sleep(2)
            
            usage_selector = (
                "css:div.col-span-2 > div > div > div > div > "
                "div:nth-child(1) > div.flex.items-center.justify-between.gap-2 > "
                "span.font-mono.text-sm\\/\\[0\\.875rem\\]"
            )
            usage_ele = self.signup_tab.ele(usage_selector)
            total_usage = "未知"
            if usage_ele:
                total_usage = usage_ele.text.split("/")[-1].strip()

            print(f"Total Usage: {total_usage}\n")
            print(f"{Fore.CYAN}{EMOJI['WAIT']} {self.translator.get('register.get_token')}...{Style.RESET_ALL}")
            max_attempts = 30
            retry_interval = 2
            attempts = 0

            while attempts < max_attempts:
                try:
                    cookies = self.signup_tab.cookies()
                    for cookie in cookies:
                        if cookie.get("name") == "WorkosCursorSessionToken":
                            token = cookie["value"].split("%3A%3A")[1]
                            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('register.token_success')}{Style.RESET_ALL}")
                            self._save_account_info(token, total_usage)
                            return True

                    attempts += 1
                    if attempts < max_attempts:
                        print(f"{Fore.YELLOW}{EMOJI['WAIT']} {self.translator.get('register.token_attempt', attempt=attempts, time=retry_interval)}{Style.RESET_ALL}")
                        time.sleep(retry_interval)
                    else:
                        print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('register.token_max_attempts', max=max_attempts)}{Style.RESET_ALL}")

                except Exception as e:
                    print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('register.token_failed', error=str(e))}{Style.RESET_ALL}")
                    attempts += 1
                    if attempts < max_attempts:
                        print(f"{Fore.YELLOW}{EMOJI['WAIT']} {self.translator.get('register.token_attempt', attempt=attempts, time=retry_interval)}{Style.RESET_ALL}")
                        time.sleep(retry_interval)

            return False

        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('register.account_error', error=str(e))}{Style.RESET_ALL}")
            return False

    def _save_account_info(self, token, total_usage):
        """Save Account Information to File"""
        try:
            # Update authentication information first
            print(f"{Fore.CYAN}{EMOJI['KEY']} {self.translator.get('register.update_cursor_auth_info')}...{Style.RESET_ALL}")
            if self.update_cursor_auth(email=self.email_address, access_token=token, refresh_token=token):
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('register.cursor_auth_info_updated')}...{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('register.cursor_auth_info_update_failed')}...{Style.RESET_ALL}")

            # Reset machine ID
            print(f"{Fore.CYAN}{EMOJI['UPDATE']} {self.translator.get('register.reset_machine_id')}...{Style.RESET_ALL}")
            resetter = MachineIDResetter(self.translator)  # Create instance with translator
            if not resetter.reset_machine_ids():  # Call reset_machine_ids method directly
                raise Exception("Failed to reset machine ID")
            
            # Save account information to file
            with open('cursor_accounts.txt', 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*50}\n")
                f.write(f"Email: {self.email_address}\n")
                f.write(f"Password: {self.password}\n")
                f.write(f"Token: {token}\n")
                f.write(f"Usage Limit: {total_usage}\n")
                f.write(f"{'='*50}\n")
                
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('register.account_info_saved')}...{Style.RESET_ALL}")
            return True
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('register.save_account_info_failed', error=str(e))}{Style.RESET_ALL}")
            return False

    def start(self):
        """Start Registration Process"""
        try:
            if self.setup_email():
                if self.register_cursor():
                    print(f"\n{Fore.GREEN}{EMOJI['DONE']} {self.translator.get('register.cursor_registration_completed')}...{Style.RESET_ALL}")
                    return True
            return False
        finally:
            # Close email tab
            if hasattr(self, 'temp_email'):
                try:
                    self.temp_email.close()
                except:
                    pass

    def update_cursor_auth(self, email=None, access_token=None, refresh_token=None):
        """Convenient function to update Cursor authentication information"""
        auth_manager = CursorAuth(translator=self.translator)
        return auth_manager.update_auth(email, access_token, refresh_token)

def main(translator=None):
    """Main function to be called from main.py"""
    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{EMOJI['START']} {translator.get('register.title')}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")

    registration = CursorRegistration(translator)
    registration.start()

    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    input(f"{EMOJI['INFO']} {translator.get('register.press_enter')}...")

if __name__ == "__main__":
    from main import translator as main_translator
    main(main_translator) 