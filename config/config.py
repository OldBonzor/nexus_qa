# config/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for the nexus_qa framework.

    Automatically loads variables from the .env file and validates their types.
    """

    # 1. Describe variables and their types
    BASE_URL: str
    API_URL: str
    TIMEOUT: int = 5  # If no Timeout in .env 5 seconds will be used
    IS_HEADLESS: bool = True  # If absent in .env, browser will start in background

    # 2. Set up Pydantic via special config dictionary
    model_config = SettingsConfigDict(
        env_file=".env",  # which file to read from
        env_file_encoding="utf-8",  # set up file encoding
        extra="ignore",  # If redundant variables in .env, just ignore them
    )


# Create one global setup for the whole framework
settings = Settings()