## Why

The `status` command stub in `cli.py` raises `NotImplementedError`. Operators need a way to inspect the current certificate state across all gateways and listeners to know which certificates are valid, expiring soon, or already expired — before running `renew`. This change implements the `status` command with Rich table, JSON, and YAML output formats.

## What Changes

- New module `src/az_acme_tool/status_command.py` with `run_status()` and `StatusError` exception
- `run_status()` loads config, calls `AzureGatewayClient.get_listener_certificate_info()` per listener, uses `cert_expiry()` to compute days remaining, classifies each entry as `valid` / `expiring_soon` / `expired`, and renders output in the requested format
- Update `cli.py` `status` command to delegate to `run_status()`
- New test file `tests/test_status_command.py` covering all acceptance criteria

## Capabilities

### New Capabilities

- `cli-status`: The `status` CLI command — certificate status inspection with Rich table, JSON, and YAML output

### Modified Capabilities

_(none)_

## Impact

- **Modified**: `src/az_acme_tool/cli.py`
- **New file**: `src/az_acme_tool/status_command.py`
- **New file**: `tests/test_status_command.py`
- **Dependencies**: `azure-gateway-client` ✅, `cert-converter` ✅, `rich`, `pyyaml` — all in `pyproject.toml`
