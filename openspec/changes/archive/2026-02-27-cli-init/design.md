## Context

The `init` command is the entry point for new users of `az-acme-tool`. It has two distinct operating modes selected by the `--config-template` flag:

1. **Template mode** (`--config-template`): Prints a YAML skeleton to stdout. Zero side effects — no file writes, no network calls.
2. **Registration mode** (default): Generates an RSA-2048 account key, persists it to disk, registers with the ACME CA, and prints confirmation.

The existing `cli.py` stub delegates to nothing — this change wires it to a new `init_command.py` module. The `AcmeClient` class (already implemented) provides `register_account()`.

Constraints (AGENTS.md):
- `mypy --strict` must pass
- `ruff` + `black --line-length 100` must be clean
- ≥80% line coverage
- Key files must be created with `0o600` permissions
- Private key material must never be logged

## Goals / Non-Goals

**Goals:**
- Implement `--config-template` path: print YAML template, exit 0
- Implement default path: generate RSA-2048 key → write with `0o600` → register ACME account → print account URL
- Guard: if key file already exists, prompt for overwrite confirmation
- Keep `cli.py` thin — all logic in `init_command.py`

**Non-Goals:**
- Creating the config directory or writing a `config.yaml` (user must do this manually using the template)
- Validating Azure credentials at init time
- Supporting EC keys (RSA-2048 only for Phase 1)

## Decisions

### D1: Separate `init_command.py` module

`cli.py` should remain a thin dispatcher. Business logic in a separate module is testable without invoking Click machinery. The module exposes `run_init(config_path: str, config_template: bool, verbose: bool) -> None`.

### D2: Key generation via `cryptography`, not `josepy`

`josepy.JWKRSA` wraps `cryptography`'s RSA key. We generate the key with `cryptography.hazmat.primitives.asymmetric.rsa.generate_private_key()`, serialize to PEM with `serialization.NoEncryption()`, write to disk, then load it back as `JWKRSA` for `AcmeClient`. This keeps key generation separate from ACME concerns and is straightforward to test.

### D3: `account_key_path` derived from config or hardcoded default

The ROADMAP specifies `account_key_path` is read from config. However, the `config.py` `AppConfig` model does not currently include an `account_key_path` field — and `init` runs before a config file necessarily exists (it may be the first run). Resolution: use a fixed default path `~/.config/az-acme-tool/account.key`, documented in the template. This is consistent with the ACME CA registration pattern where the key path is stable per installation.

**Note on `--config-template`**: The template path does not parse the config file at all — it prints and exits immediately.

### D4: Overwrite confirmation uses `click.confirm()`

`click.confirm()` integrates naturally with Click's testing framework (`CliRunner`), allowing `input="n\n"` in tests to simulate rejection without mocking `input()`.

### D5: `AcmeClient` ACME directory URL comes from a fixed Let's Encrypt production URL

For Phase 1 the ACME directory URL is `https://acme-v02.api.letsencrypt.org/directory` (hardcoded). Staging support is deferred to a future change. This default is printed in the config template as a comment.

## Risks / Trade-offs

- **`init` called without a config file**: In template mode this is expected and fully supported. In registration mode we do not need the config (only the fixed key path). Risk: low.
- **Key file permissions on Windows**: `os.chmod(path, 0o600)` is a no-op on Windows. This is acceptable — the tool targets Linux/macOS server environments.
- **ACME CA unavailable at init time**: `AcmeClient.register_account()` raises `AcmeError`. The `init` command catches this and exits with a non-zero code and clear error message.

## Migration Plan

Replaces the `NotImplementedError` stub in `cli.py:init`. No data migration needed. Existing users (none yet) unaffected.
