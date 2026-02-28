## Why

The ACME HTTP-01 challenge flow requires a publicly accessible HTTP endpoint at `/.well-known/acme-challenge/{token}` that returns the key authorization string. Without this responder, the ACME CA cannot verify domain ownership and the certificate issuance flow cannot complete. An Azure Function provides a lightweight, serverless HTTP trigger that can serve this response dynamically based on an App Setting written by the CLI.

## What Changes

- Add `azure-function/` directory at the repository root containing a deployable Azure Functions Python app
- The function handles HTTP GET requests to `/.well-known/acme-challenge/{token}` and returns the value of the `ACME_CHALLENGE_RESPONSE` environment variable as `text/plain`
- Returns HTTP 404 when `ACME_CHALLENGE_RESPONSE` is not set or empty
- The `AzureGatewayClient.update_function_app_settings()` method (already declared in the ROADMAP) is implemented in `src/az_acme_tool/azure_gateway.py` using `azure-mgmt-web` to write the key authorization value to the Function App's App Settings
- Unit tests for the Azure Function and for `update_function_app_settings()`

## Capabilities

### New Capabilities

- `azure-function-responder`: Azure Functions HTTP trigger that serves ACME HTTP-01 challenge responses from the `ACME_CHALLENGE_RESPONSE` App Setting

### Modified Capabilities

- `azure-gateway-client`: Add `update_function_app_settings(function_app_name: str, settings: dict[str, str]) -> None` method to `AzureGatewayClient` using `azure-mgmt-web` SDK

## Impact

- New directory: `azure-function/` (contains `function_app.py`, `host.json`, `requirements.txt`)
- New file: `tests/test_azure_function.py`
- Modified: `src/az_acme_tool/azure_gateway.py` (add `update_function_app_settings` method)
- Modified: `tests/test_azure_gateway.py` (add tests for `update_function_app_settings`)
- New runtime dependency: `azure-mgmt-web>=3.0` (already in `pyproject.toml`)
- `azure-function/requirements.txt` is maintained separately from `pyproject.toml` (Azure Functions deployment requirement)
