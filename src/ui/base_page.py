"""Foundational Page Object Model defining shared interactions with standard logging and safety mechanisms.

This module houses BasePage, which acts as the superclass for all Page Objects.
It encapsulates common browser interactions using Playwright's sync_api, wrapping
them in error-handling try-except blocks and standardizing logging.
"""

import logging
from typing import Optional
from playwright.sync_api import Page, Locator, TimeoutError as PlaywrightTimeoutError

# Configure logger for tracking UI automation actions
logger = logging.getLogger("nexus_qa.ui")


class BasePage:
    """Foundational Page Object containing common reusable actions for UI testing.

    Provides a clean, unified interface to interact with Web elements, incorporating
    automatic waiting, robust error handling, and standard action logging.
    """

    def __init__(self, page: Page) -> None:
        """Initialize the BasePage with a Playwright Page instance.

        Args:
            page (Page): The active Playwright page context.
        """
        self.page = page

    def navigate(self, path: str = "") -> None:
        """Navigate to a given path or absolute URL.

        If a relative path is passed, it is resolved against the configured base URL.

        Args:
            path (str): Relative path (e.g., '/auth/login') or absolute URL.
        """
        from config.settings import settings

        base_url = str(settings.BASE_UI_URL).rstrip("/")
        # If the path is not a full URL, prepend the base URL
        target_url = path if path.startswith("http") else f"{base_url}/{path.lstrip('/')}"

        logger.info(f"Navigating to URL: {target_url}")
        try:
            self.page.goto(target_url)
        except Exception as e:
            logger.error(f"Failed to navigate to {target_url}. Error: {str(e)}")
            raise

    def get_locator(self, selector_or_locator: str | Locator) -> Locator:
        """Normalize a selector (string or Locator) into a Playwright Locator.

        Educational Scaffolding:
            Accepting both raw string CSS/XPath selectors and existing Locator objects
            makes our helper methods extremely versatile across different page layers.

        Args:
            selector_or_locator (str | Locator): Target element represented as CSS, XPath, or Locator.

        Returns:
            Locator: Fully qualified Playwright Locator object.
        """
        if isinstance(selector_or_locator, Locator):
            return selector_or_locator
        return self.page.locator(selector_or_locator)

    def wait_for_visible(self, selector_or_locator: str | Locator, timeout: Optional[float] = None) -> Locator:
        """Wait for an element to become visible on the page.

        Args:
            selector_or_locator (str | Locator): Selector string or Playwright Locator.
            timeout (Optional[float]): Custom timeout in milliseconds.

        Returns:
            Locator: The locator pointing to the visible element.

        Raises:
            PlaywrightTimeoutError: If the element is not visible within the timeout period.
        """
        locator = self.get_locator(selector_or_locator)
        logger.debug(f"Waiting for element to be visible: {locator}")
        try:
            locator.wait_for(state="visible", timeout=timeout)
            return locator
        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout waiting for element to be visible: {locator}. Error: {str(e)}")
            raise

    def click(self, selector_or_locator: str | Locator) -> None:
        """Wait for an element to be ready, then perform a click action.

        Args:
            selector_or_locator (str | Locator): Selector string or Playwright Locator.
        """
        locator = self.get_locator(selector_or_locator)
        logger.info(f"Clicking element: {locator}")
        try:
            locator.click()
        except Exception as e:
            logger.error(f"Failed to click element: {locator}. Error: {str(e)}")
            raise

    def fill(self, selector_or_locator: str | Locator, value: str) -> None:
        """Wait for an element to be ready, clear it, and enter the provided text.

        Args:
            selector_or_locator (str | Locator): Selector string or Playwright Locator.
            value (str): Text value to enter.
        """
        locator = self.get_locator(selector_or_locator)
        # Suppress password logging for security compliance
        log_value = "********" if "password" in str(locator).lower() else value
        logger.info(f"Filling element: {locator} with value: '{log_value}'")
        try:
            locator.fill(value)
        except Exception as e:
            logger.error(f"Failed to fill element: {locator}. Error: {str(e)}")
            raise

    def get_text(self, selector_or_locator: str | Locator) -> str:
        """Retrieve the inner text of a target element.

        Args:
            selector_or_locator (str | Locator): Selector string or Playwright Locator.

        Returns:
            str: Inner text content of the element.
        """
        locator = self.get_locator(selector_or_locator)
        logger.debug(f"Retrieving text content for element: {locator}")
        try:
            text = locator.inner_text()
            logger.debug(f"Retrieved text: '{text}'")
            return text
        except Exception as e:
            logger.error(f"Failed to retrieve text from element: {locator}. Error: {str(e)}")
            raise

    def get_title(self) -> str:
        """Retrieve the current page title.

        Returns:
            str: Document title.
        """
        try:
            title = self.page.title()
            logger.debug(f"Current page title: '{title}'")
            return title
        except Exception as e:
            logger.error(f"Failed to retrieve page title. Error: {str(e)}")
            raise
