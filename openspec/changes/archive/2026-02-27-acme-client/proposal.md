## Why

The CLI tool needs to request and renew TLS certificates via the ACME protocol (Let's Encrypt). Without an ACME client module, the `issue` and `renew` commands cannot perform HTTP-01 challenge validation or obtain signed certificates from a CA.

## What Changes

- Introduce `AcmeClient` class in `src/az_acme_tool/acme_client.py` that wraps the `acme` + `josepy` libraries
- Implement account registration (with key reuse if key file already exists)
- Implement the full HTTP-01 challenge lifecycle: new order → get challenge → answer challenge → poll → finalize → download certificate
- Define `AcmeError` custom exception class for all ACME-related failures
- Add `acme>=2.7.0` and `josepy` as runtime dependencies in `pyproject.toml`
- Provide unit tests with mocked ACME CA responses (no real CA calls)

## Capabilities

### New Capabilities

- `acme-client`: ACME HTTP-01 challenge client — account registration, order lifecycle, challenge answering, certificate download

### Modified Capabilities

- `azure-gateway-client`: The challenge token storage step requires `AzureGatewayClient.update_function_app_settings()` (already implemented); no spec-level requirement change, only integration wiring is new.

## Impact

- New module: `src/az_acme_tool/acme_client.py`
- New test file: `tests/test_acme_client.py`
- `pyproject.toml` gains `acme>=2.7.0` and `josepy>=1.14.0` in `[project.dependencies]`
- `cli-issue` (future change) will import and use `AcmeClient` directly; no breaking changes to existing modules
