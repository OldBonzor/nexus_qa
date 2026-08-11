"""Central Pytest configuration and shared fixtures for API automation.

This module provides common test fixtures used across API tests,
including BaseClient initialization and automatic session lifecycle management.
"""

import os
import tempfile
from typing import Any, Generator
import pytest
import requests
import allure
from src.api.base_client import BaseClient


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[None]) -> Generator[None, Any, None]:
    """Hook to capture the test execution status during the 'call' phase.

    This hook wrapper runs for all execution phases. It intercepts the test report
    and attaches a custom `rep_call` attribute to the test item if the phase is "call",
    allowing downstream fixtures to inspect if the test passed or failed.
    """
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call":
        item.rep_call = rep


@pytest.fixture(scope="function", autouse=True)
def auto_attach_artifacts(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """Autouse fixture to safely capture screenshots and traces on test failure.

    This fixture yields to the test execution. To prevent 'Target closed' or
    'FixtureLookupError', it dynamically requests and registers dependencies on
    the `page` and `context` fixtures if they are active in the current test.
    
    Upon test failure, full-page screenshots and Playwright traces are securely
    attached to the Allure report, ensuring resources are cleaned up and tracing
    is stopped without memory leaks.
    """
    # Force evaluation of page/context fixtures if they exist,
    # so their setups complete before this fixture, and this fixture's
    # teardown runs BEFORE their teardown (LIFO order).
    if "page" in request.fixturenames:
        request.getfixturevalue("page")
    if "context" in request.fixturenames:
        request.getfixturevalue("context")

    yield

    # Teardown phase: capture artifacts for UI tests
    page = request.node.funcargs.get("page")
    context = request.node.funcargs.get("context")
    
    # Safely retrieve test report execution info
    rep_call = getattr(request.node, "rep_call", None)
    is_failed = rep_call is not None and rep_call.failed

    try:
        if is_failed:
            # Capture and attach screenshot on failure
            if page and not page.is_closed():
                try:
                    screenshot_bytes = page.screenshot(full_page=True)
                    allure.attach(
                        screenshot_bytes,
                        name="Failure Screenshot",
                        attachment_type=allure.attachment_type.PNG,
                    )
                except Exception as screenshot_err:
                    print(f"[Warning] Failed to capture screenshot: {screenshot_err}")

            # Export and attach Playwright trace on failure
            if context:
                try:
                    with tempfile.TemporaryDirectory() as temp_dir:
                        trace_path = os.path.join(temp_dir, "trace.zip")
                        context.tracing.stop(path=trace_path)
                        if os.path.exists(trace_path):
                            with open(trace_path, "rb") as trace_file:
                                allure.attach(
                                    trace_file.read(),
                                    name="Playwright Trace",
                                    attachment_type=allure.attachment_type.ZIP,
                                )
                except Exception as trace_err:
                    print(f"[Warning] Failed to export Playwright trace: {trace_err}")
        else:
            # Purge tracing buffers for passed/skipped tests to prevent memory bloat
            if context:
                try:
                    context.tracing.stop()
                except Exception as trace_err:
                    print(f"[Warning] Failed to stop Playwright trace: {trace_err}")

    except Exception as general_err:
        print(f"[Warning] Error during test artifact capture teardown: {general_err}")
from src.api.models.auth_models import LoginRequest, LoginResponse
from src.api.products_client import ProductsClient
from src.api.models.product_models import PriceBoundaries


BASE_URL = "https://api.practicesoftwaretesting.com"


@pytest.fixture(scope="session")
def api_client() -> Generator[BaseClient, None, None]:
    """Initialize and yield a BaseClient instance with session cleanup.

    Yields:
        BaseClient: Configured HTTP client instance ready for making requests.
    """
    client = BaseClient()
    yield client
    client.session.close()


@pytest.fixture(scope="session")
def auth_token(api_client: BaseClient) -> str:
    """Dynamically fetch a valid Bearer access token via the login endpoint.

    Returns:
        str: JWT access token for authenticated API requests.
    """
    payload = LoginRequest(
        email="admin@practicesoftwaretesting.com",
        password="welcome01"
    )
    response = api_client.post(
        "/users/login",
        json=payload.model_dump(),
        expected_status=200,
    )
    token_data = LoginResponse.model_validate(response.json())
    return token_data.access_token


@pytest.fixture(scope="session")
def products_client(api_client: BaseClient) -> ProductsClient:
    """Initialize and return a ProductsClient instance.

    Returns:
        ProductsClient: Client instance configured for /products API endpoints.
    """
    return ProductsClient()


@pytest.fixture(scope="session")
def valid_filter_pairs(products_client) -> list[dict[str, Any]]:
    unique_pairs: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()
    seen_categories: set[str] = set()
    seen_brands: set[str] = set()

    current_page = 1
    last_page = 1

    while current_page <= last_page:
        response = products_client.get_products(
            params={"page": current_page}, 
            expected_status=200
        )
        body = response.json()
        
        products_data = body.get("data", [])
        last_page = body.get("last_page", 1)

        for product in products_data:
            # Extracting IDs safely from nested dictionaries
            category_obj = product.get("category")
            brand_obj = product.get("brand")
            
            category_id = category_obj.get("id") if isinstance(category_obj, dict) else None
            brand_id = brand_obj.get("id") if isinstance(brand_obj, dict) else None
            
            is_rental = product.get("is_rental", False)
            is_location_offer = product.get("is_location_offer", False)

            if category_id and brand_id:
                pair_key = (category_id, brand_id)
                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    seen_categories.add(category_id)
                    seen_brands.add(brand_id)
                    
                    pair_info = {
                        "by_category": category_id,
                        "by_brand": brand_id,
                        "is_rental": is_rental,
                        "is_location_offer": is_location_offer
                    }
                    unique_pairs.append(pair_info)

        current_page += 1

    if not unique_pairs:
        pytest.skip("Skipped: Could not find any category+brand pairs across all catalog pages.")

    return unique_pairs


@pytest.fixture(scope="session")
def strict_filter_pairs(valid_filter_pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Filters unique_pairs to find items where both 'is_rental' and 'is_location_offer' are True.
    """
    strict_pairs = []
    for pair in valid_filter_pairs:
        if pair.get("is_rental") is True and pair.get("is_location_offer") is True:
            strict_pairs.append(pair)
    return strict_pairs


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