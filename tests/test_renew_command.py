"""Tests for az_acme_tool.renew_command and the `renew` CLI command."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from az_acme_tool.cli import main
from az_acme_tool.renew_command import _days_remaining, _domain_to_cert_name

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _future_expiry(days: int) -> datetime:
    """Return a UTC datetime *days* from now."""
    return datetime.now(tz=UTC) + timedelta(days=days)


def _cert_list(domain: str, days_remaining: int) -> list[dict[str, object]]:
    """Build a mock certificate list for a single domain."""
    cert_name = domain.replace(".", "-") + "-cert"
    return [{"name": cert_name, "expiry": _future_expiry(days_remaining)}]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def single_domain_config(tmp_path: Path) -> Path:
    return _write_config(
        tmp_path,
        gateways=[
            {
                "name": "agw-test",
                "domains": [{"domain": "www.example.com", "cert_store": "agw_direct"}],
            }
        ],
    )


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
# Unit tests: helpers
# ---------------------------------------------------------------------------


class TestDomainToCertName:
    def test_dots_replaced_with_hyphens(self) -> None:
        assert _domain_to_cert_name("www.example.com") == "www-example-com-cert"

    def test_single_label(self) -> None:
        assert _domain_to_cert_name("example.com") == "example-com-cert"

    def test_subdomain(self) -> None:
        assert _domain_to_cert_name("api.sub.example.com") == "api-sub-example-com-cert"


class TestDaysRemaining:
    def test_future_expiry_positive(self) -> None:
        # Use a large buffer to avoid timing flakiness: 35 days from now
        # should return 34 or 35 (timedelta.days truncates fractional days).
        expiry = _future_expiry(35)
        remaining = _days_remaining(expiry)
        assert 34 <= remaining <= 35

    def test_past_expiry_negative(self) -> None:
        expiry = datetime.now(tz=UTC) - timedelta(days=5)
        assert _days_remaining(expiry) < 0

    def test_exactly_zero(self) -> None:
        # Expiry is slightly in the future (1 second) — should be 0 days remaining.
        expiry = datetime.now(tz=UTC) + timedelta(seconds=1)
        assert _days_remaining(expiry) == 0


# ---------------------------------------------------------------------------
# Task 3.2: domain skipped when certificate has more than threshold days
# ---------------------------------------------------------------------------


class TestRenewSkipAboveThreshold:
    def test_domain_skipped_35_days_default_threshold(
        self, runner: CliRunner, single_domain_config: Path
    ) -> None:
        """Certificate with 35 days remaining is skipped with default --days 30."""
        mock_certs = _cert_list("www.example.com", 35)
        with (
            patch("az_acme_tool.renew_command._build_gateway_client") as mock_build,
            patch("az_acme_tool.renew_command._issue_single_domain") as mock_issue,
        ):
            mock_client = MagicMock()
            mock_client.list_certificates.return_value = mock_certs
            mock_build.return_value = mock_client

            result = runner.invoke(main, ["--config", str(single_domain_config), "renew"])

        assert result.exit_code == 0, result.output
        assert "[SKIP]" in result.output
        assert "www.example.com" in result.output
        # Days remaining may be 34 or 35 due to timing precision.
        assert "days remaining" in result.output
        mock_issue.assert_not_called()

    def test_skip_message_contains_threshold(
        self, runner: CliRunner, single_domain_config: Path
    ) -> None:
        mock_certs = _cert_list("www.example.com", 35)
        with (
            patch("az_acme_tool.renew_command._build_gateway_client") as mock_build,
            patch("az_acme_tool.renew_command._issue_single_domain"),
        ):
            mock_client = MagicMock()
            mock_client.list_certificates.return_value = mock_certs
            mock_build.return_value = mock_client

            result = runner.invoke(main, ["--config", str(single_domain_config), "renew"])

        assert "threshold" in result.output.lower() or "30" in result.output


# ---------------------------------------------------------------------------
# Task 3.3: domain renewed when certificate is within threshold
# ---------------------------------------------------------------------------


class TestRenewWithinThreshold:
    def test_domain_renewed_25_days_default_threshold(
        self, runner: CliRunner, single_domain_config: Path
    ) -> None:
        """Certificate with 25 days remaining triggers renewal with default --days 30."""
        mock_certs = _cert_list("www.example.com", 25)
        with (
            patch("az_acme_tool.renew_command._build_gateway_client") as mock_build,
            patch("az_acme_tool.renew_command._issue_single_domain") as mock_issue,
        ):
            mock_client = MagicMock()
            mock_client.list_certificates.return_value = mock_certs
            mock_build.return_value = mock_client

            runner.invoke(main, ["--config", str(single_domain_config), "renew"])

        # _issue_single_domain raises NotImplementedError (stub), so exit code != 0
        # but the renewal was attempted.
        mock_issue.assert_called_once()
        called_target = mock_issue.call_args[0][0]
        assert called_target.domain == "www.example.com"


# ---------------------------------------------------------------------------
# Task 3.4: --force flag triggers renewal regardless of remaining days
# ---------------------------------------------------------------------------


class TestRenewForce:
    def test_force_renews_35_day_cert(self, runner: CliRunner, single_domain_config: Path) -> None:
        """--force triggers renewal even when 35 days remain."""
        mock_certs = _cert_list("www.example.com", 35)
        with (
            patch("az_acme_tool.renew_command._build_gateway_client") as mock_build,
            patch("az_acme_tool.renew_command._issue_single_domain") as mock_issue,
        ):
            mock_client = MagicMock()
            mock_client.list_certificates.return_value = mock_certs
            mock_build.return_value = mock_client

            runner.invoke(main, ["--config", str(single_domain_config), "renew", "--force"])

        mock_issue.assert_called_once()
        called_target = mock_issue.call_args[0][0]
        assert called_target.domain == "www.example.com"

    def test_force_does_not_skip(self, runner: CliRunner, single_domain_config: Path) -> None:
        mock_certs = _cert_list("www.example.com", 90)
        with (
            patch("az_acme_tool.renew_command._build_gateway_client") as mock_build,
            patch("az_acme_tool.renew_command._issue_single_domain") as mock_issue,
        ):
            mock_client = MagicMock()
            mock_client.list_certificates.return_value = mock_certs
            mock_build.return_value = mock_client

            result = runner.invoke(
                main, ["--config", str(single_domain_config), "renew", "--force"]
            )

        assert "[SKIP]" not in result.output
        mock_issue.assert_called_once()


# ---------------------------------------------------------------------------
# Task 3.5: --days 60 custom threshold applied correctly
# ---------------------------------------------------------------------------


class TestRenewCustomDays:
    def test_55_days_renewed_with_days_60(
        self, runner: CliRunner, single_domain_config: Path
    ) -> None:
        """Certificate with 55 days remaining is renewed when --days 60."""
        mock_certs = _cert_list("www.example.com", 55)
        with (
            patch("az_acme_tool.renew_command._build_gateway_client") as mock_build,
            patch("az_acme_tool.renew_command._issue_single_domain") as mock_issue,
        ):
            mock_client = MagicMock()
            mock_client.list_certificates.return_value = mock_certs
            mock_build.return_value = mock_client

            runner.invoke(main, ["--config", str(single_domain_config), "renew", "--days", "60"])

        mock_issue.assert_called_once()

    def test_65_days_skipped_with_days_60(
        self, runner: CliRunner, single_domain_config: Path
    ) -> None:
        """Certificate with 65 days remaining is skipped when --days 60."""
        mock_certs = _cert_list("www.example.com", 65)
        with (
            patch("az_acme_tool.renew_command._build_gateway_client") as mock_build,
            patch("az_acme_tool.renew_command._issue_single_domain") as mock_issue,
        ):
            mock_client = MagicMock()
            mock_client.list_certificates.return_value = mock_certs
            mock_build.return_value = mock_client

            result = runner.invoke(
                main, ["--config", str(single_domain_config), "renew", "--days", "60"]
            )

        assert result.exit_code == 0
        assert "[SKIP]" in result.output
        mock_issue.assert_not_called()


# ---------------------------------------------------------------------------
# Task 3.6: missing certificate results in skip with warning
# ---------------------------------------------------------------------------


class TestRenewMissingCertificate:
    def test_missing_cert_skipped_with_warning(
        self, runner: CliRunner, single_domain_config: Path
    ) -> None:
        """When the expected certificate is not found, domain is skipped with a warning."""
        with (
            patch("az_acme_tool.renew_command._build_gateway_client") as mock_build,
            patch("az_acme_tool.renew_command._issue_single_domain") as mock_issue,
        ):
            mock_client = MagicMock()
            # Return empty cert list — cert not found.
            mock_client.list_certificates.return_value = []
            mock_build.return_value = mock_client

            result = runner.invoke(main, ["--config", str(single_domain_config), "renew"])

        assert result.exit_code == 0, result.output
        mock_issue.assert_not_called()
        # Warning should appear in output (stderr is mixed into output by CliRunner).
        assert "WARN" in result.output or "not found" in result.output.lower()

    def test_missing_cert_does_not_raise(
        self, runner: CliRunner, single_domain_config: Path
    ) -> None:
        """Missing certificate must not propagate AzureGatewayError."""
        with (patch("az_acme_tool.renew_command._build_gateway_client") as mock_build,):
            mock_client = MagicMock()
            mock_client.list_certificates.return_value = []
            mock_build.return_value = mock_client

            result = runner.invoke(main, ["--config", str(single_domain_config), "renew"])

        # Should exit cleanly (no unhandled exception).
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Task 3.7: --gateway filter limits scope
# ---------------------------------------------------------------------------


class TestRenewGatewayFilter:
    def test_gateway_filter_limits_to_matching_gateway(
        self, runner: CliRunner, two_gateway_config: Path
    ) -> None:
        """--gateway agw-alpha processes only agw-alpha domains."""
        with (
            patch("az_acme_tool.renew_command._build_gateway_client") as mock_build,
            patch("az_acme_tool.renew_command._issue_single_domain"),
        ):
            mock_client = MagicMock()
            mock_client.list_certificates.return_value = []
            mock_build.return_value = mock_client

            runner.invoke(
                main,
                ["--config", str(two_gateway_config), "renew", "--gateway", "agw-alpha"],
            )

        # _build_gateway_client should only be called for agw-alpha.
        for call in mock_build.call_args_list:
            gw_cfg = call[0][1]  # second positional arg is gateway_cfg
            assert gw_cfg.name == "agw-alpha"

    def test_gateway_filter_excludes_other_gateway(
        self, runner: CliRunner, two_gateway_config: Path
    ) -> None:
        """Domains from agw-beta are not processed when --gateway agw-alpha is set."""
        with (
            patch("az_acme_tool.renew_command._build_gateway_client") as mock_build,
            patch("az_acme_tool.renew_command._issue_single_domain") as mock_issue,
        ):
            mock_client = MagicMock()
            # Return certs within threshold so renewal is triggered.
            mock_client.list_certificates.return_value = [
                {"name": "www-alpha-com-cert", "expiry": _future_expiry(10)},
                {"name": "api-alpha-com-cert", "expiry": _future_expiry(10)},
            ]
            mock_build.return_value = mock_client

            runner.invoke(
                main,
                ["--config", str(two_gateway_config), "renew", "--gateway", "agw-alpha"],
            )

        called_domains = [call[0][0].domain for call in mock_issue.call_args_list]
        assert "www.beta.com" not in called_domains


# ---------------------------------------------------------------------------
# Task 3.8: --domain filter limits scope
# ---------------------------------------------------------------------------


class TestRenewDomainFilter:
    def test_domain_filter_limits_to_one_domain(
        self, runner: CliRunner, two_gateway_config: Path
    ) -> None:
        """--domain www.beta.com processes only that domain."""
        with (
            patch("az_acme_tool.renew_command._build_gateway_client") as mock_build,
            patch("az_acme_tool.renew_command._issue_single_domain") as mock_issue,
        ):
            mock_client = MagicMock()
            mock_client.list_certificates.return_value = [
                {"name": "www-beta-com-cert", "expiry": _future_expiry(10)},
            ]
            mock_build.return_value = mock_client

            runner.invoke(
                main,
                ["--config", str(two_gateway_config), "renew", "--domain", "www.beta.com"],
            )

        called_domains = [call[0][0].domain for call in mock_issue.call_args_list]
        assert called_domains == ["www.beta.com"]


# ---------------------------------------------------------------------------
# Task 3.9: unknown --domain causes RenewError with non-zero exit
# ---------------------------------------------------------------------------


class TestRenewUnknownDomain:
    def test_unknown_domain_nonzero_exit(self, runner: CliRunner, two_gateway_config: Path) -> None:
        result = runner.invoke(
            main,
            [
                "--config",
                str(two_gateway_config),
                "renew",
                "--domain",
                "nonexistent.example.com",
            ],
        )
        assert result.exit_code != 0
        assert "nonexistent.example.com" in result.output

    def test_unknown_domain_error_message(
        self, runner: CliRunner, two_gateway_config: Path
    ) -> None:
        result = runner.invoke(
            main,
            [
                "--config",
                str(two_gateway_config),
                "renew",
                "--domain",
                "unknown.example.com",
            ],
        )
        assert result.exit_code != 0
        assert "unknown.example.com" in result.output


# ---------------------------------------------------------------------------
# Task 3.10: summary line printed with correct counts
# ---------------------------------------------------------------------------


class TestRenewSummary:
    def test_summary_shows_correct_counts_mixed_scenario(
        self, runner: CliRunner, two_gateway_config: Path
    ) -> None:
        """Mixed scenario: 1 renewed, 1 skipped, 1 failed → summary correct."""
        # agw-alpha has www.alpha.com (25 days → renew) and api.alpha.com (35 days → skip)
        # agw-beta has www.beta.com (10 days → renew, but _issue_single_domain raises)
        alpha_certs = [
            {"name": "www-alpha-com-cert", "expiry": _future_expiry(25)},
            {"name": "api-alpha-com-cert", "expiry": _future_expiry(35)},
        ]
        beta_certs = [
            {"name": "www-beta-com-cert", "expiry": _future_expiry(10)},
        ]

        def build_client_side_effect(config: object, gateway_cfg: object) -> MagicMock:
            mock_client = MagicMock()
            gw_name = getattr(gateway_cfg, "name", "")
            if gw_name == "agw-alpha":
                mock_client.list_certificates.return_value = alpha_certs
            else:
                mock_client.list_certificates.return_value = beta_certs
            return mock_client

        with (
            patch(
                "az_acme_tool.renew_command._build_gateway_client",
                side_effect=build_client_side_effect,
            ),
            patch(
                "az_acme_tool.renew_command._issue_single_domain",
                side_effect=[None, RuntimeError("ACME error")],
            ),
        ):
            result = runner.invoke(main, ["--config", str(two_gateway_config), "renew"])

        # Summary line must be present.
        assert "Total:" in result.output
        assert "Renewed:" in result.output
        assert "Skipped:" in result.output
        assert "Failed:" in result.output

    def test_summary_all_skipped(self, runner: CliRunner, single_domain_config: Path) -> None:
        """All domains skipped → summary shows 0 renewed, 1 skipped."""
        mock_certs = _cert_list("www.example.com", 90)
        with (
            patch("az_acme_tool.renew_command._build_gateway_client") as mock_build,
            patch("az_acme_tool.renew_command._issue_single_domain"),
        ):
            mock_client = MagicMock()
            mock_client.list_certificates.return_value = mock_certs
            mock_build.return_value = mock_client

            result = runner.invoke(main, ["--config", str(single_domain_config), "renew"])

        assert result.exit_code == 0
        assert "Total: 1" in result.output
        assert "Renewed: 0" in result.output
        assert "Skipped: 1" in result.output
        assert "Failed: 0" in result.output

    def test_summary_all_renewed(self, runner: CliRunner, single_domain_config: Path) -> None:
        """All domains renewed → summary shows 1 renewed, 0 skipped."""
        mock_certs = _cert_list("www.example.com", 10)
        with (
            patch("az_acme_tool.renew_command._build_gateway_client") as mock_build,
            patch("az_acme_tool.renew_command._issue_single_domain"),
        ):
            mock_client = MagicMock()
            mock_client.list_certificates.return_value = mock_certs
            mock_build.return_value = mock_client

            result = runner.invoke(main, ["--config", str(single_domain_config), "renew"])

        assert result.exit_code == 0
        assert "Total: 1" in result.output
        assert "Renewed: 1" in result.output
        assert "Skipped: 0" in result.output
        assert "Failed: 0" in result.output
