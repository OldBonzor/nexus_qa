"""Authentication data transfer objects (DTOs) and Pydantic models.

This module defines request and response payload schemas for authentication
endpoints (e.g., /users/login) using Pydantic v2.
"""

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    """Payload schema for user login authentication request.

    Attributes:
        email (str): Registered user email address.
        password (str): User authentication password.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    email: str = Field(..., description="Registered user email address", examples=["user@example.com"])
    password: str = Field(..., description="User account password", examples=["SecretPass123!"])


class LoginResponse(BaseModel):
    """Payload schema for successful authentication response.

    Attributes:
        access_token (str): JWT bearer authorization token.
        token_type (str): Token type indicator (typically 'bearer').
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    access_token: str = Field(..., description="Bearer JWT access token")
    token_type: str = Field(..., description="Type of the access token, e.g., 'bearer'")