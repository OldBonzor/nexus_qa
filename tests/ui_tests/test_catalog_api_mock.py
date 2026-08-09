"""UI tests verifying application resilience and error handling via network mocking."""

import pytest
from playwright.sync_api import Page, expect
from src.ui.pages.inventory_page import InventoryPage


@pytest.mark.ui
class TestCatalogResilienceUI:
    """Test suite for catalog error handling and network failure resilience."""

    def test_catalog_handling_on_api_failure(self, ui_page: Page) -> None:
        """Verify that the UI handles a 500 Internal Server Error from the products API
        gracefully without crashing or hanging indefinitely.
        """
        # --- Arrange ---
        inventory_page = InventoryPage(ui_page)

        # Intercept the products endpoint and mock a 500 Server Error response
        def mock_server_error(route):
            route.fulfill(
                status=500,
                content_type="application/json",
                body='{"error": "Internal Server Error"}',
            )

        ui_page.route("**/products*", mock_server_error)

        try:
            # --- Act ---
            inventory_page.open()

            # --- Assert ---
            expect(ui_page.locator("app-root")).to_be_visible()
            expect(ui_page.locator(inventory_page.PRODUCT_CARD)).to_have_count(0)

        finally:
            ui_page.unroute("**/products*", mock_server_error)