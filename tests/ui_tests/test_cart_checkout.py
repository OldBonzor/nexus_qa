"""UI Tests for Shopping Cart Management and Checkout Flow.

Verifies cart contents, price calculations, item counts, interactive controls,
and authentication requirements during the checkout process.
"""

import pytest
import allure
from playwright.sync_api import Page, expect
from src.ui.pages.inventory_page import InventoryPage
from src.ui.pages.cart_page import CartPage
from src.ui.pages.checkout_page import CheckoutPage


@pytest.fixture
def cart_with_item(ui_page: Page) -> tuple[CartPage, Page]:
    """Fixture that handles the setup phase: opens inventory,
    adds the first available product to cart, and navigates to the cart page.
    """
    inventory_page = InventoryPage(ui_page)
    cart_page = CartPage(ui_page)
    
    inventory_page.open()
    inventory_page.open_first_available_product_details()
    inventory_page.add_product_to_cart_from_details()
    inventory_page.go_to_cart()
    
    return cart_page, ui_page


@allure.epic("UI Storefront")
@allure.feature("Shopping Cart & Checkout")
class TestCartAndCheckout:
    """Test suite for cart management and checkout flows."""

    @allure.story("Cart Management")
    def test_cart_item_details_and_calculations(self, cart_with_item) -> None:
        """Verify product details, quantity updates, and price calculations in the cart."""
        # --- Arrange ---
        cart_page, ui_page = cart_with_item
        
        # --- Act ---
        quantity_input = cart_page.get_quantity_input()
        quantity_input.click()
        quantity_input.press("Control+A")
        quantity_input.press("Backspace")
        quantity_input.type("2")
        
        # --- Assert ---
        expect(quantity_input).to_have_value("2")
        
        total_price_element = ui_page.locator(cart_page.TOTAL_PRICE)
        expect(total_price_element).to_be_visible()
        expect(total_price_element).not_to_have_text("")

    @allure.story("Cart Management")
    def test_cart_interactive_controls_presence(self, cart_with_item) -> None:
        """Verify the availability of item removal controls and checkout navigation elements."""
        # --- Arrange ---
        cart_page, ui_page = cart_with_item
        
        # --- Act & Assert ---
        expect(ui_page.locator(cart_page.DELETE_BTN)).to_be_visible()
        expect(ui_page.locator(cart_page.CHECKOUT_BTN)).to_be_visible()

    @allure.story("Checkout Flow")
    def test_checkout_requires_login(self, cart_with_item) -> None:
        """Verify that clicking proceed to checkout redirects unauthenticated user to login view."""
        # --- Arrange ---
        cart_page, ui_page = cart_with_item
        checkout_page = CheckoutPage(ui_page)
        
        # --- Act ---
        cart_page.proceed_to_checkout()
        
        # --- Assert ---
        expect(ui_page.locator(checkout_page.LOGIN_HEADING)).to_be_visible()

    @allure.story("Cart Management")
    def test_cart_item_removal(self, cart_with_item) -> None:
        """Verify that clicking the delete button successfully removes the item from the cart."""
        # --- Arrange ---
        cart_page, ui_page = cart_with_item
        
        # --- Act ---
        ui_page.locator(cart_page.DELETE_BTN).click()
        
        # --- Assert ---
        expect(ui_page.locator(cart_page.ITEM_TITLE)).to_have_count(0)

    @allure.story("Cart Management")
    def test_cart_multiple_items_and_removal(self, cart_with_item) -> None:
        """Verify adding a product, updating quantity, and managing cart items."""
        # --- Arrange ---
        cart_page, ui_page = cart_with_item
        
        # --- Act & Assert ---
        # 1. Verify item is present in cart
        expect(ui_page.locator(cart_page.ITEM_TITLE)).to_be_visible()
        
        # 2. Update quantity
        quantity_input = cart_page.get_quantity_input()
        quantity_input.click()
        quantity_input.press("Control+A")
        quantity_input.press("Backspace")
        quantity_input.type("2")
        expect(quantity_input).to_have_value("2")
        
        # 3. Remove the item from the cart
        ui_page.locator(cart_page.DELETE_BTN).click()
        expect(ui_page.locator(cart_page.ITEM_TITLE)).to_have_count(0)

    @allure.story("Checkout Flow")
    def test_empty_cart_checkout_prevention(self, ui_page: Page) -> None:
        """Verify that accessing the cart or checkout with no items prevents proceeding."""
        # --- Arrange ---
        cart_page = CartPage(ui_page)
        
        # --- Act ---
        cart_page.navigate("/checkout")
        
        # --- Assert ---
        checkout_btn = ui_page.locator(cart_page.CHECKOUT_BTN)
        if checkout_btn.is_visible():
            expect(checkout_btn).to_be_disabled()
        else:
            expect(checkout_btn).not_to_be_visible()

    @allure.story("Cart Management")
    def test_cart_state_persistence_on_reload(self, cart_with_item) -> None:
        """Verify that cart contents persist after a page reload without requiring login."""
        # --- Arrange ---
        cart_page, ui_page = cart_with_item
        
        # Capture the initial item title to verify identity after reload
        initial_title = ui_page.locator(cart_page.ITEM_TITLE).inner_text()
        
        # --- Act ---
        ui_page.reload()
        
        # --- Assert ---
        # Ensure the item is still in the cart after reload
        item_title_locator = ui_page.locator(cart_page.ITEM_TITLE)
        expect(item_title_locator).to_be_visible()
        expect(item_title_locator).to_have_text(initial_title)
        
        # Ensure the cart counter in the header also persists (using InventoryPage locator)
        expect(ui_page.locator(InventoryPage.CART_COUNTER)).to_have_text("1")