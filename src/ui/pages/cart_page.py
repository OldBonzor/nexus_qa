"""Page Object representing the Shopping Cart Page of Practice Software Testing.

Encapsulates all locators and user interactions specific to managing cart items,
updating quantities, and proceeding to checkout.
"""

from playwright.sync_api import Page, Locator
from src.ui.pages.base_page import BasePage

class CartPage(BasePage):
    """Page object for the shopping cart page."""
    
    CART_ITEM = "[data-test='cart-item']"
    ITEM_TITLE = "[data-test='product-title']"  # Adjust selector based on actual app markup
    UNIT_PRICE = "tr td:nth-child(3)"
    QUANTITY_INPUT = "input[data-test='quantity']"
    LINE_TOTAL = "tr td:nth-child(5)"
    TOTAL_PRICE = "[data-test='cart-total']" # Or appropriate total selector
    DELETE_BTN = "a.btn.btn-danger"
    CHECKOUT_BTN = "[data-test='proceed-1']"

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    def open(self) -> None:
        """Directly navigate to the cart page."""
        self.navigate_to("/checkout")
        
    def get_quantity_input(self) -> Locator:
        """Get the quantity input on the cart page."""
        return self.page.locator("input[data-test='product-quantity']")
    
    def update_quantity(self, quantity: str) -> None:
        """Update product quantity in the cart."""
        self.page.locator(self.QUANTITY_INPUT).fill(quantity)
        self.page.locator(self.QUANTITY_INPUT).press("Enter")

    def proceed_to_checkout(self) -> None:
        """Click proceed to checkout button."""
        self.click(self.CHECKOUT_BTN)