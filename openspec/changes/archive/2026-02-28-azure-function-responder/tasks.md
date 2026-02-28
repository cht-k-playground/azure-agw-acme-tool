## 1. Azure Function implementation

- [x] 1.1 Create `azure-function/` directory and `azure-function/function_app.py` with an Azure Functions Python v2 HTTP trigger at route `.well-known/acme-challenge/{token}` (GET only) — reads `ACME_CHALLENGE_RESPONSE` from `os.environ`, returns HTTP 200 with the value as `text/plain` if set and non-empty, or HTTP 404 if not set or empty
- [x] 1.2 Create `azure-function/host.json` with valid Azure Functions v2 host configuration including `extensionBundle` for HTTP triggers
- [x] 1.3 Create `azure-function/requirements.txt` with `azure-functions` pinned to a specific version compatible with Python 3.11 (e.g., `azure-functions==1.21.3`)
- [x] 1.4 Create `tests/test_azure_function.py` with unit tests covering: HTTP 200 with correct body when `ACME_CHALLENGE_RESPONSE` is set, HTTP 404 when `ACME_CHALLENGE_RESPONSE` is not set, HTTP 404 when `ACME_CHALLENGE_RESPONSE` is empty string

## 2. AzureGatewayClient extension

- [x] 2.1 Add `update_function_app_settings(self, function_app_name: str, settings: dict[str, str]) -> None` method to `AzureGatewayClient` in `src/az_acme_tool/azure_gateway.py` — uses `azure.mgmt.web.WebSiteManagementClient` to call `web_apps.update_application_settings()` with a `StringDictionary` containing the provided settings; logs only the function app name and setting key names (never values); raises `AzureGatewayError` on `HttpResponseError`
- [x] 2.2 Add unit tests for `update_function_app_settings` in `tests/test_azure_gateway.py` — covering: successful update, setting values not logged, and `AzureGatewayError` on API failure

## 3. Quality checks

- [x] 3.1 Run `ruff check src/ tests/ azure-function/` and fix any linting issues
- [x] 3.2 Run `mypy --strict src/ azure-function/` and fix any type errors
- [x] 3.3 Run `python -m pytest tests/ --cov=src/az_acme_tool --cov-report=term-missing` and confirm ≥80% line coverage
