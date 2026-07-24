"""API tests for user authentication endpoints."""

import pytest
from src.api.models.auth_models import LoginRequest, LoginResponse


def test_successful_login(api_client):
    """Verify successful user authentication with valid credentials.

    Args:
        api_client: Pytest fixture providing an instance of BaseClient.
    """
    # 1. Prepare request payload using Pydantic model
    payload = LoginRequest(
        email="admin@practicesoftwaretesting.com",
        password="welcome01"
    )

    # 2. Send POST request using BaseClient (expected_status triggers auto-assertion)
    response = api_client.post(
        "/users/login",
        json=payload.model_dump(),
        expected_status=200
    )

    # 3. Validate response structure using Pydantic model
    token_data = LoginResponse.model_validate(response.json())

    # 4. Perform final assertions on authentication token payload
    assert token_data.access_token is not None
    assert token_data.token_type.lower() == "bearer"


@pytest.mark.parametrize(
    "email, password",
    [
        ("invalid_user@practicesoftwaretesting.com", "welcome01"),       # Invalid email
        ("admin@practicesoftwaretesting.com", "wrong_password_123"),   # Invalid password
        ("invalid_user@practicesoftwaretesting.com", "wrong_pass_123"), # Both invalid
    ],
    ids=["invalid_email", "invalid_password", "both_invalid"]
)
def test_unsuccessful_login(api_client, email, password):
    """Verify that authentication fails with invalid credentials.

    Args:
        api_client: Pytest fixture providing an instance of BaseClient.
        email (str): Test email input.
        password (str): Test password input.
    """
    payload = LoginRequest(email=email, password=password)

    # Expect HTTP 401 Unauthorized for invalid credentials
    response = api_client.post(
        "/users/login",
        json=payload.model_dump(),
        expected_status=401
    )