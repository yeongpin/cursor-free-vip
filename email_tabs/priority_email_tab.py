from .email_tab_interface import EmailTabInterface
from .mail_tm_tab import MailTmTab
from .one_sec_mail_tab import OneSecMailTab
from .temp_mail_org_tab import TempMailOrgTab

class PriorityEmailTab(EmailTabInterface):
    """Tries multiple email providers in order, falling back if one fails."""
    def __init__(self, translator=None):
        self.translator = translator
        self.providers = [
            MailTmTab(translator),
            OneSecMailTab(translator),
            TempMailOrgTab(translator),
        ]
        self.active = None

    def refresh_inbox(self):
        if self.active:
            self.active.refresh_inbox()

    def check_for_cursor_email(self, poll_interval=5, timeout=120):
        for provider in self.providers:
            if provider.check_for_cursor_email(poll_interval=poll_interval, timeout=timeout):
                self.active = provider
                return True
        return False

    def get_verification_code(self):
        if self.active:
            return self.active.get_verification_code()
        return ""

    def get_email_address(self):
        # Always return the first provider's email for registration
        return self.providers[0].get_email_address() 