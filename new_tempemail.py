from DrissionPage import ChromiumPage, ChromiumOptions
import time
import os
import sys
from colorama import Fore, Style, init
import requests
import random
import string

# Initialize colorama
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
        self.blocked_domains = self.get_blocked_domains()
        
    def get_blocked_domains(self):
        """Get blocked domains list"""
        try:
            block_url = "https://raw.githubusercontent.com/qing-turnaround/cursor-free-vip/main/block_domain.txt"
            response = requests.get(block_url, timeout=5)
            if response.status_code == 200:
                # Split text and remove empty lines
                domains = [line.strip() for line in response.text.split('\n') if line.strip()]
                if self.translator:
                    print(f"{Fore.CYAN}ℹ️  {self.translator.get('email.blocked_domains_loaded', count=len(domains))}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.CYAN}ℹ️ 已加载 {len(domains)} 个被屏蔽的域名{Style.RESET_ALL}")
                return domains
            return []
        except Exception as e:
            if self.translator:
                print(f"{Fore.YELLOW}⚠️ {self.translator.get('email.blocked_domains_error', error=str(e))}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}⚠️ 获取被屏蔽域名列表失败: {str(e)}{Style.RESET_ALL}")
            return []
    
    def exclude_blocked_domains(self, domains):
        """Exclude blocked domains"""
        if not self.blocked_domains:
            return domains
            
        filtered_domains = []
        for domain in domains:
            if domain['domain'] not in self.blocked_domains:
                filtered_domains.append(domain)
                
        excluded_count = len(domains) - len(filtered_domains)
        if excluded_count > 0:
            if self.translator:
                print(f"{Fore.YELLOW}⚠️ {self.translator.get('email.domains_excluded', domains=excluded_count)}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}⚠️ 已排除 {excluded_count} 个被屏蔽的域名{Style.RESET_ALL}")
                
        return filtered_domains
        
    def _generate_credentials(self):
        """generate random username and password"""
        username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        password = ''.join(random.choices(string.ascii_letters + string.digits + string.punctuation, k=12))
        return username, password
        
    def create_email(self):
        """create temporary email"""
        max_retries = 3  # Maximum number of retries
        attempt = 0  # Current attempt count
        
        while attempt < max_retries:
            attempt += 1
            try:
                if self.translator:
                    print(f"{Fore.CYAN}ℹ️  {self.translator.get('email.visiting_site').replace('mail.tm', self.selected_service['name'])}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.CYAN}ℹ️ 正在访问 {self.selected_service['name']}...{Style.RESET_ALL}")

                # Get available domain list
                try:
                    domains_response = requests.get(f"{self.api_url}/domains", timeout=10)
                    if domains_response.status_code != 200:
                        print(f"{Fore.RED}❌ {self.translator.get('email.domains_list_error', error=domains_response.status_code)}{Style.RESET_ALL}")
                        print(f"{Fore.RED}❌ {self.translator.get('email.domains_list_error', error=domains_response.text)}{Style.RESET_ALL}")
                        raise Exception(f"{self.translator.get('email.failed_to_get_available_domains') if self.translator else 'Failed to get available domains'}")

                    domains = domains_response.json()["hydra:member"]
                    print(f"{Fore.CYAN}ℹ️  {self.translator.get('email.available_domains_loaded', count=len(domains))}{Style.RESET_ALL}")

                    if not domains:
                        raise Exception(f"{self.translator.get('email.no_available_domains') if self.translator else '没有可用域名'}")
                except Exception as e:
                    print(f"{Fore.RED}❌ 获取域名列表时出错: {str(e)}{Style.RESET_ALL}")
                    raise

                # Exclude blocked domains
                try:
                    filtered_domains = self.exclude_blocked_domains(domains)
                    if self.translator:
                        print(f"{Fore.CYAN}ℹ️  {self.translator.get('email.domains_filtered', count=len(filtered_domains))}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.CYAN}ℹ️ 过滤后剩余 {len(filtered_domains)} 个可用域名{Style.RESET_ALL}")

                    if not filtered_domains:
                        if self.translator:
                            print(f"{Fore.RED}❌ {self.translator.get('email.all_domains_blocked')}{Style.RESET_ALL}")
                        else:
                            print(f"{Fore.RED}❌ 所有域名都被屏蔽了，尝试切换服务{Style.RESET_ALL}")

                        # Switch to another service
                        for service in self.services:
                            if service["api_url"] != self.api_url:
                                self.selected_service = service
                                self.api_url = service["api_url"]
                                if self.translator:
                                    print(f"{Fore.CYAN}ℹ️  {self.translator.get('email.switching_service', service=service['name'])}{Style.RESET_ALL}")
                                else:
                                    print(f"{Fore.CYAN}ℹ️ 切换到 {service['name']} 服务{Style.RESET_ALL}")
                                return self.create_email()  # Recursively call

                        raise Exception(f"{self.translator.get('email.no_available_domains_after_filtering') if self.translator else '过滤后没有可用域名'}")
                except Exception as e:
                    print(f"{Fore.RED}❌ 过滤域名时出错: {str(e)}{Style.RESET_ALL}")
                    raise

                # Generate random username and password
                try:
                    username, password = self._generate_credentials()
                    self.password = password

                    # Create email account
                    selected_domain = filtered_domains[0]['domain']
                    email = f"{username}@{selected_domain}"

                    if self.translator:
                        print(f"{Fore.CYAN}ℹ️  {self.translator.get('email.trying_to_create_email', email=email)}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.CYAN}ℹ️ 尝试创建邮箱: {email}{Style.RESET_ALL}")

                    account_data = {
                        "address": email,
                        "password": password
                    }
                except Exception as e:
                    print(f"{Fore.RED}❌ 生成凭据时出错: {str(e)}{Style.RESET_ALL}")
                    raise

                # Create account
                try:
                    create_response = requests.post(f"{self.api_url}/accounts", json=account_data, timeout=15)

                    if create_response.status_code != 201:
                        if self.translator:
                            print(f"{Fore.RED}❌ {self.translator.get('email.failed_to_create_account', error=create_response.status_code)}{Style.RESET_ALL}")
                        else:
                            print(f"{Fore.RED}❌ 创建账户失败: 状态码 {create_response.status_code}{Style.RESET_ALL}")
                        if self.translator:
                            print(f"{Fore.RED}❌ {self.translator.get('email.failed_to_create_account', error=create_response.text)}{Style.RESET_ALL}")
                        else:
                            print(f"{Fore.RED}❌ 响应内容: {create_response.text}{Style.RESET_ALL}")

                        # If it's a domain problem, try the next available domain
                        if len(filtered_domains) > 1 and ("domain" in create_response.text.lower() or "address" in create_response.text.lower()):
                            print(f"{Fore.YELLOW}⚠️ 尝试使用下一个可用域名...{Style.RESET_ALL}")
                            # Add current domain to blocked list
                            if selected_domain not in self.blocked_domains:
                                self.blocked_domains.append(selected_domain)
                            # Recursively call yourself
                            return self.create_email()

                        raise Exception(f"{self.translator.get('email.failed_to_create_account') if self.translator else '创建账户失败'}")
                except Exception as e:
                    if self.translator:
                        print(f"{Fore.RED}❌ {self.translator.get('email.failed_to_create_account', error=str(e))}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.RED}❌ 创建账户时出错: {str(e)}{Style.RESET_ALL}")
                    raise

                # Get access token
                try:
                    token_data = {
                        "address": email,
                        "password": password
                    }

                    token_response = requests.post(f"{self.api_url}/token", json=token_data, timeout=10)
                    if token_response.status_code != 200:
                        if self.translator:
                            print(f"{Fore.RED}❌ {self.translator.get('email.failed_to_get_access_token', error=token_response.status_code)}{Style.RESET_ALL}")
                        else:
                            print(f"{Fore.RED}❌ 获取令牌失败: 状态码 {token_response.status_code}{Style.RESET_ALL}")
                        if self.translator:
                            print(f"{Fore.RED}❌ {self.translator.get('email.failed_to_get_access_token', error=token_response.text)}{Style.RESET_ALL}")
                        else:
                            print(f"{Fore.RED}❌ 响应内容: {token_response.text}{Style.RESET_ALL}")
                        raise Exception(f"{self.translator.get('email.failed_to_get_access_token') if self.translator else '获取访问令牌失败'}")

                    self.token = token_response.json()["token"]
                    self.email = email
                except Exception as e:
                    print(f"{Fore.RED}❌ 获取令牌时出错: {str(e)}{Style.RESET_ALL}")
                    raise

                if self.translator:
                    print(f"{Fore.GREEN}✅ {self.translator.get('email.create_success')}: {email}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.GREEN}✅ 创建邮箱成功: {email}{Style.RESET_ALL}")
                return email

            except Exception as e:
                if attempt < max_retries:
                    print(f"{Fore.YELLOW}⚠️ 尝试重新创建邮箱... (尝试 {attempt}/{max_retries}){Style.RESET_ALL}")
                else:
                    if self.translator:
                        print(f"{Fore.RED}❌ {self.translator.get('email.create_error')}: {str(e)}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.RED}❌ 创建邮箱出错: {str(e)}{Style.RESET_ALL}")
                return None

    def close(self):
        """close browser"""
        if self.page:
            self.page.quit()

    def refresh_inbox(self):
        """refresh inbox"""
        try:
            if self.translator:
                print(f"{Fore.CYAN}🔄 {self.translator.get('email.refreshing')}{Style.RESET_ALL}")
            else:
                print(f"{Fore.CYAN}🔄 正在刷新邮箱...{Style.RESET_ALL}")
            
            # Use API to get latest email
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
            # Use API to get email list
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(f"{self.api_url}/messages", headers=headers)
            
            if response.status_code == 200:
                messages = response.json()["hydra:member"]
                for message in messages:
                    if message["from"]["address"] == "no-reply@cursor.sh" and "Verify your email address" in message["subject"]:
                        # Get email content
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
        """get verification code"""
        try:
            # Use API to get email list
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(f"{self.api_url}/messages", headers=headers)
            
            if response.status_code == 200:
                messages = response.json()["hydra:member"]
                for message in messages:
                    if message["from"]["address"] == "no-reply@cursor.sh" and "Verify your email address" in message["subject"]:
                        # Get email content
                        message_id = message["id"]
                        message_response = requests.get(f"{self.api_url}/messages/{message_id}", headers=headers)
                        
                        if message_response.status_code == 200:
                            # Extract verification code from email content
                            email_content = message_response.json()["text"]
                            # Find 6-digit verification code
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
            
            # Test refresh function
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