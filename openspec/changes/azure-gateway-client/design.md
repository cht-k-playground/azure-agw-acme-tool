## Context

The project needs to automate TLS certificate issuance and renewal for Azure Application Gateway listeners. Currently, `cli.py` stubs `issue` and `renew` commands but has no underlying Azure SDK integration. This change introduces `AzureGatewayClient` — a thin, typed wrapper around `azure-mgmt-network` — as the first building block for the Phase 1 certificate lifecycle flow.

The existing codebase has:
- `config.py` — Pydantic models with `AzureConfig` (subscription_id, resource_group, auth_method) and `GatewayConfig` (gateway name + domain list)
- `AuthMethod` enum — `default`, `service_principal`, `managed_identity`
- No Azure SDK dependency yet

## Goals / Non-Goals

**Goals:**
- Provide a single, importable `AzureGatewayClient` class in `src/az_acme_tool/azure_gateway.py`
- Expose three operations: list certificates, get a certificate's expiry, update a listener's certificate
- Translate all Azure SDK `HttpResponseError` into a typed `AzureGatewayError`
- Add `azure-mgmt-network` and `azure-identity` to `pyproject.toml` dependencies
- Achieve ≥80% line coverage with `pytest-mock`-based tests (no real Azure calls)
- Pass `ruff`, `mypy --strict`, and `black --line-length 100`

**Non-Goals:**
- Certificate upload / PFX import (handled by `cert-converter` change)
- ACME challenge routing rule management (handled by `issue-flow-core`)
- Key Vault certificate store (Phase 2)
- Credential construction from `AuthMethod` (handled by the CLI layer / `issue-flow-core` coordinator; this client accepts an injected `TokenCredential`)

## Decisions

### D1 — Injected credential, not constructed internally

**Decision:** `AzureGatewayClient.__init__` accepts an `azure.core.credentials.TokenCredential` parameter rather than constructing credentials from `AuthMethod` internally.

**Rationale:** Keeps `AzureGatewayClient` testable without monkey-patching the Azure identity library. The CLI layer (or `issue-flow-core` coordinator) resolves the credential from `AuthMethod` once and passes it in. This mirrors the pattern used by all Azure SDK client classes themselves.

**Alternative considered:** Accept `AuthMethod` and construct `DefaultAzureCredential` / `ClientSecretCredential` / `ManagedIdentityCredential` inside the constructor. Rejected because it tightly couples credential resolution to the gateway client, making unit tests require environment variables or mocked identity calls.

---

### D2 — Module layout: single file, no sub-package

**Decision:** All code lives in `src/az_acme_tool/azure_gateway.py` — one public class, one exception class, one private helper.

**Rationale:** The surface area is small (three methods). A sub-package would add navigation overhead with no benefit at this stage. The file can be split later if it grows.

---

### D3 — Certificate expiry via `ssl_certificates` list, not Key Vault reference

**Decision:** `list_certificates()` and `get_certificate_expiry()` read from `ApplicationGateway.ssl_certificates`, using the `expiration_date` field on each `ApplicationGatewaySslCertificate`.

**Rationale:** The `cert_store` for Phase 1 is `agw_direct` (certificates uploaded directly to the gateway, not via Key Vault). The `expiration_date` field is populated by Azure when a PFX is uploaded directly. Key Vault–referenced certificates expose expiry through a different code path; that is Phase 2.

**Alternative considered:** Always fetching Key Vault secrets to read expiry. Rejected as out of scope for Phase 1 and requiring additional `azure-keyvault-secrets` dependency.

---

### D4 — `update_listener_certificate` targets the listener by name

**Decision:** `update_listener_certificate(listener_name: str, cert_name: str)` locates the named HTTP listener inside the gateway resource and sets its `ssl_certificate` sub-resource reference, then calls `begin_create_or_update` and awaits the poller.

**Rationale:** Application Gateway listener names are stable identifiers in the gateway config and are already exposed in `GatewayConfig`. Matching by name avoids exposing ARM resource IDs to callers.

**Risk:** If the gateway has no listener with `listener_name`, the method raises `AzureGatewayError` with a descriptive message rather than silently creating a new listener.

---

### D5 — Synchronous SDK calls only

**Decision:** Use the synchronous `azure-mgmt-network` client (`NetworkManagementClient`), not the async variant.

**Rationale:** The CLI is a command-line tool; async I/O provides no meaningful throughput benefit for serial certificate operations. Synchronous code is simpler to test and debug.

## Risks / Trade-offs

- **`expiration_date` may be `None`** for certificates referenced from Key Vault (not populated by Azure). `get_certificate_expiry` will raise `AzureGatewayError` in that case with a clear message. Mitigation: document the limitation in the docstring and error message.
- **Long-running `begin_create_or_update` poller** — updating a listener certificate triggers a gateway reconfiguration which can take 1–3 minutes. The synchronous `.result()` call will block the CLI process. Mitigation: acceptable for Phase 1; progress logging via structured logger will indicate the wait. A timeout of 10 minutes is enforced by passing `polling_interval` to the poller.
- **`azure-mgmt-network` version churn** — the SDK has frequent minor versions. Pinning `>=28.0.0` (current stable) provides a wide compatibility window while avoiding older APIs where `expiration_date` field names differed.

## Migration Plan

1. Add `azure-mgmt-network>=28.0.0` and `azure-identity>=1.16.0` to `pyproject.toml` `[project.dependencies]`.
2. Run `uv sync` to install.
3. Ship `src/az_acme_tool/azure_gateway.py` and `tests/test_azure_gateway.py`.
4. No CLI changes in this change; the module is imported by downstream changes.
5. Rollback: remove the two `pyproject.toml` entries and delete the new files.

## Open Questions

None — all design decisions resolved based on confirmed design decisions provided by the team.
