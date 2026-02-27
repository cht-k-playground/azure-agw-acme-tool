"""Unit tests for az_acme_tool.logging module."""

from __future__ import annotations

import json
import logging as _stdlib_logging
from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from az_acme_tool.logging import RichConsoleHandler, setup_logging

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_root_logger() -> Generator[None, None, None]:
    """Restore root logger state after each test to prevent handler leakage."""
    root = _stdlib_logging.getLogger()
    original_level = root.level
    original_handlers = list(root.handlers)
    yield
    # Close and remove all handlers added during the test
    for handler in root.handlers:
        handler.close()
    root.handlers = original_handlers
    root.setLevel(original_level)


@pytest.fixture()
def log_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect the log file to a temp directory and return the log file path."""
    log_dir = tmp_path / "logs"
    log_path = log_dir / "az-acme-tool.log"
    # Patch module-level constants so setup_logging() uses tmp locations
    monkeypatch.setattr("az_acme_tool.logging._LOG_DIR", log_dir)
    monkeypatch.setattr("az_acme_tool.logging._LOG_FILE", log_path)
    return log_path


# ---------------------------------------------------------------------------
# Task 4.1 — INFO record written as valid JSON with required fields
# ---------------------------------------------------------------------------


def test_info_record_written_as_json_lines(log_file: Path) -> None:
    """setup_logging(verbose=False) writes INFO records as valid JSON Lines."""
    setup_logging(verbose=False)

    logger = _stdlib_logging.getLogger("test.info")
    test_message = "hello from test_info_record_written_as_json_lines"
    logger.info(test_message)

    # Flush and close the file handler so the data is on disk
    root = _stdlib_logging.getLogger()
    for handler in root.handlers:
        handler.flush()

    assert log_file.exists(), "Log file was not created"
    lines = [line for line in log_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) >= 1, "Expected at least one log line"

    # Find the line that contains our message
    matching = [ln for ln in lines if test_message in ln]
    assert matching, f"No log line contains the expected message. Lines: {lines}"

    record = json.loads(matching[0])
    assert "timestamp" in record, "JSON record missing 'timestamp' field"
    assert "level" in record, "JSON record missing 'level' field"
    assert "message" in record, "JSON record missing 'message' field"
    assert record["level"] == "INFO"
    assert record["message"] == test_message

    # Validate timestamp is ISO 8601 UTC format
    ts = record["timestamp"]
    assert isinstance(ts, str), f"timestamp must be a string, got {type(ts)}"
    assert ts.endswith("Z") or ts.endswith("+00:00"), f"Unexpected timestamp format: {ts}"
    # Verify it is parseable as a datetime
    datetime.fromisoformat(ts.replace("Z", "+00:00"))  # should not raise


# ---------------------------------------------------------------------------
# Task 4.2 — DEBUG record NOT written when verbose=False
# ---------------------------------------------------------------------------


def test_debug_record_absent_when_not_verbose(log_file: Path) -> None:
    """setup_logging(verbose=False) does NOT write DEBUG records to the log file."""
    setup_logging(verbose=False)

    root = _stdlib_logging.getLogger()
    assert (
        root.level == _stdlib_logging.INFO
    ), f"Expected root logger level INFO ({_stdlib_logging.INFO}), got {root.level}"

    logger = _stdlib_logging.getLogger("test.debug_absent")
    debug_message = "this is a debug message that should not appear"
    logger.debug(debug_message)

    for handler in root.handlers:
        handler.flush()

    if log_file.exists():
        content = log_file.read_text(encoding="utf-8")
        assert debug_message not in content, "DEBUG record unexpectedly found in log file"


# ---------------------------------------------------------------------------
# Task 4.3 — DEBUG record DOES appear when verbose=True
# ---------------------------------------------------------------------------


def test_debug_record_present_when_verbose(log_file: Path) -> None:
    """setup_logging(verbose=True) writes DEBUG records to the log file."""
    setup_logging(verbose=True)

    root = _stdlib_logging.getLogger()
    assert (
        root.level == _stdlib_logging.DEBUG
    ), f"Expected root logger level DEBUG ({_stdlib_logging.DEBUG}), got {root.level}"

    logger = _stdlib_logging.getLogger("test.debug_present")
    debug_message = "verbose debug message that should appear"
    logger.debug(debug_message)

    root = _stdlib_logging.getLogger()
    for handler in root.handlers:
        handler.flush()

    assert log_file.exists(), "Log file was not created"
    content = log_file.read_text(encoding="utf-8")
    assert debug_message in content, "DEBUG record not found in log file when verbose=True"

    # Confirm the record is valid JSON with level DEBUG
    lines = [ln for ln in content.splitlines() if debug_message in ln]
    record = json.loads(lines[0])
    assert record["level"] == "DEBUG"


# ---------------------------------------------------------------------------
# Task 4.4 — Rich console receives INFO message in non-JSON format
# ---------------------------------------------------------------------------


def test_rich_console_prints_non_json_for_info(log_file: Path) -> None:
    """INFO messages sent to RichConsoleHandler do not start with '{'."""
    printed_messages: list[str] = []

    mock_console = MagicMock()

    def capture_print(msg: str, **kwargs: object) -> None:
        printed_messages.append(str(msg))

    mock_console.print.side_effect = capture_print

    with patch("az_acme_tool.logging.Console", return_value=mock_console):
        setup_logging(verbose=False)
        logger = _stdlib_logging.getLogger("test.rich_info")
        info_message = "an info message for the console"
        logger.info(info_message)

        root = _stdlib_logging.getLogger()
        for handler in root.handlers:
            handler.flush()

    # At least one call to console.print should have occurred
    assert mock_console.print.called, "Console.print was never called"

    # Find the call that contains our message
    matching = [m for m in printed_messages if info_message in m]
    assert matching, f"No console output contains the INFO message. Got: {printed_messages}"

    # The output must NOT start with '{' (i.e. not JSON)
    for msg in matching:
        assert not msg.startswith("{"), f"Console output unexpectedly looks like JSON: {msg!r}"


# ---------------------------------------------------------------------------
# Task 4.5 — DEBUG message NOT passed to Rich console when verbose=False
# ---------------------------------------------------------------------------


def test_rich_console_does_not_receive_debug_when_not_verbose(log_file: Path) -> None:
    """DEBUG messages are not emitted to the Rich console when verbose=False."""
    printed_messages: list[str] = []

    mock_console = MagicMock()

    def capture_print(msg: str, **kwargs: object) -> None:
        printed_messages.append(str(msg))

    mock_console.print.side_effect = capture_print

    debug_message = "this debug should not reach the console"

    with patch("az_acme_tool.logging.Console", return_value=mock_console):
        setup_logging(verbose=False)
        logger = _stdlib_logging.getLogger("test.rich_debug_absent")
        logger.debug(debug_message)

        root = _stdlib_logging.getLogger()
        for handler in root.handlers:
            handler.flush()

    matching = [m for m in printed_messages if debug_message in m]
    assert not matching, f"DEBUG message unexpectedly reached the console: {matching}"


# ---------------------------------------------------------------------------
# Task 4.6 — DEBUG message IS passed to Rich console when verbose=True
# ---------------------------------------------------------------------------


def test_rich_console_receives_debug_when_verbose(log_file: Path) -> None:
    """DEBUG messages ARE emitted to the Rich console when verbose=True."""
    printed_messages: list[str] = []

    mock_console = MagicMock()

    def capture_print(msg: str, **kwargs: object) -> None:
        printed_messages.append(str(msg))

    mock_console.print.side_effect = capture_print

    debug_message = "verbose debug should reach the console"

    with patch("az_acme_tool.logging.Console", return_value=mock_console):
        setup_logging(verbose=True)
        logger = _stdlib_logging.getLogger("test.rich_debug_present")
        logger.debug(debug_message)

        root = _stdlib_logging.getLogger()
        for handler in root.handlers:
            handler.flush()

    matching = [m for m in printed_messages if debug_message in m]
    assert (
        matching
    ), f"DEBUG message was not emitted to the console when verbose=True. Got: {printed_messages}"


# ---------------------------------------------------------------------------
# Task 4.7 — RichConsoleHandler.emit() calls handleError on print exception
# ---------------------------------------------------------------------------


def test_rich_console_handler_emit_calls_handle_error_on_exception(
    mocker: pytest.MockerFixture,
) -> None:
    """RichConsoleHandler.emit() calls handleError when Console.print raises."""
    handler = RichConsoleHandler()
    mocker.patch.object(handler._console, "print", side_effect=Exception("boom"))
    handle_error_mock = mocker.patch.object(handler, "handleError")

    record = _stdlib_logging.LogRecord(
        name="test",
        level=_stdlib_logging.INFO,
        pathname="",
        lineno=0,
        msg="test message",
        args=(),
        exc_info=None,
    )
    handler.emit(record)  # should not raise
    handle_error_mock.assert_called_once_with(record)
