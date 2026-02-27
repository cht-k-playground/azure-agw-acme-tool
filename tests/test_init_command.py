"""Tests for az_acme_tool.init_command and the `init` CLI command."""

from __future__ import annotations

import os
import stat
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from az_acme_tool.acme_client import AcmeError
from az_acme_tool.cli import main
from az_acme_tool.init_command import (
    _generate_and_write_key,
    run_init,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def runner() -> CliRunner:
    """Click test runner with isolated filesystem."""
    return CliRunner()


@pytest.fixture()
def isolated_runner(tmp_path: Path) -> CliRunner:
    """Click test runner; tests use tmp_path directly for file assertions."""
    return CliRunner(mix_stderr=False)


# ---------------------------------------------------------------------------
# _generate_and_write_key unit tests
# ---------------------------------------------------------------------------


class TestGenerateAndWriteKey:
    def test_creates_pem_file(self, tmp_path: Path) -> None:
        key_path = tmp_path / "account.key"
        _generate_and_write_key(key_path)
        assert key_path.exists()
        content = key_path.read_text()
        assert "PRIVATE KEY" in content

    def test_file_permissions_are_0600(self, tmp_path: Path) -> None:
        key_path = tmp_path / "account.key"
        _generate_and_write_key(key_path)
        mode = stat.S_IMODE(os.stat(key_path).st_mode)
        assert mode == 0o600

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        key_path = tmp_path / "nested" / "dir" / "account.key"
        _generate_and_write_key(key_path)
        assert key_path.exists()


# ---------------------------------------------------------------------------
# run_init unit tests
# ---------------------------------------------------------------------------


class TestRunInitTemplateMode:
    def test_template_printed_to_stdout(self, capsys: pytest.CaptureFixture[str]) -> None:
        run_init(config_path="~/.config/az-acme-tool/config.yaml", config_template=True)
        captured = capsys.readouterr()
        assert "acme_email" in captured.out or "email" in captured.out
        assert "subscription_id" in captured.out
        assert "resource_group" in captured.out
        assert "auth_method" in captured.out

    def test_template_contains_no_network_call(self) -> None:
        """Template mode must not import or call AcmeClient."""
        with patch("az_acme_tool.init_command.AcmeClient") as mock_acme:
            run_init(config_path="irrelevant", config_template=True)
            mock_acme.assert_not_called()

    def test_no_file_written_in_template_mode(self, tmp_path: Path) -> None:
        key_path = tmp_path / "account.key"
        with patch("az_acme_tool.init_command._DEFAULT_KEY_PATH", key_path):
            run_init(config_path="irrelevant", config_template=True)
        assert not key_path.exists()


# ---------------------------------------------------------------------------
# CLI integration tests via CliRunner
# ---------------------------------------------------------------------------


class TestInitCommandTemplate:
    def test_config_template_flag_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["init", "--config-template"])
        assert result.exit_code == 0

    def test_config_template_output_contains_required_keys(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["init", "--config-template"])
        assert result.exit_code == 0
        for key in ("subscription_id", "resource_group", "auth_method"):
            assert key in result.output

    def test_config_template_no_files_written(self, runner: CliRunner, tmp_path: Path) -> None:
        fake_key = tmp_path / "account.key"
        with patch("az_acme_tool.init_command._DEFAULT_KEY_PATH", fake_key):
            result = runner.invoke(main, ["init", "--config-template"])
        assert result.exit_code == 0
        assert not fake_key.exists()


class TestInitCommandRegistration:
    def _make_mock_config(self, email: str = "user@example.com") -> MagicMock:
        cfg = MagicMock()
        cfg.acme.email = email
        return cfg

    def test_key_created_with_correct_permissions(self, runner: CliRunner, tmp_path: Path) -> None:
        key_path = tmp_path / "account.key"
        config_path = tmp_path / "config.yaml"
        mock_cfg = self._make_mock_config()

        with (
            patch("az_acme_tool.init_command._DEFAULT_KEY_PATH", key_path),
            patch("az_acme_tool.init_command.AcmeClient") as mock_acme_cls,
            patch("az_acme_tool.init_command.parse_config", return_value=mock_cfg),
        ):
            mock_acme_cls.return_value.register_account.return_value = (
                "https://acme-v02.api.letsencrypt.org/acme/acct/123"
            )
            result = runner.invoke(
                main,
                ["--config", str(config_path), "init"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0, result.output
        assert key_path.exists()
        mode = stat.S_IMODE(os.stat(key_path).st_mode)
        assert mode == 0o600

    def test_account_url_printed(self, runner: CliRunner, tmp_path: Path) -> None:
        key_path = tmp_path / "account.key"
        config_path = tmp_path / "config.yaml"
        account_url = "https://acme-v02.api.letsencrypt.org/acme/acct/456"
        mock_cfg = self._make_mock_config()

        with (
            patch("az_acme_tool.init_command._DEFAULT_KEY_PATH", key_path),
            patch("az_acme_tool.init_command.AcmeClient") as mock_acme_cls,
            patch("az_acme_tool.init_command.parse_config", return_value=mock_cfg),
        ):
            mock_acme_cls.return_value.register_account.return_value = account_url
            result = runner.invoke(
                main, ["--config", str(config_path), "init"], catch_exceptions=False
            )

        assert result.exit_code == 0
        assert account_url in result.output

    def test_register_account_called_once(self, runner: CliRunner, tmp_path: Path) -> None:
        key_path = tmp_path / "account.key"
        config_path = tmp_path / "config.yaml"
        mock_cfg = self._make_mock_config()

        with (
            patch("az_acme_tool.init_command._DEFAULT_KEY_PATH", key_path),
            patch("az_acme_tool.init_command.AcmeClient") as mock_acme_cls,
            patch("az_acme_tool.init_command.parse_config", return_value=mock_cfg),
        ):
            mock_acme_cls.return_value.register_account.return_value = "https://example.com/acct/1"
            runner.invoke(main, ["--config", str(config_path), "init"], catch_exceptions=False)
            mock_acme_cls.return_value.register_account.assert_called_once()

    def test_acme_error_causes_nonzero_exit(self, runner: CliRunner, tmp_path: Path) -> None:
        key_path = tmp_path / "account.key"
        config_path = tmp_path / "config.yaml"
        mock_cfg = self._make_mock_config()

        with (
            patch("az_acme_tool.init_command._DEFAULT_KEY_PATH", key_path),
            patch("az_acme_tool.init_command.AcmeClient") as mock_acme_cls,
            patch("az_acme_tool.init_command.parse_config", return_value=mock_cfg),
        ):
            mock_acme_cls.return_value.register_account.side_effect = AcmeError("CA unavailable")
            result = runner.invoke(main, ["--config", str(config_path), "init"])

        assert result.exit_code != 0


class TestInitCommandOverwriteGuard:
    def _make_mock_config(self, email: str = "user@example.com") -> MagicMock:
        cfg = MagicMock()
        cfg.acme.email = email
        return cfg

    def test_existing_key_not_overwritten_on_n(self, runner: CliRunner, tmp_path: Path) -> None:
        key_path = tmp_path / "account.key"
        original_content = b"ORIGINAL KEY CONTENT"
        key_path.write_bytes(original_content)
        config_path = tmp_path / "config.yaml"

        with (
            patch("az_acme_tool.init_command._DEFAULT_KEY_PATH", key_path),
            patch("az_acme_tool.init_command.AcmeClient") as mock_acme_cls,
            patch("az_acme_tool.init_command.parse_config", return_value=self._make_mock_config()),
        ):
            result = runner.invoke(main, ["--config", str(config_path), "init"], input="n\n")

        # Key unchanged
        assert key_path.read_bytes() == original_content
        # ACME registration not called
        mock_acme_cls.return_value.register_account.assert_not_called()
        assert result.exit_code == 0

    def test_existing_key_overwritten_on_y(self, runner: CliRunner, tmp_path: Path) -> None:
        key_path = tmp_path / "account.key"
        original_content = b"OLD KEY"
        key_path.write_bytes(original_content)
        config_path = tmp_path / "config.yaml"
        mock_cfg = self._make_mock_config()

        with (
            patch("az_acme_tool.init_command._DEFAULT_KEY_PATH", key_path),
            patch("az_acme_tool.init_command.AcmeClient") as mock_acme_cls,
            patch("az_acme_tool.init_command.parse_config", return_value=mock_cfg),
        ):
            mock_acme_cls.return_value.register_account.return_value = "https://example.com/acct/1"
            result = runner.invoke(main, ["--config", str(config_path), "init"], input="y\n")

        assert result.exit_code == 0
        # Key file replaced with new PEM content
        assert key_path.read_bytes() != original_content
        assert b"PRIVATE KEY" in key_path.read_bytes()
        mock_acme_cls.return_value.register_account.assert_called_once()
