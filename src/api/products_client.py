"""API client module for interacting with public /products endpoints.

Provides the ProductsClient class for fetching products list,
filtering, searching, and getting product details.
"""

from typing import Any, Optional
from requests import Response
from src.api.base_client import BaseClient


class ProductsClient(BaseClient):
    """Client for interacting with the public /products API endpoints.

    Inherits from BaseClient to reuse connection pooling, logging,
    and status code assertions.
    """

    def get_products(
        self,
        params: Optional[dict[str, Any]] = None,
        expected_status: Optional[int] = None,
    ) -> Response:
        """Fetch a paginated list of products with optional filters.

        Args:
            params: Query parameters for pagination, sorting, search, and category/brand filters.
            expected_status: Expected HTTP status code for auto-assertion.

        Returns:
            HTTP response containing paginated product payload.
        """
        return self.get(
            "/products", params=params, expected_status=expected_status
        )

    def get_product_by_id(
        self,
        product_id: str,
        expected_status: Optional[int] = None,
    ) -> Response:
        """Fetch detailed information for a specific product by its unique identifier.

        Args:
            product_id: Unique product identifier string.
            expected_status: Expected HTTP status code for auto-assertion.

        Returns:
            HTTP response containing detailed product object.
        """
        return self.get(f"/products/{product_id}", expected_status=expected_status)