"""Configuration schema and loader for az-acme-tool.

Provides typed Pydantic v2 models representing the YAML configuration file
and a single public entry-point ``parse_config()`` that reads, validates, and
returns an ``AppConfig`` instance.  All configuration failures are surfaced as
``ConfigError``.
"""

from __future__ import annotations

import re
import uuid
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, EmailStr, Field, ValidationError, field_validator

# ---------------------------------------------------------------------------
# Default configuration path
# ---------------------------------------------------------------------------

_DEFAULT_CONFIG_PATH: Path = Path("~/.config/az-acme-tool/config.yaml").expanduser()

# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class ConfigError(Exception):
    """Raised for all configuration loading and validation failures."""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AuthMethod(StrEnum):
    """Authentication method for Azure SDK calls."""

    default = "default"
    service_principal = "service_principal"
    managed_identity = "managed_identity"


class CertStore(StrEnum):
    """Certificate store backend (Phase 1: Application Gateway direct only)."""

    agw_direct = "agw_direct"


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

# Conservative FQDN regex: labels of 1–63 alphanumeric/hyphen chars, TLD ≥ 2 alpha chars.
_FQDN_RE = re.compile(r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$")


class AcmeConfig(BaseModel):
    """ACME provider configuration."""

    email: EmailStr


class AzureConfig(BaseModel):
    """Azure subscription and authentication configuration."""

    subscription_id: uuid.UUID
    resource_group: str = Field(..., min_length=1)
    auth_method: AuthMethod


class DomainConfig(BaseModel):
    """Per-domain certificate configuration."""

    domain: str
    cert_store: CertStore

    @field_validator("domain")
    @classmethod
    def validate_fqdn(cls, value: str) -> str:
        """Ensure the domain field is a valid FQDN."""
        if not _FQDN_RE.match(value):
            raise ValueError(f"'{value}' is not a valid fully-qualified domain name")
        return value


class GatewayConfig(BaseModel):
    """Application Gateway configuration with one or more domain entries."""

    name: str = Field(..., min_length=1)
    domains: list[DomainConfig] = Field(..., min_length=1)


class AppConfig(BaseModel):
    """Root configuration object composed from all sub-configs."""

    acme: AcmeConfig
    azure: AzureConfig
    gateways: list[GatewayConfig] = Field(..., min_length=1)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def _extract_field_names(exc: ValidationError) -> str:
    """Return a human-readable comma-separated list of failing field paths."""
    parts: list[str] = []
    for error in exc.errors():
        loc = " -> ".join(str(part) for part in error["loc"])
        msg = error["msg"]
        parts.append(f"{loc}: {msg}")
    return "; ".join(parts)


def parse_config(path: Path = _DEFAULT_CONFIG_PATH) -> AppConfig:
    """Read, parse, and validate the YAML configuration file at *path*.

    Parameters
    ----------
    path:
        Filesystem path to the YAML configuration file.  Defaults to
        ``~/.config/az-acme-tool/config.yaml``.

    Returns
    -------
    AppConfig
        A fully-validated configuration object.

    Raises
    ------
    ConfigError
        If the file is not found, contains invalid YAML, is empty, or fails
        Pydantic validation.
    """
    try:
        raw_text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ConfigError(f"Configuration file not found: {path}")

    try:
        data: Any = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"Failed to parse YAML configuration: {exc}") from exc

    if data is None:
        raise ConfigError("Configuration file is empty")

    try:
        return AppConfig.model_validate(data)
    except ValidationError as exc:
        details = _extract_field_names(exc)
        raise ConfigError(f"Configuration validation failed: {details}") from exc
