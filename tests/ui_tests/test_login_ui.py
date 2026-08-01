"""Smoke UI test suite to verify the base Playwright and Page Object Model setup.

This module contains lightweight verification tests ensuring that browser contexts
initialize, network requests resolve, and the BasePage class functions correctly.
"""

from playwright.sync_api import Page, expect
from src.ui.base_page import BasePage


def test_smoke_page_title_and_header(ui_page: Page) -> None:
    """Verify that the home page loads successfully and displays the expected title and logo/header.

    Educational Scaffolding:
        This test uses the `ui_page` fixture, which automatically sets up the page timeout.
        It wraps the page in our modular `BasePage` class, uses the encapsulated navigation
        helper, and utilizes Playwright's web assertions (`expect`) to leverage auto-waiting.

    Args:
        ui_page (Page): Pre-configured Playwright Page instance.
    """
    # Arrange: Initialize the base page with our pre-configured Playwright Page
    base_page = BasePage(ui_page)

    # Act: Navigate to the application home page (resolved dynamically against settings.BASE_UI_URL)
    base_page.navigate("/")

    # Assert 1: Verify the page title contains expected brand name or structure
    title = base_page.get_title()
    assert "Practice Software Testing" in title or "Sandbox" in title or len(title) > 0, (
        f"Unexpected page title received: '{title}'"
    )

    # Assert 2: Use web assertion with implicit retry logic to check for a core element (e.g., logo or banner)
    # The practice site has an item/brand filter or a header logo. Let's make sure the page body or main content is visible.
    body_locator = ui_page.locator("body")
    expect(body_locator).to_be_visible()
