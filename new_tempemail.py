from DrissionPage import ChromiumPage, ChromiumOptions
import time
import os
import sys
from colorama import Fore, Style, init
import requests
import random
import string

# 初始化 colorama
init()

class NewTempEmail:
    def __init__(self, translator=None):
        self.translator = translator
        # Randomly choose between mail.tm and mail.gw
        self.services = [
            {"name": "mail.tm", "api_url": "https://api.mail.tm"},
            {"name": "mail.gw", "api_url": "https://api.mail.gw"}
        ]
        self.selected_service = random.choice(self.services)
        self.api_url = self.selected_service["api_url"]
        self.token = None
        self.email = None
        self.password = None
        
    def _generate_credentials(self):
        """生成随机用户名和密码"""
        username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        password = ''.join(random.choices(string.ascii_letters + string.digits + string.punctuation, k=12))
        return username, password
        
    def create_email(self):
        """创建临时邮箱"""
        try:
            if self.translator:
                print(f"{Fore.CYAN}ℹ️ {self.translator.get('email.visiting_site').replace('mail.tm', self.selected_service['name'])}{Style.RESET_ALL}")
            else:
                print(f"{Fore.CYAN}ℹ️ 正在访问 {self.selected_service['name']}...{Style.RESET_ALL}")
            
            # 获取可用域名列表
            domains_response = requests.get(f"{self.api_url}/domains")
            if domains_response.status_code != 200:
                raise Exception("Failed to get available domains")
                
            domains = domains_response.json()["hydra:member"]
            if not domains:
                raise Exception("No available domains")
                
            # 生成随机用户名和密码
            username, password = self._generate_credentials()
            self.password = password
            
            # 创建邮箱账户
            email = f"{username}@{domains[0]['domain']}"
            account_data = {
                "address": email,
                "password": password
            }
            
            create_response = requests.post(f"{self.api_url}/accounts", json=account_data)
            if create_response.status_code != 201:
                raise Exception("Failed to create account")
                
            # 获取访问令牌
            token_data = {
                "address": email,
                "password": password
            }
            
            token_response = requests.post(f"{self.api_url}/token", json=token_data)
            if token_response.status_code != 200:
                raise Exception("Failed to get access token")
                
            self.token = token_response.json()["token"]
            self.email = email
            
            if self.translator:
                print(f"{Fore.GREEN}✅ {self.translator.get('email.create_success')}: {email}{Style.RESET_ALL}")
            else:
                print(f"{Fore.GREEN}✅ 创建邮箱成功: {email}{Style.RESET_ALL}")
            return email
            
        except Exception as e:
            if self.translator:
                print(f"{Fore.RED}❌ {self.translator.get('email.create_error')}: {str(e)}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}❌ 创建邮箱出错: {str(e)}{Style.RESET_ALL}")
            return None
            
    def close(self):
        """关闭浏览器"""
        if self.page:
            self.page.quit()

    def refresh_inbox(self):
        """刷新邮箱"""
        try:
            if self.translator:
                print(f"{Fore.CYAN}🔄 {self.translator.get('email.refreshing')}{Style.RESET_ALL}")
            else:
                print(f"{Fore.CYAN}🔄 正在刷新邮箱...{Style.RESET_ALL}")
            
            # 使用 API 获取最新邮件
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(f"{self.api_url}/messages", headers=headers)
            
            if response.status_code == 200:
                if self.translator:
                    print(f"{Fore.GREEN}✅ {self.translator.get('email.refresh_success')}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.GREEN}✅ 邮箱刷新成功{Style.RESET_ALL}")
                return True
            
            if self.translator:
                print(f"{Fore.RED}❌ {self.translator.get('email.refresh_failed')}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}❌ 刷新邮箱失败{Style.RESET_ALL}")
            return False
            
        except Exception as e:
            if self.translator:
                print(f"{Fore.RED}❌ {self.translator.get('email.refresh_error')}: {str(e)}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}❌ 刷新邮箱出错: {str(e)}{Style.RESET_ALL}")
            return False

    def check_for_cursor_email(self):
        """检查是否有 Cursor 的验证邮件"""
        try:
            # 使用 API 获取邮件列表
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(f"{self.api_url}/messages", headers=headers)
            
            if response.status_code == 200:
                messages = response.json()["hydra:member"]
                for message in messages:
                    if message["from"]["address"] == "no-reply@cursor.sh" and "Verify your email address" in message["subject"]:
                        # 获取邮件内容
                        message_id = message["id"]
                        message_response = requests.get(f"{self.api_url}/messages/{message_id}", headers=headers)
                        if message_response.status_code == 200:
                            if self.translator:
                                print(f"{Fore.GREEN}✅ {self.translator.get('email.verification_found')}{Style.RESET_ALL}")
                            else:
                                print(f"{Fore.GREEN}✅ 找到验证邮件{Style.RESET_ALL}")
                            return True
                            
            if self.translator:
                print(f"{Fore.YELLOW}⚠️ {self.translator.get('email.verification_not_found')}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}⚠️ 未找到验证邮件{Style.RESET_ALL}")
            return False
            
        except Exception as e:
            if self.translator:
                print(f"{Fore.RED}❌ {self.translator.get('email.verification_error')}: {str(e)}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}❌ 检查验证邮件出错: {str(e)}{Style.RESET_ALL}")
            return False

    def get_verification_code(self):
        """获取验证码"""
        try:
            # 使用 API 获取邮件列表
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(f"{self.api_url}/messages", headers=headers)
            
            if response.status_code == 200:
                messages = response.json()["hydra:member"]
                for message in messages:
                    if message["from"]["address"] == "no-reply@cursor.sh" and "Verify your email address" in message["subject"]:
                        # 获取邮件内容
                        message_id = message["id"]
                        message_response = requests.get(f"{self.api_url}/messages/{message_id}", headers=headers)
                        
                        if message_response.status_code == 200:
                            # 从邮件内容中提取验证码
                            email_content = message_response.json()["text"]
                            # 查找6位数字验证码
                            import re
                            code_match = re.search(r'\b\d{6}\b', email_content)
                            
                            if code_match:
                                code = code_match.group(0)
                                if self.translator:
                                    print(f"{Fore.GREEN}✅ {self.translator.get('email.verification_code_found')}: {code}{Style.RESET_ALL}")
                                else:
                                    print(f"{Fore.GREEN}✅ 获取验证码成功: {code}{Style.RESET_ALL}")
                                return code
            
            if self.translator:
                print(f"{Fore.YELLOW}⚠️ {self.translator.get('email.verification_code_not_found')}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}⚠️ 未找到有效的验证码{Style.RESET_ALL}")
            return None
            
        except Exception as e:
            if self.translator:
                print(f"{Fore.RED}❌ {self.translator.get('email.verification_code_error')}: {str(e)}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}❌ 获取验证码出错: {str(e)}{Style.RESET_ALL}")
            return None

def main(translator=None):
    temp_email = NewTempEmail(translator)
    
    try:
        email = temp_email.create_email()
        if email:
            if translator:
                print(f"\n{Fore.CYAN}📧 {translator.get('email.address')}: {email}{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.CYAN}📧 临时邮箱地址: {email}{Style.RESET_ALL}")
            
            # 测试刷新功能
            while True:
                if translator:
                    choice = input(f"\n{translator.get('email.refresh_prompt')}: ").lower()
                else:
                    choice = input("\n按 R 刷新邮箱，按 Q 退出: ").lower()
                if choice == 'r':
                    temp_email.refresh_inbox()
                elif choice == 'q':
                    break
                    
    finally:
        temp_email.close()

if __name__ == "__main__":
    main()