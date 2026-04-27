## Why

The `issue` command currently has a `_issue_single_domain()` stub that raises `NotImplementedError`. All prerequisite components are now complete (`AcmeClient`, `AzureGatewayClient`, `CertConverter`, `azure-function-responder`). This change wires them together into the complete 14-step ACME HTTP-01 certificate issuance pipeline for a single domain on a single gateway.

## What Changes

- Implement `_issue_single_domain()` in `src/az_acme_tool/issue_command.py` with the full 14-step ACME flow
- Extend the config schema (`AppConfig` / `GatewayConfig`) to include the fields required by the pipeline:
  - `acme.directory_url` — ACME CA directory URL (e.g. Let's Encrypt production or staging)
  - `acme.account_key_path` — path to the PEM-encoded ACME account private key
  - `gateway.acme_function_name` — Azure Function App name used for HTTP-01 challenge responses
- The 14 steps are:
  1. Read config + resolve target domain
  2. Create ACME order (`new_order`)
  3. Get HTTP-01 challenge (`get_http01_challenge`) → token + key_authorization
  4. Write key_authorization to Azure Function App Settings (`update_function_app_settings`)
  5. Create temporary path-based routing rule on AGW (`add_routing_rule`)
  6. Notify ACME CA (`answer_challenge`)
  7. Poll until validated (`poll_until_valid`, max 60s)
  8. Finalize order with CSR (`finalize_order`)
  9. Download certificate PEM (`download_certificate`)
  10. Convert PEM → PFX (`pem_to_pfx`, random in-memory password)
  11. Upload PFX to AGW as SSL Certificate (`upload_ssl_certificate`)
  12. Find all listeners using the old certificate name
  13. Update each listener to reference the new certificate (`update_listener_certificate`)
  14. Delete temporary routing rule (`delete_routing_rule`) — always in `finally` block
- Unit tests for the 14-step flow (all Azure/ACME calls mocked)

## Capabilities

### New Capabilities

- `issue-flow-core`: The complete 14-step ACME HTTP-01 certificate issuance pipeline for a single domain

### Modified Capabilities

- `config-schema`: Add `acme.directory_url`, `acme.account_key_path`, and `gateway.acme_function_name` fields
- `cli-issue`: Replace `_issue_single_domain()` stub with real implementation; add `upload_ssl_certificate`, `add_routing_rule`, and listener-update methods to `AzureGatewayClient`
- `azure-gateway-client`: Add `upload_ssl_certificate()`, `add_routing_rule()`, and `get_listeners_by_cert_name()` methods

## Impact

- Modified: `src/az_acme_tool/config.py` (extend `AcmeConfig`, `GatewayConfig`)
- Modified: `src/az_acme_tool/issue_command.py` (implement `_issue_single_domain`)
- Modified: `src/az_acme_tool/azure_gateway.py` (add `upload_ssl_certificate`, `add_routing_rule`, `get_listeners_by_cert_name`)
- Modified: `tests/test_config.py` (update for new required fields)
- Modified: `tests/test_azure_gateway.py` (add tests for new methods)
- Modified: `tests/test_issue_command.py` (add tests for 14-step pipeline)
- Dependencies: all existing (no new runtime dependencies)
