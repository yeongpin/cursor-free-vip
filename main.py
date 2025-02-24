# main.py
# This script allows the user to choose which script to run.
import os
import sys
import json
from logo import print_logo
from colorama import Fore, Style, init

# 初始化colorama
init()

# 定义emoji和颜色常量
EMOJI = {
    "FILE": "📄",
    "BACKUP": "💾",
    "SUCCESS": "✅",
    "ERROR": "❌",
    "INFO": "ℹ️",
    "RESET": "🔄",
    "MENU": "📋",
    "ARROW": "➜",
    "LANG": "🌐",
    "UPDATE": "🔄"
}

class Translator:
    def __init__(self):
        self.current_language = 'en'  # Default language set to English
        self.translations = {}
        self.load_translations()
    
    def load_translations(self):
        """加载所有可用的翻译"""
        locales_dir = os.path.join(os.path.dirname(__file__), 'locales')
        if hasattr(sys, '_MEIPASS'):
            locales_dir = os.path.join(sys._MEIPASS, 'locales')
            
        for file in os.listdir(locales_dir):
            if file.endswith('.json'):
                lang_code = file[:-5]  # 移除 .json
                with open(os.path.join(locales_dir, file), 'r', encoding='utf-8') as f:
                    self.translations[lang_code] = json.load(f)
    
    def get(self, key, **kwargs):
        """获取翻译文本"""
        try:
            keys = key.split('.')
            value = self.translations.get(self.current_language, {})
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k, key)
                else:
                    return key  # 如果中間值不是字典，返回原始key
            return value.format(**kwargs) if kwargs else value
        except Exception:
            return key  # 出現任何錯誤時返回原始key
    
    def set_language(self, lang_code):
        """设置当前语言"""
        if lang_code in self.translations:
            self.current_language = lang_code
            return True
        return False

# 创建翻译器实例
translator = Translator()

def print_menu():
    """打印菜单选项"""
    print(f"\n{Fore.CYAN}{EMOJI['MENU']} {translator.get('menu.title')}:{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{'─' * 40}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}0{Style.RESET_ALL}. {EMOJI['ERROR']} {translator.get('menu.exit')}")
    print(f"{Fore.GREEN}1{Style.RESET_ALL}. {EMOJI['RESET']} {translator.get('menu.reset')}")
    print(f"{Fore.GREEN}2{Style.RESET_ALL}. {EMOJI['SUCCESS']} {translator.get('menu.register')}")
    print(f"{Fore.GREEN}3{Style.RESET_ALL}. {EMOJI['SUCCESS']} {translator.get('menu.register_manual')}")
    print(f"{Fore.GREEN}4{Style.RESET_ALL}. {EMOJI['ERROR']} {translator.get('menu.quit')}")
    print(f"{Fore.GREEN}5{Style.RESET_ALL}. {EMOJI['LANG']} {translator.get('menu.select_language')}")
    print(f"{Fore.GREEN}6{Style.RESET_ALL}. {EMOJI['UPDATE']} {translator.get('menu.disable_auto_update')}")
    print(f"{Fore.YELLOW}{'─' * 40}{Style.RESET_ALL}")

def select_language():
    """语言选择菜单"""
    print(f"\n{Fore.CYAN}{EMOJI['LANG']} {translator.get('menu.select_language')}:{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{'─' * 40}{Style.RESET_ALL}")
    
    languages = translator.get('languages')
    for i, (code, name) in enumerate(languages.items()):
        print(f"{Fore.GREEN}{i}{Style.RESET_ALL}. {name}")
    
    try:
        choice = input(f"\n{EMOJI['ARROW']} {Fore.CYAN}{translator.get('menu.input_choice', choices='0-' + str(len(languages)-1))}: {Style.RESET_ALL}")
        if choice.isdigit() and 0 <= int(choice) < len(languages):
            lang_code = list(languages.keys())[int(choice)]
            translator.set_language(lang_code)
            return True
    except (ValueError, IndexError):
        pass
    
    print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('menu.invalid_choice')}{Style.RESET_ALL}")
    return False

def main():
    print_logo()
    print_menu()
    
    while True:
        try:
            choice = input(f"\n{EMOJI['ARROW']} {Fore.CYAN}{translator.get('menu.input_choice', choices='0-6')}: {Style.RESET_ALL}")

            if choice == "0":
                print(f"\n{Fore.YELLOW}{EMOJI['INFO']} {translator.get('menu.exit')}...{Style.RESET_ALL}")
                print(f"{Fore.CYAN}{'═' * 50}{Style.RESET_ALL}")
                return
            elif choice == "1":
                import reset_machine_manual
                reset_machine_manual.run(translator)
                break
            elif choice == "2":
                import cursor_register
                cursor_register.main(translator)
                break
            elif choice == "3":
                import cursor_register_manual
                cursor_register_manual.main(translator)
                break
            elif choice == "4":
                import quit_cursor
                quit_cursor.quit_cursor(translator)
                break
            elif choice == "5":
                if select_language():
                    print_menu()
                continue
            elif choice == "6":
                import disable_auto_update
                disable_auto_update.run(translator)
                break
            else:
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('menu.invalid_choice')}{Style.RESET_ALL}")
                print_menu()

        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}{EMOJI['INFO']} {translator.get('menu.program_terminated')}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'═' * 50}{Style.RESET_ALL}")
            return
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('menu.error_occurred', error=str(e))}{Style.RESET_ALL}")
            break

    print(f"\n{Fore.CYAN}{'═' * 50}{Style.RESET_ALL}")
    input(f"{EMOJI['INFO']} {translator.get('menu.press_enter')}...{Style.RESET_ALL}")

if __name__ == "__main__":
    main()