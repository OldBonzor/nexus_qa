"""API tests for the products endpoints."""

from math import ceil
from typing import Any, Optional
import pytest
from src.api.models.product_models import Category, Brand, PriceBoundaries, ProductsListResponse, ProductItem
from src.api.products_client import ProductsClient


class TestProductsList:
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


class TestProductDetails:
    """Suite for testing product details endpoint (/products/{id})."""
    def test_get_product_by_id(self, products_client: ProductsClient):
        """Verify that product requested using valid ID returns 200 code with product data"""
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
        ids=["non_existing_id", "only_spacebars_in_id", "only_special_symbols_in_id"]
        )
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


class TestProductsSearch:
    @pytest.mark.parametrize("queries, expected_keyword", [
        (["hammer", "HAMMER", "HaMmEr"], "hammer"),
        (["pliers", "PLIERS", "PlIeRs"], "pliers")
        ],
        ids=["lower_capital_mixed_1", "lower_capital_mixed_2"])
    def test_search_products_by_name_case_insensitive(
        self, 
        products_client: ProductsClient, 
        queries: list[str],
        expected_keyword: str,
        ):
        """Check searching products by keyword using query parameter (q)"""

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

    @pytest.mark.parametrize(
        "invalid_name", 
    [
        "non-existing-name-999",    # Non-existing item name
        "   ",                       # Spacebars in item name
        "@#$%^&*()~!?,;",           # Special symbols in item name
    ],
    ids=["non_existing_name", "only_spacebars_in_name", "only_special_symbols_in_name"]
    )
    def test_search_products_by_name_not_found(
        self, 
        products_client: ProductsClient, 
        invalid_name: str
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


class TestProductsFilter:
    """Suite for testing product list filtering by category and brand."""
    @pytest.mark.parametrize(
        "filter_mode", ["category_only", "brand_only", "category_and_brand"],
        ids=["category_only", "brand_only", "combined_category_and_brand"]
    )
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
            if filter_mode == "category_only":
                params = {"by_category": pair["by_category"]}
            elif filter_mode == "brand_only":
                params = {"by_brand": pair["by_brand"]}
            else:
                params = pair

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

    @pytest.mark.parametrize(
        "filter_mode",
        [
            "invalid_category_only",
            "invalid_brand_only",
            "both_invalid",
            "valid_category_invalid_brand",
            "invalid_category_valid_brand",
        ],
        ids=[
            "invalid_category_only",
            "invalid_brand_only",
            "both_invalid",
            "valid_category_invalid_brand",
            "invalid_category_valid_brand",
        ]
    )
    def test_filter_products_by_non_existing_categories_and_brands_returns_empty(
        self, 
        products_client: ProductsClient, 
        valid_filter_pairs: list[dict], 
        filter_mode: str
    ):
        """Check that filtering by non-existing category or brand IDs returns an empty list."""

        # --- Arrange ---
        valid_pair = valid_filter_pairs[0]
        non_existing_id = "non-existing-id-999"

        if filter_mode == "invalid_category_only":
            params = {"by_category": non_existing_id}
        elif filter_mode == "invalid_brand_only":
            params = {"by_brand": non_existing_id}
        elif filter_mode == "both_invalid":
            params = {"by_category": non_existing_id, "by_brand": non_existing_id}
        elif filter_mode == "valid_category_invalid_brand":
            params = {"by_category": valid_pair["by_category"], "by_brand": non_existing_id}            
        elif filter_mode == "invalid_category_valid_brand":
            params = {"by_category": non_existing_id, "by_brand": valid_pair["by_brand"]}

        # --- Act & Assert ---
        response = products_client.get_products(params=params, expected_status=200)
        products_data = ProductsListResponse(**response.json())
    
        assert products_data.total == 0, (f"Expected empty list for params {params}, got {products_data.data}")
        assert len(products_data.data) == 0, (f"Expected total = 0 for params {params}, got {products_data.total}")


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


class TestProductsPriceFilter:
    """Suite for testing product price filtering capabilities via API."""

    @pytest.mark.parametrize(
        "get_params_func, validation_type",
        [
            # ==============================================================================
            # Group 1: exact_bounds (Exact boundaries)
            # ==============================================================================
            pytest.param(
                lambda b: {"between": f"price,{b.exact_price},{b.exact_price}"},
                "exact_bounds",
                id="1. Exact Match (min==max)",
            ),
            pytest.param(
                lambda b: {"between": f"price,{b.min_price},{b.exact_price}"},
                "exact_bounds",
                id="2. Standard Valid Range (min < max via exact_price)",
            ),
            pytest.param(
                lambda b: {"between": f"price,{b.min_price:.2f},{b.exact_price:.2f}"},
                "exact_bounds",
                id="3. Cents Precision (.2f)",
            ),
            pytest.param(
                lambda b: {"between": f"price,{b.min_price + 0.123456:.6f},{b.exact_price + 0.987654:.6f}"},
                "exact_bounds",
                id="4. Excessive Float Precision (.6f)",
            ),
            pytest.param(
                lambda b: {"between": f"price,{b.exact_price},"},
                "exact_bounds",
                marks=pytest.mark.xfail(
                    reason="BUG: Backend fails to parse trailing comma in 'price,min,' and returns empty list",
                    strict=True,
                ),
                id="5. Only min_price",
            ),
            pytest.param(
                lambda b: {"between": f"price,,{b.exact_price}"},
                "exact_bounds",
                id="6. Only max_price",
            ),
            # ==============================================================================
            # Group 2: full_coverage (Full DB coverage)
            # ==============================================================================
            pytest.param(
                lambda b: {"between": f"price,{b.min_price},{b.max_price}"},
                "full_coverage",
                id="7. Full DB Price Coverage",
            ),
            # ==============================================================================
            # Group 3: all_items (Filter ignored)
            # ==============================================================================
            pytest.param(
                lambda b: {"between": "price,,"},
                "filter_ignored",
                id="8. Filter Ignored (price,,)",
            ),
            pytest.param(
                lambda b: {"between": "price,,null"},
                "filter_ignored",
                id="9. Filter Ignored (price,,null)",
            ),
            pytest.param(
                lambda b: {"between": "price,null,"},
                "filter_ignored",
                id="10. Filter Ignored (price,null,)",
            ),
            pytest.param(
                lambda b: {"between": "price,null,null"},
                "filter_ignored",
                id="11. Filter Ignored (price,null,null)",
            ),
            pytest.param(
                lambda b: {},
                "all_items",
                id="12. Filter Ignored (no between param)",
            ),
            # ==============================================================================
            # Group 4: empty_result (Empty result)
            # ==============================================================================
            pytest.param(
                lambda b: {"between": f"price,{b.max_price + 10000.00},{b.max_price + 20000.00}"},
                "empty_result",
                id="13. Out of Bounds (+10k..+20k -> empty_result)",
            ),
            pytest.param(
                lambda b: {"between": "price,0,0"},
                "empty_result",
                id="14. Zero Price Range (0..0 -> empty_result)",
            ),
        ],
    )
    def test_filter_products_by_price_range(
        self,
        products_client: ProductsClient,  # <-- Добавлено : ProductsClient
        price_boundaries: PriceBoundaries,
        raw_products_data: list[dict[str, Any]],
        get_params_func: Any,
        validation_type: str,
    ):
        """Validates price range filtering logic, dynamic pagination, and boundary conditions."""
        # --- Arrange ---
        params = get_params_func(price_boundaries)

        # ----------------------------------------------------------------------------------
        # Group 1: exact_bounds
        # ----------------------------------------------------------------------------------
        if validation_type == "exact_bounds":
            # --- Act ---
            all_items, _ = self._fetch_all_pages(products_client, params)

            # Protection from backend error returning empty items list
            assert len(all_items) > 0, f"Filter {params} returned 0 items, expected at least 1."

            # Parse limits
            raw_between = params.get("between", "").replace("price,", "").split(",")
            raw_min = raw_between[0] if len(raw_between) > 0 else ""
            raw_max = raw_between[1] if len(raw_between) > 1 else ""

            if raw_min and raw_min != "null":
                min_limit = float(raw_min)
            else:
                min_limit = None

            if raw_max and raw_max != "null":
                max_limit = float(raw_max)
            else:
                max_limit = None

            # --- Assert ---
            for item in all_items:
                price = float(item["price"])
                if min_limit is not None:
                    assert price >= min_limit, f"Price {price} is less than min_limit {min_limit}"
                if max_limit is not None:
                    assert price <= max_limit, f"Price {price} is greater than max_limit {max_limit}"

        # ----------------------------------------------------------------------------------
        # Group 2: full_coverage
        # ----------------------------------------------------------------------------------
        elif validation_type == "full_coverage":
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
        elif validation_type == "all_items":
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
        elif validation_type == "empty_result":
            # --- Act ---
            response = products_client.get_products(params=params, expected_status=200)
            res_json = response.json()
            items = res_json.get("data", [])

            # --- Assert ---
            assert len(items) == 0, f"Expected 0 items in data, got {len(items)}"
            assert res_json.get("total", 0) == 0, f"Expected total=0, got {res_json.get('total')}"

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
        "integer_overflow"
    ])
    def test_filter_products_by_price_range_invalid(
        self, 
        products_client: ProductsClient, 
        invalid_filter: str, 
        description: str, 
    ):
        """Verify that invalid price filters do not crash the backend with 500 error."""
        # Arrange
        params = {"between": invalid_filter}

        # Act
        response = products_client.get_products(params=params, expected_status=None)

        # Assert
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


    @pytest.mark.skip(reason="WIP")
    def test_filter_products_combined(self, products_client: ProductsClient):
        # --- Arrange ---
        # --- Act ---
        # --- Assert ---
        pass


class TestProductsSorting:
    @pytest.mark.skip(reason="WIP")
    def test_get_products_sorting(self, products_client: ProductsClient):
        # --- Arrange ---
        # --- Act ---
        # --- Assert ---
        pass


