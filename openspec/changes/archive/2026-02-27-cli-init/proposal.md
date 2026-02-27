## Why

The `init` command stub in `cli.py` currently raises `NotImplementedError`. Users need a one-time setup command that generates an ACME account key, registers the account with the CA, and optionally prints a config file template — without any of these being wired up today. This change completes the `init` command so the tool is usable end-to-end for first-time setup.

## What Changes

- Implement the `init` Click command in `src/az_acme_tool/cli.py`, replacing the `NotImplementedError` stub
- New helper module `src/az_acme_tool/init_command.py` containing the `run_init()` orchestration function, keeping `cli.py` thin
- `--config-template` path: print a YAML template to stdout with placeholder values for all required fields; exit 0 without any Azure or ACME calls
- Default path: generate RSA-2048 ACME account key → write to `account_key_path` (from config or default `~/.config/az-acme-tool/account.key`) with `0o600` permissions → call `AcmeClient.register_account()` → print key path + account URL + next-step guidance
- If `account_key_path` already exists, prompt user for confirmation before overwriting
- New test file `tests/test_init_command.py` covering all acceptance criteria

## Capabilities

### New Capabilities

- `cli-init`: The `init` CLI command — key generation, ACME account registration, and config template printing

### Modified Capabilities

- `cli-root-options`: The `init` command implementation within `cli.py` changes from stub to delegating to `run_init()` — no spec-level requirement changes, only implementation

## Impact

- **Modified**: `src/az_acme_tool/cli.py` — replace `init` stub body
- **New file**: `src/az_acme_tool/init_command.py`
- **New file**: `tests/test_init_command.py`
- **Dependencies**: `acme`, `josepy`, `cryptography`, `click` — all already in `pyproject.toml`
- **No new runtime dependencies**
