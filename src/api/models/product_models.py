"""Domain models and schemas for Products API requests and responses."""

from typing import NamedTuple, Optional
from pydantic import BaseModel, Field


class PriceBoundaries(NamedTuple):
    """Container for catalog price metrics used in price range filter tests.

    Attributes:
        min_price: Minimum item price in the catalog.
        max_price: Maximum item price in the catalog.
        exact_price: Median item price for exact matching.
        mid_price: Average item price across the catalog.
    """
    min_price: float
    max_price: float
    exact_price: float
    mid_price: float


class Category(BaseModel):
    """Product category schema."""
    id: str
    name: str
    slug: Optional[str] = None


class Brand(BaseModel):
    """Product brand schema."""
    id: str
    name: str
    slug: Optional[str] = None


class ProductItem(BaseModel):
    """Product entity schema.

    Attributes:
        id: Unique identifier of the product.
        name: Name of the product.
        description: Detailed product description.
        price: Unit price (must be strictly positive).
        is_location_offer: Flag indicating localized promo offer.
        is_rental: Flag indicating rental item availability.
        in_stock: Flag indicating item availability in inventory.
        category: Associated product category details.
        brand: Associated product brand details.
    """
    id: str
    name: str
    description: Optional[str] = None
    price: float = Field(gt=0, description="Product price (must be greater than 0)")
    is_location_offer: Optional[bool] = None
    is_rental: Optional[bool] = None
    in_stock: Optional[bool] = None
    category: Optional[Category] = None
    brand: Optional[Brand] = None


class ProductsListResponse(BaseModel):
    """Paginated list response schema for the products API endpoint.

    Attributes:
        current_page: Currently active page number.
        from_item: Starting item index of the current page.
        last_page: Total number of available pages.
        per_page: Number of items returned per page.
        to_item: Ending item index of the current page.
        total: Total amount of products matching the request.
        data: List of product items on the current page.
    """
    current_page: int
    from_item: Optional[int] = Field(None, alias="from")
    last_page: int
    per_page: int
    to_item: Optional[int] = Field(None, alias="to")
    total: int
    data: list[ProductItem]