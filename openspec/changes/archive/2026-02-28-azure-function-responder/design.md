## Context

The ACME HTTP-01 challenge requires a publicly reachable HTTP endpoint at `/.well-known/acme-challenge/{token}` that returns the key authorization string. The CLI creates a temporary path-based routing rule on Azure Application Gateway that forwards this path to an Azure Function backend. The Function reads the key authorization from its App Settings (`ACME_CHALLENGE_RESPONSE`) and returns it as `text/plain`.

The `AzureGatewayClient` in `src/az_acme_tool/azure_gateway.py` already has `update_function_app_settings()` referenced in the ROADMAP but not yet implemented. The `azure-mgmt-web>=3.0` dependency is already declared in `pyproject.toml`.

**Constraints:**
- Python 3.11+, `mypy --strict`, `ruff`, `black --line-length 100`
- Azure Functions Python v2 programming model (`azure-functions>=1.17.0`)
- `azure-function/requirements.txt` is the sole permitted `requirements.txt` — maintained separately from `pyproject.toml`, not managed by uv
- No new runtime dependencies needed in `pyproject.toml` (uses existing `azure-mgmt-web`)
- Private key material and key authorization values must never be logged

## Goals / Non-Goals

**Goals:**
- Implement `azure-function/function_app.py` with an HTTP trigger for `/.well-known/acme-challenge/{token}`
- Implement `azure-function/host.json` and `azure-function/requirements.txt`
- Implement `AzureGatewayClient.update_function_app_settings()` in `src/az_acme_tool/azure_gateway.py`
- Unit tests for the Azure Function (mock HTTP trigger) and for `update_function_app_settings()`

**Non-Goals:**
- Deploying the Azure Function (deployment is a manual/CI step)
- Authentication on the Function endpoint (ACME CA must reach it unauthenticated)
- Storing multiple challenge tokens simultaneously (single `ACME_CHALLENGE_RESPONSE` setting)
- Key Vault integration for the challenge response

## Decisions

### Decision 1: Azure Functions Python v2 programming model

**Choice**: Use the Azure Functions Python v2 programming model (`@app.route` decorator style) with `azure-functions>=1.17.0`.

**Rationale**: The v2 model is the current recommended approach for Python Azure Functions. It uses a single `function_app.py` entry point with decorator-based bindings, which is simpler and more Pythonic than the v1 model's `function.json` + `__init__.py` pattern.

**Alternative considered**: v1 model — rejected because it requires a separate `function.json` per function and is being deprecated.

### Decision 2: Route pattern for the HTTP trigger

**Choice**: Route `/.well-known/acme-challenge/{token}` with HTTP GET method only.

**Rationale**: The ACME RFC 8555 specifies HTTP GET for challenge validation. The route must match exactly what the ACME CA will request. Azure Functions v2 supports custom routes via the `route` parameter on `@app.route`.

**Note**: Azure Functions strips the leading `/` from custom routes — the route parameter should be `".well-known/acme-challenge/{token}"` (without leading slash).

### Decision 3: Challenge response storage

**Choice**: Read `ACME_CHALLENGE_RESPONSE` from `os.environ` (Azure Function App Settings).

**Rationale**: App Settings are the standard mechanism for passing configuration to Azure Functions. The CLI writes the key authorization value via `update_function_app_settings()` before triggering the ACME challenge. This avoids any persistent storage and the value is overwritten on each challenge.

**Alternative considered**: Azure Blob Storage or Table Storage — rejected as over-engineered for a single ephemeral value.

### Decision 4: `update_function_app_settings` implementation

**Choice**: Use `azure.mgmt.web.WebSiteManagementClient.web_apps.update_application_settings()` to update App Settings.

**Rationale**: This is the standard ARM API for updating Azure Function App Settings. The `azure-mgmt-web` SDK is already declared as a dependency. The method accepts a `StringDictionary` object with the settings to merge.

**Security**: The key authorization value must not appear in any log output. The method logs only the function app name and setting key names, never values.

### Decision 5: Linter rule suppressions

**Choice**: No linter rules will be disabled.

**Rationale**: The implementation is straightforward and does not require any suppression.

## Risks / Trade-offs

- [Risk] Azure Function App Settings update has eventual consistency — there may be a brief delay before the new value is visible to the Function → Mitigation: The CLI already waits for the ACME CA to validate (polling loop), so a few seconds of propagation delay is acceptable. The `answer_challenge()` call is made after `update_function_app_settings()`.
- [Risk] `ACME_CHALLENGE_RESPONSE` contains the key authorization for the most recent challenge only — concurrent challenges for multiple domains would overwrite each other → Mitigation: The current design processes one domain at a time (batch parallelism is deferred to `issue-flow-batch`). This is an accepted limitation for Phase 1.
- [Risk] Azure Function cold start latency may cause the first ACME CA validation request to time out → Mitigation: The ACME CA retries validation; the polling loop in `poll_until_valid()` provides up to 60 seconds for the Function to warm up.
- [Risk] `azure-function/requirements.txt` must be kept in sync with the `azure-functions` package version used → Mitigation: Pin to a specific version in `requirements.txt` and document the version in this design.

## Migration Plan

1. Create `azure-function/` directory with `function_app.py`, `host.json`, `requirements.txt`
2. Add `update_function_app_settings()` to `AzureGatewayClient`
3. Add unit tests for both
4. No migration needed — purely additive change
5. Deployment of the Azure Function is a manual step outside this change's scope
