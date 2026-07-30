"""Central Pytest configuration and shared fixtures for API automation.

This module provides common test fixtures used across API tests,
including BaseClient initialization and automatic session lifecycle management.
"""

from typing import Any, Generator
import pytest
import requests
from src.api.base_client import BaseClient
from src.api.products_client import ProductsClient
from src.api.models.product_models import PriceBoundaries


BASE_URL = "https://api.practicesoftwaretesting.com"


@pytest.fixture(scope="module")
def api_client() -> Generator[BaseClient, None, None]:
    """Initialize and yield a BaseClient instance with session cleanup.

    Yields:
        BaseClient: Configured HTTP client instance ready for making requests.
    """
    client = BaseClient()
    yield client
    client.session.close()


@pytest.fixture(scope="module")
def products_client(api_client: BaseClient) -> ProductsClient:
    """Initialize and return a ProductsClient instance.

    Returns:
        ProductsClient: Client instance configured for /products API endpoints.
    """
    return ProductsClient()


@pytest.fixture(scope="module")
def valid_filter_pairs(products_client: ProductsClient) -> list[dict[str, Any]]:
    """Dynamically fetch real category and brand ID pairs from the catalog.

    Returns:
        list[dict[str, Any]]: Unique category and brand filter pairs.
    """
    response = products_client.get_products(expected_status=200)
    products_data = response.json().get("data", [])

    unique_pairs = []
    seen_categories = set()
    seen_brands = set()

    for product in products_data:
        category_id = product.get("category", {}).get("id")
        brand_id = product.get("brand", {}).get("id")

        if category_id and brand_id:
            if (
                category_id not in seen_categories
                and brand_id not in seen_brands
            ):
                seen_categories.add(category_id)
                seen_brands.add(brand_id)

                unique_pairs.append(
                    {"by_category": category_id, "by_brand": brand_id}
                )
                if len(unique_pairs) == 2:
                    break

    if len(unique_pairs) < 2:
        pytest.fail(
            f"Could not find at least 2 unique category+brand pairs in DB. Found: {len(unique_pairs)}"
        )

    return unique_pairs


@pytest.fixture(scope="module")
def raw_products_data(products_client: ProductsClient) -> list[dict[str, Any]]:
    """Fetch all products across all pages using backend pagination.

    Returns:
        list[dict[str, Any]]: Complete list of raw product dictionaries.
    """
    all_products = []
    page = 1
    last_page = 1

    # Retrieve items page-by-page until last_page is reached
    while page <= last_page:
        response = products_client.get_products(
            params={"page": page}, expected_status=200
        )
        res_json = response.json()

        last_page = res_json.get("last_page") or page
        products_data = res_json.get("data", [])
        all_products.extend(products_data)

        page += 1

    return all_products


@pytest.fixture(scope="module")
def non_overlapping_pairs(
    raw_products_data: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Extract category-brand pairs that do not co-exist in any product.

    Processes pre-fetched raw products in memory to guarantee zero
    overlapping products for combined filter tests.

    Returns:
        list[dict[str, Any]]: List of non-overlapping category/brand filter pairs.
    """
    existing_pairs = set()
    all_categories = set()
    all_brands = set()
    non_overlapping_pairs = []

    for product in raw_products_data:
        category_id = product.get("category", {}).get("id")
        brand_id = product.get("brand", {}).get("id")

        if category_id and brand_id:
            existing_pairs.add((category_id, brand_id))
            all_categories.add(category_id)
            all_brands.add(brand_id)

    # Searching for non-overlapping pairs
    for category_id in all_categories:
        for brand_id in all_brands:
            if (category_id, brand_id) not in existing_pairs:
                pair = {"by_category": category_id, "by_brand": brand_id}

                if pair not in non_overlapping_pairs:
                    non_overlapping_pairs.append(pair)

            if len(non_overlapping_pairs) >= 2:
                break

        if len(non_overlapping_pairs) >= 2:
            break

    if len(non_overlapping_pairs) < 2:
        pytest.skip(
            "Could not find at least 2 unique non-overlapping category+brand pairs "
            f"in current DB. Found: {len(non_overlapping_pairs)} pairs"
        )

    return non_overlapping_pairs


@pytest.fixture(scope="module")
def price_boundaries(
    raw_products_data: list[dict[str, Any]],
) -> PriceBoundaries:
    """Calculate catalog price metrics from raw in-memory products.

    Returns:
        PriceBoundaries: Object containing min, max, exact, and mid catalog prices.
    """
    all_prices = []

    for product in raw_products_data:
        raw_price = product.get("price")
        if raw_price is not None:
            try:
                all_prices.append(float(raw_price))
            except (ValueError, TypeError):
                continue

    if not all_prices:
        pytest.skip("No valid prices found in the current product catalog.")

    all_prices.sort()

    return PriceBoundaries(
        min_price=all_prices[0],
        max_price=all_prices[-1],
        exact_price=all_prices[len(all_prices) // 2],
        mid_price=round(sum(all_prices) / len(all_prices), 2),
    )