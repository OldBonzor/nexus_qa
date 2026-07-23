import os
from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Project configuration management using Pydantic Settings.
    
    Loads variables from the environment or a .env file and validates them.
    """
    
    # --- Environment Configuration ---
    ENVIRONMENT: str = Field(default="local", validation_alias="ENV")

    # --- Target Application URLs ---
    BASE_UI_URL: HttpUrl = Field(default="https://practicesoftwaretesting.com")
    BASE_API_URL: HttpUrl = Field(default="https://api.practicesoftwaretesting.com")

    # --- Test User Credentials ---
    TEST_USER_EMAIL: str = Field(default="admin@practicesoftwaretesting.com")
    TEST_USER_PASSWORD: str = Field(default="admin")

    # --- Framework Settings ---
    PAGE_TIMEOUT: int = Field(default=30000, description="Timeout in milliseconds for UI elements")
    HEADLESS_MODE: bool = Field(default=True, description="Run UI tests in headless mode")

    # Configuration binding to read from external .env file
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


# Global settings instance to be imported across the framework
settings = Settings()