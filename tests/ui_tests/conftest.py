"""Pytest configuration and shared fixtures for UI automation.

This module provides common UI test fixtures, leveraging Playwright to manage
browser context and page lifecycles. It integrates with Pydantic settings.
"""

import pytest
import allure
from typing import Any, Dict, Generator
from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Error as PlaywrightError,
)
from config.settings import settings


def pytest_addoption(parser: pytest.Parser):
    """Register custom CLI options for viewport configuration."""
    group = parser.getgroup("viewport", "Viewport configuration")
    group.addoption(
        "--viewport-width",
        action="store",
        default=1920,
        type=int,
    )
    group.addoption(
        "--viewport-height",
        action="store",
        default=1080,
        type=int,
    )
    group.addoption(
        "--zoom",
        action="store",
        default="1.0",
        help="Page zoom level (e.g., '0.8' for 80%). Use for demo recording.",
    )


@pytest.fixture(autouse=True)
def playwright_tracing(page, request):
    """Automatically start Playwright tracing and attach failure artifacts (screenshots & traces).

    Stops tracing and attaches screenshot + .zip trace bundle to the Allure report
    only if the test fails during setup, execution, or teardown.
    """
    # Start tracing before test execution
    page.context.tracing.start(screenshots=True, snapshots=True, sources=True)

    yield

    # Retrieve test phase reports set by the pytest_runtest_makereport hook
    rep_setup = getattr(request.node, "rep_setup", None)
    rep_call = getattr(request.node, "rep_call", None)
    rep_teardown = getattr(request.node, "rep_teardown", None)

    # Check if the test failed in any of its execution phases
    is_failed = False
    for rep in (rep_setup, rep_call, rep_teardown):
        if rep and rep.failed:
            is_failed = True
            break

    if is_failed:
        # 1. Capture and attach failure screenshot
        with allure.step("Attach failure screenshot"):
            try:
                screenshot = page.screenshot(full_page=True)
                allure.attach(
                    screenshot,
                    name="Failure Screenshot",
                    attachment_type=allure.attachment_type.PNG,
                )
            except PlaywrightError as e:
                print(f"[Warning] Could not capture screenshot due to Playwright error: {e}")
            except Exception as e:
                print(f"[Warning] Unexpected error during screenshot capture: {e}")

        # 2. Stop tracing and attach trace archive
        with allure.step("Attach Playwright trace archive"):
            try:
                trace_path = f"artifacts/trace_{request.node.name}.zip"
                page.context.tracing.stop(path=trace_path)

                allure.attach.file(
                    trace_path,
                    name="Playwright Trace Archive",
                    attachment_type="application/zip",
                    extension=".zip",
                )
            except PlaywrightError as e:
                print(f"[Warning] Could not save trace due to Playwright error: {e}")
            except Exception as e:
                print(f"[Warning] Unexpected error during trace attachment: {e}")
    else:
        # Stop tracing without saving to disk for passed tests
        try:
            page.context.tracing.stop()
        except Exception:
            pass


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: Dict[str, Any], pytestconfig: pytest.Config) -> Dict[str, Any]:
    """
    Override browser context arguments to set viewport dimensions.
    
    This fixture prioritizes CLI flags ('--viewport-width', '--viewport-height') 
    provided at runtime, falling back to industry-standard 1920x1080 if not specified.
    """
    width = pytestconfig.getoption("--viewport-width")
    height = pytestconfig.getoption("--viewport-height")
    
    return {
        **browser_context_args,
        "viewport": {
            "width": width,
            "height": height,
        },
    }


@pytest.fixture(scope="function")
def context(browser: Browser, browser_context_args: dict) -> Generator[BrowserContext, None, None]:
    """Override standard context fixture to initialize Playwright tracing on startup.

    Educational Scaffolding:
        This fixture overrides the default pytest-playwright `context` fixture,
        automatically starts tracing with screenshots, snapshots, and sources,
        and safely closes the context on teardown to prevent resource leakage.

    Args:
        browser: The active Playwright Browser instance.
        browser_context_args: Base arguments configured for the context.

    Yields:
        BrowserContext: The tracing-enabled context.
    """
    context = browser.new_context(**browser_context_args)
    yield context
    context.close()


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args: dict, request: pytest.FixtureRequest) -> dict:
    """Override browser launch arguments, prioritizing CLI flags over settings."""
    is_headed_cli = request.config.getoption("--headed") if request.config.inicfg else False
    
    return {
        **browser_type_launch_args,
        "headless": False if is_headed_cli else settings.HEADLESS_MODE,
    }   


@pytest.fixture(scope="function")
def ui_page(page: Page, pytestconfig: pytest.Config) -> Generator[Page, None, None]:
    """Provide a pre-configured Page instance for UI testing.

    Educational Scaffolding:
        This fixture wraps the default Playwright `page` fixture, configures the base
        timeout limit according to the global configuration settings, and automatically
        handles standard teardown after the test execution completes.

    Args:
        page: The default Playwright Page instance.
        pytestconfig: The active pytest configuration object.

    Yields:
        Page: Configured Playwright Page instance.
    """
    # Apply zoom at page start if given in CLI
    zoom_level = pytestconfig.getoption("--zoom")
    if zoom_level != "1.0":
        page.evaluate(f"document.body.style.zoom = '{zoom_level}'")

    # Configure the default timeout from global configuration (Pydantic settings)
    page.set_default_timeout(settings.PAGE_TIMEOUT)
    
    yield page
    
    # Context/Page is automatically closed by pytest-playwright,
    # but any custom per-test UI cleanup can be added here if needed.