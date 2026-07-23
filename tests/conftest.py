"""Central Pytest configuration and shared fixtures for API automation.

This module provides common test fixtures used across API tests,
including BaseClient initialization and automatic session lifecycle management.
"""

from typing import Generator
import pytest
from src.api.base_client import BaseClient


@pytest.fixture(scope="function")
def api_client() -> Generator[BaseClient, None, None]:
    """Pytest fixture to initialize and yield a BaseClient instance.

    Creates a new BaseClient for each test function and ensures proper cleanup
    by closing the underlying requests session after test execution completes.

    Yields:
        BaseClient: Configured HTTP client instance ready for making requests.
    """
    client = BaseClient()
    yield client
    client.session.close()