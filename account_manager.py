import os
from colorama import Fore, Style
import re

# Define emoji constants
EMOJI = {
    'SUCCESS': '✅',
    'ERROR': '❌',
    'INFO': 'ℹ️'
}

class AccountManager:
    def __init__(self, translator=None):
        self.translator = translator
        self.accounts_file = 'cursor_accounts.txt'
    
    def save_account_info(self, email, password, token, total_usage):
        """Save account information to file"""
        try:
            with open(self.accounts_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*50}\n")
                f.write(f"Email: {email}\n")
                f.write(f"Password: {password}\n")
                f.write(f"Token: {token}\n")
                f.write(f"Usage Limit: {total_usage}\n")
                f.write(f"{'='*50}\n")
                
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('register.account_info_saved') if self.translator else 'Account information saved'}...{Style.RESET_ALL}")
            return True
            
        except Exception as e:
            error_msg = self.translator.get('register.save_account_info_failed', error=str(e)) if self.translator else f'Failed to save account information: {str(e)}'
            print(f"{Fore.RED}{EMOJI['ERROR']} {error_msg}{Style.RESET_ALL}")
            return False
    
    def get_last_email_domain(self):
        """Get the domain from the last used email"""
        try:
            if not os.path.exists(self.accounts_file):
                return None
            
            # Only read the last 1KB of data from the file
            with open(self.accounts_file, 'rb') as f:
                # Get file size
                f.seek(0, os.SEEK_END)
                file_size = f.tell()
                
                if file_size == 0:
                    return None
                
                # Determine the number of bytes to read, maximum 1KB
                read_size = min(1024, file_size)
                
                # Move to the appropriate position to start reading
                f.seek(file_size - read_size)
                
                # Read the end data
                data = f.read(read_size).decode('utf-8', errors='ignore')
            
            # Split by lines and search in reverse
            lines = data.split('\n')
            for line in reversed(lines):
                if line.strip().startswith('Email:'):
                    email = line.split('Email:')[1].strip()
                    # Extract domain part (after @)
                    if '@' in email:
                        return email.split('@')[1]
                    return None
            
            # If no email is found in the last 1KB
            return None
            
        except Exception as e:
            error_msg = self.translator.get('account.get_last_email_domain_failed', error=str(e)) if self.translator else f'Failed to get the last used email domain: {str(e)}'
            print(f"{Fore.RED}{EMOJI['ERROR']} {error_msg}{Style.RESET_ALL}")
            return None
    
    def suggest_email(self, first_name, last_name):
        """Generate a suggested email based on first and last name with the last used domain"""
        try:
            # Get the last used email domain
            domain = self.get_last_email_domain()
            if not domain:
                return None
            
            # Generate email prefix from first and last name (lowercase)
            email_prefix = f"{first_name.lower()}.{last_name.lower()}"
            
            # Combine prefix and domain
            suggested_email = f"{email_prefix}@{domain}"
            
            return suggested_email
        
        except Exception as e:
            error_msg = self.translator.get('account.suggest_email_failed', error=str(e)) if self.translator else f'Failed to suggest email: {str(e)}'
            print(f"{Fore.RED}{EMOJI['ERROR']} {error_msg}{Style.RESET_ALL}")
            return None
