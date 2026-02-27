## 1. Dependencies

- [x] 1.1 Add `azure-mgmt-network>=28.0.0` and `azure-identity>=1.16.0` to `[project.dependencies]` in `pyproject.toml`
- [x] 1.2 Run `uv sync` to install the new dependencies and verify the lock file updates

## 2. Core Implementation

- [x] 2.1 Create `src/az_acme_tool/azure_gateway.py` with `AzureGatewayError` exception class
- [x] 2.2 Implement `AzureGatewayClient.__init__(self, subscription_id, resource_group, gateway_name, credential)` initialising `NetworkManagementClient`
- [x] 2.3 Implement `list_certificates(self) -> list[dict[str, Any]]` — fetch gateway, iterate `ssl_certificates`, return list of `{name, expiry}` dicts; catch `HttpResponseError` → `AzureGatewayError`
- [x] 2.4 Implement `get_certificate_expiry(self, cert_name: str) -> datetime` — call `list_certificates`, find by name, validate expiry not None; raise `AzureGatewayError` for not-found and None-expiry cases
- [x] 2.5 Implement `update_listener_certificate(self, listener_name: str, cert_name: str) -> None` — fetch gateway, locate listener and cert by name, update listener's `ssl_certificate` sub-resource reference, call `begin_create_or_update(...).result()`; raise `AzureGatewayError` for missing listener, missing cert, or SDK errors

## 3. Type Checking and Linting

- [x] 3.1 Ensure all public functions and methods have complete type annotations
- [x] 3.2 Run `mypy --strict src/az_acme_tool/azure_gateway.py` and fix all errors
- [x] 3.3 Run `ruff check src/az_acme_tool/azure_gateway.py` and fix all warnings
- [x] 3.4 Run `black --line-length 100 src/az_acme_tool/azure_gateway.py` to format

## 4. Tests

- [x] 4.1 Create `tests/test_azure_gateway.py` with fixtures that mock `NetworkManagementClient` using `pytest-mock`
- [x] 4.2 Write tests for `AzureGatewayClient` instantiation (credential and subscription_id passed to SDK)
- [x] 4.3 Write tests for `list_certificates` — certificates present, empty list, `HttpResponseError` → `AzureGatewayError`
- [x] 4.4 Write tests for `get_certificate_expiry` — found with expiry, not found, expiry is None, API error
- [x] 4.5 Write tests for `update_listener_certificate` — success, listener not found, cert not found, API error
- [x] 4.6 Run `pytest tests/test_azure_gateway.py -v` and confirm all tests pass
- [x] 4.7 Run `pytest --cov=az_acme_tool.azure_gateway --cov-report=term-missing tests/test_azure_gateway.py` and confirm ≥80% line coverage
