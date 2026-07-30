"""API tests for user authentication endpoints."""

import pytest
from src.api.base_client import BaseClient
from src.api.models.auth_models import LoginRequest, LoginResponse


def test_successful_login(api_client: BaseClient) -> None:
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
    # Schema validation via Pydantic
    token_data = LoginResponse.model_validate(response.json())

    # Token payload assertions
    assert token_data.access_token is not None
    assert token_data.token_type.lower() == "bearer"


@pytest.mark.parametrize(
    "email, password",
    [
        ("invalid_user@practicesoftwaretesting.com", "welcome01"),  # Invalid email
        ("admin@practicesoftwaretesting.com", "wrong_password_123"),  # Invalid password
        ("invalid_user@practicesoftwaretesting.com", "wrong_pass_123"),  # Both invalid
    ],
    ids=["invalid_email", "invalid_password", "both_invalid"],
)
def test_unsuccessful_login(
    api_client: BaseClient,
    email: str,
    password: str,
) -> None:
    """Verify that authentication fails with invalid credentials."""
    # --- Arrange & Act ---
    payload = LoginRequest(email=email, password=password)

    # --- Assert ---
    # HTTP 401 Unauthorized assertions
    response = api_client.post(
        "/users/login",
        json=payload.model_dump(),
        expected_status=401,
    )
