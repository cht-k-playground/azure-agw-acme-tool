## Why

The tool currently has no structured logging infrastructure, making it impossible to diagnose failures or audit certificate operations. Establishing a logging foundation now enables all future commands to emit consistent, machine-readable records and rich console feedback from the start.

## What Changes

- Introduce `src/az_acme_tool/logging.py` exposing a `setup_logging(verbose: bool) -> None` function.
- Configure a JSON Lines file handler writing to `~/.config/az-acme-tool/logs/az-acme-tool.log` (fields: `timestamp`, `level`, `message`).
- Configure a Rich console handler (stderr) for human-readable output with colour support.
- Wire `setup_logging()` into the `main` Click group in `cli.py` so all subcommands inherit logging configuration.
- `--verbose` flag (already present on `main`) sets the root log level to `DEBUG`; default is `INFO`.
- Add `rich` to `[project.dependencies]` in `pyproject.toml`.
- Add unit tests in `tests/test_logging.py` covering JSON Lines structure and verbose/non-verbose behaviour.

## Capabilities

### New Capabilities

- `structured-logging`: Provides JSON Lines file logging and Rich console output infrastructure, including the public `setup_logging(verbose: bool) -> None` entry point.

### Modified Capabilities

- `cli-root-options`: The `main` Click group now calls `setup_logging()` using the `verbose` flag value already stored in context.

## Impact

- **New file**: `src/az_acme_tool/logging.py`
- **Modified file**: `src/az_acme_tool/cli.py` — adds `setup_logging()` call in `main()`
- **Modified file**: `pyproject.toml` — adds `rich>=13.0` to `[project.dependencies]`
- **New file**: `tests/test_logging.py`
- No public API or CLI interface changes; `--verbose` flag behaviour is unchanged in signature, only its effect is now implemented.
