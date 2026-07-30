"""API base client architecture for the nexus_qa framework.

This module defines the strict contract and structural skeleton for HTTP clients.
It enforces standard HTTP methods (GET, POST, PUT, DELETE) using an Abstract Base Class
and provides a concrete BaseClient utilizing the `requests` library.
"""

import abc
import json as json_lib
import logging
from typing import Any, Optional
import requests
from config.settings import settings

# Configure module-level logger
logger = logging.getLogger(__name__)


class APIClientError(Exception):
    """Exception raised for errors in the API client execution.

    Attributes:
        method: HTTP method of the failed request.
        url: Target URL of the failed request.
        message: Detailed error description or underlying reason.
    """

    def __init__(self, method: str, url: str, message: str) -> None:
        self.method = method
        self.url = url
        self.message = message
        super().__init__(f"API Request Failed: [{method}] {url} - Reason: {message}")


class AbstractAPIClient(abc.ABC):
    """Abstract Base Class defining the contract for all API clients within nexus_qa.

    This contract ensures consistent method signatures, explicit type hinting,
    and standardized response objects across all service-specific clients.
    """

    @abc.abstractmethod
    def get(
        self,
        url: str,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        expected_status: Optional[int] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Perform an HTTP GET request.

        Args:
            url: The target endpoint or relative path.
            params: Query parameters to attach.
            headers: HTTP headers to include.
            timeout: Timeout in seconds.
            expected_status: Expected status code for auto-assertion.
            **kwargs: Additional keyword arguments passed to requests.

        Returns:
            The HTTP response object.
        """

    @abc.abstractmethod
    def post(
        self,
        url: str,
        data: Optional[Any] = None,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        expected_status: Optional[int] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Perform an HTTP POST request.

        Args:
            url: The target endpoint or relative path.
            data: Raw request body.
            json: JSON payload structure.
            headers: HTTP headers to include.
            timeout: Timeout in seconds.
            expected_status: Expected status code for auto-assertion.
            **kwargs: Additional keyword arguments passed to requests.

        Returns:
            The HTTP response object.
        """

    @abc.abstractmethod
    def put(
        self,
        url: str,
        data: Optional[Any] = None,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        expected_status: Optional[int] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Perform an HTTP PUT request.

        Args:
            url: The target endpoint or relative path.
            data: Raw request body.
            json: JSON payload structure.
            headers: HTTP headers to include.
            timeout: Timeout in seconds.
            expected_status: Expected status code for auto-assertion.
            **kwargs: Additional keyword arguments passed to requests.

        Returns:
            The HTTP response object.
        """

    @abc.abstractmethod
    def delete(
        self,
        url: str,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        expected_status: Optional[int] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Perform an HTTP DELETE request.

        Args:
            url: The target endpoint or relative path.
            headers: HTTP headers to include.
            timeout: Timeout in seconds.
            expected_status: Expected status code for auto-assertion.
            **kwargs: Additional keyword arguments passed to requests.

        Returns:
            The HTTP response object.
        """


class BaseClient(AbstractAPIClient):
    """Concrete implementation of AbstractAPIClient using the `requests` library.

    This client initializes a `requests.Session` for efficient connection pooling,
    automatically resolves and prepends `BASE_API_URL`, and manages centralized
    logging and default timeouts.
    """

    def __init__(self) -> None:
        """Initialize the BaseClient session and configure base URL & defaults."""
        self.session = requests.Session()

        # Explicitly configure a default Content-Type header on the session level.
        # This ensures all outbound API calls assume a JSON payload structure by default,
        # unless custom request-specific headers are provided during execution.
        self.session.headers.update({"Content-Type": "application/json"})

        self.base_url = str(settings.BASE_API_URL).rstrip("/")

        # Dynamically calculate default timeout in seconds (e.g., PAGE_TIMEOUT / 1000.0)
        self.default_timeout = float(settings.PAGE_TIMEOUT) / 1000.0

    def assert_status_code(self, response: requests.Response, expected_code: int = 200) -> None:
        """Assert that the response status code matches the expected code.

        Args:
            response: The response object from requests.
            expected_code: The expected HTTP status code. Defaults to 200.

        Raises:
            AssertionError: If response status code does not match expected_code.
        """
        if response.status_code != expected_code:
            try:
                body_json = response.json()
                body_str = json_lib.dumps(body_json, indent=2)
            except (ValueError, TypeError):
                body_str = response.text

            # Truncate response body if it's excessively long to keep pytest outputs neat
            max_length = 1000
            if len(body_str) > max_length:
                body_str = body_str[:max_length] + "\n... [TRUNCATED] ..."

            # Extract request details from response
            request_method = response.request.method if response.request else "UNKNOWN"
            request_url = response.request.url if response.request else "UNKNOWN"

            error_msg = (
                f"Status Code Mismatch!\n"
                f"Request: [{request_method}] {request_url}\n"
                f"Expected status: {expected_code}\n"
                f"Actual status:   {response.status_code}\n"
                f"Response body:\n{body_str}"
            )
            raise AssertionError(error_msg)

    def _resolve_url(self, endpoint: str) -> str:
        """Resolve a full URL given an endpoint or path.

        If the endpoint is already a full absolute URL, it is returned untouched.
        Otherwise, `BASE_API_URL` is prepended to the relative path.

        Args:
            endpoint: Endpoint path or full URL.

        Returns:
            Resolved absolute URL.
        """
        if endpoint.startswith(("http://", "https://")):
            return endpoint
        # Ensure correct slash joining without duplication
        clean_endpoint = endpoint.lstrip("/")
        return f"{self.base_url}/{clean_endpoint}"

    def _sanitize_data(self, data: Any) -> Any:
        """Recursively mask sensitive keys in dictionaries or nested structures.

        Args:
            data: dict, list, or primitive type to sanitize.

        Returns:
            Sanitized copy with sensitive data replaced with '[MASKED]'.
        """
        sensitive_keys = {
            "authorization",
            "token",
            "api-key",
            "x-api-key",
            "cookie",
            "password",
            "secret",
            "auth",
            "bearer",
            "credentials",
            "session",
            "apikey",
        }

        if isinstance(data, dict):
            sanitized_dict: dict[Any, Any] = {}
            for key, value in data.items():
                if isinstance(key, str) and key.lower() in sensitive_keys:
                    sanitized_dict[key] = "[MASKED]"
                else:
                    sanitized_dict[key] = self._sanitize_data(value)
            return sanitized_dict
            
        if isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
            
        return data

    def _execute_request(
        self,
        method: str,
        url: str,
        expected_status: Optional[int] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Centralized request execution engine.

        This private method handles:
        1. Injecting default timeouts if not explicitly provided.
        2. Resolving URL paths.
        3. Sanitizing sensitive request data (headers, params, json, etc.) for logging.
        4. Comprehensive Logging (Requests/Responses metadata).
        5. Centralized exception handling and wrapping failures in APIClientError.
        6. Centralized status code assertions if expected_status is specified.

        Args:
            method: HTTP method (e.g., 'GET', 'POST').
            url: Endpoint or full URL.
            expected_status: Expected status code for auto-assertion.
            **kwargs: HTTP request arguments (headers, parameters, body, timeout, etc.).

        Returns:
            Executed HTTP response object.

        Raises:
            APIClientError: If the request fails due to a network error or timeout.
            AssertionError: If expected_status is set and status code mismatch occurs.
        """
        # 1. Resolve URL
        resolved_url = self._resolve_url(url)
        
        # 2. Timeout handling injection: Ensure default_timeout is applied
        if kwargs.get("timeout") is None:
            kwargs["timeout"] = self.default_timeout

        # 3. Sanitize inputs for logging
        sanitized_kwargs = self._sanitize_data(kwargs)

        # 4. Logging outbound request metadata
        logger.info(
            "Sending HTTP Request: [%s] %s - Params: %s - Headers: %s - Timeout: %s",
            method,
            resolved_url,
            sanitized_kwargs.get("params"),
            sanitized_kwargs.get("headers"),
            kwargs.get("timeout"),
        )

        try:
            # 5. Execute actual request
            response = self.session.request(method=method, url=resolved_url, **kwargs)
            
            # 6. Logging successful response metadata
            logger.info(
                "Received HTTP Response: [%s] %s - Status Code: %d - Elapsed: %s",
                method,
                resolved_url,
                response.status_code,
                response.elapsed,
            )

            # 7. Automatically assert status code if specified
            if expected_status is not None:
                self.assert_status_code(response, expected_status)

            return response
            
        except requests.exceptions.RequestException as exc:
            # 8. Intercept errors, log nicely with stack info, and raise custom exception
            error_msg = f"{type(exc).__name__}: {str(exc)}"
            logger.error(
                "HTTP Request Failed: [%s] %s - Reason: %s",
                method,
                resolved_url,
                error_msg,
                exc_info=True
            )
            raise APIClientError(method=method, url=resolved_url, message=error_msg) from exc

    def get(
        self,
        url: str,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        expected_status: Optional[int] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Perform an HTTP GET request."""
        return self._execute_request(
            method="GET",
            url=url,
            expected_status=expected_status,
            params=params,
            headers=headers,
            timeout=timeout,
            **kwargs,
        )

    def post(
        self,
        url: str,
        data: Optional[Any] = None,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        expected_status: Optional[int] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Perform an HTTP POST request."""
        return self._execute_request(
            method="POST",
            url=url,
            expected_status=expected_status,
            data=data,
            json=json,
            headers=headers,
            timeout=timeout,
            **kwargs,
        )

    def put(
        self,
        url: str,
        data: Optional[Any] = None,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        expected_status: Optional[int] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Perform an HTTP PUT request."""
        return self._execute_request(
            method="PUT",
            url=url,
            expected_status=expected_status,
            data=data,
            json=json,
            headers=headers,
            timeout=timeout,
            **kwargs,
        )

    def delete(
        self,
        url: str,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        expected_status: Optional[int] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Perform an HTTP DELETE request."""
        return self._execute_request(
            method="DELETE",
            url=url,
            expected_status=expected_status,
            headers=headers,
            timeout=timeout,
            **kwargs,
        )   