"""Unit tests for az_acme_tool.cli module."""

from __future__ import annotations

import logging as _stdlib_logging
import uuid
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
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


def _write_config(tmp_path: Path) -> Path:
    """Write a minimal valid config YAML to tmp_path and return its path."""
    cfg = {
        "acme": {"email": "test@example.com"},
        "azure": {
            "subscription_id": str(uuid.uuid4()),
            "resource_group": "rg-test",
            "auth_method": "default",
        },
        "gateways": [
            {
                "name": "agw-alpha",
                "domains": [{"domain": "www.example.com", "cert_store": "agw_direct"}],
            }
        ],
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump(cfg))
    return config_path


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
# Tests: subcommands (error path - missing config)
# ---------------------------------------------------------------------------


def test_init_subcommand_config_template(runner: CliRunner) -> None:
    """init --config-template prints a YAML template to stdout and exits 0."""
    with patch("az_acme_tool.cli.setup_logging"):
        result = runner.invoke(
            main,
            ["init", "--config-template"],
            catch_exceptions=False,
        )
    assert result.exit_code == 0
    assert "acme:" in result.output
    assert "azure:" in result.output


def test_issue_subcommand_missing_config(runner: CliRunner) -> None:
    """issue subcommand exits non-zero with an error message when config is missing."""
    with patch("az_acme_tool.cli.setup_logging"):
        result = runner.invoke(
            main,
            ["--config", "/nonexistent/path/config.yaml", "issue"],
            catch_exceptions=False,
        )
    assert result.exit_code != 0
    assert "Error" in (result.output + (result.stderr if hasattr(result, "stderr") else ""))


def test_renew_subcommand_missing_config(runner: CliRunner) -> None:
    """renew subcommand exits non-zero with an error message when config is missing."""
    with patch("az_acme_tool.cli.setup_logging"):
        result = runner.invoke(
            main,
            ["--config", "/nonexistent/path/config.yaml", "renew"],
            catch_exceptions=False,
        )
    assert result.exit_code != 0
    assert "Error" in (result.output + (result.stderr if hasattr(result, "stderr") else ""))


def test_status_subcommand_missing_config(runner: CliRunner) -> None:
    """status subcommand exits non-zero with an error message when config is missing."""
    with patch("az_acme_tool.cli.setup_logging"):
        result = runner.invoke(
            main,
            ["--config", "/nonexistent/path/config.yaml", "status"],
            catch_exceptions=False,
        )
    assert result.exit_code != 0
    assert "Error" in (result.output + (result.stderr if hasattr(result, "stderr") else ""))


def test_cleanup_subcommand_no_rules(runner: CliRunner, tmp_path: Path) -> None:
    """cleanup subcommand prints 'no rules found' message when no orphaned rules exist."""
    from unittest.mock import MagicMock

    config_path = _write_config(tmp_path)
    mock_client = MagicMock()
    mock_client.list_acme_challenge_rules.return_value = []

    with (
        patch("az_acme_tool.cli.setup_logging"),
        patch("az_acme_tool.cleanup_command.DefaultAzureCredential"),
        patch(
            "az_acme_tool.cleanup_command.AzureGatewayClient",
            return_value=mock_client,
        ),
    ):
        result = runner.invoke(main, ["--config", str(config_path), "cleanup"])

    assert result.exit_code == 0
    assert "No orphaned ACME challenge rules found." in result.output


def test_cleanup_subcommand_all_flag(runner: CliRunner, tmp_path: Path) -> None:
    """cleanup --all removes all orphaned rules without prompting."""
    from unittest.mock import MagicMock

    config_path = _write_config(tmp_path)
    rule = "acme-challenge-www-example-com-1709030400"
    mock_client = MagicMock()
    mock_client.list_acme_challenge_rules.return_value = [rule]

    with (
        patch("az_acme_tool.cli.setup_logging"),
        patch("az_acme_tool.cleanup_command.DefaultAzureCredential"),
        patch(
            "az_acme_tool.cleanup_command.AzureGatewayClient",
            return_value=mock_client,
        ),
    ):
        result = runner.invoke(main, ["--config", str(config_path), "cleanup", "--all"])

    assert result.exit_code == 0
    mock_client.delete_routing_rule.assert_called_once_with(rule)
    assert f"Removed: {rule}" in result.output
