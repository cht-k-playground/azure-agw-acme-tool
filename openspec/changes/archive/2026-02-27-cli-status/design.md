## Context

The `status` command queries every configured Application Gateway for its SSL certificate metadata and renders it in a chosen format. It builds on the real `AzureGatewayClient` interface (already implemented): `list_certificates()` returns a list of `{"name": str, "expiry": datetime | None}` dicts per gateway.

The ROADMAP describes using `get_listener_certificate_info()` + `cert_expiry()`. However, the implemented `AzureGatewayClient` exposes `list_certificates()` (enumerates all certs on the gateway) instead. The `status` command uses `list_certificates()` to enumerate certificates — this is semantically equivalent and more efficient (one API call per gateway vs. one per listener).

Constraints: `mypy --strict`, `ruff`, `black --line-length 100`, ≥80% coverage, structured exceptions.

## Goals / Non-Goals

**Goals:**
- Iterate all configured gateways; for each, call `AzureGatewayClient.list_certificates()`
- Classify each certificate: `valid` (>30 days), `expiring_soon` (≤30 days, >0), `expired` (≤0)
- Render in `table` (Rich), `json`, or `yaml` format per `--output` flag
- JSON output is machine-readable with the schema: `gateway`, `resource_group`, `name`, `expiry_date` (ISO 8601), `days_remaining`, `status`

**Non-Goals:**
- Per-listener filtering (Phase 2)
- Gateway/domain filter flags (the `status` command shows all configured gateways)

## Decisions

### D1: Use `list_certificates()` not `get_listener_certificate_info()`

The implemented `AzureGatewayClient` exposes `list_certificates()`. This is the correct interface to use. The ROADMAP's reference to `get_listener_certificate_info()` reflects the original design intent; the actual implementation chose a simpler certificate-enumeration model.

### D2: Status classification thresholds are hardcoded at 30 days

The ROADMAP defines: >30 days = valid, ≤30 and >0 = expiring soon, ≤0 = expired. These are fixed in Phase 1; `cli-renew` uses `--days` for its own threshold independently.

### D3: `None` expiry dates are shown as "N/A" in table output, omitted from JSON

Key Vault-referenced certificates have no public_cert_data. Their expiry is `None`. Table shows "N/A"; JSON omits `expiry_date` / `days_remaining` (sets to `null`).

### D4: `AzureGatewayClient` instantiated with `DefaultAzureCredential`

For Phase 1, authentication always uses `DefaultAzureCredential`. The `auth_method` config field is stored but only `default` is implemented in Phase 1.

### D5: Module-level `_classify_status()` helper for testability

Days-remaining → status mapping is a pure function, easily unit-tested in isolation.

## Risks / Trade-offs

- `DefaultAzureCredential` requires Azure credentials in the environment; in CI tests, `AzureGatewayClient` is always mocked.
- Rich table output goes to stdout; for non-TTY environments the table renders without colours (Rich's default behaviour).
