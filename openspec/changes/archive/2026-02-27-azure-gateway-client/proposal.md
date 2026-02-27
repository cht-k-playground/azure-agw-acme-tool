## Why

The `issue` and `renew` CLI commands require a typed client that can read certificate state from Azure Application Gateway and deploy updated TLS certificates back to gateway listeners. Without this client layer, no automated certificate lifecycle operations are possible. This change implements the `AzureGatewayClient` as the first of three foundational clients for Phase 1 (change 1-B in the implementation plan).

## What Changes

- New module `src/az_acme_tool/azure_gateway.py` containing `AzureGatewayClient` and `AzureGatewayError`.
- `AzureGatewayClient` wraps the Azure SDK (`azure-mgmt-network`) to provide three operations:
  - `list_certificates()` → returns all SSL certificates attached to a gateway, with name and expiry.
  - `get_certificate_expiry(cert_name)` → returns the expiry `datetime` for a named certificate.
  - `update_listener_certificate(listener_name, cert_name)` → updates an HTTP listener to reference a new certificate object (used by the issue-flow-core coordinator in step 1-E).
- Client is instantiated with `(subscription_id, resource_group, gateway_name)` plus a credential object (injected by the CLI layer to support all three `AuthMethod` variants).
- All Azure SDK `HttpResponseError` exceptions are caught and re-raised as `AzureGatewayError`.
- New runtime dependency: `azure-mgmt-network` (and `azure-identity` for credential resolution).

## Capabilities

### New Capabilities
- `azure-gateway-client`: Typed Python client for reading SSL certificate state from and writing updated TLS certificates to an Azure Application Gateway; exposes `list_certificates()`, `get_certificate_expiry()`, and `update_listener_certificate()`.

### Modified Capabilities
<!-- No existing spec-level requirements change -->

## Impact

- **New file**: `src/az_acme_tool/azure_gateway.py`
- **New tests**: `tests/test_azure_gateway.py` (mocked Azure SDK)
- **`pyproject.toml`**: add `azure-mgmt-network>=28.0.0` and `azure-identity>=1.16.0` to `[project.dependencies]`
- **No changes** to `cli.py`, `config.py`, or `logging.py` in this change
- Downstream changes (`acme-client`, `cert-converter`, `issue-flow-core`) will import `AzureGatewayClient` and `AzureGatewayError` from this module
