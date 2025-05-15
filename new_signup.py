from DrissionPage import ChromiumOptions, ChromiumPage
import time
import os
import signal
import random
from colorama import Fore, Style
import configparser
from pathlib import Path
import sys
from config import get_config 
from utils import get_default_browser_path as utils_get_default_browser_path
from utils import ProgressBar

# Add global variable at the beginning of the file
_translator = None

# Add global variable to track our Chrome processes
_chrome_process_ids = []

def cleanup_chrome_processes(translator=None):
    """Clean only Chrome processes launched by this script"""
    global _chrome_process_ids
    
    if not _chrome_process_ids:
        print("\nNo Chrome processes to clean...")
        return
        
    print("\nCleaning Chrome processes launched by this script...")
    try:
        if os.name == 'nt':
            for pid in _chrome_process_ids:
                try:
                    os.system(f'taskkill /F /PID {pid} /T 2>nul')
                except:
                    pass
        else:
            for pid in _chrome_process_ids:
                try:
                    os.kill(pid, signal.SIGTERM)
                except:
                    pass
        _chrome_process_ids = []  # Reset the list after cleanup
    except Exception as e:
        if translator:
            print(f"{Fore.RED}❌ {translator.get('register.cleanup_error', error=str(e))}{Style.RESET_ALL}")
        else:
            print(f"清理进程时出错: {e}")

def signal_handler(signum, frame):
    """Handle Ctrl+C signal"""
    global _translator
    if _translator:
        print(f"{Fore.CYAN}{_translator.get('register.exit_signal')}{Style.RESET_ALL}")
    else:
        print("\n接收到退出信号，正在关闭...")
    cleanup_chrome_processes(_translator)
    os._exit(0)

def simulate_human_input(page, url, config, translator=None):
    """Visit URL"""
    if translator:
        print(f"{Fore.CYAN}🚀 {translator.get('register.visiting_url')}: {url}{Style.RESET_ALL}")
    
    # First visit blank page
    page.get('about:blank')
    time.sleep(get_random_wait_time(config, 'page_load_wait'))
    
    # Visit target page
    page.get(url)
    time.sleep(get_random_wait_time(config, 'page_load_wait'))

def fill_signup_form(page, first_name, last_name, email, config, translator=None):
    """Fill signup form"""
    pb = ProgressBar("Filling registration form...")
    pb.start()
    try:
        if translator:
            print(f"{Fore.CYAN}📧 {translator.get('register.filling_form')}{Style.RESET_ALL}")
        else:
            print("\n正在填写注册表单...")
        # Fill first name
        first_name_input = page.ele("@name=first_name")
        if first_name_input:
            first_name_input.input(first_name)
            time.sleep(get_random_wait_time(config, 'input_wait'))
        # Fill last name
        last_name_input = page.ele("@name=last_name")
        if last_name_input:
            last_name_input.input(last_name)
            time.sleep(get_random_wait_time(config, 'input_wait'))
        # Fill email
        email_input = page.ele("@name=email")
        if email_input:
            email_input.input(email)
            time.sleep(get_random_wait_time(config, 'input_wait'))
        # Click submit button
        submit_button = page.ele("@type=submit")
        if submit_button:
            submit_button.click()
            time.sleep(get_random_wait_time(config, 'submit_wait'))
        pb.stop("Form filled!")
        if translator:
            print(f"{Fore.GREEN}✅ {translator.get('register.form_success')}{Style.RESET_ALL}")
        else:
            print("Form filled successfully")
        return True
    except Exception as e:
        pb.stop("Form fill failed!")
        if translator:
            print(f"{Fore.RED}❌ {translator.get('register.form_error', error=str(e))}{Style.RESET_ALL}")
        else:
            print(f"Error filling form: {e}")
        return False

def get_user_documents_path():
    """Get user Documents folder path"""
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Shell Folders") as key:
                documents_path, _ = winreg.QueryValueEx(key, "Personal")
                return documents_path
        except Exception as e:
            # fallback
            return os.path.join(os.path.expanduser("~"), "Documents")
    elif sys.platform == "darwin":
        return os.path.join(os.path.expanduser("~"), "Documents")
    else:  # Linux
        # Get actual user's home directory
        sudo_user = os.environ.get('SUDO_USER')
        if sudo_user:
            return os.path.join("/home", sudo_user, "Documents")
        return os.path.join(os.path.expanduser("~"), "Documents")

def get_random_wait_time(config, timing_type='page_load_wait'):
    """
    Get random wait time from config
    Args:
        config: ConfigParser object
        timing_type: Type of timing to get (page_load_wait, input_wait, submit_wait)
    Returns:
        float: Random wait time or fixed time
    """
    try:
        if not config.has_section('Timing'):
            return random.uniform(0.1, 0.8)  # Default value
            
        if timing_type == 'random':
            min_time = float(config.get('Timing', 'min_random_time', fallback='0.1'))
            max_time = float(config.get('Timing', 'max_random_time', fallback='0.8'))
            return random.uniform(min_time, max_time)
            
        time_value = config.get('Timing', timing_type, fallback='0.1-0.8')
        
        # Check if it's a fixed time value
        if '-' not in time_value and ',' not in time_value:
            return float(time_value)  # Return fixed time
            
        # Process range time
        min_time, max_time = map(float, time_value.split('-' if '-' in time_value else ','))
        return random.uniform(min_time, max_time)
    except:
        return random.uniform(0.1, 0.8)  # Return default value when error

def setup_driver(translator=None):
    """Setup browser driver"""
    global _chrome_process_ids
    
    try:
        # Get config
        config = get_config(translator)
        if not config:
            raise Exception("Config could not be loaded. Please check your config file.")
        # Ensure [Browser] section and defaults exist
        if not config.has_section('Browser'):
            config.add_section('Browser')
        if not config.has_option('Browser', 'default_browser'):
            config.set('Browser', 'default_browser', 'chrome')
        if not config.has_option('Browser', 'chrome_path'):
            config.set('Browser', 'chrome_path', utils_get_default_browser_path('chrome'))
        
        # Get browser type and path
        browser_type = config.get('Browser', 'default_browser', fallback='chrome')
        browser_path = config.get('Browser', f'{browser_type}_path', fallback=utils_get_default_browser_path(browser_type))
        
        if not browser_path or not os.path.exists(browser_path):
            if translator:
                print(f"{Fore.YELLOW}⚠️ {browser_type} {translator.get('register.browser_path_invalid')}{Style.RESET_ALL}")
            browser_path = utils_get_default_browser_path(browser_type)

        # For backward compatibility, also check Chrome path
        if browser_type == 'chrome':
            chrome_path = config.get('Chrome', 'chromepath', fallback=None)
            if chrome_path and os.path.exists(chrome_path):
                browser_path = chrome_path

        # Set browser options
        co = ChromiumOptions()
        
        # Set browser path
        co.set_browser_path(browser_path)
        
        # Use incognito mode
        co.set_argument("--incognito")

        if sys.platform == "linux":
            # Set Linux specific options
            co.set_argument("--no-sandbox")
            
        # Stealth: Add arguments to mask automation (keep for anti-bot, but not headless)
        co.set_argument("--disable-blink-features=AutomationControlled")
        co.set_argument("--disable-infobars")
        co.set_argument("--disable-dev-shm-usage")
        co.set_argument("--disable-gpu")
        co.set_argument("--disable-extensions")
        co.set_argument("--disable-default-apps")
        co.set_argument("--disable-popup-blocking")
        co.set_argument("--disable-notifications")
        co.set_argument("--disable-translate")
        co.set_argument("--disable-background-networking")
        co.set_argument("--disable-background-timer-throttling")
        co.set_argument("--disable-backgrounding-occluded-windows")
        co.set_argument("--disable-breakpad")
        co.set_argument("--disable-client-side-phishing-detection")
        co.set_argument("--disable-component-extensions-with-background-pages")
        co.set_argument("--disable-features=site-per-process,TranslateUI")
        co.set_argument("--disable-hang-monitor")
        co.set_argument("--disable-ipc-flooding-protection")
        co.set_argument("--disable-prompt-on-repost")
        co.set_argument("--disable-renderer-backgrounding")
        co.set_argument("--disable-sync")
        co.set_argument("--metrics-recording-only")
        co.set_argument("--no-first-run")
        co.set_argument("--safebrowsing-disable-auto-update")
        co.set_argument("--password-store=basic")
        co.set_argument("--use-mock-keychain")
        # Set a common user-agent
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        co.set_argument(f"--user-agent={user_agent}")
        
        # Set random port
        co.auto_port()
        
        # Do NOT use headless mode
        co.headless(False)
        if translator:
            print(f"{'[Visible]'} browser mode enabled.")
        
        # Log browser info
        if translator:
            print(f"{Fore.CYAN}🌐 {translator.get('register.using_browser', browser=browser_type, path=browser_path)}{Style.RESET_ALL}")
        
        try:
            # Load extension
            extension_path = os.path.join(os.getcwd(), "turnstilePatch")
            if os.path.exists(extension_path):
                co.set_argument("--allow-extensions-in-incognito")
                co.add_extension(extension_path)
        except Exception as e:
            if translator:
                print(f"{Fore.RED}❌ {translator.get('register.extension_load_error', error=str(e))}{Style.RESET_ALL}")
            else:
                print(f"Error loading extension: {e}")
        
        if translator:
            print(f"{Fore.CYAN}🚀 {translator.get('register.starting_browser')}{Style.RESET_ALL}")
        else:
            print("Starting browser...")
        
        # Record Chrome processes before launching
        before_pids = []
        try:
            import psutil
            browser_process_names = {
                'chrome': ['chrome', 'chromium'],
                'edge': ['msedge', 'edge'],
                'firefox': ['firefox'],
                'brave': ['brave', 'brave-browser']
            }
            process_names = browser_process_names.get(browser_type, ['chrome'])
            before_pids = [p.pid for p in psutil.process_iter() if any(name in p.name().lower() for name in process_names)]
        except:
            pass
            
        # Launch browser with progress bar
        pb = ProgressBar("Starting browser...")
        pb.start()
        page = ChromiumPage(co)
        # Patch navigator.webdriver to false
        try:
            page.run_js("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        except Exception as e:
            if translator:
                print(f"{Fore.YELLOW}⚠️ JS stealth patch failed: {e}{Style.RESET_ALL}")
        time.sleep(1)
        pb.stop("Browser started!")
        
        # Record browser processes after launching and find new ones
        try:
            import psutil
            process_names = browser_process_names.get(browser_type, ['chrome'])
            after_pids = [p.pid for p in psutil.process_iter() if any(name in p.name().lower() for name in process_names)]
            # Find new browser processes
            new_pids = [pid for pid in after_pids if pid not in before_pids]
            _chrome_process_ids.extend(new_pids)
            
            if _chrome_process_ids:
                print(f"{translator.get('register.tracking_processes', count=len(_chrome_process_ids), browser=browser_type)}")
            else:
                print(f"{Fore.YELLOW}Warning: {translator.get('register.no_new_processes_detected', browser=browser_type)}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{translator.get('register.could_not_track_processes', browser=browser_type, error=str(e))}")
            
        return config, page

    except Exception as e:
        if translator:
            print(f"{Fore.RED}❌ {translator.get('register.browser_setup_error', error=str(e))}{Style.RESET_ALL}")
        else:
            print(f"Error setting up browser: {e}")
        raise

def handle_turnstile(page, config, translator=None):
    """Handle Turnstile verification"""
    pb = ProgressBar("Verifying human...")
    pb.start()
    try:
        if translator:
            print(f"\n{Fore.CYAN}🔄 {translator.get('register.handling_turnstile')}{Style.RESET_ALL}")
        else:
            print("\nProcessing security verification...\n")
        # Default: wait 5s after each attempt, random wait 3-7s between retries
        turnstile_time = float(config.get('Turnstile', 'handle_turnstile_time', fallback='5'))
        random_time_str = config.get('Turnstile', 'handle_turnstile_random_time', fallback='3-7')
        # Parse random time range
        try:
            min_time, max_time = map(float, random_time_str.split('-'))
        except:
            min_time, max_time = 3, 7  # Default value
        max_retries = 4  # Increased patience: more retries
        retry_count = 0
        while retry_count < max_retries:
            retry_count += 1
            if translator:
                print(f"\n{Fore.CYAN}🔄 {translator.get('register.retry_verification', attempt=retry_count)}{Style.RESET_ALL}")
            else:
                print(f"\nRetrying verification... (Attempt {retry_count})\n")
            try:
                # Try to reset turnstile
                page.run_js("try { turnstile.reset() } catch(e) { }")
                time.sleep(turnstile_time)  # from config
                # Locate verification box element
                challenge_check = (
                    page.ele("@id=cf-turnstile", timeout=2)
                    .child()
                    .shadow_root.ele("tag:iframe")
                    .ele("tag:body")
                    .sr("tag:input")
                )
                if challenge_check:
                    if translator:
                        print(f"\n{Fore.CYAN}🔄 {translator.get('register.detect_turnstile')}{Style.RESET_ALL}")
                    else:
                        print("\nDetected security verification...\n")
                    # from config
                    time.sleep(random.uniform(min_time, max_time))
                    challenge_check.click()
                    time.sleep(turnstile_time)  # from config
                    # check verification result
                    if check_verification_success(page, translator):
                        pb.stop("Verification passed!")
                        if translator:
                            print(f"\n{Fore.GREEN}✅ {translator.get('register.verification_success')}{Style.RESET_ALL}\n")
                        else:
                            print("\nVerification successful!\n")
                        return True
            except Exception as e:
                if translator:
                    print(f"\n{Fore.RED}❌ {translator.get('register.verification_failed')}{Style.RESET_ALL}\n")
                else:
                    print(f"\nVerification attempt failed.\n")
            # Check if verification has been successful
            if check_verification_success(page, translator):
                pb.stop("Verification passed!")
                if translator:
                    print(f"\n{Fore.GREEN}✅ {translator.get('register.verification_success')}{Style.RESET_ALL}\n")
                else:
                    print("\nVerification successful!\n")
                return True
            time.sleep(random.uniform(min_time, max_time))
        pb.stop("Verification failed!")
        if translator:
            print(f"\n{Fore.RED}❌ {translator.get('register.verification_failed')}{Style.RESET_ALL}\n")
        else:
            print("\nExceeded maximum retry attempts.\n")
        print("\n[!] Automated verification failed. This is likely due to advanced anti-bot protection.\nIf you see a CAPTCHA or human verification, please solve it manually in the browser, or consider integrating a CAPTCHA-solving service.\n")
        return False
    except Exception as e:
        pb.stop("Verification error!")
        if translator:
            print(f"\n{Fore.RED}❌ {translator.get('register.verification_error', error=str(e))}{Style.RESET_ALL}\n")
        else:
            print(f"\nError in verification process: {e}\n")
        return False

def check_verification_success(page, translator=None):
    """Check if verification is successful"""
    try:
        # Check if there is a subsequent form element, indicating verification has passed
        if (page.ele("@name=password", timeout=0.5) or 
            page.ele("@name=email", timeout=0.5) or
            page.ele("@data-index=0", timeout=0.5) or
            page.ele("Account Settings", timeout=0.5)):
            return True
        
        # Check if there is an error message
        error_messages = [
            'xpath://div[contains(text(), "Can\'t verify the user is human")]',
            'xpath://div[contains(text(), "Error: 600010")]',
            'xpath://div[contains(text(), "Please try again")]'
        ]
        
        for error_xpath in error_messages:
            if page.ele(error_xpath):
                return False
            
        return False
    except:
        return False

def generate_password(length=12):
    """Generate random password"""
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
    return ''.join(random.choices(chars, k=length))

def fill_password(page, password: str, config, translator=None):
    """
    Fill password form
    """
    pb = ProgressBar("Setting password...")
    pb.start()
    try:
        print(f"{Fore.CYAN}🔑 {translator.get('register.setting_password') if translator else 'Setting password'}{Style.RESET_ALL}")
        
        # Fill password
        password_input = page.ele("@name=password")
        print(f"{Fore.CYAN}🔑 {translator.get('register.setting_on_password')}: {password}{Style.RESET_ALL}")
        if password_input:
            password_input.input(password)

        # Click submit button
        submit_button = page.ele("@type=submit")
        if submit_button:
            submit_button.click()
            time.sleep(get_random_wait_time(config, 'submit_wait'))
            
        pb.stop("Password set!")
        print(f"{Fore.GREEN}✅ {translator.get('register.password_submitted') if translator else 'Password submitted'}{Style.RESET_ALL}")
        
        return True
        
    except Exception as e:
        pb.stop("Password set failed!")
        print(f"{Fore.RED}❌ {translator.get('register.password_error', error=str(e)) if translator else f'Error setting password: {str(e)}'}{Style.RESET_ALL}")

        return False

def handle_verification_code(browser_tab, email_tab, controller, config, translator=None):
    """Handle verification code"""
    try:
        # Section header
        print("\n== Waiting for Verification Code ==")
        # Only print once
        if translator:
            print(f"{Fore.CYAN}⏳ {translator.get('register.waiting_for_verification_code')}{Style.RESET_ALL}")
        else:
            print("⏳ Waiting for verification code...")
        # Check if using manual input verification code
        if hasattr(controller, 'get_verification_code') and email_tab is None:  # Manual mode
            verification_code = controller.get_verification_code()
            if verification_code:
                for i, digit in enumerate(verification_code):
                    browser_tab.ele(f"@data-index={i}").input(digit)
                    time.sleep(get_random_wait_time(config, 'verification_code_input'))
                print(f"{Fore.GREEN}✅ {translator.get('register.verification_success') if translator else 'Verification successful!'}{Style.RESET_ALL}")
                time.sleep(get_random_wait_time(config, 'verification_success_wait'))
                if handle_turnstile(browser_tab, config, translator):
                    print(f"{Fore.GREEN}✅ {translator.get('register.verification_success') if translator else 'Verification successful!'}{Style.RESET_ALL}")
                    time.sleep(get_random_wait_time(config, 'verification_retry_wait'))
                    print(f"{Fore.CYAN}🔑 {translator.get('register.visiting_url') if translator else 'Visiting URL'}: https://www.cursor.com/settings{Style.RESET_ALL}")
                    browser_tab.get("https://www.cursor.com/settings")
                    time.sleep(get_random_wait_time(config, 'settings_page_load_wait'))
                    return True, browser_tab
                return False, None
        # Automatic verification code logic
        elif email_tab:
            pb = ProgressBar("Waiting for verification code...")
            pb.start()
            time.sleep(get_random_wait_time(config, 'email_check_initial_wait'))
            email_tab.refresh_inbox()
            time.sleep(get_random_wait_time(config, 'email_refresh_wait'))
            if email_tab.check_for_cursor_email():
                pb.stop("Verification code received!")
                verification_code = email_tab.get_verification_code()
                if verification_code:
                    for i, digit in enumerate(verification_code):
                        browser_tab.ele(f"@data-index={i}").input(digit)
                        time.sleep(get_random_wait_time(config, 'verification_code_input'))
                    print(f"{Fore.GREEN}✅ {translator.get('register.verification_success') if translator else 'Verification successful!'}{Style.RESET_ALL}")
                    time.sleep(get_random_wait_time(config, 'verification_success_wait'))
                    if handle_turnstile(browser_tab, config, translator):
                        print(f"{Fore.GREEN}✅ {translator.get('register.verification_success') if translator else 'Verification successful!'}{Style.RESET_ALL}")
                        time.sleep(get_random_wait_time(config, 'verification_retry_wait'))
                        print(f"{Fore.CYAN}🔑 {translator.get('register.visiting_url') if translator else 'Visiting URL'}: https://www.cursor.com/settings{Style.RESET_ALL}")
                        browser_tab.get("https://www.cursor.com/settings")
                        time.sleep(get_random_wait_time(config, 'settings_page_load_wait'))
                        return True, browser_tab
                    else:
                        print(f"{Fore.RED}❌ {translator.get('register.verification_failed') if translator else 'Verification failed.'}{Style.RESET_ALL}")
                        return False, None
                else:
                    pb.stop("No verification code received in time.")
                    print(f"{Fore.RED}❌ No verification code received in time.{Style.RESET_ALL}")
                    return False, None
            pb.stop("No verification code received in time.")
            print(f"{Fore.RED}❌ No verification code received in time.{Style.RESET_ALL}")
            return False, None
        # Get verification code, set timeout
        verification_code = None
        max_attempts = 20
        retry_interval = get_random_wait_time(config, 'retry_interval')
        start_time = time.time()
        timeout = float(config.get('Timing', 'max_timeout', fallback='160'))
        for attempt in range(max_attempts):
            if time.time() - start_time > timeout:
                print(f"{Fore.RED}❌ {translator.get('register.verification_timeout') if translator else 'Verification code timeout.'}{Style.RESET_ALL}")
                print("[!] No verification code received. This may be due to temp email provider issues, anti-bot detection, or email delivery delays.")
                print("    - Try a different temp email provider.")
                print("    - Try running in visible (non-headless) mode.")
                print("    - Check your network or try again later.")
                break
            verification_code = controller.get_verification_code()
            if verification_code:
                print(f"{Fore.GREEN}✅ {translator.get('register.verification_success') if translator else 'Verification code received!'}{Style.RESET_ALL}")
                break
            remaining_time = int(timeout - (time.time() - start_time))
            if retry_interval > 2 and attempt == 0:
                print(f"⏳ Still waiting for verification code... (up to {remaining_time}s left)")
            email_tab.refresh_inbox()
            time.sleep(retry_interval)
        if verification_code:
            for i, digit in enumerate(verification_code):
                browser_tab.ele(f"@data-index={i}").input(digit)
                time.sleep(get_random_wait_time(config, 'verification_code_input'))
            print(f"{Fore.GREEN}✅ {translator.get('register.verification_success') if translator else 'Verification successful!'}{Style.RESET_ALL}")
            time.sleep(get_random_wait_time(config, 'verification_success_wait'))
            if handle_turnstile(browser_tab, config, translator):
                print(f"{Fore.GREEN}✅ {translator.get('register.verification_success') if translator else 'Verification successful!'}{Style.RESET_ALL}")
                time.sleep(get_random_wait_time(config, 'verification_retry_wait'))
                print(f"{Fore.CYAN}🔑 {translator.get('register.visiting_url') if translator else 'Visiting URL'}: https://www.cursor.com/settings{Style.RESET_ALL}")
                browser_tab.get("https://www.cursor.com/settings")
                time.sleep(get_random_wait_time(config, 'settings_page_load_wait'))
                return True, browser_tab
            else:
                print(f"{Fore.RED}❌ {translator.get('register.verification_failed') if translator else 'Verification failed.'}{Style.RESET_ALL}")
                return False, None
        print(f"{Fore.RED}❌ {translator.get('register.verification_failed') if translator else 'Verification failed.'}{Style.RESET_ALL}")
        print("[!] Registration failed. See above for troubleshooting suggestions.")
        return False, None
    except Exception as e:
        print(f"{Fore.RED}❌ {translator.get('register.verification_error', error=str(e)) if translator else f'Verification error: {e}'}{Style.RESET_ALL}")
        print("[!] Registration failed due to an unexpected error.")
        return False, None

def handle_sign_in(browser_tab, email, password, translator=None):
    """Handle login process"""
    try:
        # Check if on login page
        sign_in_header = browser_tab.ele('xpath://h1[contains(text(), "Sign in")]')
        if not sign_in_header:
            return True  # If not on login page, it means login is successful
            
        print(f"{Fore.CYAN}检测到登录页面，开始登录...{Style.RESET_ALL}")
        
        # Fill email
        email_input = browser_tab.ele('@name=email')
        if email_input:
            email_input.input(email)
            time.sleep(1)
            
            # Click Continue
            continue_button = browser_tab.ele('xpath://button[contains(@class, "BrandedButton") and text()="Continue"]')
            if continue_button:
                continue_button.click()
                time.sleep(2)
                
                # Handle Turnstile verification
                if handle_turnstile(browser_tab, translator):
                    # Fill password
                    password_input = browser_tab.ele('@name=password')
                    if password_input:
                        password_input.input(password)
                        time.sleep(1)
                        
                        # Click Sign in
                        sign_in_button = browser_tab.ele('xpath://button[@name="intent" and @value="password"]')
                        if sign_in_button:
                            sign_in_button.click()
                            time.sleep(2)
                            
                            # Handle last Turnstile verification
                            if handle_turnstile(browser_tab, translator):
                                print(f"{Fore.GREEN}Login successful!{Style.RESET_ALL}")
                                time.sleep(3)
                                return True
                                
        print(f"{Fore.RED}Login failed{Style.RESET_ALL}")
        return False
        
    except Exception as e:
        print(f"{Fore.RED}Login process error: {str(e)}{Style.RESET_ALL}")
        return False

def main(email=None, password=None, first_name=None, last_name=None, email_tab=None, controller=None, translator=None, headless=True):
    """Main function, can receive account information, email tab, and translator"""
    global _translator
    global _chrome_process_ids
    _translator = translator  # Save to global variable
    _chrome_process_ids = []  # Reset the process IDs list
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    page = None
    success = False
    try:
        config, page = setup_driver(translator)
        if translator:
            print(f"{Fore.CYAN}🚀 {translator.get('register.browser_started')}{Style.RESET_ALL}")
        
        # Visit registration page
        url = "https://authenticator.cursor.sh/sign-up"
        
        # Visit page
        simulate_human_input(page, url, config, translator)
        if translator:
            print(f"{Fore.CYAN}🔄 {translator.get('register.waiting_for_page_load')}{Style.RESET_ALL}")
        time.sleep(get_random_wait_time(config, 'page_load_wait'))
        
        # If account information is not provided, generate random information
        if not all([email, password, first_name, last_name]):
            first_name = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=6)).capitalize()
            last_name = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=6)).capitalize()
            email = f"{first_name.lower()}{random.randint(100,999)}@example.com"
            password = generate_password()
            
            # Save account information
            with open('test_accounts.txt', 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*50}\n")
                f.write(f"Email: {email}\n")
                f.write(f"Password: {password}\n")
                f.write(f"{'='*50}\n")
        
        # Fill form
        if fill_signup_form(page, first_name, last_name, email, config, translator):
            if translator:
                print(f"\n{Fore.GREEN}✅ {translator.get('register.form_submitted')}{Style.RESET_ALL}")
            
            # Handle first Turnstile verification
            if handle_turnstile(page, config, translator):
                if translator:
                    print(f"\n{Fore.GREEN}✅ {translator.get('register.first_verification_passed')}{Style.RESET_ALL}")
                
                # Fill password
                if fill_password(page, password, config, translator):
                    if translator:
                        print(f"\n{Fore.CYAN}🔄 {translator.get('register.waiting_for_second_verification')}{Style.RESET_ALL}")
                                        
                    # Handle second Turnstile verification
                    if handle_turnstile(page, config, translator):
                        if translator:
                            print(f"\n{Fore.CYAN}🔄 {translator.get('register.waiting_for_verification_code')}{Style.RESET_ALL}")
                        if handle_verification_code(page, email_tab, controller, config, translator):
                            success = True
                            return True, page
                        else:
                            print(f"\n{Fore.RED}❌ {translator.get('register.verification_code_processing_failed') if translator else 'Verification code processing failed'}{Style.RESET_ALL}")
                    else:
                        print(f"\n{Fore.RED}❌ {translator.get('register.second_verification_failed') if translator else 'Second verification failed'}{Style.RESET_ALL}")
                else:
                    print(f"\n{Fore.RED}❌ {translator.get('register.second_verification_failed') if translator else 'Second verification failed'}{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.RED}❌ {translator.get('register.first_verification_failed') if translator else 'First verification failed'}{Style.RESET_ALL}")
        
        return False, None
        
    except Exception as e:
        print(f"发生错误: {e}")
        return False, None
    finally:
        if page and not success:  # Only clean up when failed
            try:
                page.quit()
            except:
                pass
            cleanup_chrome_processes(translator)

if __name__ == "__main__":
    os.environ['BROWSER_HEADLESS'] = 'True'
    main()  # Run without parameters, use randomly generated information 