import requests
import hashlib
import random
import string
import time
import re
from .email_tab_interface import EmailTabInterface

class TempMailOrgTab(EmailTabInterface):
    """Implementation of EmailTabInterface for temp-mail.org"""

    def __init__(self, translator=None):
        self.translator = translator
        self.base_url = "https://api.temp-mail.org/request"
        self.email = self._generate_email()
        self.email_hash = hashlib.md5(self.email.encode()).hexdigest()
        self._cached_verification_code = None
        self._cached_mail_id = None

    def _generate_email(self):
        # Get available domains
        try:
            resp = requests.get(f"{self.base_url}/domains/format/json/")
            domains = resp.json()
            domain = random.choice(domains)
        except Exception:
            # fallback domain
            domain = "@temp-mail.org"
        username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        return f"{username}{domain}"

    def refresh_inbox(self):
        # No-op for API polling
        pass

    def check_for_cursor_email(self, poll_interval=5, timeout=120):
        """Poll for a new email from Cursor and extract the verification code."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                url = f"{self.base_url}/mail/id/{self.email_hash}/format/json/"
                resp = requests.get(url)
                if resp.status_code == 200:
                    mails = resp.json()
                    for mail in mails:
                        if 'cursor' in mail.get('mail_from', '').lower():
                            code = self._extract_verification_code(mail)
                            if code:
                                self._cached_verification_code = code
                                self._cached_mail_id = mail.get('mail_id')
                                return True
                # If not found, wait and retry
                time.sleep(poll_interval)
            except Exception:
                time.sleep(poll_interval)
        return False

    def _extract_verification_code(self, mail):
        # Try to extract a 6-digit code from the email text
        text = mail.get('mail_text', '')
        match = re.search(r'\b(\d{6})\b', text)
        if match:
            return match.group(1)
        return None

    def get_verification_code(self):
        return self._cached_verification_code or ""

    def get_email_address(self):
        return self.email

if __name__ == "__main__":
    tab = TempMailOrgTab()
    print("Generated email:", tab.get_email_address())
    print("Waiting for Cursor email...")
    if tab.check_for_cursor_email():
        print("Verification code:", tab.get_verification_code())
    else:
        print("No verification code received in time.") 