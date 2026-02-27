## 1. Dependencies

- [x] 1.1 Add `rich>=13.0` to `[project.dependencies]` in `pyproject.toml` and run `uv sync` to install it

## 2. Core Logging Module

- [x] 2.1 Create `src/az_acme_tool/logging.py` with a `JsonLinesFormatter` class that formats log records as `{"timestamp": ..., "level": ..., "message": ...}` JSON Lines
- [x] 2.2 Implement `RichConsoleHandler(logging.Handler)` in `src/az_acme_tool/logging.py` that wraps `rich.console.Console(stderr=True)` and prints plain (non-JSON) messages
- [x] 2.3 Implement `setup_logging(verbose: bool) -> None` in `src/az_acme_tool/logging.py` that creates the log directory, attaches the file handler with `JsonLinesFormatter`, attaches `RichConsoleHandler`, and sets the root logger level to `DEBUG` when `verbose=True` or `INFO` otherwise
- [x] 2.4 Verify `src/az_acme_tool/logging.py` passes `mypy --strict` and `ruff check` with no errors

## 3. CLI Wiring

- [x] 3.1 Import `setup_logging` from `az_acme_tool.logging` in `src/az_acme_tool/cli.py`
- [x] 3.2 Call `setup_logging(verbose=verbose)` in the `main` Click group body immediately after `ctx.ensure_object(dict)`, before any subcommand executes
- [x] 3.3 Verify `src/az_acme_tool/cli.py` passes `mypy --strict` and `ruff check` with no errors

## 4. Unit Tests

- [x] 4.1 Create `tests/test_logging.py` with a test that calls `setup_logging(verbose=False)`, emits an INFO log record, and asserts the JSON Lines file contains a valid JSON object with `timestamp`, `level`, and `message` fields (use `tmp_path` to redirect log file path via monkeypatch)
- [x] 4.2 Add a test that verifies a DEBUG record does NOT appear in the log file when `verbose=False`
- [x] 4.3 Add a test that verifies a DEBUG record DOES appear in the log file when `verbose=True`
- [x] 4.4 Add a test that mocks `rich.console.Console` and asserts that an INFO message is printed to stderr in non-JSON format (does not start with `{`)
- [x] 4.5 Add a test that asserts a DEBUG message is NOT passed to the Rich console when `verbose=False`
- [x] 4.6 Add a test that asserts a DEBUG message IS passed to the Rich console when `verbose=True`

## 5. Coverage and Quality Gate

- [x] 5.1 Run `pytest --cov=az_acme_tool.logging tests/test_logging.py` and confirm line coverage is ≥80%
- [x] 5.2 Run `ruff check src/ tests/` and `mypy --strict src/` and confirm no errors remain
- [x] 5.3 Run `black --line-length 100 --check src/ tests/` and fix any formatting issues
