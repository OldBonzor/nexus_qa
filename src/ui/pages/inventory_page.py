"""Page Object representing the Catalog and Inventory Page of Practice Software Testing.

Encapsulates all locators and user interactions specific to the storefront,
catalog sorting, filtering, and cart operations.
"""

from typing import List
from playwright.sync_api import Locator, expect
from src.ui.pages.base_page import BasePage


class InventoryPage(BasePage):
    """Page Object for the Practice Software Testing Inventory/Catalog Page."""

    # UI Locators for catalog, filters, products, and cart
    SORT_SELECT = "select[data-test='sort']"
    CATEGORY_CHECKBOX = "input[type='checkbox']"
    PRODUCT_CARD = "a.card[data-test^='product-']"
    PRODUCT_TITLE = ".card-title"
    PRODUCT_DESCRIPTION = "#description"
    PRODUCT_DETAIL_PRICE = "[data-test='unit-price']"
    PRODUCT_PRICE = "[data-test='product-price']"
    PRODUCT_IMAGE = ".card-img-top"
    SEARCH_INPUT = "[data-test='search-query']"
    SEARCH_SUBMIT = "[data-test='search-submit']"
    CO2_RATING = "[data-test='co2-rating-badge'] .co2-letter.active"
    ADD_TO_CART_BTN = "[data-test='add-to-cart']"
    CART_COUNTER = "[data-test='cart-quantity']"
    NAV_CART = "[data-test='nav-cart']"
    
    @staticmethod
    def get_category_checkbox_locator(category_name: str) -> str:
        """Generate a dynamic locator for a category filter checkbox.

        Args:
            category_name (str): Name of the category (e.g., 'Hand Tools').

        Returns:
            str: CSS or XPath selector for the category label/checkbox.
        """
        return f"//label[contains(text(), '{category_name}')]"

    def open(self, expected_status: int = 200) -> None:
        """Navigate to the main storefront catalog page and wait for product data response.

        Args:
            expected_status (int): Expected HTTP response status code for products request (default: 200).
        """
        with self.page.expect_response(lambda res: "/products" in res.url and res.status == expected_status) as response_info:
            self.navigate("/")
        
        response = response_info.value
        assert response.status == expected_status, f"Catalog failed with status: {response.status}, expected {expected_status}"

    def search_product(self, query: str) -> None:
        """Type a search query into the search input field and submit,
        waiting for the network response to synchronize the filtered product grid
        and prevent race conditions.

        Args:
            query (str): The keyword or product name to search for (e.g., 'Hammer').
        """
        search_input_locator = self.page.locator(self.SEARCH_INPUT)
        search_submit_locator = self.page.locator(self.SEARCH_SUBMIT)

        self.wait_for_visible(search_input_locator)
        search_input_locator.fill(query)

        # Wrap the submission in a network response expectation for the products search endpoint
        with self.page.expect_response("**/products/search*") as response_info:
            search_submit_locator.click()

        response = response_info.value
        assert (response.status == 200), (
            f"Failed to perform product search. Status: {response.status}"
        )

        # Check if any product cards are present using count() to avoid hardcoded timeouts
        product_cards = self.page.locator(self.PRODUCT_CARD)
        if product_cards.count() > 0:
            product_cards.first.wait_for(state="visible")

    def sort_by(self, sort_option_value: str) -> None:
        """Select a sorting option from the product catalog dropdown and wait for grid update.

        Args:
            sort_option_value (str): Visible text or label of the sorting option to select 
                                     (e.g., 'Price (Low - High)').
        """
        self.page.locator(self.PRODUCT_CARD).first.wait_for(state="visible")
        
        sort_locator = self.page.locator(self.SORT_SELECT)
        self.wait_for_visible(sort_locator)
        
        # Expect the products endpoint to be called and return sorted data upon selection
        with self.page.expect_response("**/products*") as response_info:
            sort_locator.select_option(label=sort_option_value)
            
        response = response_info.value
        assert response.status == 200, f"Failed to sort products. Status: {response.status}"

        # Ensure the product grid successfully re-renders after sorting
        expect(self.page.locator(self.PRODUCT_CARD).first).to_be_visible()

    def filter_by_category(
        self,
        category_name: str | None = None,
        subcategory_name: str | None = None,
    ) -> None:
        """Filter the product catalog by selecting a category and an optional nested subcategory
        using reliable text-based element targeting.

        Args:
            category_name (str): The main category visible name (e.g., 'Hand Tools').
            subcategory_name (str | None): The nested subcategory visible name if applicable (e.g., 'Hammer').
        """
        self.page.locator(self.PRODUCT_CARD).first.wait_for(state="visible")
        
        target_name = subcategory_name if subcategory_name else category_name
        
        target_checkbox = self.page.locator(f"//label[contains(normalize-space(), '{target_name}')]//input[@type='checkbox']")
        self.wait_for_visible(target_checkbox.first)
        
        with self.page.expect_response("**/products*") as response_info:
            target_checkbox.first.click(force=True)

        response = response_info.value
        assert response.status == 200, f"Failed to filter products. Status: {response.status}"

        # Allow a short moment for grid update; if no products match, don't crash hard on visibility if empty check handles it
        try:
            expect(self.page.locator(self.PRODUCT_CARD).first).to_be_visible()
        except AssertionError:
            expect(self.page.locator(self.PRODUCT_CARD)).to_have_count(0)

    def get_product_cards(self) -> Locator:
        """Retrieve all product card locators currently displayed in the catalog grid,
        ensuring the grid is fully loaded and synchronized to prevent race conditions.

        Returns:
            Locator: A Playwright Locator representing all matching product cards.
        """
        cards_locator = self.page.locator(self.PRODUCT_CARD)
        expect(cards_locator.first).to_be_visible()
        return cards_locator

    def get_all_product_prices(self) -> List[float]:
        """Extract and parse all product prices currently displayed in the catalog grid safely,
        skipping invalid or non-numeric price formats to prevent test crashes.
        """
        price_locator = self.page.locator(self.PRODUCT_PRICE)
        expect(price_locator.first).to_be_visible()
        
        price_elements = price_locator.all_inner_texts()
        
        parsed_prices = []
        for price_str in price_elements:
            cleaned_str = price_str.replace("$", "").replace(",", "").strip()
            try:
                if cleaned_str:
                    parsed_prices.append(float(cleaned_str))
            except ValueError:
                # Skip elements which can't be converted to digits (Markup bugs protection)
                continue
                
        return parsed_prices

    def get_all_product_names(self) -> list[str]:
        """Retrieve the names of all products currently displayed in the catalog.

        Returns:
            A list of product names as strings.
        """
        # Locate all product title elements using the predefined locator constant
        titles = self.page.locator(self.PRODUCT_TITLE).all_inner_texts()
        return [title.strip() for title in titles]

    def get_all_product_co2_ratings(self) -> List[str]:
        """Retrieve the active CO2 ratings of all products currently displayed in the catalog.

        Returns:
            A list of active CO2 rating letters as strings.
        """
        rating_locator = self.page.locator(self.CO2_RATING)
        expect(rating_locator.first).to_be_visible()
        ratings = rating_locator.all_inner_texts()
        return [rating.strip() for rating in ratings]

    def get_product_values_by_sort_option(self, sort_option: str) -> List:
        """Fetch product values (prices, names, or ratings) based on the sorting option using match/case."""
        match sort_option:
            case option if "Price" in option:
                return self.get_all_product_prices()
            case option if "Name" in option:
                return self.get_all_product_names()
            case option if "CO₂" in option or "CO2" in option:
                return self.get_all_product_co2_ratings()
            case _:
                raise ValueError(f"Unsupported sorting option: {sort_option}")

    def get_product_cards_count(self) -> int:
        """Get the count of currently visible product cards in the catalog."""  
        return self.page.locator(self.PRODUCT_CARD).count()

    def open_first_product_details(self) -> None:
        """Open the details page of the first available product from the catalog grid."""
        first_card = self.page.locator(self.PRODUCT_CARD).first
        self.wait_for_visible(first_card)
        first_card.click()

    def open_first_available_product_details(self) -> None:
        """Open the details page of the first product that is currently in stock (not out of stock)."""
        available_card = self.page.locator(self.PRODUCT_CARD).filter(has_not_text="Out of stock").first
        self.wait_for_visible(available_card)
        available_card.click()

    def add_product_to_cart_from_details(self) -> None:
        add_btn = self.page.locator(self.ADD_TO_CART_BTN)
        expect(add_btn).to_be_enabled()
        
        with self.page.expect_response("**/carts*") as response_info:
            add_btn.click()
            
        response = response_info.value
        assert response.status in [200, 201], f"Failed to add product to cart. Status: {response.status}"

    def get_cart_counter_value(self) -> str:
        """Retrieve the text value from the cart counter badge in the header safely.

        Returns:
            str: Number of items shown in the cart badge (e.g., '1').
        """
        counter_locator = self.page.locator(self.CART_COUNTER)
        expect(counter_locator).to_be_visible()
        return counter_locator.inner_text().strip()

    def go_to_cart(self) -> None:
        """Navigate to the shopping cart via UI elements in the header."""
        cart_link = self.page.locator(self.NAV_CART)
        expect(cart_link).to_be_visible()
        cart_link.click()