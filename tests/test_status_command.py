"""Tests for az_acme_tool.status_command and the `status` CLI command."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from az_acme_tool.cli import main
from az_acme_tool.status_command import (
    CertStatusEntry,
    StatusError,
    _classify_status,
    _collect_status,
    _entry_to_dict,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


def _write_config(tmp_path: Path) -> Path:
    import yaml as _yaml

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
    config_path.write_text(_yaml.dump(cfg))
    return config_path


def _future_expiry(days: int = 60) -> datetime:
    return datetime.now(tz=UTC) + timedelta(days=days)


def _past_expiry(days: int = 10) -> datetime:
    return datetime.now(tz=UTC) - timedelta(days=days)


# ---------------------------------------------------------------------------
# _classify_status unit tests
# ---------------------------------------------------------------------------


class TestClassifyStatus:
    def test_31_days_is_valid(self) -> None:
        assert _classify_status(31) == "valid"

    def test_30_days_is_expiring_soon(self) -> None:
        assert _classify_status(30) == "expiring_soon"

    def test_29_days_is_expiring_soon(self) -> None:
        assert _classify_status(29) == "expiring_soon"

    def test_1_day_is_expiring_soon(self) -> None:
        assert _classify_status(1) == "expiring_soon"

    def test_0_days_is_expired(self) -> None:
        assert _classify_status(0) == "expired"

    def test_minus_1_day_is_expired(self) -> None:
        assert _classify_status(-1) == "expired"

    def test_none_days_is_valid(self) -> None:
        assert _classify_status(None) == "valid"


# ---------------------------------------------------------------------------
# _collect_status unit tests
# ---------------------------------------------------------------------------


class TestCollectStatus:
    def test_returns_entries_from_gateway(self, tmp_path: Path) -> None:
        from az_acme_tool.config import parse_config

        config_path = _write_config(tmp_path)
        config = parse_config(config_path)
        expiry = _future_expiry(90)

        with (
            patch("az_acme_tool.status_command.DefaultAzureCredential"),
            patch("az_acme_tool.status_command.AzureGatewayClient") as mock_client_cls,
        ):
            mock_client = MagicMock()
            mock_client.list_certificates.return_value = [
                {"name": "www-example-com-cert", "expiry": expiry}
            ]
            mock_client_cls.return_value = mock_client

            entries = _collect_status(config)

        assert len(entries) == 1
        assert entries[0].name == "www-example-com-cert"
        assert entries[0].status == "valid"

    def test_azure_error_raises_status_error(self, tmp_path: Path) -> None:
        from az_acme_tool.config import parse_config

        config_path = _write_config(tmp_path)
        config = parse_config(config_path)

        with (
            patch("az_acme_tool.status_command.DefaultAzureCredential"),
            patch("az_acme_tool.status_command.AzureGatewayClient") as mock_client_cls,
        ):
            mock_client = MagicMock()
            mock_client.list_certificates.side_effect = RuntimeError("Azure error")
            mock_client_cls.return_value = mock_client

            with pytest.raises(StatusError, match="agw-alpha"):
                _collect_status(config)


# ---------------------------------------------------------------------------
# _entry_to_dict tests
# ---------------------------------------------------------------------------


class TestEntryToDict:
    def test_expiry_is_iso_string(self) -> None:
        expiry = _future_expiry(50)
        entry = CertStatusEntry(
            gateway="agw",
            resource_group="rg",
            name="cert",
            expiry=expiry,
            days_remaining=50,
            status="valid",
        )
        d = _entry_to_dict(entry)
        assert d["expiry_date"] == expiry.isoformat()

    def test_none_expiry_is_null(self) -> None:
        entry = CertStatusEntry(
            gateway="agw",
            resource_group="rg",
            name="cert",
            expiry=None,
            days_remaining=None,
            status="valid",
        )
        d = _entry_to_dict(entry)
        assert d["expiry_date"] is None
        assert d["days_remaining"] is None


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------


class TestStatusCommandJson:
    def test_json_output_parseable(self, runner: CliRunner, tmp_path: Path) -> None:
        config_path = _write_config(tmp_path)
        expiry = _future_expiry(90)

        with (
            patch("az_acme_tool.status_command.DefaultAzureCredential"),
            patch("az_acme_tool.status_command.AzureGatewayClient") as mock_cls,
        ):
            mock_cls.return_value.list_certificates.return_value = [
                {"name": "test-cert", "expiry": expiry}
            ]
            result = runner.invoke(
                main, ["--config", str(config_path), "status", "--output", "json"]
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 1
        assert "gateway" in data[0]
        assert "name" in data[0]
        assert "status" in data[0]
        assert "expiry_date" in data[0]

    def test_json_valid_cert_has_valid_status(self, runner: CliRunner, tmp_path: Path) -> None:
        config_path = _write_config(tmp_path)
        expiry = _future_expiry(90)

        with (
            patch("az_acme_tool.status_command.DefaultAzureCredential"),
            patch("az_acme_tool.status_command.AzureGatewayClient") as mock_cls,
        ):
            mock_cls.return_value.list_certificates.return_value = [
                {"name": "valid-cert", "expiry": expiry}
            ]
            result = runner.invoke(
                main, ["--config", str(config_path), "status", "--output", "json"]
            )

        data = json.loads(result.output)
        assert data[0]["status"] == "valid"


class TestStatusCommandYaml:
    def test_yaml_output_parseable(self, runner: CliRunner, tmp_path: Path) -> None:
        config_path = _write_config(tmp_path)
        expiry = _future_expiry(90)

        with (
            patch("az_acme_tool.status_command.DefaultAzureCredential"),
            patch("az_acme_tool.status_command.AzureGatewayClient") as mock_cls,
        ):
            mock_cls.return_value.list_certificates.return_value = [
                {"name": "test-cert", "expiry": expiry}
            ]
            result = runner.invoke(
                main, ["--config", str(config_path), "status", "--output", "yaml"]
            )

        assert result.exit_code == 0
        data = yaml.safe_load(result.output)
        assert isinstance(data, list)


class TestStatusCommandTable:
    def test_table_output_contains_headers(self, runner: CliRunner, tmp_path: Path) -> None:
        config_path = _write_config(tmp_path)
        expiry = _future_expiry(90)

        with (
            patch("az_acme_tool.status_command.DefaultAzureCredential"),
            patch("az_acme_tool.status_command.AzureGatewayClient") as mock_cls,
        ):
            mock_cls.return_value.list_certificates.return_value = [
                {"name": "test-cert", "expiry": expiry}
            ]
            result = runner.invoke(main, ["--config", str(config_path), "status"])

        assert result.exit_code == 0
        # Rich table renders header labels
        assert (
            "Gateway" in result.output
            or "Certificate" in result.output
            or "Status" in result.output
        )
