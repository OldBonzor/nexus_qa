"""Pytest configuration and shared fixtures for UI automation.

This module provides common UI test fixtures, leveraging Playwright to manage
browser context and page lifecycles. It integrates with Pydantic settings.
"""

from typing import Generator
import pytest
from playwright.sync_api import Browser, BrowserContext, Page
from config.settings import settings


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args: dict, request: pytest.FixtureRequest) -> dict:
    """Override browser launch arguments, prioritizing CLI flags over settings."""
    is_headed_cli = request.config.getoption("--headed") if request.config.inicfg else False
    
    return {
        **browser_type_launch_args,
        "headless": False if is_headed_cli else settings.HEADLESS_MODE,
    }   


@pytest.fixture(scope="function")
def ui_page(page: Page) -> Generator[Page, None, None]:
    """Provide a pre-configured Page instance for UI testing.

    Educational Scaffolding:
        This fixture wraps the default Playwright `page` fixture, configures the base
        timeout limit according to the global configuration settings, and automatically
        handles standard teardown after the test execution completes.

    Args:
        page: The default Playwright Page instance.

    Yields:
        Page: Configured Playwright Page instance.
    """
    # Configure the default timeout from global configuration (Pydantic settings)
    page.set_default_timeout(settings.PAGE_TIMEOUT)
    
    yield page
    
    # Context/Page is automatically closed by pytest-playwright,
    # but any custom per-test UI cleanup can be added here if needed.
