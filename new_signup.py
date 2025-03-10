from DrissionPage import ChromiumOptions, ChromiumPage
import time
import os
import signal
import random
from colorama import Fore, Style
import configparser
from pathlib import Path
import sys
import locale

# 在文件开头添加全局变量
_translator = None

def cleanup_chrome_processes(translator=None):
    """清理所有Chrome相关进程"""
    print("\n正在清理Chrome进程...")
    try:
        if os.name == 'nt':
            os.system('taskkill /F /IM chrome.exe /T 2>nul')
            os.system('taskkill /F /IM chromedriver.exe /T 2>nul')
        else:
            os.system('pkill -f chrome')
            os.system('pkill -f chromedriver')
    except Exception as e:
        if translator:
            print(f"{Fore.RED}❌ {translator.get('register.cleanup_error', error=str(e))}{Style.RESET_ALL}")
        else:
            print(f"清理进程时出错: {e}")

def signal_handler(signum, frame):
    """处理Ctrl+C信号"""
    global _translator
    if _translator:
        print(f"{Fore.CYAN}{_translator.get('register.exit_signal')}{Style.RESET_ALL}")
    else:
        print("\n接收到退出信号，正在关闭...")
    cleanup_chrome_processes(_translator)
    os._exit(0)

def simulate_human_input(page, url, config, translator=None):
    """访问网址"""
    if translator:
        print(f"{Fore.CYAN}🚀 {translator.get('register.visiting_url')}: {url}{Style.RESET_ALL}")
    
    # 先访问空白页面
    page.get('about:blank')
    time.sleep(get_random_wait_time(config, 'page_load_wait'))
    
    # 访问目标页面
    page.get(url)
    time.sleep(get_random_wait_time(config, 'page_load_wait'))

def fill_signup_form(page, first_name, last_name, email, config, translator=None):
    """填写注册表单"""
    try:
        if translator:
            print(f"{Fore.CYAN}📧 {translator.get('register.filling_form')}{Style.RESET_ALL}")
        else:
            print("\n正在填写注册表单...")
        
        # 填写名字
        first_name_input = page.ele("@name=first_name")
        if first_name_input:
            first_name_input.input(first_name)
            time.sleep(get_random_wait_time(config, 'input_wait'))
        
        # 填写姓氏
        last_name_input = page.ele("@name=last_name")
        if last_name_input:
            last_name_input.input(last_name)
            time.sleep(get_random_wait_time(config, 'input_wait'))
        
        # 填写邮箱
        email_input = page.ele("@name=email")
        if email_input:
            email_input.input(email)
            time.sleep(get_random_wait_time(config, 'input_wait'))
        
        # 点击提交按钮
        submit_button = page.ele("@type=submit")
        if submit_button:
            submit_button.click()
            time.sleep(get_random_wait_time(config, 'submit_wait'))
            
        if translator:
            print(f"{Fore.GREEN}✅ {translator.get('register.form_success')}{Style.RESET_ALL}")
        else:
            print("表单填写完成")
        return True
        
    except Exception as e:
        if translator:
            print(f"{Fore.RED}❌ {translator.get('register.form_error', error=str(e))}{Style.RESET_ALL}")
        else:
            print(f"填写表单时出错: {e}")
        return False

def get_default_chrome_path():
    """Get default Chrome path"""
    if sys.platform == "win32":
        paths = [
            os.path.join(os.environ.get('PROGRAMFILES', ''), 'Google/Chrome/Application/chrome.exe'),
            os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Google/Chrome/Application/chrome.exe'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google/Chrome/Application/chrome.exe')
        ]
    elif sys.platform == "darwin":
        paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        ]
    else:  # Linux
        paths = [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable"
        ]

    for path in paths:
        if os.path.exists(path):
            return path
    return ""

def get_user_documents_path():
    """Get user Documents folder path"""
    if sys.platform == "win32":
        try:
            # 使用Windows API获取Documents文件夹路径
            import ctypes
            from ctypes import windll, wintypes
            
            CSIDL_PERSONAL = 5  # Documents文件夹
            SHGFP_TYPE_CURRENT = 0  # 获取当前路径而非默认路径
            
            buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)
            
            # 确保路径有效
            if buf.value:
                return buf.value
            
            # 如果API失败，回退到普通方法
            return os.path.join(os.path.expanduser("~"), "Documents")
        except Exception:
            # 出错时回退到普通方法
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
            return random.uniform(0.1, 0.8)  # 默认值
            
        if timing_type == 'random':
            min_time = float(config.get('Timing', 'min_random_time', fallback='0.1'))
            max_time = float(config.get('Timing', 'max_random_time', fallback='0.8'))
            return random.uniform(min_time, max_time)
            
        time_value = config.get('Timing', timing_type, fallback='0.1-0.8')
        
        # 检查是否为固定时间值
        if '-' not in time_value and ',' not in time_value:
            return float(time_value)  # 返回固定时间
            
        # 处理范围时间
        min_time, max_time = map(float, time_value.split('-' if '-' in time_value else ','))
        return random.uniform(min_time, max_time)
    except:
        return random.uniform(0.1, 0.8)  # 出错时返回默认值

def setup_config(translator=None):
    """Setup configuration file and return config object"""
    try:
        # Set configuration file path
        config_dir = os.path.join(get_user_documents_path(), ".cursor-free-vip")
        config_file = os.path.join(config_dir, "config.ini")

        # Create config directory (if it doesn't exist)
        os.makedirs(config_dir, exist_ok=True)

        # Read or create configuration file
        config = configparser.ConfigParser()
        
        # 默认配置
        default_config = {
            'Chrome': {
                'chromepath': get_default_chrome_path()
            },
            'Turnstile': {
                'handle_turnstile_time': '2',
                'handle_turnstile_random_time': '1-3'
            },
            'Timing': {
                'min_random_time': '0.1',
                'max_random_time': '0.8',
                'page_load_wait': '0.1-0.8',
                'input_wait': '0.3-0.8',
                'submit_wait': '0.5-1.5',
                'verification_code_input': '0.1-0.3',    # 验证码输入间隔
                'verification_success_wait': '2-3',       # 验证成功后等待
                'verification_retry_wait': '2-3',         # 验证重试等待
                'email_check_initial_wait': '4-6',        # 首次等待邮件时间
                'email_refresh_wait': '2-4',              # 邮箱刷新等待时间
                'settings_page_load_wait': '1-2',         # 设置页面加载等待
                'failed_retry_time': '0.5-1',             # 验证失败重试等待时间
                'retry_interval': '8-12',                 # 重试间隔时间
                'max_timeout': '160'                      # 最大超时时间
            }
        }

        # Add OS-specific path configurations
        if sys.platform == "win32":
            appdata = os.getenv("APPDATA")
            default_config['WindowsPaths'] = {
                'storage_path': os.path.join(appdata, "Cursor", "User", "globalStorage", "storage.json"),
                'sqlite_path': os.path.join(appdata, "Cursor", "User", "globalStorage", "state.vscdb"),
                'machine_id_path': os.path.join(os.getenv("APPDATA"), "Cursor", "machineId"),
                'cursor_path': os.path.join(os.getenv("LOCALAPPDATA", ""), "Programs", "Cursor", "resources", "app")
            }
        elif sys.platform == "darwin":
            default_config['MacPaths'] = {
                'storage_path': os.path.abspath(os.path.expanduser("~/Library/Application Support/Cursor/User/globalStorage/storage.json")),
                'sqlite_path': os.path.abspath(os.path.expanduser("~/Library/Application Support/Cursor/User/globalStorage/state.vscdb")),
                'machine_id_path': os.path.expanduser("~/Library/Application Support/Cursor/machineId"),
                'cursor_path': "/Applications/Cursor.app/Contents/Resources/app"
            }
        elif sys.platform == "linux":
            sudo_user = os.environ.get('SUDO_USER')
            actual_home = f"/home/{sudo_user}" if sudo_user else os.path.expanduser("~")
            
            default_config['LinuxPaths'] = {
                'storage_path': os.path.abspath(os.path.join(actual_home, ".config/Cursor/User/globalStorage/storage.json")),
                'sqlite_path': os.path.abspath(os.path.join(actual_home, ".config/Cursor/User/globalStorage/state.vscdb")),
                'machine_id_path': os.path.expanduser("~/.config/Cursor/machineId"),
                'cursor_path': "/opt/Cursor/resources/app"  # 默認路徑
            }

        if os.path.exists(config_file):
            try:
                # 明确指定使用UTF-8编码读取
                config.read(config_file, encoding='utf-8')
            except UnicodeDecodeError:
                # 如果UTF-8解码失败，尝试使用系统默认编码或其他常见编码
                try:
                    # 尝试使用系统默认编码
                    config.read(config_file, encoding=locale.getpreferredencoding())
                except:
                    # 如果仍然失败，尝试使用GBK编码（中文Windows系统常用）
                    try:
                        config.read(config_file, encoding='gbk')
                    except:
                        # 最后尝试以二进制方式读取，然后进行转换
                        with open(config_file, 'rb') as f:
                            content = f.read()
                        # 清除可能包含的BOM标记并尝试以latin-1编码（能处理任何字节）
                        content = content.replace(b'\xef\xbb\xbf', b'')
                        with open(config_file + '.tmp', 'w', encoding='utf-8') as f:
                            f.write(content.decode('latin-1'))
                        config.read(config_file + '.tmp', encoding='utf-8')
                        os.remove(config_file + '.tmp')  # 清理临时文件
            
            config_modified = False

            # 检查并添加缺失的配置项
            for section, options in default_config.items():
                if not config.has_section(section):
                    config.add_section(section)
                    config_modified = True
                for option, value in options.items():
                    if not config.has_option(section, option):
                        config.set(section, option, value)
                        config_modified = True
                        if translator:
                            print(f"{Fore.YELLOW}ℹ️ {translator.get('register.config_option_added', option=f'{section}.{option}') if translator else f'添加配置项: {section}.{option}'}{Style.RESET_ALL}")

            # 如果有新增配置项，保存文件
            if config_modified:
                with open(config_file, 'w', encoding='utf-8') as f:
                    config.write(f)
                if translator:
                    print(f"{Fore.GREEN}✅ {translator.get('register.config_updated') if translator else '配置文件已更新'}{Style.RESET_ALL}")
        else:
            # 创建新配置文件
            config = configparser.ConfigParser()
            for section, options in default_config.items():
                config.add_section(section)
                for option, value in options.items():
                    config.set(section, option, value)
            
            # 确保使用UTF-8编码保存配置文件
            with open(config_file, 'w', encoding='utf-8') as f:
                config.write(f)
            if translator:
                print(f"{Fore.GREEN}✅ {translator.get('register.config_created') if translator else '已创建配置文件'}: {config_file}{Style.RESET_ALL}")

        return config

    except Exception as e:
        if translator:
            print(f"{Fore.RED}❌ {translator.get('register.config_setup_error', error=str(e)) if translator else f'配置设置出错: {str(e)}'}{Style.RESET_ALL}")
        raise

def setup_driver(translator=None):
    """Setup browser driver"""
    try:
        # 获取配置
        config = setup_config(translator)
        
        # Get Chrome path
        chrome_path = config.get('Chrome', 'chromepath', fallback=get_default_chrome_path())
        
        if not chrome_path or not os.path.exists(chrome_path):
            if translator:
                print(f"{Fore.YELLOW}⚠️ {translator.get('register.chrome_path_invalid') if translator else 'Chrome路径无效，使用默认路径'}{Style.RESET_ALL}")
            chrome_path = get_default_chrome_path()

        # Set browser options
        co = ChromiumOptions()
        
        # Set Chrome path
        co.set_browser_path(chrome_path)
        
        # Use incognito mode
        co.set_argument("--incognito")

        # 设置随机端口
        co.set_argument("--no-sandbox")
        
        # 设置随机端口
        co.auto_port()
        
        # 使用有头模式(一定要设置为False，模拟人类操作)
        co.headless(False)
        
        try:
            # 加载插件
            extension_path = os.path.join(os.getcwd(), "turnstilePatch")
            if os.path.exists(extension_path):
                co.set_argument("--allow-extensions-in-incognito")
                co.add_extension(extension_path)
        except Exception as e:
            if translator:
                print(f"{Fore.RED}❌ {translator.get('register.extension_load_error', error=str(e))}{Style.RESET_ALL}")
            else:
                print(f"加载插件失败: {e}")
        
        if translator:
            print(f"{Fore.CYAN}🚀 {translator.get('register.starting_browser')}{Style.RESET_ALL}")
        else:
            print("正在启动浏览器...")
        
        page = ChromiumPage(co)
        return config, page

    except Exception as e:
        if translator:
            print(f"{Fore.RED}❌ {translator.get('register.browser_setup_error', error=str(e))}{Style.RESET_ALL}")
        else:
            print(f"设置浏览器时出错: {e}")
        raise

def handle_turnstile(page, config, translator=None):
    """处理 Turnstile 验证"""
    try:
        if translator:
            print(f"{Fore.CYAN}🔄 {translator.get('register.handling_turnstile')}{Style.RESET_ALL}")
        else:
            print("\n正在处理 Turnstile 验证...")
        
        # from config
        turnstile_time = float(config.get('Turnstile', 'handle_turnstile_time', fallback='2'))
        random_time_str = config.get('Turnstile', 'handle_turnstile_random_time', fallback='1-3')
        
        # 解析随机时间范围
        try:
            min_time, max_time = map(float, random_time_str.split('-'))
        except:
            min_time, max_time = 1, 3  # 默认值
        
        max_retries = 2
        retry_count = 0

        while retry_count < max_retries:
            retry_count += 1
            if translator:
                print(f"{Fore.CYAN}🔄 {translator.get('register.retry_verification', attempt=retry_count)}{Style.RESET_ALL}")
            else:
                print(f"第 {retry_count} 次尝试验证...")

            try:
                # 尝试重置 turnstile
                page.run_js("try { turnstile.reset() } catch(e) { }")
                time.sleep(turnstile_time)  # from config

                # 定位验证框元素
                challenge_check = (
                    page.ele("@id=cf-turnstile", timeout=2)
                    .child()
                    .shadow_root.ele("tag:iframe")
                    .ele("tag:body")
                    .sr("tag:input")
                )

                if challenge_check:
                    if translator:
                        print(f"{Fore.CYAN}🔄 {translator.get('register.detect_turnstile')}{Style.RESET_ALL}")
                    else:
                        print("检测到验证框...")
                    
                    # from config
                    time.sleep(random.uniform(min_time, max_time))
                    challenge_check.click()
                    time.sleep(turnstile_time)  # from config

                    # check verification result
                    if check_verification_success(page, translator):
                        if translator:
                            print(f"{Fore.GREEN}✅ {translator.get('register.verification_success')}{Style.RESET_ALL}")
                        else:
                            print("验证通过！")
                        return True

            except Exception as e:
                if translator:
                    print(f"{Fore.RED}❌ {translator.get('register.verification_failed')}{Style.RESET_ALL}")
                else:
                    print(f"验证尝试失败: {e}")

            # 检查是否已经验证成功
            if check_verification_success(page, translator):
                if translator:
                    print(f"{Fore.GREEN}✅ {translator.get('register.verification_success')}{Style.RESET_ALL}")
                else:
                    print("验证通过！")
                return True

            time.sleep(random.uniform(min_time, max_time))

        if translator:
            print(f"{Fore.RED}❌ {translator.get('register.verification_failed')}{Style.RESET_ALL}")
        else:
            print("超出最大重试次数")
        return False

    except Exception as e:
        if translator:
            print(f"{Fore.RED}❌ {translator.get('register.verification_error', error=str(e))}{Style.RESET_ALL}")
        else:
            print(f"验证过程出错: {e}")
        return False

def check_verification_success(page, translator=None):
    """检查验证是否成功"""
    try:
        # 检查是否存在后续表单元素，这表示验证已通过
        if (page.ele("@name=password", timeout=0.5) or 
            page.ele("@name=email", timeout=0.5) or
            page.ele("@data-index=0", timeout=0.5) or
            page.ele("Account Settings", timeout=0.5)):
            return True
        
        # 检查是否出现错误消息
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
    """生成随机密码"""
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
    return ''.join(random.choices(chars, k=length))

def fill_password(page, password: str, config, translator=None) -> bool:
    """
    填写密码表单
    """
    try:
        print(f"{Fore.CYAN}🔑 {translator.get('register.setting_password') if translator else '设置密码'}{Style.RESET_ALL}")
        
        # 等待密码框出现并尝试多次
        max_retries = 5
        for i in range(max_retries):
            # 检查是否出现错误信息
            if page.ele("This email is not available."):
                print(f"{Fore.RED}❌ {translator.get('register.email_used') if translator else '注册失败：邮箱已被使用'}{Style.RESET_ALL}")
                return False

            # 查找密码输入框
            password_input = page.ele("@name=password")
            if password_input:
                # 清除可能存在的旧值并输入新密码
                password_input.click()
                time.sleep(get_random_wait_time(config, 'input_wait'))
                password_input.input(password)
                time.sleep(get_random_wait_time(config, 'input_wait'))

                # 查找并点击提交按钮
                submit_button = page.ele("@type=submit")
                if submit_button:
                    submit_button.click()
                    print(f"{Fore.GREEN}✅ {translator.get('register.password_submitted') if translator else '密码已提交'}{Style.RESET_ALL}")
                    time.sleep(get_random_wait_time(config, 'submit_wait'))
                    return True
                else:
                    print(f"{Fore.YELLOW}⚠️ {translator.get('register.retry_submit') if translator else '未找到提交按钮，重试中...'}{Style.RESET_ALL}")
            
            # 如果没找到密码框，等待后重试
            time.sleep(get_random_wait_time(config, 'failed_retry_time'))
            if i < max_retries - 1:  # 不是最后一次尝试时才打印
                print(f"{Fore.YELLOW}⚠️ {translator.get('register.retry_password', attempt=i+1) if translator else f'第 {i+1} 次尝试设置密码...'}{Style.RESET_ALL}")

        print(f"{Fore.RED}❌ {translator.get('register.password_set_failed') if translator else '密码设置失败：超过重试次数'}{Style.RESET_ALL}")
        return False

    except Exception as e:
        print(f"{Fore.RED}❌ {translator.get('register.password_error', error=str(e)) if translator else f'设置密码时出错: {str(e)}'}{Style.RESET_ALL}")
        return False

def handle_verification_code(browser_tab, email_tab, controller, email, password, config, translator=None):
    """处理验证码"""
    try:
        if translator:
            print(f"\n{Fore.CYAN}{translator.get('register.waiting_for_verification_code')}{Style.RESET_ALL}")
            
        # 检查是否使用手动输入验证码
        if hasattr(controller, 'get_verification_code') and email_tab is None:  # 手动模式
            verification_code = controller.get_verification_code()
            if verification_code:
                # 在注册页面填写验证码
                for i, digit in enumerate(verification_code):
                    browser_tab.ele(f"@data-index={i}").input(digit)
                    time.sleep(get_random_wait_time(config, 'verification_code_input'))
                
                print(f"{translator.get('register.verification_success')}")
                time.sleep(get_random_wait_time(config, 'verification_success_wait'))
                
                # 处理最后一次 Turnstile 验证
                if handle_turnstile(browser_tab, config, translator):
                    if translator:
                        print(f"{Fore.GREEN}✅ {translator.get('register.verification_success')}{Style.RESET_ALL}")
                    time.sleep(get_random_wait_time(config, 'verification_retry_wait'))
                    
                    # 访问设置页面
                    print(f"{Fore.CYAN} {translator.get('register.visiting_url')}: https://www.cursor.com/settings{Style.RESET_ALL}")
                    browser_tab.get("https://www.cursor.com/settings")
                    time.sleep(get_random_wait_time(config, 'settings_page_load_wait'))
                    return True, browser_tab
                    
                return False, None
                
        # 自动获取验证码逻辑
        elif email_tab:
            print(f"{translator.get('register.waiting_for_verification_code')}")
            time.sleep(get_random_wait_time(config, 'email_check_initial_wait'))

            # 使用已有的 email_tab 刷新邮箱
            email_tab.refresh_inbox()
            time.sleep(get_random_wait_time(config, 'email_refresh_wait'))

            # 检查邮箱是否有验证码邮件
            if email_tab.check_for_cursor_email():
                verification_code = email_tab.get_verification_code()
                if verification_code:
                    # 在注册页面填写验证码
                    for i, digit in enumerate(verification_code):
                        browser_tab.ele(f"@data-index={i}").input(digit)
                        time.sleep(get_random_wait_time(config, 'verification_code_input'))
                    
                    if translator:
                        print(f"{Fore.GREEN}✅ {translator.get('register.verification_success')}{Style.RESET_ALL}")
                    time.sleep(get_random_wait_time(config, 'verification_success_wait'))
                    
                    # 处理最后一次 Turnstile 验证
                    if handle_turnstile(browser_tab, config, translator):
                        if translator:
                            print(f"{Fore.GREEN}✅ {translator.get('register.verification_success')}{Style.RESET_ALL}")
                        time.sleep(get_random_wait_time(config, 'verification_retry_wait'))
                        
                        # 访问设置页面
                        if translator:
                            print(f"{Fore.CYAN}🔑 {translator.get('register.visiting_url')}: https://www.cursor.com/settings{Style.RESET_ALL}")
                        browser_tab.get("https://www.cursor.com/settings")
                        time.sleep(get_random_wait_time(config, 'settings_page_load_wait'))
                        return True, browser_tab
                        
                    else:
                        if translator:
                            print(f"{Fore.RED}❌ {translator.get('register.verification_failed')}{Style.RESET_ALL}")
                        else:
                            print("最后一次验证失败")
                        return False, None
                        
            # 获取验证码，设置超时
            verification_code = None
            max_attempts = 20
            retry_interval = get_random_wait_time(config, 'retry_interval')  # 使用 get_random_wait_time
            start_time = time.time()
            timeout = float(config.get('Timing', 'max_timeout', fallback='160'))  # 這個可以保持不變因為是固定值

            if translator:
                print(f"{Fore.CYAN}{translator.get('register.start_getting_verification_code')}{Style.RESET_ALL}")
            
            for attempt in range(max_attempts):
                # 检查是否超时
                if time.time() - start_time > timeout:
                    if translator:
                        print(f"{Fore.RED}❌ {translator.get('register.verification_timeout')}{Style.RESET_ALL}")
                    break
                    
                verification_code = controller.get_verification_code()
                if verification_code:
                    if translator:
                        print(f"{Fore.GREEN}✅ {translator.get('register.verification_success')}{Style.RESET_ALL}")
                    break
                    
                remaining_time = int(timeout - (time.time() - start_time))
                if translator:
                    print(f"{Fore.CYAN}{translator.get('register.try_get_code', attempt=attempt + 1, time=remaining_time)}{Style.RESET_ALL}")
                
                # 刷新邮箱
                email_tab.refresh_inbox()
                time.sleep(retry_interval)  # 使用 get_random_wait_time
            
            if verification_code:
                # 在注册页面填写验证码
                for i, digit in enumerate(verification_code):
                    browser_tab.ele(f"@data-index={i}").input(digit)
                    time.sleep(get_random_wait_time(config, 'verification_code_input'))
                
                if translator:
                    print(f"{Fore.GREEN}✅ {translator.get('register.verification_success')}{Style.RESET_ALL}")
                time.sleep(get_random_wait_time(config, 'verification_success_wait'))
                
                # 处理最后一次 Turnstile 验证
                if handle_turnstile(browser_tab, config, translator):
                    if translator:
                        print(f"{Fore.GREEN}✅ {translator.get('register.verification_success')}{Style.RESET_ALL}")
                    time.sleep(get_random_wait_time(config, 'verification_retry_wait'))
                    
                    # 直接访问设置页面
                    if translator:
                        print(f"{Fore.CYAN}{translator.get('register.visiting_url')}: https://www.cursor.com/settings{Style.RESET_ALL}")
                    browser_tab.get("https://www.cursor.com/settings")
                    time.sleep(get_random_wait_time(config, 'settings_page_load_wait'))
                    
                    # 直接返回成功，让 cursor_register.py 处理账户信息获取
                    return True, browser_tab
                    
                else:
                    if translator:
                        print(f"{Fore.RED}❌ {translator.get('register.verification_failed')}{Style.RESET_ALL}")
                    return False, None
                
            return False, None
            
    except Exception as e:
        if translator:
            print(f"{Fore.RED}❌ {translator.get('register.verification_error', error=str(e))}{Style.RESET_ALL}")
        return False, None

def handle_sign_in(browser_tab, email, password, translator=None):
    """处理登录流程"""
    try:
        # 检查是否在登录页面
        sign_in_header = browser_tab.ele('xpath://h1[contains(text(), "Sign in")]')
        if not sign_in_header:
            return True  # 如果不是登录页面，说明已经登录成功
            
        print(f"{Fore.CYAN}检测到登录页面，开始登录...{Style.RESET_ALL}")
        
        # 填写邮箱
        email_input = browser_tab.ele('@name=email')
        if email_input:
            email_input.input(email)
            time.sleep(1)
            
            # 点击 Continue
            continue_button = browser_tab.ele('xpath://button[contains(@class, "BrandedButton") and text()="Continue"]')
            if continue_button:
                continue_button.click()
                time.sleep(2)
                
                # 处理 Turnstile 验证
                if handle_turnstile(browser_tab, translator):
                    # 填写密码
                    password_input = browser_tab.ele('@name=password')
                    if password_input:
                        password_input.input(password)
                        time.sleep(1)
                        
                        # 点击 Sign in
                        sign_in_button = browser_tab.ele('xpath://button[@name="intent" and @value="password"]')
                        if sign_in_button:
                            sign_in_button.click()
                            time.sleep(2)
                            
                            # 处理最后一次 Turnstile 验证
                            if handle_turnstile(browser_tab, translator):
                                print(f"{Fore.GREEN}登录成功！{Style.RESET_ALL}")
                                time.sleep(3)
                                return True
                                
        print(f"{Fore.RED}登录失败{Style.RESET_ALL}")
        return False
        
    except Exception as e:
        print(f"{Fore.RED}登录过程出错: {str(e)}{Style.RESET_ALL}")
        return False

def main(email=None, password=None, first_name=None, last_name=None, email_tab=None, controller=None, translator=None):
    """主函数，可以接收账号信息、邮箱标签页和翻译器"""
    global _translator
    _translator = translator  # 保存到全局变量
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    page = None
    success = False
    try:
        config, page = setup_driver(translator)
        if translator:
            print(f"{Fore.CYAN}🚀 {translator.get('register.browser_started')}{Style.RESET_ALL}")
        
        # 访问注册页面
        url = "https://authenticator.cursor.sh/sign-up"
        if translator:
            print(f"\n{Fore.CYAN}{translator.get('register.visiting_url')}: {url}{Style.RESET_ALL}")
        
        # 访问页面
        simulate_human_input(page, url, config, translator)
        if translator:
            print(f"{Fore.CYAN}{translator.get('register.waiting_for_page_load')}{Style.RESET_ALL}")
        time.sleep(get_random_wait_time(config, 'page_load_wait'))
        
        # 如果没有提供账号信息，则生成随机信息
        if not all([email, password, first_name, last_name]):
            first_name = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=6)).capitalize()
            last_name = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=6)).capitalize()
            email = f"{first_name.lower()}{random.randint(100,999)}@example.com"
            password = generate_password()
            
            # 保存账号信息
            with open('test_accounts.txt', 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*50}\n")
                f.write(f"Email: {email}\n")
                f.write(f"Password: {password}\n")
                f.write(f"{'='*50}\n")
        
        # 填写表单
        if fill_signup_form(page, first_name, last_name, email, config, translator):
            if translator:
                print(f"\n{Fore.GREEN}{translator.get('register.form_submitted')}{Style.RESET_ALL}")
            
            # 处理第一次 Turnstile 验证
            if handle_turnstile(page, config, translator):
                if translator:
                    print(f"\n{Fore.GREEN}{translator.get('register.first_verification_passed')}{Style.RESET_ALL}")
                
                # 填写密码
                if fill_password(page, password, config, translator):
                    if translator:
                        print(f"\n{Fore.CYAN}{translator.get('register.waiting_for_second_verification')}{Style.RESET_ALL}")
                    time.sleep(2)
                    
                    # 处理第二次 Turnstile 验证
                    if handle_turnstile(page, config, translator):
                        if translator:
                            print(f"\n{Fore.CYAN}{translator.get('register.waiting_for_verification_code')}{Style.RESET_ALL}")
                        if handle_verification_code(page, email_tab, controller, email, password, config, translator):
                            success = True
                            return True, page
                        else:
                            print(f"\n{Fore.RED} {translator.get('register.verification_code_processing_failed') if translator else '验证码处理失败'}{Style.RESET_ALL}")
                    else:
                        print(f"\n{Fore.RED} {translator.get('register.second_verification_failed') if translator else '第二次验证失败'}{Style.RESET_ALL}")
                else:
                    print(f"\n{Fore.RED} {translator.get('register.second_verification_failed') if translator else '第二次验证失败'}{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.RED} {translator.get('register.first_verification_failed') if translator else '第一次验证失败'}{Style.RESET_ALL}")
        
        return False, None
        
    except Exception as e:
        print(f"发生错误: {e}")
        return False, None
    finally:
        if page and not success:  # 只在失败时清理
            try:
                page.quit()
            except:
                pass
            cleanup_chrome_processes(translator)

if __name__ == "__main__":
    main()  # 直接运行时不传参数，使用随机生成的信息 