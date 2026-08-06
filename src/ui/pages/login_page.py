"""Page Object representing the Login Page of Practice Software Testing.

Encapsulates all locators and user interactions specific to the authentication view.
"""

from playwright.sync_api import expect
from src.ui.pages.base_page import BasePage


class LoginPage(BasePage):
    """Page Object for the Practice Software Testing Login Page."""

    # UI Locators for the login form elements
    EMAIL_INPUT = "id=email"
    PASSWORD_INPUT = "id=password"
    LOGIN_BUTTON = "[data-test='login-submit']"
    ALERT_ERROR = "css=.alert-danger"
    
    # Unique marker for the secure zone interface (avoids URL race conditions)
    USER_NAV_MENU = "[data-test='nav-menu']"

    def open(self) -> None:
        """Navigate to the login page view."""
        self.navigate("/auth/login")

    def login(self, email: str, password: str) -> None:
        """Perform the complete authentication workflow through the form.

        Args:
            email (str): User email address.
            password (str): User password.
        """
        self.fill(self.EMAIL_INPUT, email)
        self.fill(self.PASSWORD_INPUT, password)
        self.click(self.LOGIN_BUTTON)

    def login_with_stability(self, email: str, password: str) -> None:
        """Perform resilient login ensuring inputs are ready and awaiting network response."""
        # Ensure input elements are visible and interactable before typing
        self.wait_for_visible(self.EMAIL_INPUT)
        self.fill(self.EMAIL_INPUT, email)
        self.fill(self.PASSWORD_INPUT, password)
        
        # Wrap click in a network response expectation to guarantee backend processing
        with self.page.expect_response("**/users/login") as response_info:
            self.click(self.LOGIN_BUTTON)
            
        response = response_info.value
        assert response.status == 200, f"Login failed with backend status code: {response.status}"

    def get_error_message(self) -> str:
        """Retrieve the authentication error message text from the alert block.

        Returns:
            str: Inner text of the error alert element.
        """
        return self.get_text(self.wait_for_visible(self.ALERT_ERROR))

    def verify_successful_login(self) -> None:
        """Verify successful login exclusively via the unique user menu element in the secure zone."""
        # Relying solely on DOM visibility of the secure area to prevent SPA router race conditions
        expect(self.page.locator(self.USER_NAV_MENU)).to_be_visible(timeout=10000)