import requests
import time
import re
from .email_tab_interface import EmailTabInterface

class MailTmTab(EmailTabInterface):
    """Implementation of EmailTabInterface for mail.tm API"""
    def __init__(self, translator=None):
        self.translator = translator
        self.base_url = "https://api.mail.tm"
        self.address, self.password = self._create_account()
        self.token = self._get_token()
        self._cached_verification_code = None
        self._cached_mail_id = None

    def _create_account(self):
        # Get available domains
        domains = requests.get(f"{self.base_url}/domains").json()["hydra:member"]
        domain = domains[0]["domain"]
        import random, string
        username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        address = f"{username}@{domain}"
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        requests.post(f"{self.base_url}/accounts", json={"address": address, "password": password})
        return address, password

    def _get_token(self):
        resp = requests.post(f"{self.base_url}/token", json={"address": self.address, "password": self.password})
        return resp.json()["token"]

    def refresh_inbox(self):
        pass

    def check_for_cursor_email(self, poll_interval=5, timeout=120):
        headers = {"Authorization": f"Bearer {self.token}"}
        start_time = time.time()
        while time.time() - start_time < timeout:
            resp = requests.get(f"{self.base_url}/messages", headers=headers)
            if resp.status_code == 200:
                for mail in resp.json()["hydra:member"]:
                    if "cursor" in mail.get("from", {}).get("address", "").lower():
                        mail_id = mail["id"]
                        code = self._extract_verification_code(mail_id, headers)
                        if code:
                            self._cached_verification_code = code
                            self._cached_mail_id = mail_id
                            return True
            time.sleep(poll_interval)
        return False

    def _extract_verification_code(self, mail_id, headers):
        resp = requests.get(f"{self.base_url}/messages/{mail_id}", headers=headers)
        text = resp.json().get("text", "")
        match = re.search(r'\b(\d{6})\b', text)
        if match:
            return match.group(1)
        return None

    def get_verification_code(self):
        return self._cached_verification_code or ""

    def get_email_address(self):
        return self.address 