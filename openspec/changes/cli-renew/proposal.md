## Why

The `renew` command is the next Phase 1-C CLI command required to complete the core MVP. Without it, operators cannot automate certificate renewal — they must manually re-issue every certificate regardless of its remaining validity. The `cli-issue` orchestration layer and all its dependencies (`azure-gateway-client`, `acme-client`, `cert-converter`) are now complete, making this the right time to implement `renew`.

## What Changes

- Implement `run_renew()` in a new `src/az_acme_tool/renew_command.py` module.
- Wire the existing `renew` Click stub in `cli.py` to call `run_renew()` (replacing the current `raise NotImplementedError`).
- For each domain target, query the current certificate expiry via `AzureGatewayClient.get_listener_certificate_info()` and `cert_converter.cert_expiry()`.
- Skip domains whose certificate has more than `--days` (default 30) days remaining, unless `--force` is set.
- Reuse `_issue_single_domain` from `issue_command.py` (or its equivalent) to perform the actual renewal for qualifying domains.
- Add `--gateway` and `--domain` filter flags to `renew` (consistent with `issue`).
- Emit per-domain skip/renew decisions to stdout and a final summary line.

## Capabilities

### New Capabilities

- `cli-renew`: The `renew` command — queries certificate expiry from Azure Application Gateway listeners and conditionally re-issues certificates that are within the renewal threshold.

### Modified Capabilities

- `cli-issue`: The `renew` command reuses `_resolve_targets` and `_issue_single_domain` from `issue_command.py`. These helpers are not changing their signatures, but `_issue_single_domain` must be importable from `renew_command.py`. No spec-level requirement changes.

## Impact

- New file: `src/az_acme_tool/renew_command.py`
- New file: `tests/test_renew_command.py`
- Modified: `src/az_acme_tool/cli.py` — `renew` command stub wired to `run_renew()`
- Dependencies used: `azure-gateway-client` (`get_listener_certificate_info`), `cert-converter` (`cert_expiry`), `issue_command` (`_resolve_targets`, `_issue_single_domain`)
- No new runtime dependencies required.
