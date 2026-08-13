"""API tests for the products endpoints."""

import pytest
import allure
from math import ceil
from typing import Any, Optional
from src.api.models.product_models import (
    PriceBoundaries,
    ProductItem,
    ProductsListResponse,
)
from src.api.products_client import ProductsClient


@allure.epic("API Backend")
@allure.feature("Products Management")
class TestProductsList:
    """Suite for testing product list retrieval, data contracts, and pagination behavior."""
    @allure.story("Get Products List")
    @pytest.mark.smoke
    def test_get_products_list(self, products_client: ProductsClient) -> None:
        """Test retrieving list of products and response contract validity."""
        # --- Arrange & Act ---
        # 1. Call GET /products via ProductsClient (expecting 200 OK)
        response = products_client.get_products(expected_status=200)

        # 2. Parse and validate response via Pydantic model
        products_data = ProductsListResponse(**response.json())

        # --- Assert ---
        # - Data list is not empty (len(data) > 0)
        # - First product's price is greater that 0 (data[0].price > 0)
        assert len(products_data.data) > 0, "Expected products list must not be empty"
        assert products_data.data[0].price > 0, "Expected product price must be greater than 0"

    @allure.story("Pagination")
    @pytest.mark.parametrize("page", [1, 2], ids=["first_page", "second_page"])
    def test_get_products_pagination(self, products_client: ProductsClient, page: int):
        """Verify pagination functionality: page navigation and and current page response.
        
        Note: Backend has fixed per_page size of 9 items
        """
        # --- Arrange ---
        params = {"page": page}
        expected_per_page = 9

        # --- Act ---
        response = products_client.get_products(
            params=params,
            expected_status=200,
        )
        products_data = ProductsListResponse(**response.json())

        # --- Assert ---
        # 1. Echo parameters check
        assert products_data.current_page == page, (
            f"Expected page {page}, but got {products_data.current_page}"
        )

        # 2. Item count limits check (per_page limit)
        assert len(products_data.data) <= expected_per_page, (
            f"Page {page} returned {len(products_data.data)} items, "
            f"which exceeds the per_page limit of {expected_per_page}"
        )
        assert len(products_data.data) > 0, (
            f"Expected page {page} to contain product items"
        )

    @allure.story("Pagination")
    def test_get_products_last_page(self, products_client: ProductsClient):
        """Guarantees testing the backend last page calculation and 
        the exact item count on the final page.
        """
        # --- Arrange ---
        per_page = 9

        # 1. Fetch initial metadata to dynamically determine total number of pages
        initial_response = products_client.get_products(
            params={"page": 1},
            expected_status=200
        )
        initial_data = ProductsListResponse(**initial_response.json())

        # 2. Calculate expected last page and expected item count on it
        total = initial_data.total
        if total > 0:
            expected_last_page = ceil(total / per_page)
            expected_count = total % per_page or per_page
        else:
            expected_last_page = 1
            expected_count = 0

        # --- Act ---
        # Fetch data specifically for the calculated last page
        response = products_client.get_products(
            params={"page": initial_data.last_page},
            expected_status=200
        )
        last_page_data = ProductsListResponse(**response.json())

        # --- Assert ---
        # 1. Backend last_page calculation check
        assert initial_data.last_page == expected_last_page, (
            f"Backend miscalculated last_page: for total={total} "
            f"expected {expected_last_page}, but got {initial_data.last_page}"
        )

        # 2. Last page response metadata check
        assert last_page_data.current_page == expected_last_page, (
            f"Expected current page to be {expected_last_page}, "
            f"but got {last_page_data.current_page}"
        )

        # 3. Strict remainder check of the guaranteed last page
        assert len(last_page_data.data) == expected_count, (
            f"Last page {expected_last_page} (total items {initial_data.total}) "
            f"is expected to have {expected_count} items displayed, "
            f"but got {len(last_page_data.data)} items"
        )

    @allure.story("Pagination")
    def test_get_products_pagination_invalid(self, products_client: ProductsClient):
        """Verify that requesting a page beyond last_page returns an empty list."""
        # --- Arrange ---
        out_of_range_page = 9999

        # --- Act ---
        response = products_client.get_products(
            params={"page": out_of_range_page}, 
            expected_status=200
        )
        products_data = ProductsListResponse(**response.json())

        # --- Assert ---
        assert products_data.current_page == out_of_range_page, (
            f"Expected current_page to be {out_of_range_page}, "
            f"but got {products_data.current_page}"
        )
        assert len(products_data.data) == 0, (
            f"Expected empty data list for out-of-range page {out_of_range_page}, "
            f"but got {len(products_data.data)} items"
        )


@allure.epic("API Backend")
@allure.feature("Product Details")
class TestProductDetails:
    """Suite for testing product details endpoint (/products/{id})."""
    @allure.story("Get Product By ID")
    @pytest.mark.smoke
    def test_get_product_by_id(self, products_client: ProductsClient):
        """Verify that product requested using valid ID returns 200 code with product data."""
        # --- Arrange ---
        # 1. Getting list of items to get existing item ID from it
        products_response = products_client.get_products(expected_status=200)
        products_list = ProductsListResponse(**products_response.json())

        # 2. Check that item list is not empty
        assert len(products_list.data) > 0, ("Precondition failed: Products list is empty")

        # 3. Prepare expectations
        expected_product = products_list.data[0]
        expected_id = expected_product.id
        expected_name = expected_product.name
        expected_price = expected_product.price

        # --- Act ---
        item_response = products_client.get_product_by_id(
            product_id=expected_id,
            expected_status=200
        )
        product_data = ProductItem(**item_response.json())

        # --- Assert ---
        assert product_data.id == expected_id, (f"Expected result for {expected_id}, "
            f"but got {product_data.id} instead")
        assert product_data.name == expected_name, (f"Expected {expected_name}, "
            f"but got {product_data.name} instead")
        assert product_data.price == expected_price, (f"Expected {expected_price}, "
            f"but got {product_data.price} instead")

    @pytest.mark.parametrize(
        "invalid_id, expected_status, expected_error_message",
        [
            ("non-existing-id-999", 404, "Requested item not found"), # Non-existing item id
            ("   ", 404, "Requested item not found"),     # Spacebars in id
            ("@#$%^&*()~!?,;", 404, "Requested item not found"),     # Special symbols in id
        ],
        ids=["non_existing_id", "only_spacebars_in_id", "only_special_symbols_in_id"],
        )
    @allure.story("Get Product By ID")
    def test_get_product_by_id_not_found(
        self, 
        products_client: ProductsClient, 
        invalid_id: str, 
        expected_status: int, 
        expected_error_message: str,
    ):
        """Verify that product requested using invalid ID returns 404 error response."""
        # --- Arrange ---
        # --- Act ---
        response = products_client.get_product_by_id(
            product_id=invalid_id, 
            expected_status=expected_status,
            )
        error_data = response.json()

        # --- Assert ---
        assert error_data.get("message") == expected_error_message, (
            f"Requested item not found, "
            f"Expected error message {expected_error_message}, "
            f"but got {error_data.get('message')}"
            )


@allure.epic("API Backend")
@allure.feature("Product Search")
class TestProductsSearch:
    """Suite for testing product search functionality, keyword matching, and negative search cases."""
    @allure.story("Search Products")
    @pytest.mark.parametrize("queries, expected_keyword", [
        (["hammer", "HAMMER", "HaMmEr"], "hammer"),
        (["pliers", "PLIERS", "PlIeRs"], "pliers")
        ],
        ids=["lower_capital_mixed_1", "lower_capital_mixed_2"],
        )
    def test_search_products_by_name_case_insensitive(
        self, 
        products_client: ProductsClient, 
        queries: list[str],
        expected_keyword: str,
    ):
        """Check searching products by keyword using query parameter (q)."""

        # --- Arrange ---
        baseline_total = None

        # --- Act & Assert ---
        for query in queries:
            response = products_client.get_products(params={"q": query}, expected_status=200)
            products_data = ProductsListResponse(**response.json())

            assert len(products_data.data) > 0, (f"Expected results for query {query}, got emptly list")

            if baseline_total is None:
                baseline_total = products_data.total
            else:
                assert products_data.total == baseline_total, (
                    f"Count mismatch for {query}: expected {baseline_total}, got {products_data.total}"
                )

            invalid_items = [
                item.name for item in products_data.data 
                if expected_keyword not in item.name.lower()
            ]
            assert not invalid_items, (
                f"For query {query} expected {expected_keyword} in all items, "
                f" but not found in invalid items {invalid_items}"
                )

    @allure.story("Search Products")
    @pytest.mark.parametrize(
        "invalid_name", 
    [
        "non-existing-name-999",    # Non-existing item name
        "   ",                       # Spacebars in item name
        "@#$%^&*()~!?,;",           # Special symbols in item name
    ],
    ids=["non_existing_name", "only_spacebars_in_name", "only_special_symbols_in_name"],
    )
    def test_search_products_by_name_not_found(
        self, 
        products_client: ProductsClient, 
        invalid_name: str,
    ):
        """Check searching products endpoint with different invalid names in query."""
        # --- Arrange & Act ---
        response = products_client.get_products(params={"q": invalid_name}, expected_status=200)
        products_data = ProductsListResponse(**response.json())

        # --- Assert ---
        assert products_data.data == [], (
            f"Expected empty list for {invalid_name}, "
            f"got {products_data.data} instead"
            )
        assert products_data.total == 0, (
            f"Expected total = 0, "
            f"got {products_data.total}"
        )


@allure.epic("API Backend")
@allure.feature("Product Filtering")
class TestProductsFilter:
    """Suite for testing product list filtering by category and brand."""
    @pytest.mark.smoke
    @allure.story("Filter by Category")
    @allure.title("Filtering products: Basic category filter check")
    def test_filter_products_by_category(
        self, 
        products_client: ProductsClient, 
        valid_filter_pairs: list[dict[str, Any]]
    ):
        """
        Quick smoke test: Validates product filtering by a single category
        using the first available pair to ensure the filter endpoint is responsive.
        """
        # --- Arrange ---
        # Take the first pair to perform a quick health check
        target_pair = valid_filter_pairs[0]
        params = {"by_category": target_pair["by_category"]}

        # --- Act ---
        response = products_client.get_products(params=params, expected_status=200)
        products_data = ProductsListResponse(**response.json())

        # --- Assert ---
        assert products_data.total > 0, "Expected total > 0 for a basic category filter"
        for product in products_data.data:
            assert product.category.id == params["by_category"], (
                f"Expected category ID {params['by_category']}, got {product.category.id}"
            )

    @pytest.mark.parametrize(
        "filter_mode", ["brand_only", "category_and_brand"],
        ids=["brand_only", "combined_category_and_brand"],
    )
    @allure.story("Filter by Category and Brand")
    @allure.title("Filtering products: Category='{category}', Brand='{brand}'")
    def test_filter_products_by_category_by_brand_mix(
        self, 
        products_client: ProductsClient, 
        valid_filter_pairs: list[dict[str, Any]], 
        filter_mode: str
    ):
        """
        Validates product filtering by single category, single brand,
        and a combination of both across multiple dynamic database pairs.
        """
        # Loop over each dynamic category-brand pair from the fixture
        # to avoid hardcoding single entities and prevent backend response mocking false-positives
        for pair in valid_filter_pairs:
            # --- Arrange ---
            match filter_mode:
                case "brand_only":
                    params = {"by_brand": pair["by_brand"]}
                case "category_and_brand":
                    params = pair
                case _:
                    raise ValueError(f"Unsupported filter_mode: {filter_mode}")

            # --- Act ---
            response = products_client.get_products(params=params, expected_status=200)
            products_data = ProductsListResponse(**response.json())

            # --- Assert ---
            assert products_data.total > 0, f"Expected total > 0 for params {params}"
            assert len(products_data.data) > 0, f"Expected non-empty data list for params {params}"

            # Verify that all returned items strictly match the applied query filters
            for product in products_data.data:
                if "by_category" in params:
                    assert product.category.id == params["by_category"], (
                        f"Expected category ID {params['by_category']}, got {product.category.id}"
                    )
                if "by_brand" in params:
                    assert product.brand.id == params["by_brand"], (
                        f"Expected brand ID {params['by_brand']}, got {product.brand.id}"
                    )
    
    @allure.story("Filter by Category and Brand")
    @pytest.mark.parametrize(
        "filter_mode",
        [
            "invalid_category_only",
            "invalid_brand_only",
            "both_invalid",
            "valid_category_invalid_brand",
            "invalid_category_valid_brand",
            "whitespace_category_only",
            "whitespace_brand_only",
        ],
    )
    def test_filter_products_by_non_existing_categories_and_brands_returns_empty(
        self, 
        products_client: ProductsClient, 
        valid_filter_pairs: list[dict], 
        filter_mode: str,
    ):
        """Check that filtering by non-existing category or brand IDs (or spacebars) returns an empty list."""

        # --- Arrange ---
        valid_pair = valid_filter_pairs[0]
        non_existing_id = "non-existing-id-999"

        match filter_mode:
            case "invalid_category_only":
                params = {"by_category": non_existing_id}
            case "invalid_brand_only":
                params = {"by_brand": non_existing_id}
            case "both_invalid":
                params = {"by_category": non_existing_id, "by_brand": non_existing_id}
            case "valid_category_invalid_brand":
                params = {"by_category": valid_pair["by_category"], "by_brand": non_existing_id}            
            case "invalid_category_valid_brand":
                params = {"by_category": non_existing_id, "by_brand": valid_pair["by_brand"]}
            case "whitespace_category_only":
                params = {"by_category": "   "}
            case "whitespace_brand_only":
                params = {"by_brand": "   "}
            case _:
                raise ValueError(f"Unsupported filter_mode: {filter_mode}")

        # --- Act & Assert ---
        response = products_client.get_products(params=params, expected_status=200)
        products_data = ProductsListResponse(**response.json())
    
        assert products_data.total == 0, f"Expected empty list for params {params}, got {products_data.data}"
        assert len(products_data.data) == 0, f"Expected total = 0 for params {params}, got {products_data.total}"

    @allure.story("Filter by Category and Brand")
    def test_filter_products_by_non_overlapping_category_and_brand_returns_empty(
        self,
        products_client: ProductsClient, 
        non_overlapping_pairs: list[dict],
    ):
        """Validates that filtering by a valid category and a valid brand that do NOT co-exist
        on any product returns HTTP 200 with total=0 and an empty list.
        """
        # --- Arrange & Act ---

        for filter_params in non_overlapping_pairs:
            response = products_client.get_products(
                params=filter_params, expected_status=200
            )
            products_data = ProductsListResponse(**response.json())

            # --- Assert ---
            assert products_data.total == 0, (
                f"Expected total == 0 for non-overlapping params {filter_params}, "
                f"got total={products_data.total}"
            )
            assert products_data.data == [], (
                f"Expected empty data array for non-overlapping params {filter_params}, "
                f"got {len(products_data.data)} item(s): {products_data.data}"
            )


@allure.epic("API Backend")
@allure.feature("Price Filtering")
class TestProductsPriceFilter:
    """Suite for testing product price filtering capabilities via API."""

    @allure.story("Price Range Validation")
    @allure.title("{test_id}")
    @pytest.mark.parametrize(
        "get_params_func, validation_type, test_id",
        [
            # ==============================================================================
            # Group 1: exact_bounds (Exact boundaries)
            # ==============================================================================
            pytest.param(
                lambda b: {"between": f"price,{b.exact_price},{b.exact_price}"},
                "exact_bounds",
                "1. Exact Match (min==max)",
            ),
            pytest.param(
                lambda b: {"between": f"price,{b.min_price},{b.exact_price}"},
                "exact_bounds",
                "2. Standard Valid Range (min < max via exact_price)",
            ),
            pytest.param(
                lambda b: {"between": f"price,{b.min_price:.2f},{b.exact_price:.2f}"},
                "exact_bounds",
                "3. Cents Precision (.2f)",
            ),
            pytest.param(
                lambda b: {"between": f"price,{b.min_price + 0.123456:.6f},{b.exact_price + 0.987654:.6f}"},
                "exact_bounds",
                "4. Excessive Float Precision (.6f)",
            ),
            pytest.param(
                lambda b: {"between": f"price,{b.exact_price},"},
                "exact_bounds",
                "5. Only min_price",
                marks=pytest.mark.xfail(
                    reason="BUG: Backend fails to parse trailing comma in 'price,min,' and returns empty list",
                    strict=True,
                ),
            ),
            pytest.param(
                lambda b: {"between": f"price,,{b.exact_price}"},
                "exact_bounds",
                "6. Only max_price",
            ),
            # ==============================================================================
            # Group 2: full_coverage (Full DB coverage)
            # ==============================================================================
            pytest.param(
                lambda b: {"between": f"price,{b.min_price},{b.max_price}"},
                "full_coverage",
                "7. Full DB Price Coverage",
            ),
            # ==============================================================================
            # Group 3: all_items (Filter ignored)
            # ==============================================================================
            pytest.param(
                lambda b: {},
                "all_items",
                "8. Filter Ignored (no between param)",
            ),
            # ==============================================================================
            # Group 4: empty_result (Empty result)
            # ==============================================================================
            pytest.param(
                lambda b: {"between": "price,,"},
                "empty_result",
                "9. Empty Result (price,,)",
            ),
            pytest.param(
                lambda b: {"between": "price,,null"},
                "empty_result",
                "10. Empty Result (price,,null)",
            ),
            pytest.param(
                lambda b: {"between": "price,null,"},
                "empty_result",
                "11. Empty Result (price,null,)",
            ),
            pytest.param(
                lambda b: {"between": "price,null,null"},
                "empty_result",
                "12. Empty Result (price,null,null)",
            ),
            pytest.param(
                lambda b: {"between": f"price,{b.max_price + 10000.00},{b.max_price + 20000.00}"},
                "empty_result",
                "13. Empty Result (Out of Bounds: +10k..+20k)",
            ),
            pytest.param(
                lambda b: {"between": "price,0,0"},
                "empty_result",
                "14. Empty Result (Zero Price Range: 0..0)",
            ),
        ],
    )
    def test_filter_products_by_price_range(
        self,
        products_client: ProductsClient,
        price_boundaries: PriceBoundaries,
        raw_products_data: list[dict[str, Any]],
        get_params_func: Any,
        validation_type: str,
        test_id: str,
    ):
        """Validates price range filtering logic, dynamic pagination, and boundary conditions."""
        # --- Arrange ---
        params = get_params_func(price_boundaries)

        match validation_type:
            # ----------------------------------------------------------------------------------
            # Group 1: exact_bounds
            # ----------------------------------------------------------------------------------
            case "exact_bounds":
                # --- Act ---
                all_items, _ = self._fetch_all_pages(products_client, params)

                # --- Assert ---
                assert len(all_items) > 0, f"Filter {params} returned 0 items, expected at least 1."

                raw_between = params.get("between", "").replace("price,", "").split(",")
                raw_min = raw_between[0] if len(raw_between) > 0 else ""
                raw_max = raw_between[1] if len(raw_between) > 1 else ""

                min_limit = float(raw_min) if raw_min and raw_min != "null" else None
                max_limit = float(raw_max) if raw_max and raw_max != "null" else None

                for item in all_items:
                    price = float(item["price"])
                    if min_limit is not None:
                        assert price >= min_limit, f"Price {price} is less than min_limit {min_limit}"
                    if max_limit is not None:
                        assert price <= max_limit, f"Price {price} is greater than max_limit {max_limit}"

            # ----------------------------------------------------------------------------------
            # Group 2: full_coverage
            # ----------------------------------------------------------------------------------
            case "full_coverage":
                # --- Act ---
                all_items, total = self._fetch_all_pages(products_client, params)

                # --- Assert ---
                assert total == len(raw_products_data), (
                    f"Expected total count {len(raw_products_data)}, but API returned total={total}"
                )
                assert len(all_items) == len(raw_products_data), (
                    f"Expected total items {len(raw_products_data)}, but fetched {len(all_items)}"
                )

                returned_prices = [float(item["price"]) for item in all_items]
                assert price_boundaries.min_price in returned_prices, (
                    f"min_price ({price_boundaries.min_price}) is missing from response"
                )
                assert price_boundaries.max_price in returned_prices, (
                    f"max_price ({price_boundaries.max_price}) is missing from response"
                )

            # ----------------------------------------------------------------------------------
            # Group 3: all_items
            # ----------------------------------------------------------------------------------
            case "all_items" | "filter_ignored":
                # --- Act ---
                all_items, total = self._fetch_all_pages(products_client, params)

                # --- Assert ---
                assert total == len(raw_products_data), (
                    f"Filter should be ignored. Expected total={len(raw_products_data)}, got {total}"
                )
                assert len(all_items) == len(raw_products_data), (
                    f"Filter should be ignored. Expected {len(raw_products_data)} items, got {len(all_items)}"
                )

            # ----------------------------------------------------------------------------------
            # Group 4: empty_result
            # ----------------------------------------------------------------------------------
            case "empty_result":
                # --- Act ---
                response = products_client.get_products(params=params, expected_status=200)
                res_json = response.json()
                items = res_json.get("data", [])

                # --- Assert ---
                assert len(items) == 0, f"Expected 0 items in data, got {len(items)}"
                assert res_json.get("total", 0) == 0, f"Expected total=0, got {res_json.get('total')}"

            # ----------------------------------------------------------------------------------
            # Safeguard: Unsupported validation type
            # ----------------------------------------------------------------------------------
            case _:
                raise ValueError(f"Unsupported validation_type: {validation_type}")

    @staticmethod
    def _fetch_all_pages(
        products_client,
        params: dict[str, Any],
        max_pages: int = 100,
    ) -> tuple[list[dict[str, Any]], int]:
        """Dynamically fetches all items across all pagination pages with infinite loop guards."""
        all_items = []
        page = 1
        last_page = 1
        total_items = 0

        while page <= last_page:
            assert page <= max_pages, f"Exceeded maximum page safety limit ({max_pages}). Possible infinite loop."

            response = products_client.get_products(params={**params, "page": page}, expected_status=200)
            res_json = response.json()

            last_page = res_json.get("last_page", 1)
            total_items = res_json.get("total", 0)
            items = res_json.get("data", [])

            if page < last_page:
                assert len(items) > 0, f"Page {page} returned empty data before reaching last_page ({last_page})."

            all_items.extend(items)
            page += 1

        return all_items, total_items

    @allure.story("Invalid Price Filters Negative")
    @allure.title("Filter by price range: {id}")
    @pytest.mark.parametrize("invalid_filter, description", [
        ("price,100,10", "Inverted range (min > max)"),
        ("price,-50,100", "Negative min price"),
        ("price,10,-50", "Negative max price"),
        ("price,-50,-10", "Both negative prices (min < 0 and max < 0)"),
        ("price,10,5,100", "Comma instead of dot in float"),
        ("price,abc,100", "Non-numeric min value"),
        ("price,10,999999999999999999999999999", "Integer overflow max value"),
    ], ids=[
        "inverted_range",
        "negative_min",
        "negative_max",
        "negative_both",
        "comma_float",
        "non_numeric",
        "integer_overflow",
    ]
    )
    def test_filter_products_by_price_range_invalid(
        self, 
        products_client: ProductsClient, 
        invalid_filter: str, 
        description: str, 
    ):
        """Verify that invalid price filters do not crash the backend with 500 error."""
        # --- Arrange ---
        params = {"between": invalid_filter}

        # --- Act ---
        response = products_client.get_products(params=params, expected_status=None)

        # --- Assert ---
        match response.status_code:
            case 500:
                pytest.fail(
                    f"Backend crashed with 500 Internal Server Error for [{description}]. "
                    f"Filter: '{invalid_filter}'"
                )
            case 200:
                payload = response.json()
                data = payload.get("data")
                assert isinstance(data, list), (
                    f"Response body for [{description}] missing 'data' list structure. Got: {type(data)}"
                )
            case 400 | 422:
                pass  # Validation error is an expected response for invalid filter input
            case _:
                pytest.fail(f"Unexpected HTTP status code {response.status_code} for [{description}]")


@allure.epic("API Backend")
@allure.feature("Complex Filtering")
class TestProductsComplexFiltering:
    """Integration test suite verifying complex multi-parameter product filter combinations."""

    def _verify_page_2_filters_persistence(
        self,
        products_client: ProductsClient,
        query_params: dict[str, Any],
        parsed_response: ProductsListResponse,
    ) -> None:
        """Verifies that query filters persist when navigating to page 2.

        If the filtered dataset contains fewer than 2 pages due to limited test site data,
        explicitly skips the pagination assertion to prevent false-positive test passes.
        """
        if parsed_response.last_page < 2:
            pytest.skip(
                f"Skipping Page 2 persistence check: filtered dataset contains only {parsed_response.total} "
                f"item(s) (last_page={parsed_response.last_page}). At least 10 items required for page 2 validation."
            )

        page_2_response = products_client.get_products(
            params={**query_params, "page": 2},
            expected_status=200,
        )
        parsed_page_2 = ProductsListResponse.model_validate(page_2_response.json())

        assert parsed_page_2.current_page == 2, (
            f"Expected current_page=2, got {parsed_page_2.current_page}"
        )

        # Extract expected filter criteria once using pattern matching
        expected_category_id: str | None = None
        expected_brand_id: str | None = None
        expected_rental: bool | None = None
        expected_location_offer: bool | None = None

        for key, value in query_params.items():
            match key:
                case "by_category":
                    expected_category_id = str(value)
                case "by_brand":
                    expected_brand_id = str(value)
                case "is_rental":
                    expected_rental = str(value).lower() == "true"
                case "is_location_offer":
                    expected_location_offer = str(value).lower() == "true"

        # Validate page 2 items in O(N) complexity with clear, readable conditions
        for product in parsed_page_2.data:
            if expected_category_id and product.category:
                assert product.category.id == expected_category_id, (
                    f"Page 2 filter loss: expected category {expected_category_id}, got {product.category.id}"
                )
            if expected_brand_id and product.brand:
                assert product.brand.id == expected_brand_id, (
                    f"Page 2 filter loss: expected brand {expected_brand_id}, got {product.brand.id}"
                )
            if expected_rental is not None:
                assert product.is_rental is expected_rental, (
                    f"Page 2 filter loss: expected is_rental={expected_rental}, got {product.is_rental}"
                )
            if expected_location_offer is not None:
                assert product.is_location_offer is expected_location_offer, (
                    f"Page 2 filter loss: expected is_location_offer={expected_location_offer}, got {product.is_location_offer}"
                )

    def _assert_case_domain_rules(
        self,
        case_type: str,
        products: list[ProductItem],
        filter_pair: dict[str, str],
        price_boundaries: PriceBoundaries,
        search_keyword: str | None,
    ) -> None:
        """Validates case-specific domain filter expectations via pattern matching."""
        match case_type:
            case "category_brand_price_rental":
                if len(products) == 0:
                    pytest.skip(
                        f"Skipping assertion: no rental products found in database for "
                        f"category_id='{filter_pair.get('by_category')}' and "
                        f"brand_id='{filter_pair.get('by_brand')}'"
                    )

                for p in products:
                    assert p.category and p.category.id == filter_pair["by_category"]
                    assert p.brand and p.brand.id == filter_pair["by_brand"]
                    assert (
                        price_boundaries.min_price
                        <= p.price
                        <= price_boundaries.max_price
                    )
                    assert p.is_rental is True

            case "category_price_search":
                assert len(products) > 0, "Expected matching products, got 0"
                for p in products:
                    assert p.category and p.category.id == filter_pair["by_category"]
                    assert (
                        price_boundaries.min_price
                        <= p.price
                        <= price_boundaries.max_price
                    )
                    assert search_keyword and (
                        (p.name and search_keyword.lower() in p.name.lower())
                        or (
                            p.description
                            and search_keyword.lower() in p.description.lower()
                        )
                    ), f"Search keyword '{search_keyword}' not found in product name or description"

            case "brand_location_offer_price":
                assert len(products) > 0, "Expected matching products, got 0"
                for p in products:
                    assert p.brand and p.brand.id == filter_pair["by_brand"]
                    assert p.price == price_boundaries.exact_price
                    assert p.is_location_offer is True

            case "non_overlapping_with_price":
                assert len(products) == 0, f"Expected empty array, got {len(products)}"

            case "all_six_filters":
                for p in products:
                    assert p.category and p.category.id == filter_pair["by_category"]
                    assert p.brand and p.brand.id == filter_pair["by_brand"]
                    assert p.is_rental is True
                    assert p.is_location_offer is True

    @allure.story("Multi-parameter Filtering")
    @pytest.mark.parametrize(
        "case_type, use_non_overlapping, extra_params, search_keyword",
        [
            ("category_brand_price_rental", False, {"is_rental": "true"}, None),
            ("category_price_search", False, {}, "Pliers"),
            ("brand_location_offer_price", False, {"is_location_offer": "true"}, None),
            ("non_overlapping_with_price", True, {}, None),
        ],
        ids=[
            "combine_category_brand_price_range_and_rental",
            "combine_category_price_range_and_search_query",
            "combine_brand_location_offer_and_exact_price",
            "combine_non_overlapping_filters_with_price_range_returns_empty",
        ],
    )
    def test_filter_products_combined(
        self,
        products_client: ProductsClient,
        valid_filter_pairs: list[dict[str, str]],
        non_overlapping_pairs: list[dict[str, str]],
        price_boundaries: PriceBoundaries,
        case_type: str,
        use_non_overlapping: bool,
        extra_params: dict[str, Any],
        search_keyword: str | None,
    ) -> None:
        """Verify multi-parameter combined filtering and pagination persistence."""
        # --- Arrange ---
        if not use_non_overlapping and not valid_filter_pairs:
            pytest.skip("Skipped: No valid filter pairs available in the catalog for this combination test.")
        if use_non_overlapping and not non_overlapping_pairs:
            pytest.skip("Skipped: No non-overlapping pairs available in the catalog.")

        filter_pair = (
            non_overlapping_pairs[0] if use_non_overlapping else valid_filter_pairs[0]
        )

        match case_type:
            case "category_brand_price_rental":
                # Contains: by_category, by_brand, is_rental="true", between=min,max
                query_params = {
                    **filter_pair,
                    **extra_params,
                    "between": f"price,{price_boundaries.min_price},{price_boundaries.max_price}",
                }

            case "category_price_search":
                # Original logic removed "by_brand" and added "q": search_keyword
                query_params = {
                    "by_category": filter_pair["by_category"],
                    "q": search_keyword,
                    **extra_params,
                    "between": f"price,{price_boundaries.min_price},{price_boundaries.max_price}",
                }

            case "brand_location_offer_price":
                # Original logic removed "by_category", kept "is_location_offer"="true", set exact_price
                query_params = {
                    "by_brand": filter_pair["by_brand"],
                    **extra_params,
                    "between": f"price,{price_boundaries.exact_price},{price_boundaries.exact_price}",
                }

            case "non_overlapping_with_price":
                # Contains non-overlapping filter_pair + price range
                query_params = {
                    **filter_pair,
                    **extra_params,
                    "between": f"price,{price_boundaries.min_price},{price_boundaries.max_price}",
                }

        # --- Act ---
        response = products_client.get_products(params=query_params, expected_status=200)
        parsed_response = ProductsListResponse.model_validate(response.json())

        # --- Assert: Pagination smoke check ---
        assert parsed_response.current_page == 1
        assert parsed_response.per_page == 9

        # --- Assert: Page 2 persistence & Domain filter assertions ---
        self._verify_page_2_filters_persistence(products_client, query_params, parsed_response)
        self._assert_case_domain_rules(
            case_type,
            parsed_response.data,
            filter_pair,
            price_boundaries,
            search_keyword,
        )

    @allure.story("Multi-parameter Filtering")
    def test_filter_all_six_filters_edge_case(
        self,
        products_client: ProductsClient,
        strict_filter_pairs: list[dict[str, str]],
        price_boundaries: PriceBoundaries,
    ) -> None:
        """Verify multi-parameter combined filtering using all 6 filters simultaneously."""
        # --- Arrange ---
        if not strict_filter_pairs:
            pytest.skip(
                "Skipped: No products found in the database matching all 6 filters simultaneously "
                "(required category, brand, is_rental=True, and is_location_offer=True)."
            )

        filter_pair = strict_filter_pairs[0]
        search_keyword = "Pliers"

        query_params = {
            **filter_pair,
            "is_rental": "true",
            "is_location_offer": "true",
            "q": search_keyword,
            "between": f"price,{price_boundaries.min_price},{price_boundaries.max_price}",
        }

        # --- Act ---
        response = products_client.get_products(params=query_params, expected_status=200)
        parsed_response = ProductsListResponse.model_validate(response.json())

        # --- Assert: Domain filter assertions ---
        self._assert_case_domain_rules(
            "all_six_filters",
            parsed_response.data,
            filter_pair,
            price_boundaries,
            search_keyword,
        )


@allure.epic("API Backend")
@allure.feature("Filtering Negative")
class TestProductsFilteringNegative:
    """Negative test suite verifying product filter tolerance to malformed query parameters."""

    @allure.story("Malformed Filter Parameters")
    @pytest.mark.parametrize(
        "query_params",
        [
            {"is_rental": "invalid_boolean"},
            {"is_location_offer": "not_a_bool"},
        ],
        ids=[
            "invalid_is_rental_flag_ignored",
            "invalid_is_location_offer_flag_ignored",
        ],
    )
    def test_filter_products_ignores_invalid_boolean_flags(
        self,
        products_client: ProductsClient,
        query_params: dict[str, Any],
    ) -> None:
        """Verify API ignores malformed boolean parameters and returns non-empty product list."""
        # --- Arrange & Act ---
        response = products_client.get_products(params=query_params, expected_status=200)
        parsed_response = ProductsListResponse.model_validate(response.json())

        # --- Assert: API falls back to default page (9 products per page) ---
        assert len(parsed_response.data) == 9, (
            f"Expected default page size of 9 products, got {len(parsed_response.data)}"
        )
        assert parsed_response.total > 0

    @allure.story("Malformed Filter Parameters")
    @pytest.mark.parametrize(
        "raw_params, mix_valid_data",
        [
            # All 6 filter parameters malformed simultaneously
            (
                {
                    "by_category": "invalid_cat_uuid!",
                    "by_brand": "invalid_brand_uuid!",
                    "is_rental": "not_a_bool",
                    "is_location_offer": "maybe",
                    "between": "price,abc,xyz",
                    "q": "invalid_search_query_!@#",
                },
                False,
            ),
            # Valid category & brand mixed with malformed price range
            (
                {"is_rental": "true", "between": "price,invalid_min,invalid_max"},
                True,
            ),
        ],
        ids=[
            "all_six_malformed_filters_simultaneously_returns_empty",
            "malformed_price_between_returns_empty",
        ],
    )
    def test_filter_products_malformed_ranges_and_ids_return_empty(
        self,
        products_client: ProductsClient,
        valid_filter_pairs: list[dict[str, Any]],
        raw_params: dict[str, Any],
        mix_valid_data: bool,
    ) -> None:
        """Verify API safely returns empty data list (total: 0) when query conditions produce no matches."""
        # --- Arrange ---
        query_params = raw_params.copy()
        if mix_valid_data:
            query_params.update(valid_filter_pairs[0])

        # --- Act ---
        response = products_client.get_products(params=query_params, expected_status=200)
        parsed_response = ProductsListResponse.model_validate(response.json())

        # --- Assert: Query conditions match nothing, returning empty list safely ---
        assert parsed_response.total == 0, f"Expected 0 products, got {parsed_response.total}"
        assert len(parsed_response.data) == 0


@allure.epic("API Backend")
@allure.feature("Product Sorting")
class TestProductsSortingPositive:
    """Positive test suite verifying product list sorting by name and price in both directions."""

    # --- Helpers ---

    def _extract_sort_values(self, products: list[ProductItem], sort_field: str) -> list[Any]:
        """Extract and normalize values from products list for sorting verification."""
        match sort_field:
            case "price":
                return [product.price for product in products]
            case "name":
                # Lowercase names to ensure case-insensitive alphabetical comparison matching DB collation
                return [product.name.lower() for product in products]
            case _:
                raise ValueError(f"Unsupported sort field: {sort_field}")

    def _assert_is_sorted(
        self,
        products: list[ProductItem],
        sort_field: str,
        direction: str,
    ) -> None:
        """Assert that extracted product values match expected sorted order."""
        is_descending: bool = direction == "desc"
        actual_values = self._extract_sort_values(products, sort_field)
        expected_values = sorted(actual_values, reverse=is_descending)

        assert actual_values == expected_values, (
            f"Products are not correctly sorted by '{sort_field}' in '{direction}' order.\n"
            f"Actual:   {actual_values}\n"
            f"Expected: {expected_values}"
        )

    # --- Tests ---

    @pytest.mark.parametrize(
        "sort_field, direction",
        [
            ("price", "asc"),
            ("price", "desc"),
            ("name", "asc"),
            ("name", "desc"),
        ],
        ids=[
            "sort_by_price_ascending",
            "sort_by_price_descending",
            "sort_by_name_ascending",
            "sort_by_name_descending",
        ],
    )
    @allure.story("Sorting Positive")
    @pytest.mark.smoke
    def test_get_products_sorting(
        self,
        products_client: ProductsClient,
        sort_field: str,
        direction: str,
    ) -> None:
        """Verify API correctly returns sorted product data according to requested field and direction."""
        # --- Arrange ---
        query_params: dict[str, Any] = {"sort": f"{sort_field},{direction}"}

        # --- Act ---
        response = products_client.get_products(params=query_params, expected_status=200)
        parsed_response = ProductsListResponse.model_validate(response.json())

        # --- Assert ---
        assert len(parsed_response.data) == 9, (
            f"Expected default page size of 9 products, got {len(parsed_response.data)}"
        )
        self._assert_is_sorted(parsed_response.data, sort_field, direction)


@allure.epic("API Backend")
@allure.feature("Product Sorting")
class TestProductsSortingNegative:
    """Negative test suite verifying API fallback behavior when invalid sorting parameters are provided."""

    @allure.story("Sorting Negative")
    @pytest.mark.parametrize(
        "sort_param",
        [
            pytest.param(
                "invalid_field,asc",
                marks=pytest.mark.xfail(
                    reason="BUG: Backend throws 500 Internal Server Error instead of fallback to default sorting"
                ),
                id="invalid_sort_field",
            ),
            pytest.param(
                "price,sideways",
                id="invalid_sort_direction",
            ),
            pytest.param(
                "price-asc",
                marks=pytest.mark.xfail(
                    reason="BUG: Backend throws 500 Internal Server Error when comma delimiter is missing"
                ),
                id="invalid_delimiter_format",
            ),
        ],
    )
    def test_get_products_sorting_fallback(
        self,
        products_client: ProductsClient,
        sort_param: str,
    ) -> None:
        """Verify API handles invalid sorting parameters gracefully by falling back to default pagination response."""
        # --- Arrange & Act ---
        response = products_client.get_products(
            params={"sort": sort_param},
            expected_status=200,
        )
        parsed_response = ProductsListResponse.model_validate(response.json())

        # --- Assert ---
        assert len(parsed_response.data) == 9, (
            f"Expected default fallback page size of 9 products for invalid sort param '{sort_param}', "
            f"got {len(parsed_response.data)}"
        )
        assert parsed_response.total > 0, (
            f"Expected total products count to be greater than 0 for invalid sort param '{sort_param}'"
        )


@allure.epic("API Backend")
@allure.feature("Security & Sanitization")
class TestProductsSecurity:
    """Security and sanitization test suite for products filtering and search API endpoints."""

    @allure.story("Input Sanitization & Injection Protection")
    @pytest.mark.parametrize(
        "filter_params",
        [
            pytest.param({"q": "' OR '1'='1"}, id="sqli_boolean_bypass_search"),
            pytest.param({"by_category": "'; DROP TABLE products;--"}, id="sqli_destructive_syntax_category"),
            pytest.param({"q": "<script>alert(1)</script>"}, id="xss_script_injection_search"),
            pytest.param({"q": "%' OR '%'"}, id="sqli_wildcard_percent_search"),
            pytest.param({"by_brand": "*"}, id="glob_wildcard_asterisk_brand"),
            pytest.param({"q": "A" * 2500}, id="buffer_overflow_long_string_search"),
            pytest.param({"by_category": "01KYMGDH%00"}, id="null_byte_injection_category"),
        ],
    )
    def test_filter_products_with_invalid_or_malicious_strings_returns_empty(
        self,
        products_client: ProductsClient,
        filter_params: dict[str, Any],
    ) -> None:
        """Verify API safely handles SQLi, XSS, wildcards, long strings and null-bytes without crashing or exposing data."""
        # --- Act ---
        response = products_client.get_products(
            params=filter_params,
            expected_status=200,
        )
        parsed_response = ProductsListResponse.model_validate(response.json())

        # --- Assert ---
        assert len(parsed_response.data) == 0, (
            f"Expected empty data list for malicious/invalid filter {filter_params}, "
            f"but received {len(parsed_response.data)} items (possible injection or data exposure!)"
        )
        assert parsed_response.total == 0, (
            f"Expected total to be 0 for malicious filter {filter_params}, "
            f"got total={parsed_response.total}"
        )