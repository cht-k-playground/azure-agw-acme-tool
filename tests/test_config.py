"""Unit tests for az_acme_tool.config module."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from az_acme_tool.config import (
    AppConfig,
    AuthMethod,
    CertStore,
    ConfigError,
    parse_config,
)

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

_VALID_CONFIG: dict[str, Any] = {
    "acme": {"email": "admin@example.com"},
    "azure": {
        "subscription_id": "123e4567-e89b-12d3-a456-426614174000",
        "resource_group": "my-rg",
        "auth_method": "default",
    },
    "gateways": [
        {
            "name": "my-gateway",
            "domains": [
                {"domain": "example.com", "cert_store": "agw_direct"},
            ],
        }
    ],
}


@pytest.fixture()
def valid_config_file(tmp_path: Path) -> Path:
    """Write a valid minimal YAML config to a temporary file and return its path."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump(_VALID_CONFIG), encoding="utf-8")
    return config_file


# ---------------------------------------------------------------------------
# Task 5.2 — valid full config returns correct AppConfig
# ---------------------------------------------------------------------------


def test_parse_config_valid_returns_app_config(valid_config_file: Path) -> None:
    """parse_config() with a fully valid YAML returns a correct AppConfig instance."""
    result = parse_config(valid_config_file)

    assert isinstance(result, AppConfig)
    assert result.acme.email == "admin@example.com"
    assert str(result.azure.subscription_id) == "123e4567-e89b-12d3-a456-426614174000"
    assert result.azure.resource_group == "my-rg"
    assert result.azure.auth_method == AuthMethod.default
    assert len(result.gateways) == 1
    assert result.gateways[0].name == "my-gateway"
    assert len(result.gateways[0].domains) == 1
    assert result.gateways[0].domains[0].domain == "example.com"
    assert result.gateways[0].domains[0].cert_store == CertStore.agw_direct


# ---------------------------------------------------------------------------
# Task 5.3 — missing acme_email raises ConfigError naming acme_email
# ---------------------------------------------------------------------------


def test_missing_acme_email_raises_config_error(tmp_path: Path) -> None:
    """Missing acme_email raises ConfigError that names the failing field."""
    data: dict[str, Any] = {
        "acme": {},  # email missing
        "azure": {
            "subscription_id": "123e4567-e89b-12d3-a456-426614174000",
            "resource_group": "my-rg",
            "auth_method": "default",
        },
        "gateways": [
            {
                "name": "gw",
                "domains": [{"domain": "example.com", "cert_store": "agw_direct"}],
            }
        ],
    }
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump(data), encoding="utf-8")

    with pytest.raises(ConfigError) as exc_info:
        parse_config(config_file)

    assert "email" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Task 5.4 — missing subscription_id raises ConfigError naming subscription_id
# ---------------------------------------------------------------------------


def test_missing_subscription_id_raises_config_error(tmp_path: Path) -> None:
    """Missing subscription_id raises ConfigError that names the failing field."""
    data: dict[str, Any] = {
        "acme": {"email": "admin@example.com"},
        "azure": {
            # subscription_id missing
            "resource_group": "my-rg",
            "auth_method": "default",
        },
        "gateways": [
            {
                "name": "gw",
                "domains": [{"domain": "example.com", "cert_store": "agw_direct"}],
            }
        ],
    }
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump(data), encoding="utf-8")

    with pytest.raises(ConfigError) as exc_info:
        parse_config(config_file)

    assert "subscription_id" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Task 5.5 — missing resource_group raises ConfigError naming resource_group
# ---------------------------------------------------------------------------


def test_missing_resource_group_raises_config_error(tmp_path: Path) -> None:
    """Missing resource_group raises ConfigError that names the failing field."""
    data: dict[str, Any] = {
        "acme": {"email": "admin@example.com"},
        "azure": {
            "subscription_id": "123e4567-e89b-12d3-a456-426614174000",
            # resource_group missing
            "auth_method": "default",
        },
        "gateways": [
            {
                "name": "gw",
                "domains": [{"domain": "example.com", "cert_store": "agw_direct"}],
            }
        ],
    }
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump(data), encoding="utf-8")

    with pytest.raises(ConfigError) as exc_info:
        parse_config(config_file)

    assert "resource_group" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Task 5.6 — non-UUID subscription_id raises ConfigError
# ---------------------------------------------------------------------------


def test_non_uuid_subscription_id_raises_config_error(tmp_path: Path) -> None:
    """Non-UUID subscription_id raises ConfigError."""
    data: dict[str, Any] = {
        "acme": {"email": "admin@example.com"},
        "azure": {
            "subscription_id": "not-a-uuid",
            "resource_group": "my-rg",
            "auth_method": "default",
        },
        "gateways": [
            {
                "name": "gw",
                "domains": [{"domain": "example.com", "cert_store": "agw_direct"}],
            }
        ],
    }
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump(data), encoding="utf-8")

    with pytest.raises(ConfigError):
        parse_config(config_file)


# ---------------------------------------------------------------------------
# Task 5.7 — invalid email raises ConfigError
# ---------------------------------------------------------------------------


def test_invalid_email_raises_config_error(tmp_path: Path) -> None:
    """Invalid email in acme_email raises ConfigError."""
    data: dict[str, Any] = {
        "acme": {"email": "not-an-email"},
        "azure": {
            "subscription_id": "123e4567-e89b-12d3-a456-426614174000",
            "resource_group": "my-rg",
            "auth_method": "default",
        },
        "gateways": [
            {
                "name": "gw",
                "domains": [{"domain": "example.com", "cert_store": "agw_direct"}],
            }
        ],
    }
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump(data), encoding="utf-8")

    with pytest.raises(ConfigError):
        parse_config(config_file)


# ---------------------------------------------------------------------------
# Task 5.8 — invalid auth_method raises ConfigError
# ---------------------------------------------------------------------------


def test_invalid_auth_method_raises_config_error(tmp_path: Path) -> None:
    """Invalid auth_method value raises ConfigError."""
    data: dict[str, Any] = {
        "acme": {"email": "admin@example.com"},
        "azure": {
            "subscription_id": "123e4567-e89b-12d3-a456-426614174000",
            "resource_group": "my-rg",
            "auth_method": "invalid_auth",
        },
        "gateways": [
            {
                "name": "gw",
                "domains": [{"domain": "example.com", "cert_store": "agw_direct"}],
            }
        ],
    }
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump(data), encoding="utf-8")

    with pytest.raises(ConfigError):
        parse_config(config_file)


# ---------------------------------------------------------------------------
# Task 5.9 — invalid cert_store raises ConfigError
# ---------------------------------------------------------------------------


def test_invalid_cert_store_raises_config_error(tmp_path: Path) -> None:
    """Invalid cert_store value raises ConfigError."""
    data: dict[str, Any] = {
        "acme": {"email": "admin@example.com"},
        "azure": {
            "subscription_id": "123e4567-e89b-12d3-a456-426614174000",
            "resource_group": "my-rg",
            "auth_method": "default",
        },
        "gateways": [
            {
                "name": "gw",
                "domains": [{"domain": "example.com", "cert_store": "key_vault"}],
            }
        ],
    }
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump(data), encoding="utf-8")

    with pytest.raises(ConfigError):
        parse_config(config_file)


# ---------------------------------------------------------------------------
# Task 5.10 — invalid FQDN raises ConfigError
# ---------------------------------------------------------------------------


def test_invalid_fqdn_raises_config_error(tmp_path: Path) -> None:
    """Invalid FQDN in domain raises ConfigError."""
    data: dict[str, Any] = {
        "acme": {"email": "admin@example.com"},
        "azure": {
            "subscription_id": "123e4567-e89b-12d3-a456-426614174000",
            "resource_group": "my-rg",
            "auth_method": "default",
        },
        "gateways": [
            {
                "name": "gw",
                "domains": [{"domain": "not a valid domain!", "cert_store": "agw_direct"}],
            }
        ],
    }
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump(data), encoding="utf-8")

    with pytest.raises(ConfigError):
        parse_config(config_file)


# ---------------------------------------------------------------------------
# Task 5.11 — file not found raises ConfigError
# ---------------------------------------------------------------------------


def test_file_not_found_raises_config_error(tmp_path: Path) -> None:
    """File not found raises ConfigError."""
    non_existent = tmp_path / "does_not_exist.yaml"

    with pytest.raises(ConfigError) as exc_info:
        parse_config(non_existent)

    assert "not found" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Task 5.12 — malformed YAML raises ConfigError
# ---------------------------------------------------------------------------


def test_malformed_yaml_raises_config_error(tmp_path: Path) -> None:
    """Malformed YAML raises ConfigError."""
    config_file = tmp_path / "bad.yaml"
    config_file.write_text("key: [unclosed bracket\n", encoding="utf-8")

    with pytest.raises(ConfigError) as exc_info:
        parse_config(config_file)

    assert "yaml" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Task 5.13 — empty YAML file raises ConfigError("Configuration file is empty")
# ---------------------------------------------------------------------------


def test_empty_yaml_raises_config_error(tmp_path: Path) -> None:
    """Empty YAML file raises ConfigError with 'Configuration file is empty' message."""
    config_file = tmp_path / "empty.yaml"
    config_file.write_text("", encoding="utf-8")

    with pytest.raises(ConfigError, match="Configuration file is empty"):
        parse_config(config_file)


# ---------------------------------------------------------------------------
# Task 5.14 — all three valid auth_method values are accepted
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "auth_method_value, expected_member",
    [
        ("default", AuthMethod.default),
        ("service_principal", AuthMethod.service_principal),
        ("managed_identity", AuthMethod.managed_identity),
    ],
)
def test_all_auth_method_values_accepted(
    tmp_path: Path, auth_method_value: str, expected_member: AuthMethod
) -> None:
    """All three valid auth_method values are accepted and map to enum members."""
    data: dict[str, Any] = {
        "acme": {"email": "admin@example.com"},
        "azure": {
            "subscription_id": "123e4567-e89b-12d3-a456-426614174000",
            "resource_group": "my-rg",
            "auth_method": auth_method_value,
        },
        "gateways": [
            {
                "name": "gw",
                "domains": [{"domain": "example.com", "cert_store": "agw_direct"}],
            }
        ],
    }
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump(data), encoding="utf-8")

    result = parse_config(config_file)
    assert result.azure.auth_method == expected_member


# ---------------------------------------------------------------------------
# S-2a — empty gateways list raises ConfigError
# ---------------------------------------------------------------------------


def test_empty_gateways_raises_config_error(tmp_path: Path) -> None:
    """parse_config() raises ConfigError when gateways is an empty list."""
    data: dict[str, Any] = {
        "acme": {"email": "test@example.com"},
        "azure": {
            "subscription_id": "12345678-1234-1234-1234-123456789012",
            "resource_group": "my-rg",
            "auth_method": "default",
        },
        "gateways": [],
    }
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump(data), encoding="utf-8")

    with pytest.raises(ConfigError):
        parse_config(config_file)


# ---------------------------------------------------------------------------
# S-2b — gateway with empty domains list raises ConfigError
# ---------------------------------------------------------------------------


def test_empty_domains_raises_config_error(tmp_path: Path) -> None:
    """parse_config() raises ConfigError when a gateway's domains is an empty list."""
    data: dict[str, Any] = {
        "acme": {"email": "test@example.com"},
        "azure": {
            "subscription_id": "12345678-1234-1234-1234-123456789012",
            "resource_group": "my-rg",
            "auth_method": "default",
        },
        "gateways": [
            {
                "name": "my-agw",
                "domains": [],
            }
        ],
    }
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump(data), encoding="utf-8")

    with pytest.raises(ConfigError):
        parse_config(config_file)


# ---------------------------------------------------------------------------
# Task 5.15 — cert_store: agw_direct is accepted and maps to CertStore.agw_direct
# ---------------------------------------------------------------------------


def test_agw_direct_cert_store_accepted(tmp_path: Path) -> None:
    """cert_store: agw_direct is accepted and maps to CertStore.agw_direct."""
    data: dict[str, Any] = {
        "acme": {"email": "admin@example.com"},
        "azure": {
            "subscription_id": "123e4567-e89b-12d3-a456-426614174000",
            "resource_group": "my-rg",
            "auth_method": "default",
        },
        "gateways": [
            {
                "name": "gw",
                "domains": [{"domain": "sub.example.com", "cert_store": "agw_direct"}],
            }
        ],
    }
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump(data), encoding="utf-8")

    result = parse_config(config_file)
    assert result.gateways[0].domains[0].cert_store == CertStore.agw_direct
