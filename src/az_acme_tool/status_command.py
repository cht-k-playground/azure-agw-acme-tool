"""Implementation of the `az-acme-tool status` command.

Queries every configured Application Gateway for its SSL certificate metadata
and renders the results in Rich table, JSON, or YAML format.

All failures are surfaced as :class:`StatusError`.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from azure.identity import DefaultAzureCredential
from rich.console import Console
from rich.table import Table

from az_acme_tool.azure_gateway import AzureGatewayClient
from az_acme_tool.config import AppConfig, parse_config

logger = logging.getLogger(__name__)

# Status label constants
_STATUS_VALID = "valid"
_STATUS_EXPIRING = "expiring_soon"
_STATUS_EXPIRED = "expired"

_EXPIRY_THRESHOLD_DAYS = 30

# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class StatusError(Exception):
    """Raised for failures within the status command."""


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class CertStatusEntry:
    """Represents the status of a single certificate on a gateway."""

    gateway: str
    resource_group: str
    name: str
    expiry: datetime | None
    days_remaining: int | None
    status: str  # "valid" | "expiring_soon" | "expired"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _classify_status(days_remaining: int | None) -> str:
    """Return the status string for the given days-remaining value.

    Parameters
    ----------
    days_remaining:
        Number of full days until certificate expiry.  ``None`` means the
        expiry date is unknown (e.g. Key Vault reference).

    Returns
    -------
    str
        One of ``"valid"``, ``"expiring_soon"``, or ``"expired"``.
        Unknown expiry returns ``"valid"`` (conservative default).
    """
    if days_remaining is None:
        return _STATUS_VALID
    if days_remaining > _EXPIRY_THRESHOLD_DAYS:
        return _STATUS_VALID
    if days_remaining > 0:
        return _STATUS_EXPIRING
    return _STATUS_EXPIRED


def _collect_status(config: AppConfig) -> list[CertStatusEntry]:
    """Query all configured gateways and return certificate status entries.

    Parameters
    ----------
    config:
        Parsed application configuration.

    Returns
    -------
    list[CertStatusEntry]
        One entry per certificate found across all configured gateways.

    Raises
    ------
    StatusError
        If an Azure API call fails for any gateway.
    """
    credential = DefaultAzureCredential()
    entries: list[CertStatusEntry] = []
    now = datetime.now(tz=UTC)

    for gateway_cfg in config.gateways:
        client = AzureGatewayClient(
            subscription_id=str(config.azure.subscription_id),
            resource_group=config.azure.resource_group,
            gateway_name=gateway_cfg.name,
            credential=credential,
        )
        try:
            certs = client.list_certificates()
        except Exception as exc:
            raise StatusError(
                f"Failed to list certificates on gateway '{gateway_cfg.name}': {exc}"
            ) from exc

        for cert in certs:
            expiry: datetime | None = cert.get("expiry")
            days_remaining: int | None = None
            if expiry is not None:
                delta = expiry - now
                days_remaining = delta.days

            status = _classify_status(days_remaining)
            entries.append(
                CertStatusEntry(
                    gateway=gateway_cfg.name,
                    resource_group=config.azure.resource_group,
                    name=cert.get("name", ""),
                    expiry=expiry,
                    days_remaining=days_remaining,
                    status=status,
                )
            )

    return entries


def _render_table(entries: list[CertStatusEntry]) -> None:
    """Render certificate status as a Rich table to stdout."""
    console = Console()
    table = Table(show_header=True, header_style="bold")
    table.add_column("Gateway")
    table.add_column("Certificate")
    table.add_column("Expiry Date")
    table.add_column("Days Remaining")
    table.add_column("Status")

    for entry in entries:
        expiry_str = entry.expiry.strftime("%Y-%m-%d") if entry.expiry else "N/A"
        days_str = str(entry.days_remaining) if entry.days_remaining is not None else "N/A"
        if entry.status == _STATUS_VALID:
            status_str = "✅ Valid"
        elif entry.status == _STATUS_EXPIRING:
            status_str = "⚠️  Expiring Soon"
        else:
            status_str = "❌ Expired"
        table.add_row(entry.gateway, entry.name, expiry_str, days_str, status_str)

    console.print(table)


def _entry_to_dict(entry: CertStatusEntry) -> dict[str, Any]:
    """Convert a :class:`CertStatusEntry` to a JSON-serialisable dict."""
    return {
        "gateway": entry.gateway,
        "resource_group": entry.resource_group,
        "name": entry.name,
        "expiry_date": entry.expiry.isoformat() if entry.expiry else None,
        "days_remaining": entry.days_remaining,
        "status": entry.status,
    }


def _render_json(entries: list[CertStatusEntry]) -> None:
    """Print certificate status as a JSON array to stdout."""
    data = [_entry_to_dict(e) for e in entries]
    print(json.dumps(data, indent=2))


def _render_yaml(entries: list[CertStatusEntry]) -> None:
    """Print certificate status as YAML to stdout."""
    data = [_entry_to_dict(e) for e in entries]
    print(yaml.dump(data, default_flow_style=False, allow_unicode=True), end="")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_status(config_path: str, output_format: str) -> None:
    """Execute the `status` command logic.

    Parameters
    ----------
    config_path:
        Path to the config YAML file.
    output_format:
        One of ``"table"``, ``"json"``, or ``"yaml"``.

    Raises
    ------
    StatusError
        If configuration loading or Azure API calls fail.
    """
    try:
        config = parse_config(Path(config_path).expanduser())
    except Exception as exc:
        raise StatusError(f"Failed to load configuration: {exc}") from exc

    entries = _collect_status(config)

    if output_format == "json":
        _render_json(entries)
    elif output_format == "yaml":
        _render_yaml(entries)
    else:
        _render_table(entries)
