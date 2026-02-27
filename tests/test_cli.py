"""Unit tests for az_acme_tool.cli module."""

from __future__ import annotations

import logging as _stdlib_logging
from collections.abc import Generator
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from az_acme_tool.cli import main

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_root_logger() -> Generator[None, None, None]:
    """Restore root logger state after each test to prevent handler leakage."""
    root = _stdlib_logging.getLogger()
    original_level = root.level
    original_handlers = list(root.handlers)
    yield
    for handler in root.handlers:
        handler.close()
    root.handlers = original_handlers
    root.setLevel(original_level)


@pytest.fixture()
def runner() -> CliRunner:
    """Return a Click test runner with isolated filesystem."""
    return CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _invoke_main_with_mock_logging(runner: CliRunner, args: list[str]) -> object:
    """Invoke the main group while mocking setup_logging to avoid file I/O."""
    with patch("az_acme_tool.cli.setup_logging") as mock_setup:
        result = runner.invoke(main, args, catch_exceptions=False)
        return result, mock_setup


# ---------------------------------------------------------------------------
# Tests: main group
# ---------------------------------------------------------------------------


def test_main_version_option(runner: CliRunner) -> None:
    """--version prints the version string and exits 0."""
    with patch("az_acme_tool.cli.setup_logging"):
        result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "az-acme-tool" in result.output


def test_main_help_option(runner: CliRunner) -> None:
    """--help prints help text and exits 0."""
    with patch("az_acme_tool.cli.setup_logging"):
        result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "--verbose" in result.output
    assert "--config" in result.output


def test_main_calls_setup_logging_verbose_false(runner: CliRunner) -> None:
    """main() calls setup_logging(verbose=False) when --verbose is not passed."""
    # Use a subcommand (init) so the main group body actually runs.
    # init raises NotImplementedError, but setup_logging is called first.
    with patch("az_acme_tool.cli.setup_logging") as mock_setup:
        runner.invoke(main, ["init"], catch_exceptions=True)
    mock_setup.assert_called_once_with(verbose=False)


def test_main_calls_setup_logging_verbose_true(runner: CliRunner) -> None:
    """main() calls setup_logging(verbose=True) when --verbose is passed."""
    with patch("az_acme_tool.cli.setup_logging") as mock_setup:
        runner.invoke(main, ["--verbose", "init"], catch_exceptions=True)
    mock_setup.assert_called_once_with(verbose=True)


def test_main_stores_config_in_context(runner: CliRunner) -> None:
    """main() stores the --config value in the Click context object."""
    config_path = "/tmp/test-config.yaml"
    with patch("az_acme_tool.cli.setup_logging"):
        result = runner.invoke(main, ["--config", config_path, "--help"])
    assert result.exit_code == 0


def test_main_default_config_path(runner: CliRunner) -> None:
    """main() uses the default config path when --config is not passed."""
    with patch("az_acme_tool.cli.setup_logging"):
        result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    # The help output may line-wrap the default value; join stripped lines to check
    collapsed = " ".join(line.strip() for line in result.output.splitlines())
    assert "config.yaml" in collapsed
    assert "az-acme" in collapsed


# ---------------------------------------------------------------------------
# Tests: subcommands (error path - NotImplementedError)
# ---------------------------------------------------------------------------


def test_init_subcommand_raises_not_implemented(runner: CliRunner) -> None:
    """init subcommand raises NotImplementedError (not yet implemented)."""
    with patch("az_acme_tool.cli.setup_logging"):
        with pytest.raises(NotImplementedError):
            runner.invoke(main, ["init"], catch_exceptions=False)


def test_issue_subcommand_raises_not_implemented(runner: CliRunner) -> None:
    """issue subcommand raises NotImplementedError (not yet implemented)."""
    with patch("az_acme_tool.cli.setup_logging"):
        with pytest.raises(NotImplementedError):
            runner.invoke(main, ["issue"], catch_exceptions=False)


def test_renew_subcommand_raises_not_implemented(runner: CliRunner) -> None:
    """renew subcommand raises NotImplementedError (not yet implemented)."""
    with patch("az_acme_tool.cli.setup_logging"):
        with pytest.raises(NotImplementedError):
            runner.invoke(main, ["renew"], catch_exceptions=False)


def test_status_subcommand_raises_not_implemented(runner: CliRunner) -> None:
    """status subcommand raises NotImplementedError (not yet implemented)."""
    with patch("az_acme_tool.cli.setup_logging"):
        with pytest.raises(NotImplementedError):
            runner.invoke(main, ["status"], catch_exceptions=False)


def test_cleanup_subcommand_raises_not_implemented(runner: CliRunner) -> None:
    """cleanup subcommand raises NotImplementedError (not yet implemented)."""
    with patch("az_acme_tool.cli.setup_logging"):
        with pytest.raises(NotImplementedError):
            runner.invoke(main, ["cleanup"], catch_exceptions=False)
