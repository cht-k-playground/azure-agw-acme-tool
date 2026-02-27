# az-acme-tool — Development Roadmap

This document tracks all planned OpenSpec changes for the project.
Each item maps to exactly one `/opsx:propose` → `/opsx:apply` → `/opsx:archive` cycle.

**How to use this file**:
- Pick the next `[ ]` item in the current phase.
- Run `/opsx:propose <change-name>` to begin.
- Mark `[x]` only after `/opsx:archive` completes.
- Do not start a new item while another change is `in_progress`.

**Status legend**:
- `[ ]` Not started
- `[~]` In progress (change exists under `openspec/changes/`)
- `[x]` Done (archived under `openspec/changes/archive/`)

---

## Phase 1 — Core MVP

> Goal: a fully functional CLI that can issue, renew, and inspect certificates
> on Azure Application Gateway using ACME HTTP-01 validation.

### Foundation

- [ ] `config-schema` — Define and validate the YAML configuration model
  - Pydantic v2 models for `AcmeConfig`, `AzureConfig`, `GatewayConfig`, `DomainConfig`
  - Validation rules: email format, UUID subscription ID, FQDN format, domain format
  - `cert_store` enum: `agw_direct` only (Key Vault deferred to Phase 2)
  - `auth_method` enum: `default | service_principal | managed_identity`
  - `parse_config(path)` public function + custom `ConfigError` exception class
  - Unit tests covering all validation rules (≥80% coverage)

- [ ] `logging-setup` — Structured logging and console output infrastructure
  - JSON Lines file logger → `~/.config/az-acme-tool/logs/az-acme-tool.log`
  - Rich console output with colour and progress indicators
  - Log levels: `DEBUG` (verbose), `INFO` (default), `WARNING`, `ERROR`
  - `--verbose` flag wired into the root Click group context
  - Unit tests for log record structure

### CLI Commands

- [ ] `cli-init` — Implement the `init` command
  - Generate RSA-2048 ACME account private key, write to `account_key_path` with mode `0o600`
  - Register account with the ACME CA using `acme` + `josepy`
  - `--config-template` flag: print a ready-to-edit YAML template to stdout
  - Console output matching the spec (key path, account URL, next-steps)
  - Unit tests with mocked ACME CA and filesystem

- [ ] `cli-issue` — Implement the `issue` command (orchestration only)
  - Read and validate config; filter by `--gateway` / `--domain` when provided
  - Dry-run mode: log all planned steps without executing Azure or ACME calls
  - Progress output matching the spec (per-domain step list + summary)
  - Delegates to `AcmeClient` and `AzureGatewayClient` (stubs acceptable at this stage)
  - Unit tests for filtering logic and dry-run behaviour

- [ ] `cli-renew` — Implement the `renew` command
  - Query each AGW listener's certificate expiry via Azure SDK
  - Skip domains whose certificate expires beyond `--days` threshold (default 30)
  - `--force` flag bypasses the threshold check
  - Re-uses `issue` orchestration for the actual renewal
  - Unit tests with mocked expiry dates

- [ ] `cli-status` — Implement the `status` command
  - Fetch SSL certificate metadata from each AGW listener via Azure SDK
  - Compute days-to-expiry; flag certificates expiring within 30 days
  - Output formats: `table` (Rich), `json`, `yaml`
  - Unit tests for expiry calculation and all three output formats

- [ ] `cli-cleanup` — Implement the `cleanup` command
  - List all routing rules whose name matches the ACME challenge naming convention
  - `--all` flag removes every matched rule; default shows a confirmation prompt
  - Unit tests with mocked Azure SDK responses

### Azure Integration

- [ ] `azure-gateway-client` — Azure SDK wrapper for Application Gateway operations
  - `AzureGatewayClient` class initialised with `DefaultAzureCredential` (or SP/MI override)
  - Methods: `get_gateway()`, `upload_ssl_certificate()`, `add_routing_rule()`, `delete_routing_rule()`, `get_listener_certificate_info()`
  - `HttpResponseError` handling on every SDK call; `AzureError` custom exception hierarchy
  - Exponential back-off (max 3 attempts) on 429 / 5xx responses
  - Unit tests with `pytest-mock` patching `azure.mgmt.network`

### ACME Integration

- [ ] `acme-client` — ACME HTTP-01 challenge client
  - `AcmeClient` class: `new_order()`, `get_http01_challenge()`, `answer_challenge()`, `finalize_order()`, `download_certificate()`
  - Retry with exponential back-off (max 3 attempts, base delay 10 s) on transient errors
  - `AcmeError` custom exception class
  - Unit tests with mocked ACME CA responses

### Certificate Handling

- [ ] `cert-converter` — PEM → PFX conversion and fingerprint utilities
  - `pem_to_pfx(cert_pem, key_pem, password)` → `bytes`
  - `cert_fingerprint(cert_pem)` → SHA-256 hex string
  - `cert_expiry(cert_pem)` → `datetime`
  - Private key material never written to disk; all operations in-memory
  - Unit tests using self-signed test certificates generated with `cryptography`

### End-to-End Wiring

- [ ] `issue-flow-integration` — Wire all components into the full issue flow
  - Connect `AcmeClient` ↔ `AzureGatewayClient` ↔ `CertConverter` inside `issue` orchestration
  - Implement the 14-step HTTP-01 flow from the sequence diagram in the requirements
  - Listener auto-discovery by `host_names` / SNI (UC-04: shared-cert listeners)
  - Batch processing: failure on one domain must not abort remaining domains
  - Integration tests using Let's Encrypt Staging + mocked AGW SDK calls

---

## Phase 2 — Enterprise Extensions

> Goal: Key Vault integration, automated scheduling, and observability.
> Do not start Phase 2 items until all Phase 1 items are `[x]`.

- [ ] `keyvault-cert-store` — Azure Key Vault as an alternative certificate store
  - `cert_store: key_vault` support in config schema
  - `key_vault_name` + `key_vault_secret_name` fields per domain
  - `KeyVaultCertStore` class using `azure-keyvault-certificates`
  - Unit tests with mocked Key Vault SDK

- [ ] `renewal-scheduler` — Scheduled automatic renewal
  - `schedule` sub-command (or cron-compatible design)
  - Configurable `renew_before_days` in config YAML
  - Idempotent: safe to run on a schedule without side-effects
  - Unit tests for scheduling logic

- [ ] `webhook-notifications` — Post-operation webhook notifications
  - Optional `notifications` section in config YAML
  - Targets: generic HTTP webhook (Teams / Slack compatible)
  - Events: `certificate_issued`, `certificate_renewed`, `certificate_failed`
  - Unit tests with mocked HTTP client

- [ ] `revoke-command` — Implement the `revoke` command
  - Revoke a certificate via the ACME CA
  - Remove the corresponding SSL certificate object from AGW
  - Confirmation prompt before any destructive action
  - Unit tests with mocked ACME + Azure SDK

---

## Cross-Cutting (applies to all phases)

These are not standalone changes but constraints every change must satisfy:

- All public functions and methods must carry full type annotations.
- Every change must keep `mypy --strict` and `ruff` clean; no suppressions without justification in `design.md`.
- Line coverage across `src/az_acme_tool/` must remain **≥ 80 %** after each change.
- No secrets, private keys, or credentials may appear in committed code or test fixtures.
