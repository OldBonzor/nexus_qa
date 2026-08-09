"""Page Object representing the Checkout and Authentication Flow of Practice Software Testing.

Encapsulates locators and checks related to the checkout process and login redirection.
"""

from playwright.sync_api import Page, Locator
from src.ui.pages.base_page import BasePage

class CheckoutPage(BasePage):
    """Page object for the checkout and login redirection flow."""
    
    LOGIN_HEADING = "h3:has-text('Login')"  # Or specific selector for login form title

    def __init__(self, page: Page):
        """Initialize CheckoutPage with Playwright page instance."""
        super().__init__(page)

    @property
    def login_heading(self) -> Locator:
        """Get login page heading locator for validation."""
        return self.page.locator(self.LOGIN_HEADING)