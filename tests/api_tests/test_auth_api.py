"""API tests for user authentication and protected endpoints."""

import pytest
import allure
from src.api.base_client import BaseClient
from src.api.models.auth_models import LoginRequest, LoginResponse


@allure.epic("API Backend")
@allure.feature("Authentication & Security")
class TestAuthAndProtectedEndpoints:
    """Test suite for authentication workflows and protected resource access."""

    @allure.story("User Login")
    @pytest.mark.smoke
    def test_successful_login(self, api_client: BaseClient) -> None:
        """Verify successful user authentication with valid credentials."""
        # --- Arrange & Act ---
        payload = LoginRequest(
            email="admin@practicesoftwaretesting.com",
            password="welcome01"
        )
        response = api_client.post(
            "/users/login",
            json=payload.model_dump(),
            expected_status=200,
        )

        # --- Assert ---
        token_data = LoginResponse.model_validate(response.json())
        assert token_data.access_token is not None
        assert token_data.token_type.lower() == "bearer"

    @allure.story("User Login")
    @allure.title("Unsuccessful login attempt for email: '{email}'")
    @pytest.mark.parametrize(
        "email, password",
        [
            ("invalid_user@practicesoftwaretesting.com", "welcome01"),  # Invalid email
            ("admin@practicesoftwaretesting.com", "wrong_password_123"),  # Invalid password
            ("invalid_user@practicesoftwaretesting.com", "wrong_pass_123"),  # Both invalid
        ],
        ids=["invalid_email", "invalid_password", "invalid_email_and_password"],
    )
    def test_unsuccessful_login(
        self,
        api_client: BaseClient,
        email: str,
        password: str,
    ) -> None:
        """Verify that authentication fails with invalid credentials."""
        # --- Arrange ---
        payload = LoginRequest(email=email, password=password)

        # --- Act ---
        response = api_client.post(
            "/users/login",
            json=payload.model_dump(),
        )

        # --- Assert ---
        assert response.status_code == 401, f"Expected status 401, got {response.status_code}"

    @allure.story("Protected Endpoints")
    @allure.title("Access protected endpoint '{endpoint}' using Bearer token")
    @pytest.mark.smoke
    @pytest.mark.parametrize(
        "endpoint",
        [
            "/users/me",
        ],
        ids=["users_me"],
    )
    def test_protected_endpoints_with_bearer(
        self,
        api_client: BaseClient,
        auth_token: str,
        endpoint: str,
    ) -> None:
        """Verify access to protected endpoints using a valid Bearer token."""
        # --- Arrange ---
        headers = {"Authorization": f"Bearer {auth_token}"}

        # --- Act ---
        response = api_client.get(
            endpoint,
            headers=headers,
            expected_status=200,
        )

        # --- Assert ---
        data = response.json()
        assert isinstance(data, (dict, list)), "Response must be a dictionary or a list"

    @allure.story("Protected Endpoints")
    def test_protected_endpoint_unauthorized(self, api_client: BaseClient) -> None:
        """Verify that protected endpoints reject requests without a token."""
        # --- Act ---
        response = api_client.get("/users/me")

        # --- Assert ---
        assert response.status_code == 401, f"Expected status 401, got {response.status_code}"

    @allure.story("Protected Endpoints")
    @allure.title("Reject access for invalid authentication token: '{invalid_auth_header}'")
    @pytest.mark.parametrize(
        "invalid_auth_header",
        [
            "Bearer invalid_fake_token_12345",  # Random string
            "Bearer header.BROKEN.signature",   # Malformed JWT structure
        ],
        ids=["random_token", "malformed_token"],
    )
    def test_protected_endpoint_invalid_token(
        self,
        api_client: BaseClient,
        invalid_auth_header: str,
    ) -> None:
        """Verify that protected endpoints reject requests with invalid or malformed tokens."""
        # --- Arrange ---
        headers = {"Authorization": invalid_auth_header}

        # --- Act ---
        response = api_client.get(
            "/users/me",
            headers=headers,
        )

        # --- Assert ---
        assert response.status_code == 401, f"Expected status 401, got {response.status_code}"