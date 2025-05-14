import requests
import time
import re
import random
import string
from .email_tab_interface import EmailTabInterface

class OneSecMailTab(EmailTabInterface):
    """Implementation of EmailTabInterface for 1secmail.com API"""
    def __init__(self, translator=None):
        self.translator = translator
        self.base_url = "https://www.1secmail.com/api/v1/"
        self.login, self.domain = self._generate_account()
        self.address = f"{self.login}@{self.domain}"
        self._cached_verification_code = None
        self._cached_mail_id = None

    def _generate_account(self):
        domains = [
            "1secmail.com", "1secmail.org", "1secmail.net",
            "wwjmp.com", "esiix.com", "xojxe.com", "yoggm.com"
        ]
        login = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        domain = random.choice(domains)
        return login, domain

    def refresh_inbox(self):
        pass

    def check_for_cursor_email(self, poll_interval=5, timeout=120):
        start_time = time.time()
        while time.time() - start_time < timeout:
            params = {
                "action": "getMessages",
                "login": self.login,
                "domain": self.domain
            }
            resp = requests.get(self.base_url, params=params)
            if resp.status_code == 200:
                for mail in resp.json():
                    if "cursor" in mail.get("from", "").lower():
                        mail_id = mail["id"]
                        code = self._extract_verification_code(mail_id)
                        if code:
                            self._cached_verification_code = code
                            self._cached_mail_id = mail_id
                            return True
            time.sleep(poll_interval)
        return False

    def _extract_verification_code(self, mail_id):
        params = {
            "action": "readMessage",
            "login": self.login,
            "domain": self.domain,
            "id": mail_id
        }
        resp = requests.get(self.base_url, params=params)
        text = resp.json().get("textBody", "")
        match = re.search(r'\b(\d{6})\b', text)
        if match:
            return match.group(1)
        return None

    def get_verification_code(self):
        return self._cached_verification_code or ""

    def get_email_address(self):
        return self.address 