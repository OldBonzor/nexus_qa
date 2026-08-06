"""UI test suite for catalog inventory, sorting, filtering, and guest cart interactions."""

import pytest
from playwright.sync_api import Page, expect
from src.ui.pages.inventory_page import InventoryPage


@pytest.mark.ui
class TestCatalogAndInventoryUI:
    """Test class covering catalog storefront operations."""

    def test_catalog_display_products(self, ui_page: Page) -> None:
        """Verify that products are correctly displayed in the catalog grid
        with mandatory attributes: title, price, and image.
        """
        # --- Arrange ---
        inventory_page = InventoryPage(ui_page)
        inventory_page.open()

        # --- Act & Assert ---
        product_cards = inventory_page.get_product_cards()
        assert product_cards.count() > 0, "No product cards found on the catalog page."

        for card in product_cards.all():
            expect(card.locator(InventoryPage.PRODUCT_TITLE)).to_be_visible()
            expect(card.locator(InventoryPage.PRODUCT_IMAGE)).to_be_visible()
            expect(card.locator(InventoryPage.PRODUCT_PRICE)).to_be_visible()

    @pytest.mark.parametrize(
        (
            "search_query",
            "expected_keyword",
        ),
        [
            ("Hammer", "Hammer"),
            ("Sander", "Sander"),
        ],
        ids=[
            "search_hammer",
            "search_sander",
        ],
    )
    def test_search_product(
        self,
        ui_page: Page,
        search_query: str,
        expected_keyword: str,
    ) -> None:
        """Verify that searching for a product returns relevant items matching the query."""
        # --- Arrange ---
        inventory_page = InventoryPage(ui_page)
        inventory_page.open()

        # --- Act ---
        inventory_page.search_product(search_query)

        # --- Assert ---
        product_names = inventory_page.get_all_product_names()
        assert len(product_names) > 0, (f"No products found for search query: '{search_query}'")
        assert all(expected_keyword.lower() in name.lower() for name in product_names), (
            f"Some products do not match the search query '{search_query}'. "
            f"Actual products: {product_names}"
        )

    def test_search_product_no_results(self, ui_page: Page) -> None:
        """Verify that searching for a non-existent product results in an empty catalog grid."""
        # --- Arrange ---
        inventory_page = InventoryPage(ui_page)
        inventory_page.open()
        non_existent_query = "NonExistentProductXYZ123"

        # --- Act ---
        inventory_page.search_product(non_existent_query)

        # --- Assert ---
        empty_product_names = inventory_page.get_all_product_names()
        assert len(empty_product_names) == 0, (
            f"Expected zero products for query '{non_existent_query}', "
            f"but found: {empty_product_names}"
        )

    @pytest.mark.parametrize(
        ("sort_option", "descending"),
        [
            ("Price (Low - High)", False),
            ("Price (High - Low)", True),
            ("Name (A - Z)", False),
            ("Name (Z - A)", True),
            ("CO₂ Rating (A - E)", False),
            ("CO₂ Rating (E - A)", True),
        ],
        ids=[
            "price_low_to_high",
            "price_high_to_low",
            "name_a_to_z",
            "name_z_to_a",
            "co2_a_to_e",
            "co2_e_to_a",
        ],
    )
    def test_catalog_sorting_parametrized(
        self, 
        ui_page: Page, 
        sort_option: str, 
        descending: bool
    ) -> None:
        """Verify that products on the main page can be sorted by various options
        in both ascending and descending directions, and the UI correctly reflects
        the sorted order after network synchronization.
        """
        # --- Arrange ---
        inventory_page = InventoryPage(ui_page)
        inventory_page.open()

        # --- Act ---
        inventory_page.sort_by(sort_option)

        # --- Act ---
        # Fetch actual values from the UI based on the sorting type using match/case
        values = inventory_page.get_product_values_by_sort_option(sort_option)

        assert len(values) > 1, f"Not enough products found on the page to verify sorting for {sort_option}."

        assert values == sorted(values, reverse=descending), (
            f"Products are not sorted correctly for {sort_option} "
            f"(descending={descending}). Actual values: {values}"
        )

    @pytest.mark.parametrize(
        "category, subcategory, expected_keywords",
        [
            ("Hand Tools", "Hammer", ["Hammer"]),
            ("Hand Tools", "Pliers", ["pliers", "cutter"]),
            ("Power Tools", "Sander", ["Sander"]),
            (None, "Hammer", ["Hammer"]),
        ],
        ids=[
            "Hand Tools -> Hammer",
            "Hand Tools -> Pliers (with cutter)",
            "Power Tools -> Sander",
            "Only Subcategory -> Hammer",
        ],
    )
    def test_catalog_filtering_by_category(
        self,
        ui_page: Page,
        category: str | None,
        subcategory: str | None,
        expected_keywords: list[str],
    ) -> None:
        """Verify that products on the main page can be filtered by category 
        and optional nested subcategories, and the UI correctly reflects the filtered results.
        """
        # --- Arrange ---
        inventory_page = InventoryPage(ui_page)
        inventory_page.open()

        # --- Act ---
        # Apply category filter using match/case based on category structure complexity
        match (category, subcategory):
            case (cat, sub) if sub is not None:
                inventory_page.filter_by_category(category_name=cat, subcategory_name=sub)
            case (cat, None):
                inventory_page.filter_by_category(category_name=cat)
            case _:
                raise ValueError(f"Unsupported category filter combination: {category} -> {subcategory}")

        # --- Assert --- 
        # Verify that all displayed products match the selected category/keyword
        product_names = inventory_page.get_all_product_names()
        assert len(product_names) > 0, f"No products found for category: {category} / {subcategory}"

        assert all(
            any(keyword.lower() in name.lower() for keyword in expected_keywords) 
            for name in product_names
        ), (
            f"Some products do not match any of the expected filter keywords '{expected_keywords}'. "
            f"Actual products: {product_names}"
        )