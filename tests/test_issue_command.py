"""Tests for az_acme_tool.issue_command and the `issue` CLI command."""

from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from az_acme_tool.cli import main
from az_acme_tool.issue_command import IssueError, _resolve_targets

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


def _write_config(tmp_path: Path, gateways: list[dict]) -> Path:  # type: ignore[type-arg]
    """Write a minimal valid config YAML and return its path."""
    cfg = {
        "acme": {"email": "test@example.com"},
        "azure": {
            "subscription_id": str(uuid.uuid4()),
            "resource_group": "rg-test",
            "auth_method": "default",
        },
        "gateways": gateways,
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump(cfg))
    return config_path


@pytest.fixture()
def two_gateway_config(tmp_path: Path) -> Path:
    return _write_config(
        tmp_path,
        gateways=[
            {
                "name": "agw-alpha",
                "domains": [
                    {"domain": "www.alpha.com", "cert_store": "agw_direct"},
                    {"domain": "api.alpha.com", "cert_store": "agw_direct"},
                ],
            },
            {
                "name": "agw-beta",
                "domains": [
                    {"domain": "www.beta.com", "cert_store": "agw_direct"},
                ],
            },
        ],
    )


# ---------------------------------------------------------------------------
# _resolve_targets unit tests
# ---------------------------------------------------------------------------


class TestResolveTargets:
    def test_no_filter_returns_all(self, two_gateway_config: Path) -> None:
        from az_acme_tool.config import parse_config

        cfg = parse_config(two_gateway_config)
        targets = _resolve_targets(cfg, None, None)
        domains = [t.domain for t in targets]
        assert "www.alpha.com" in domains
        assert "api.alpha.com" in domains
        assert "www.beta.com" in domains
        assert len(targets) == 3

    def test_gateway_filter(self, two_gateway_config: Path) -> None:
        from az_acme_tool.config import parse_config

        cfg = parse_config(two_gateway_config)
        targets = _resolve_targets(cfg, "agw-alpha", None)
        assert all(t.gateway_name == "agw-alpha" for t in targets)
        assert len(targets) == 2

    def test_domain_filter(self, two_gateway_config: Path) -> None:
        from az_acme_tool.config import parse_config

        cfg = parse_config(two_gateway_config)
        targets = _resolve_targets(cfg, None, "www.beta.com")
        assert len(targets) == 1
        assert targets[0].domain == "www.beta.com"

    def test_combined_filter(self, two_gateway_config: Path) -> None:
        from az_acme_tool.config import parse_config

        cfg = parse_config(two_gateway_config)
        targets = _resolve_targets(cfg, "agw-alpha", "api.alpha.com")
        assert len(targets) == 1
        assert targets[0].domain == "api.alpha.com"

    def test_unknown_domain_raises_issue_error(self, two_gateway_config: Path) -> None:
        from az_acme_tool.config import parse_config

        cfg = parse_config(two_gateway_config)
        with pytest.raises(IssueError, match="nonexistent.example.com"):
            _resolve_targets(cfg, None, "nonexistent.example.com")


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------


class TestIssueDryRun:
    def test_dry_run_prints_planned_steps(
        self, runner: CliRunner, two_gateway_config: Path
    ) -> None:
        result = runner.invoke(main, ["--config", str(two_gateway_config), "issue", "--dry-run"])
        assert result.exit_code == 0, result.output
        assert "[DRY-RUN]" in result.output
        assert "www.alpha.com" in result.output
        assert "www.beta.com" in result.output

    def test_dry_run_no_sdk_calls(self, runner: CliRunner, two_gateway_config: Path) -> None:
        with patch("az_acme_tool.issue_command._issue_single_domain") as mock_issue:
            result = runner.invoke(
                main, ["--config", str(two_gateway_config), "issue", "--dry-run"]
            )
        assert result.exit_code == 0
        mock_issue.assert_not_called()

    def test_dry_run_exits_zero(self, runner: CliRunner, two_gateway_config: Path) -> None:
        result = runner.invoke(main, ["--config", str(two_gateway_config), "issue", "--dry-run"])
        assert result.exit_code == 0


class TestIssueGatewayFilter:
    def test_gateway_filter_limits_domains(
        self, runner: CliRunner, two_gateway_config: Path
    ) -> None:
        with patch("az_acme_tool.issue_command._issue_single_domain") as mock_issue:
            runner.invoke(
                main, ["--config", str(two_gateway_config), "issue", "--gateway", "agw-alpha"]
            )
        called_domains = [call.args[0].domain for call in mock_issue.call_args_list]
        assert "www.alpha.com" in called_domains or "api.alpha.com" in called_domains
        assert "www.beta.com" not in called_domains


class TestIssueDomainFilter:
    def test_domain_filter_limits_to_one(self, runner: CliRunner, two_gateway_config: Path) -> None:
        with patch("az_acme_tool.issue_command._issue_single_domain") as mock_issue:
            runner.invoke(
                main,
                ["--config", str(two_gateway_config), "issue", "--domain", "www.beta.com"],
            )
        called_domains = [call.args[0].domain for call in mock_issue.call_args_list]
        assert called_domains == ["www.beta.com"]

    def test_unknown_domain_nonzero_exit(self, runner: CliRunner, two_gateway_config: Path) -> None:
        result = runner.invoke(
            main,
            [
                "--config",
                str(two_gateway_config),
                "issue",
                "--domain",
                "nonexistent.example.com",
            ],
        )
        assert result.exit_code != 0
        assert "nonexistent.example.com" in result.output or "nonexistent.example.com" in (
            result.stderr if hasattr(result, "stderr") else ""
        )


class TestIssueSummary:
    def test_summary_printed_after_dry_run(
        self, runner: CliRunner, two_gateway_config: Path
    ) -> None:
        result = runner.invoke(main, ["--config", str(two_gateway_config), "issue", "--dry-run"])
        assert "Summary" in result.output
        assert "3 domain(s)" in result.output

    def test_summary_shows_failed_on_error(
        self, runner: CliRunner, two_gateway_config: Path
    ) -> None:
        with patch(
            "az_acme_tool.issue_command._issue_single_domain",
            side_effect=RuntimeError("ACME error"),
        ):
            result = runner.invoke(main, ["--config", str(two_gateway_config), "issue"])
        assert "failed" in result.output.lower()
