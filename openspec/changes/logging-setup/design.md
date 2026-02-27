## Context

The `az-acme-tool` CLI currently has no logging infrastructure. The `main` Click group already accepts a `--verbose` flag and stores it in `ctx.obj["verbose"]`, but nothing consumes it. Every future command (issue, renew, status, cleanup) needs a reliable way to emit structured diagnostic records and user-facing messages without each command reinventing output handling.

This design introduces a single module, `src/az_acme_tool/logging.py`, that is called once at CLI startup and configures two handlers on the Python root logger: a JSON Lines file handler and a Rich console handler.

## Goals / Non-Goals

**Goals:**
- Provide `setup_logging(verbose: bool) -> None` as the single entry point for logging configuration.
- Write every log record ≥ INFO (or ≥ DEBUG when verbose) as a JSON Lines entry to `~/.config/az-acme-tool/logs/az-acme-tool.log`.
- Print human-readable, coloured output to stderr via `rich.console.Console` for INFO and above (always), plus DEBUG when verbose.
- Wire `setup_logging()` into `cli.py:main()` immediately, so all subcommands inherit configuration.
- Ensure `mypy --strict` and `ruff` pass without suppressions.
- Achieve ≥80% line coverage in `tests/test_logging.py`.

**Non-Goals:**
- Log rotation / retention policy (deferred to a future change).
- Per-command log level overrides (the global `--verbose` flag is sufficient for now).
- Structured log fields beyond `timestamp`, `level`, `message` (additional context fields deferred).
- Windows-specific path handling (project targets Linux/macOS cloud runners).

## Decisions

### 1. Module name: `logging.py` vs `log.py`

**Decision**: Use `src/az_acme_tool/logging.py`.

**Rationale**: Mirrors the roadmap naming (`setup_logging`). Shadow of stdlib `logging` is contained within the package namespace; external imports use `az_acme_tool.logging`. Any internal module that needs stdlib logging imports it as `import logging as _logging` or accesses via `logging.getLogger` before the package module is on `sys.path` under the same name. Given that this module itself must import stdlib `logging`, it will use `import logging` at the top with a module-level alias resolved carefully — alternatively the file is structured so stdlib `logging` is imported at the top before any local imports. This is standard practice in Python projects that shadow stdlib names.

**Alternative considered**: Naming it `log.py` (no shadow risk). Rejected because roadmap spec and public function name (`setup_logging`) align with `logging.py`, and the shadow issue is manageable.

### 2. JSON Lines formatting

**Decision**: Use a custom `logging.Formatter` subclass (`JsonLinesFormatter`) that emits `{"timestamp": ..., "level": ..., "message": ...}` as a single line per record.

**Rationale**: `json` is in stdlib; no extra dependency. A custom formatter keeps the handler generic (`logging.FileHandler`) and makes the output trivially parseable. The `timestamp` field uses ISO 8601 format (`datetime.utcnow().isoformat() + "Z"`).

**Alternative considered**: `python-json-logger` third-party library. Rejected to avoid an extra dependency for something trivially implemented in ~15 lines.

### 3. Rich console handler

**Decision**: Implement a `RichConsoleHandler(logging.Handler)` subclass that wraps `rich.console.Console(stderr=True)` and calls `console.print()` with a plain format string (no JSON). INFO+ messages are always shown; DEBUG messages appear only when the root logger level is DEBUG.

**Rationale**: Rich is already required by the roadmap. Using `Console(stderr=True)` leaves stdout free for machine-readable output (e.g., `--output json` in future commands). Because Python's logging framework handles level filtering via the handler's own level, `RichConsoleHandler` sets its level to `logging.DEBUG` and relies on the root logger's level to filter DEBUG in non-verbose mode.

**Alternative considered**: Using `rich.logging.RichHandler` directly. Rejected because it adds timestamp/path columns to the console output that are not appropriate for a CLI tool; a thin wrapper gives us a clean one-line format.

### 4. Verbose flag wiring

**Decision**: `cli.py:main()` calls `setup_logging(verbose=verbose)` as its first statement after `ctx.ensure_object(dict)`.

**Rationale**: The `main` group runs before any subcommand, so calling `setup_logging()` here guarantees every subcommand operates in a fully configured logging environment. `verbose` is already passed as a parameter to `main()` by Click.

### 5. Log file directory creation

**Decision**: `setup_logging()` calls `Path(log_path).parent.mkdir(parents=True, exist_ok=True)` before attaching the file handler.

**Rationale**: First-run experience requires the directory to be created automatically. Using `exist_ok=True` makes the call idempotent.

### 6. Log level management

**Decision**: `setup_logging()` sets the root logger level to `logging.DEBUG` when `verbose=True`, otherwise `logging.INFO`. Both handlers are added to the root logger.

**Rationale**: Centralising level on the root logger means third-party libraries' loggers also respect the level (desired behaviour for debugging Azure SDK calls). The file handler receives all records the root logger passes through; the Rich handler also receives all records but only renders them at INFO+ in the non-verbose console format.

## Risks / Trade-offs

- **Shadow of stdlib `logging`**: The module file `az_acme_tool/logging.py` shadows `logging` within the package. Within `logging.py` itself, stdlib `logging` must be imported before any relative imports. This is handled by importing `logging` as the very first statement in the file (it resolves to stdlib because the package is not yet fully initialised at import time). Risk is low; well-understood Python pattern.
- **File handler on every test run**: Tests that call `setup_logging()` will attempt to create the log directory and file in `~/.config/az-acme-tool/logs/`. Tests must patch `logging.FileHandler` or use `tmp_path` to avoid filesystem side effects.
- **Rich version compatibility**: `rich>=13.0` is specified; breaking changes in Rich's public API are infrequent. Risk is low.

## Migration Plan

1. Add `rich>=13.0` to `pyproject.toml` `[project.dependencies]` and run `uv sync`.
2. Create `src/az_acme_tool/logging.py`.
3. Edit `src/az_acme_tool/cli.py` to call `setup_logging(verbose=verbose)` in `main()`.
4. Create `tests/test_logging.py` with unit tests.
5. Run `ruff check`, `mypy --strict`, `pytest --cov` to confirm all pass.

Rollback: revert the three file changes; `rich` can remain in dependencies (it is a benign addition).

## Open Questions

- None. All design decisions are resolved; implementation can proceed.
