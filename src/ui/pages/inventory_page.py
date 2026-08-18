"""Page Object representing the Catalog and Inventory Page of Practice Software Testing.

Encapsulates all locators and user interactions specific to the storefront,
catalog sorting, filtering, and cart operations.
"""

from typing import List, Callable
from playwright.sync_api import Locator, expect
from src.ui.pages.base_page import BasePage
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_result


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

    def wait_for_grid_update(
        self, 
        initial_values: list, 
        action_callback: Callable[[], list], 
        allow_empty: bool = False
    ) -> list:
        """Universal polling-synchronization coordinator using tenacity.
        
        Args:
            initial_values (list): The state of data before action.
            action_callback (Callable[[], list]): A function that fetches current data.
            allow_empty (bool): If True, accepts an empty list [] as a valid final result 
                                (e.g., for zero-result search or filter tests).
        """
        @retry(
            stop=stop_after_attempt(15),  # Max ~3 seconds with 0.2s interval
            wait=wait_fixed(0.2),         # Check every 200ms
            # Retry if:
            # 1. The result is empty AND we do NOT allow empty lists (standard behavior).
            # 2. OR the result is still equal to the initial pre-action values.
            retry=retry_if_result(
                lambda current: (not current and not allow_empty) or (current == initial_values)
            ),
            reraise=True
        )
        def _poll() -> list:
            return action_callback()
        
        return _poll()

    def search_product(self, query: str, allow_empty: bool = False) -> None:
        """Type a search query into the search input field and submit,
        synchronizing product grid updates using tenacity polling.

        This approach ensures resilience against SPA DOM re-rendering delays
        without tightly coupling tests to specific internal API endpoints.

        Args:
            query (str): The keyword or product name to search for (e.g., 'Hammer').
        """
        search_input_locator = self.page.locator(self.SEARCH_INPUT)
        search_submit_locator = self.page.locator(self.SEARCH_SUBMIT)

        # Ensure input field is ready and fill the search query
        self.wait_for_visible(search_input_locator)
        search_input_locator.fill(query)

        # 1. Capture the initial state of the product grid (names) before searching
        initial_values = self.get_all_product_names()

        # 2. Submit the search form
        self.wait_for_visible(search_submit_locator)
        search_submit_locator.click()

        # 3. Synchronize using the universal tenacity coordinator.
        # It polls until product names change or elements render, handling empty DOM states safely.
        self.wait_for_grid_update(
            initial_values,
            lambda: self.get_all_product_names(),
            allow_empty=allow_empty
        )

    def sort_by(self, sort_option_value: str) -> None:
        """Select a sorting option and synchronize grid updates using the tenacity coordinator.
        
        Args:
            sort_option_value (str): The visible text or label of the sorting option.
        """
        product_cards = self.get_product_cards()
        product_cards.first.wait_for(state="visible")
        
        # 1. Capture the initial state of the grid before sorting
        initial_values = self.get_product_values_by_sort_option(sort_option_value)
        
        # 2. Interact with the sorting dropdown
        sort_locator = self.page.locator(self.SORT_SELECT)
        self.wait_for_visible(sort_locator)
        sort_locator.select_option(label=sort_option_value)
        
        # 3. Synchronize via tenacity coordinator
        self.wait_for_grid_update(
            initial_values,
            lambda: self.get_product_values_by_sort_option(sort_option_value)
        )

    def filter_by_category(
        self,
        category_name: str | None = None,
        subcategory_name: str | None = None,
    ) -> None:
        """Filter the product catalog by selecting a category or subcategory,
        synchronizing grid updates using the tenacity coordinator.

        Args:
            category_name (str): The main category visible name (e.g., 'Hand Tools').
            subcategory_name (str | None): The nested subcategory visible name if applicable (e.g., 'Hammer').
        """
        self.get_product_cards().first.wait_for(state="visible")
        
        target_name = subcategory_name if subcategory_name else category_name
        target_checkbox = self.page.locator(f"//label[contains(normalize-space(), '{target_name}')]//input[@type='checkbox']")
        self.wait_for_visible(target_checkbox.first)
        
        # 1. Capture initial state of product names before filtering
        initial_values = self.get_all_product_names()

        # 2. Click category/subcategory filter checkbox
        target_checkbox.first.click(force=True)

        # 3. Synchronize via tenacity coordinator
        self.wait_for_grid_update(
            initial_values,
            lambda: self.get_all_product_names()
        )

    def get_product_cards(self) -> Locator:
        """Retrieve the product card locator as a Locator factory pattern,
        avoiding pre-evaluated static lists and preventing race conditions.

        Returns:
            Locator: A Playwright Locator representing matching product cards.
        """
        return self.page.locator(self.PRODUCT_CARD)

    def get_all_product_prices(self) -> List[float]:
        """Extract all product prices from the grid as floats.
        Relies on grid stability managed by the tenacity coordinator."""
        # Fetch raw inner text from all price elements currently present in the DOM
        price_elements = self.page.locator(self.PRODUCT_PRICE).all_inner_texts()
        
        parsed_prices = []
        for price_str in price_elements:
            # Clean currency symbols, commas, and whitespace for safe float conversion
            cleaned_str = price_str.replace("$", "").replace(",", "").strip()
            if cleaned_str:
                try:
                    parsed_prices.append(float(cleaned_str))
                except ValueError:
                    # Gracefully skip any malformed price strings
                    continue
        return parsed_prices

    def get_all_product_names(self) -> List[str]:
        """Retrieve titles of all visible products in the grid."""
        # Extract title texts directly without redundant visibility assertions
        titles = self.page.locator(self.PRODUCT_TITLE).all_inner_texts()
        return [title.strip() for title in titles]

    def get_all_product_co2_ratings(self) -> List[str]:
        """Retrieve CO2 rating letters for all products in the grid."""
        # Fetch active CO2 rating badges text elements
        ratings = self.page.locator(self.CO2_RATING).all_inner_texts()
        return [rating.strip() for rating in ratings]

    def get_product_values_by_sort_option(self, sort_option: str) -> List:
        """Fetch product values (prices, names, or ratings) based on the sorting option using match/case.
        Safely returns an empty list during transient DOM re-rendering states.
        """
        cards = self.get_product_cards()
        if cards.count() == 0:
            return []
        
        try:
            match sort_option:
                case option if "Price" in option:
                    return self.get_all_product_prices()
                case option if "Name" in option:
                    return self.get_all_product_names()
                case option if "CO₂" in option or "CO2" in option:
                    return self.get_all_product_co2_ratings()
                case _:
                    raise ValueError(f"Unsupported sorting option: {sort_option}")
        except Exception:
            return []

    def get_product_cards_count(self) -> int:
        """Get the count of currently visible product cards in the catalog."""  
        return self.get_product_cards().count()

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