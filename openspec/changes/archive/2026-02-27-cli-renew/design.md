## Context

The `renew` command stub already exists in `cli.py` but raises `NotImplementedError`. All its dependencies are complete:
- `AzureGatewayClient.list_certificates()` and `get_certificate_expiry()` are available in `azure_gateway.py`.
- `cert_expiry()` is available in `cert_converter.py`.
- `_resolve_targets()` and `_issue_single_domain()` are available in `issue_command.py`.

The `renew` command must query each domain's current certificate expiry from Azure, compare it against a configurable threshold, and only re-issue certificates that are within the renewal window.

## Goals / Non-Goals

**Goals:**
- Implement `run_renew()` in `src/az_acme_tool/renew_command.py`.
- Wire the `renew` Click stub in `cli.py` to call `run_renew()`.
- Support `--days <n>` (default 30) threshold and `--force` flag.
- Support `--gateway` and `--domain` filters (consistent with `issue`).
- Emit per-domain skip/renew decisions and a final summary.
- ≥80% line coverage in `tests/test_renew_command.py`.
- Pass `ruff`, `mypy --strict`, and `black --line-length 100`.

**Non-Goals:**
- Implementing the actual 14-step ACME pipeline (that is `issue-flow-core`).
- Batch/parallel processing (that is `issue-flow-batch`).
- Modifying `_issue_single_domain` — it remains a stub that raises `NotImplementedError`.

## Decisions

### Decision 1: New module `renew_command.py` (not extending `issue_command.py`)

**Rationale**: The `renew` command has distinct orchestration logic (expiry check + conditional skip) that does not belong in `issue_command.py`. Keeping them separate follows the existing pattern (`init_command.py`, `issue_command.py`, `status_command.py`).

**Alternative considered**: Adding `run_renew()` directly to `issue_command.py`. Rejected because it would mix two distinct command concerns in one module.

### Decision 2: Expiry lookup via `AzureGatewayClient.list_certificates()`

**Rationale**: `list_certificates()` returns all certs with their expiry in one API call. For each domain target, we derive the expected certificate name using the `{domain_sanitized}-cert` naming convention (dots replaced with hyphens), then look up its expiry from the list. This avoids one API call per domain.

**Alternative considered**: Calling `get_certificate_expiry(cert_name)` per domain. Acceptable but less efficient for multi-domain gateways.

### Decision 3: Certificate name derivation

The naming convention `{domain_sanitized}-cert` (dots → hyphens) is established in the ROADMAP and `azure-gateway-client` spec. `renew_command.py` will implement a `_domain_to_cert_name(domain: str) -> str` helper that applies this transformation.

### Decision 4: Graceful handling of missing certificates

If a domain's expected certificate is not found on the gateway (e.g., never issued), the `renew` command SHALL log a warning and skip that domain rather than failing the entire batch. This is consistent with the "failure isolation" principle from `issue-flow-batch`.

### Decision 5: Reuse `_resolve_targets` from `issue_command`

`_resolve_targets` is a pure function with no side effects. It will be imported directly from `issue_command` to avoid duplication. `_issue_single_domain` is also imported to perform the actual renewal.

### Decision 6: `--gateway` and `--domain` flags on `renew`

The ROADMAP does not explicitly list these flags for `renew`, but they are consistent with `issue` and necessary for targeted operations. They are added to the Click stub in `cli.py`.

## Risks / Trade-offs

- [Risk] `_issue_single_domain` is still a stub (raises `NotImplementedError`). → Mitigation: The `renew` command will catch `NotImplementedError` and report it as a failure in the summary, consistent with how `issue` handles errors. Tests mock `_issue_single_domain` to verify the renewal path.
- [Risk] Certificate name derivation may not match the actual cert name if the cert was uploaded with a different naming convention. → Mitigation: This is a known limitation documented in the ROADMAP. The `renew` command will log a warning and skip if the cert is not found.
- [Risk] `list_certificates()` makes one Azure API call per gateway. For large deployments this is acceptable; batching is deferred to `issue-flow-batch`.

## Migration Plan

1. Create `src/az_acme_tool/renew_command.py`.
2. Create `tests/test_renew_command.py`.
3. Update `cli.py` `renew` stub to call `run_renew()` and add `--gateway`/`--domain` flags.
4. Run `ruff`, `mypy --strict`, `black`, and `pytest --cov`.

## Open Questions

None — all design decisions are resolved.
