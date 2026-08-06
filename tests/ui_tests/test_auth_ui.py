"""UI test suite for authorization, security, and session management."""

import pytest
from playwright.sync_api import Page, expect
from config.settings import settings
from src.ui.pages.login_page import LoginPage


@pytest.mark.ui
class TestAuthAndSecurityUI:
    """Test class covering authentication and security scenarios."""

    @pytest.mark.xfail(
        reason="Frontend Angular router fails to update route and view properly after successful login API response on test stand."
    )
    def test_successful_login(self, ui_page: Page) -> None:
        """Successful login with valid credentials via UI using stability hooks."""
        # Arrange
        login_page = LoginPage(ui_page)
        login_page.open()

        # Act
        login_page.login_with_stability(settings.TEST_USER_EMAIL, settings.TEST_USER_PASSWORD)
        
        # Assert
        login_page.verify_successful_login()

    def test_login_with_invalid_credentials(self, ui_page: Page) -> None:
        """Negative login scenario with an incorrect password."""
        # Arrange
        login_page = LoginPage(ui_page)
        login_page.open()

        # Act
        login_page.login(settings.TEST_USER_EMAIL, "wrong_password_123")
        error_text = login_page.get_error_message()

        # Assert
        assert "Invalid email or password" in error_text or "Unauthorized" in error_text, \
            f"Expected error message not found. Actual text: '{error_text}'"

    def test_unauthorized_access_redirection(self, ui_page: Page) -> None:
        """Security role model check (direct URL access without authentication)."""
        # Arrange
        login_page = LoginPage(ui_page)
        expected_login_url = f"{str(settings.BASE_UI_URL).rstrip('/')}/auth/login"

        # Act
        login_page.navigate("/admin/dashboard")

        # Assert
        expect(ui_page).to_have_url(expected_login_url)

    @pytest.mark.xfail(
        reason="Frontend Angular router fails to update route and view properly after successful login API response on test stand."
    )
    def test_session_persistence_after_page_reload(self, ui_page: Page) -> None:
        """Verify session persistence after a hard page refresh using stability hooks."""
        # Arrange
        login_page = LoginPage(ui_page)
        
        # Act
        login_page.open()
        login_page.login_with_stability(settings.TEST_USER_EMAIL, settings.TEST_USER_PASSWORD)
        login_page.verify_successful_login()
        ui_page.reload()

        # Assert
        login_page.verify_successful_login()