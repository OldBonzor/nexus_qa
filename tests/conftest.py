"""Central Pytest configuration and shared fixtures for API automation.

This module provides common test fixtures used across API tests,
including BaseClient initialization and automatic session lifecycle management.
"""

import os
import platform
import pytest
import json
import playwright
import shutil
from typing import Any, Generator
from src.api.base_client import BaseClient
from src.api.models.auth_models import LoginRequest, LoginResponse
from src.api.products_client import ProductsClient
from src.api.models.product_models import PriceBoundaries


BASE_URL = "https://api.practicesoftwaretesting.com"


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[None]) -> Generator[None, Any, None]:
    """Hook to capture test execution status across all phases (setup, call, teardown).

    Attaches rep_setup, rep_call, and rep_teardown to the test item
    so fixtures can inspect if the test failed at any stage.
    """
    outcome = yield
    rep = outcome.get_result()
    # Dynamically sets rep_setup, rep_call, or rep_teardown depending on the current phase
    setattr(item, f"rep_{rep.when}", rep)


@pytest.fixture(scope="session", autouse=True)
def configure_allure_environment():
    """Automatically generate Allure metadata files (environment.properties,
    categories.json, executor.json) and ensure a pristine results directory
    at the beginning of the test session.
    
    Clears out stale test results from previous runs while preserving the directory 
    itself to remain fully compatible with Docker volume mounts.
    """
    results_dir = "allure-results"
    
    # Purge stale results to prevent cross-run artifact contamination
    if os.path.exists(results_dir):
        for filename in os.listdir(results_dir):
            file_path = os.path.join(results_dir, filename)
            if filename == '.gitkeep':
                continue
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Warning: Failed to delete stale artifact {file_path}: {e}")
    else:
        os.makedirs(results_dir, exist_ok=True)
    
    # 1. Environment Properties
    env_properties = {
        "Environment": os.getenv("TEST_ENV", "Docker / Staging"),
        "Python.Version": platform.python_version(),
        "Platform.OS": f"{platform.system()} {platform.release()}",
        "Playwright.Version": getattr(playwright, "__version__", "Unknown"),
        "Execution.Type": "Containerized (Docker)" if os.getenv("DOCKER_CONTAINER") else "Local",
        "Author": "Denis B.",
    }
    env_path = os.path.join(results_dir, "environment.properties")
    try:
        with open(env_path, "w", encoding="utf-8") as f:
            for key, value in env_properties.items():
                f.write(f"{key}={value}\n")
    except Exception as e:
        print(f"Warning: Failed to generate environment.properties: {e}")

    # 2. Categories Definition (Smart Error Grouping)
    categories = [
        {
            "name": "Product Defects",
            "matchedStatuses": ["failed"],
            "messageRegex": ".*AssertionError.*|.*Mismatch.*",
            "traceRegex": ".*assert.*",
            "flaky": False
        },
        {
            "name": "Test / Infrastructure Defects",
            "matchedStatuses": ["broken", "failed"],
            "messageRegex": ".*TimeoutError.*|.*ConnectionError.*|.*HTTP 5\\d{2}.*",
            "flaky": False
        }
    ]
    categories_path = os.path.join(results_dir, "categories.json")
    try:
        with open(categories_path, "w", encoding="utf-8") as f:
            json.dump(categories, f, indent=2)
    except Exception as e:
        print(f"Warning: Failed to generate categories.json: {e}")

    # 3. Executor Information (CI/CD Runner Context)
    is_ci = os.getenv("CI", "false").lower() == "true"
    executor_info = {
        "name": "GitHub Actions" if is_ci else "Local Machine",
        "type": "github" if is_ci else "local",
        "url": os.getenv("GITHUB_SERVER_URL", "") + "/" + os.getenv("GITHUB_REPOSITORY", "") if is_ci else "http://localhost",
        "buildUrl": os.getenv("GITHUB_RUN_URL", "") if is_ci else "http://localhost",
        "buildName": os.getenv("GITHUB_RUN_ID", "Manual Local Run"),
        "reportUrl": os.getenv("ALLURE_REPORT_URL", "")
    }
    executor_path = os.path.join(results_dir, "executor.json")
    try:
        with open(executor_path, "w", encoding="utf-8") as f:
            json.dump(executor_info, f, indent=2)
    except Exception as e:
        print(f"Warning: Failed to generate executor.json: {e}")


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