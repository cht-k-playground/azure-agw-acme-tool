"""Tests for az_acme_tool.cleanup_command and the `cleanup` CLI command.

All Azure SDK calls are mocked via pytest-mock; no real Azure credentials
or network access are required.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from az_acme_tool.azure_gateway import AzureGatewayError
from az_acme_tool.cleanup_command import CleanupError, run_cleanup
from az_acme_tool.cli import main

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_config(tmp_path: Path) -> Path:
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


# ---------------------------------------------------------------------------
# run_cleanup unit tests
# ---------------------------------------------------------------------------


class TestRunCleanupNoRules:
    def test_no_rules_prints_message(self, tmp_path: Path) -> None:
        """When no orphaned rules exist, prints the 'no rules found' message."""
        config_path = _write_config(tmp_path)

        mock_client = MagicMock()
        mock_client.list_acme_challenge_rules.return_value = []

        with (
            patch("az_acme_tool.cleanup_command.DefaultAzureCredential"),
            patch(
                "az_acme_tool.cleanup_command.AzureGatewayClient",
                return_value=mock_client,
            ),
        ):
            runner = CliRunner()
            result = runner.invoke(
                main,
                ["--config", str(config_path), "cleanup"],
            )

        assert result.exit_code == 0
        assert "No orphaned ACME challenge rules found." in result.output
        mock_client.delete_routing_rule.assert_not_called()


class TestRunCleanupAllFlag:
    def test_all_flag_removes_all_rules_without_prompting(self, tmp_path: Path) -> None:
        """With --all, all matching rules are deleted without confirmation prompts."""
        config_path = _write_config(tmp_path)
        rules = [
            "acme-challenge-www-example-com-1709030400",
            "acme-challenge-api-example-com-1709030401",
        ]

        mock_client = MagicMock()
        mock_client.list_acme_challenge_rules.return_value = rules

        with (
            patch("az_acme_tool.cleanup_command.DefaultAzureCredential"),
            patch(
                "az_acme_tool.cleanup_command.AzureGatewayClient",
                return_value=mock_client,
            ),
        ):
            runner = CliRunner()
            result = runner.invoke(
                main,
                ["--config", str(config_path), "cleanup", "--all"],
            )

        assert result.exit_code == 0
        assert mock_client.delete_routing_rule.call_count == 2
        for rule in rules:
            assert f"Removed: {rule}" in result.output
        # No confirmation prompts should appear
        assert "Delete rule" not in result.output

    def test_all_flag_no_rules_prints_message(self, tmp_path: Path) -> None:
        """With --all and no rules, prints the 'no rules found' message."""
        config_path = _write_config(tmp_path)

        mock_client = MagicMock()
        mock_client.list_acme_challenge_rules.return_value = []

        with (
            patch("az_acme_tool.cleanup_command.DefaultAzureCredential"),
            patch(
                "az_acme_tool.cleanup_command.AzureGatewayClient",
                return_value=mock_client,
            ),
        ):
            runner = CliRunner()
            result = runner.invoke(
                main,
                ["--config", str(config_path), "cleanup", "--all"],
            )

        assert result.exit_code == 0
        assert "No orphaned ACME challenge rules found." in result.output


class TestRunCleanupInteractive:
    def test_interactive_yes_deletes_rule(self, tmp_path: Path) -> None:
        """In interactive mode, answering 'y' deletes the rule."""
        config_path = _write_config(tmp_path)
        rule = "acme-challenge-www-example-com-1709030400"

        mock_client = MagicMock()
        mock_client.list_acme_challenge_rules.return_value = [rule]

        with (
            patch("az_acme_tool.cleanup_command.DefaultAzureCredential"),
            patch(
                "az_acme_tool.cleanup_command.AzureGatewayClient",
                return_value=mock_client,
            ),
        ):
            runner = CliRunner()
            result = runner.invoke(
                main,
                ["--config", str(config_path), "cleanup"],
                input="y\n",
            )

        assert result.exit_code == 0
        mock_client.delete_routing_rule.assert_called_once_with(rule)
        assert f"Removed: {rule}" in result.output

    def test_interactive_no_skips_rule(self, tmp_path: Path) -> None:
        """In interactive mode, answering 'n' skips the rule without deleting."""
        config_path = _write_config(tmp_path)
        rule = "acme-challenge-www-example-com-1709030400"

        mock_client = MagicMock()
        mock_client.list_acme_challenge_rules.return_value = [rule]

        with (
            patch("az_acme_tool.cleanup_command.DefaultAzureCredential"),
            patch(
                "az_acme_tool.cleanup_command.AzureGatewayClient",
                return_value=mock_client,
            ),
        ):
            runner = CliRunner()
            result = runner.invoke(
                main,
                ["--config", str(config_path), "cleanup"],
                input="n\n",
            )

        assert result.exit_code == 0
        mock_client.delete_routing_rule.assert_not_called()
        assert "Removed:" not in result.output

    def test_interactive_mixed_responses(self, tmp_path: Path) -> None:
        """In interactive mode, only rules confirmed with 'y' are deleted."""
        config_path = _write_config(tmp_path)
        rules = [
            "acme-challenge-www-example-com-1709030400",
            "acme-challenge-api-example-com-1709030401",
        ]

        mock_client = MagicMock()
        mock_client.list_acme_challenge_rules.return_value = rules

        with (
            patch("az_acme_tool.cleanup_command.DefaultAzureCredential"),
            patch(
                "az_acme_tool.cleanup_command.AzureGatewayClient",
                return_value=mock_client,
            ),
        ):
            runner = CliRunner()
            result = runner.invoke(
                main,
                ["--config", str(config_path), "cleanup"],
                input="y\nn\n",
            )

        assert result.exit_code == 0
        mock_client.delete_routing_rule.assert_called_once_with(rules[0])
        assert f"Removed: {rules[0]}" in result.output
        assert f"Removed: {rules[1]}" not in result.output


class TestRunCleanupErrors:
    def test_raises_cleanup_error_on_list_failure(self, tmp_path: Path) -> None:
        """CleanupError is raised when list_acme_challenge_rules fails."""
        config_path = _write_config(tmp_path)

        mock_client = MagicMock()
        mock_client.list_acme_challenge_rules.side_effect = AzureGatewayError(
            "API failure"
        )

        with (
            patch("az_acme_tool.cleanup_command.DefaultAzureCredential"),
            patch(
                "az_acme_tool.cleanup_command.AzureGatewayClient",
                return_value=mock_client,
            ),
        ):
            with pytest.raises(CleanupError, match="Failed to list ACME challenge rules"):
                run_cleanup(config_path=str(config_path), cleanup_all=True)

    def test_raises_cleanup_error_on_delete_failure(self, tmp_path: Path) -> None:
        """CleanupError is raised when delete_routing_rule fails."""
        config_path = _write_config(tmp_path)
        rule = "acme-challenge-www-example-com-1709030400"

        mock_client = MagicMock()
        mock_client.list_acme_challenge_rules.return_value = [rule]
        mock_client.delete_routing_rule.side_effect = AzureGatewayError("Delete failed")

        with (
            patch("az_acme_tool.cleanup_command.DefaultAzureCredential"),
            patch(
                "az_acme_tool.cleanup_command.AzureGatewayClient",
                return_value=mock_client,
            ),
        ):
            with pytest.raises(CleanupError, match="Failed to delete rule"):
                run_cleanup(config_path=str(config_path), cleanup_all=True)

    def test_cli_exits_nonzero_on_cleanup_error(self, tmp_path: Path) -> None:
        """CLI exits with code 1 when CleanupError is raised."""
        config_path = _write_config(tmp_path)

        mock_client = MagicMock()
        mock_client.list_acme_challenge_rules.side_effect = AzureGatewayError(
            "API failure"
        )

        with (
            patch("az_acme_tool.cleanup_command.DefaultAzureCredential"),
            patch(
                "az_acme_tool.cleanup_command.AzureGatewayClient",
                return_value=mock_client,
            ),
        ):
            runner = CliRunner()
            result = runner.invoke(
                main,
                ["--config", str(config_path), "cleanup", "--all"],
            )

        assert result.exit_code == 1
        assert "Error:" in result.output
