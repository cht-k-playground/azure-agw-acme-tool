"""Tests for az_acme_tool.issue_command and the `issue` CLI command."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from az_acme_tool.cli import main
from az_acme_tool.config import parse_config
from az_acme_tool.issue_command import (
    DomainTarget,
    IssueError,
    _issue_single_domain,
    _resolve_targets,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


def _write_config(tmp_path: Path, gateways: list[dict]) -> Path:  # type: ignore[type-arg]
    """Write a minimal valid config YAML and return its path."""
    cfg = {
        "acme": {
            "email": "test@example.com",
            "directory_url": "https://acme-staging-v02.api.letsencrypt.org/directory",
            "account_key_path": "/tmp/account.key",
        },
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
                "acme_function_name": "alpha-acme-func",
                "domains": [
                    {"domain": "www.alpha.com", "cert_store": "agw_direct"},
                    {"domain": "api.alpha.com", "cert_store": "agw_direct"},
                ],
            },
            {
                "name": "agw-beta",
                "acme_function_name": "beta-acme-func",
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
        cfg = parse_config(two_gateway_config)
        targets = _resolve_targets(cfg, None, None)
        domains = [t.domain for t in targets]
        assert "www.alpha.com" in domains
        assert "api.alpha.com" in domains
        assert "www.beta.com" in domains
        assert len(targets) == 3

    def test_gateway_filter(self, two_gateway_config: Path) -> None:
        cfg = parse_config(two_gateway_config)
        targets = _resolve_targets(cfg, "agw-alpha", None)
        assert all(t.gateway_name == "agw-alpha" for t in targets)
        assert len(targets) == 2

    def test_domain_filter(self, two_gateway_config: Path) -> None:
        cfg = parse_config(two_gateway_config)
        targets = _resolve_targets(cfg, None, "www.beta.com")
        assert len(targets) == 1
        assert targets[0].domain == "www.beta.com"

    def test_combined_filter(self, two_gateway_config: Path) -> None:
        cfg = parse_config(two_gateway_config)
        targets = _resolve_targets(cfg, "agw-alpha", "api.alpha.com")
        assert len(targets) == 1
        assert targets[0].domain == "api.alpha.com"

    def test_unknown_domain_raises_issue_error(self, two_gateway_config: Path) -> None:
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


# ---------------------------------------------------------------------------
# _issue_single_domain — 14-step ACME pipeline
# ---------------------------------------------------------------------------


class TestIssueSingleDomain:
    """Tests for the 14-step ACME HTTP-01 pipeline.

    All Azure SDK and ACME library calls are mocked at the boundaries:
    ``AcmeClient`` and ``AzureGatewayClient`` are patched in the
    ``az_acme_tool.issue_command`` module.
    """

    @staticmethod
    def _build_order_with_http01(domain: str) -> MagicMock:
        """Build a mock order whose authorizations contain one HTTP01 challenge."""
        order = MagicMock()
        # Use a tiny class whose name is "HTTP01" so the implementation can
        # detect it via type(...).__name__ without importing the real class.
        http01 = type("HTTP01", (), {})()
        challb = MagicMock()
        challb.chall = http01
        authzr = MagicMock()
        authzr.body.identifier.value = domain
        authzr.body.challenges = [challb]
        order.authorizations = [authzr]
        return order

    def test_calls_all_14_steps_in_order(self, tmp_path: Path) -> None:
        """The 14-step pipeline calls every method in the documented order."""
        gateways = [
            {
                "name": "agw-alpha",
                "acme_function_name": "alpha-acme-func",
                "domains": [{"domain": "www.alpha.com", "cert_store": "agw_direct"}],
            }
        ]
        config_path = _write_config(tmp_path, gateways)
        config = parse_config(config_path)
        target = DomainTarget(gateway_name="agw-alpha", domain="www.alpha.com")

        acme = MagicMock()
        order = self._build_order_with_http01("www.alpha.com")
        acme.new_order.return_value = order
        acme.get_http01_challenge.return_value = ("TOKEN", "TOKEN.KEYAUTH")
        acme.finalize_order.return_value = order
        acme.download_certificate.return_value = (
            "-----BEGIN CERTIFICATE-----\nfake\n-----END CERTIFICATE-----\n"
        )

        agw = MagicMock()
        agw.get_listeners_by_cert_name.return_value = ["listener-1", "listener-2"]

        with (
            patch("az_acme_tool.issue_command._build_acme_client", return_value=acme),
            patch("az_acme_tool.issue_command._build_gateway_client", return_value=agw),
            patch(
                "az_acme_tool.issue_command.pem_to_pfx",
                return_value=b"FAKE_PFX_BYTES",
            ),
            patch(
                "az_acme_tool.issue_command.generate_csr",
                return_value=b"FAKE_CSR_DER",
            ),
            patch(
                "az_acme_tool.issue_command._generate_domain_key_pem",
                return_value=(
                    "-----BEGIN RSA PRIVATE KEY-----\nfake\n-----END RSA PRIVATE KEY-----\n"
                ),
            ),
            patch("az_acme_tool.issue_command.time.time", return_value=1709030400),
        ):
            _issue_single_domain(target, config)

        # Step 2: register account
        acme.register_account.assert_called_once()
        reg_kwargs = acme.register_account.call_args.kwargs
        assert reg_kwargs["email"] == "test@example.com"
        # Step 3: new_order
        acme.new_order.assert_called_once_with(["www.alpha.com"])
        # Step 4: get_http01_challenge
        acme.get_http01_challenge.assert_called_once_with(order, "www.alpha.com")
        # Step 5: update_function_app_settings
        agw.update_function_app_settings.assert_called_once()
        ufas_kwargs = agw.update_function_app_settings.call_args.kwargs
        assert ufas_kwargs["function_app_name"] == "alpha-acme-func"
        assert ufas_kwargs["settings"] == {"ACME_CHALLENGE_RESPONSE": "TOKEN.KEYAUTH"}
        # Step 6: add_routing_rule with timestamped name
        agw.add_routing_rule.assert_called_once()
        arr_kwargs = agw.add_routing_rule.call_args.kwargs
        assert arr_kwargs["rule_name"] == "acme-challenge-www-alpha-com-1709030400"
        assert arr_kwargs["domain"] == "www.alpha.com"
        assert arr_kwargs["backend_fqdn"] == "alpha-acme-func.azurewebsites.net"
        # Step 7: answer_challenge
        acme.answer_challenge.assert_called_once()
        # Step 8: poll_until_valid
        acme.poll_until_valid.assert_called_once_with(order)
        # Step 9: finalize_order with the production CSR
        acme.finalize_order.assert_called_once()
        assert acme.finalize_order.call_args.args[1] == b"FAKE_CSR_DER"
        # Step 10: download_certificate
        acme.download_certificate.assert_called_once_with(order)
        # Step 12: upload_ssl_certificate with cert_name and PFX bytes
        agw.upload_ssl_certificate.assert_called_once()
        usc_kwargs = agw.upload_ssl_certificate.call_args.kwargs
        assert usc_kwargs["cert_name"] == "www-alpha-com-cert"
        assert usc_kwargs["pfx_data"] == b"FAKE_PFX_BYTES"
        # Step 13: get_listeners_by_cert_name + update_listener_certificate per listener
        agw.get_listeners_by_cert_name.assert_called_once_with("www-alpha-com-cert")
        assert agw.update_listener_certificate.call_count == 2
        # Step 14: delete_routing_rule cleanup
        agw.delete_routing_rule.assert_called_once_with(
            "acme-challenge-www-alpha-com-1709030400"
        )

    def test_delete_routing_rule_called_on_step7_failure(
        self, tmp_path: Path
    ) -> None:
        """If answer_challenge (step 7) raises, the temporary rule is still deleted."""
        gateways = [
            {
                "name": "agw-alpha",
                "acme_function_name": "alpha-acme-func",
                "domains": [{"domain": "www.alpha.com", "cert_store": "agw_direct"}],
            }
        ]
        config = parse_config(_write_config(tmp_path, gateways))
        target = DomainTarget(gateway_name="agw-alpha", domain="www.alpha.com")

        acme = MagicMock()
        order = self._build_order_with_http01("www.alpha.com")
        acme.new_order.return_value = order
        acme.get_http01_challenge.return_value = ("T", "T.KA")
        acme.answer_challenge.side_effect = RuntimeError("ACME boom")

        agw = MagicMock()

        with (
            patch("az_acme_tool.issue_command._build_acme_client", return_value=acme),
            patch("az_acme_tool.issue_command._build_gateway_client", return_value=agw),
        ):
            with pytest.raises(RuntimeError, match="ACME boom"):
                _issue_single_domain(target, config)

        # The temporary rule must still be deleted via the finally block.
        agw.delete_routing_rule.assert_called_once()
        # And subsequent steps must NOT have run.
        acme.finalize_order.assert_not_called()
        agw.upload_ssl_certificate.assert_not_called()

    def test_pfx_password_not_in_logs(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """The randomly generated PFX password must not appear in any log message."""
        gateways = [
            {
                "name": "agw-alpha",
                "acme_function_name": "alpha-acme-func",
                "domains": [{"domain": "www.alpha.com", "cert_store": "agw_direct"}],
            }
        ]
        config = parse_config(_write_config(tmp_path, gateways))
        target = DomainTarget(gateway_name="agw-alpha", domain="www.alpha.com")

        captured_password: dict[str, str] = {}

        def _capture_upload(**kwargs: object) -> None:
            captured_password["pw"] = str(kwargs["password"])

        acme = MagicMock()
        order = self._build_order_with_http01("www.alpha.com")
        acme.new_order.return_value = order
        acme.get_http01_challenge.return_value = ("T", "T.KA")
        acme.finalize_order.return_value = order
        acme.download_certificate.return_value = (
            "-----BEGIN CERTIFICATE-----\nfake\n-----END CERTIFICATE-----\n"
        )

        agw = MagicMock()
        agw.upload_ssl_certificate.side_effect = _capture_upload
        agw.get_listeners_by_cert_name.return_value = []

        with (
            patch("az_acme_tool.issue_command._build_acme_client", return_value=acme),
            patch("az_acme_tool.issue_command._build_gateway_client", return_value=agw),
            patch(
                "az_acme_tool.issue_command.pem_to_pfx",
                return_value=b"FAKE_PFX_BYTES",
            ),
            patch(
                "az_acme_tool.issue_command.generate_csr",
                return_value=b"FAKE_CSR_DER",
            ),
            patch(
                "az_acme_tool.issue_command._generate_domain_key_pem",
                return_value=(
                    "-----BEGIN RSA PRIVATE KEY-----\nfake\n-----END RSA PRIVATE KEY-----\n"
                ),
            ),
            caplog.at_level(logging.DEBUG, logger="az_acme_tool.issue_command"),
        ):
            _issue_single_domain(target, config)

        secret = captured_password["pw"]
        assert secret  # sanity: the password was actually generated
        assert secret not in caplog.text
