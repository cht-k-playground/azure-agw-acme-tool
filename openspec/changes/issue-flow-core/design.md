## Context

The `issue` command's `_issue_single_domain()` function currently raises `NotImplementedError`. All prerequisite components are now complete:
- `AcmeClient` — ACME v2 HTTP-01 challenge client (`acme_client.py`)
- `AzureGatewayClient` — Azure Application Gateway operations (`azure_gateway.py`)
- `CertConverter` — PEM → PFX conversion and CSR generation (`cert_converter.py`)
- `azure-function-responder` — Azure Function serving challenge responses

The config schema (`AppConfig`) is missing three fields required by the pipeline:
- `acme.directory_url` — ACME CA directory URL
- `acme.account_key_path` — path to the PEM-encoded ACME account private key
- `gateway.acme_function_name` — Azure Function App name for HTTP-01 challenge responses

The `AzureGatewayClient` is also missing three methods required by the pipeline:
- `upload_ssl_certificate(cert_name, pfx_data, password)` — upload PFX to AGW
- `add_routing_rule(rule_name, domain, backend_fqdn)` — create temporary path-based rule
- `get_listeners_by_cert_name(cert_name)` — find all listeners using a given certificate

**Constraints:**
- Python 3.11+, `mypy --strict`, `ruff`, `black --line-length 100`
- PFX password must never be logged or written to disk
- Temporary routing rule must be deleted in a `finally` block even if steps 7–13 fail
- All Azure SDK calls must handle `HttpResponseError` explicitly
- ACME operations must implement exponential back-off retry (max 3 attempts)

## Goals / Non-Goals

**Goals:**
- Extend `AppConfig` / `AcmeConfig` / `GatewayConfig` with the three new required fields
- Add `upload_ssl_certificate()`, `add_routing_rule()`, and `get_listeners_by_cert_name()` to `AzureGatewayClient`
- Implement `_issue_single_domain()` with the complete 14-step ACME pipeline
- Unit tests for all new code (all Azure/ACME calls mocked)

**Non-Goals:**
- Batch/parallel processing of multiple domains (deferred to `issue-flow-batch`)
- Key Vault certificate storage (deferred to Phase 2)

## Decisions

### Decision 1: Config schema extension approach

**Choice**: Add `directory_url: str` and `account_key_path: Path` to `AcmeConfig`; add `acme_function_name: str` to `GatewayConfig`.

**Rationale**: These are configuration values (not operational flags), so they belong in the YAML config per the CLI Design Constraints in AGENTS.md. Making them required fields ensures the pipeline cannot run without them.

**Alternative considered**: Optional fields with defaults — rejected because there is no sensible default for a CA directory URL or account key path.

### Decision 2: PFX password generation

**Choice**: Generate a random 32-character password using `secrets.token_urlsafe(32)` in `_issue_single_domain()`. The password is passed to `pem_to_pfx()` and `upload_ssl_certificate()` and then discarded. It is never logged or written to disk.

**Rationale**: Azure Application Gateway requires a password for PFX upload but does not need it after upload. A random per-issuance password provides defense-in-depth.

### Decision 3: Temporary routing rule cleanup

**Choice**: Wrap steps 5–13 in a `try/finally` block. The `finally` clause calls `delete_routing_rule(rule_name)` unconditionally.

**Rationale**: The ROADMAP spec (step 14) explicitly requires the temporary rule to be deleted even if earlier steps fail. A `finally` block is the idiomatic Python mechanism for guaranteed cleanup.

### Decision 4: SSL certificate naming

**Choice**: `{domain_sanitized}-cert` where `domain_sanitized` replaces `.` with `-`.

**Rationale**: Matches the ROADMAP spec: `www.example.com` → `www-example-com-cert`.

### Decision 5: Temporary routing rule naming

**Choice**: `acme-challenge-{domain_sanitized}-{unix_timestamp}` where `unix_timestamp` is `int(time.time())`.

**Rationale**: Matches the ROADMAP spec naming convention. The timestamp suffix ensures uniqueness across concurrent runs.

### Decision 6: `add_routing_rule` implementation

**Choice**: Add a new URL path map entry to the AGW with a path rule for `/.well-known/acme-challenge/*` pointing to a new backend pool that targets `backend_fqdn`. Backend HTTP settings use HTTPS port 443 with `pickHostNameFromBackendAddress: true`. The function app FQDN is `{acme_function_name}.azurewebsites.net`.

**Rationale**: The ROADMAP spec defines the exact path pattern and backend settings.

### Decision 7: Linter rule suppressions

**Choice**: No linter rules will be disabled.

**Rationale**: The implementation is straightforward and does not require any suppression.

## Risks / Trade-offs

- [Risk] `add_routing_rule` creates a new URL path map + backend pool + HTTP settings on the AGW, which may conflict with existing resources if names collide → Mitigation: Use the timestamp-suffixed rule name; the backend pool and HTTP settings use the same name as the rule for uniqueness.
- [Risk] The AGW `begin_create_or_update` call in `add_routing_rule` may time out for large gateway configurations → Mitigation: Use a 600-second timeout (consistent with other gateway operations).
- [Risk] If `delete_routing_rule` fails in the `finally` block, the temporary rule is left orphaned → Mitigation: Log the error clearly; the `cleanup` command can remove it later.
- [Risk] `get_listeners_by_cert_name` may return an empty list if no listener uses the old cert name (e.g., first issuance) → Mitigation: If no listeners are found, skip step 13 (no update needed); log a warning.

## Migration Plan

1. Extend `config.py` with new fields
2. Add `upload_ssl_certificate`, `add_routing_rule`, `get_listeners_by_cert_name` to `AzureGatewayClient`
3. Implement `_issue_single_domain()` in `issue_command.py`
4. Update tests
5. No migration needed — purely additive change (existing config files will fail validation until the new required fields are added, which is the intended behavior)
