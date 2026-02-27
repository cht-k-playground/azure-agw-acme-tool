"""Implementation of the `az-acme-tool renew` command.

Provides :func:`run_renew` which is called by the thin Click command wiring in
``cli.py``.  This module handles:

* Config loading and gateway/domain filtering (reuses :func:`_resolve_targets`
  from :mod:`issue_command`)
* Per-domain certificate expiry lookup via :class:`AzureGatewayClient`
* Threshold comparison: skip domains whose certificate has more than
  ``--days`` days remaining (unless ``--force`` is set)
* Graceful skip when a domain's expected certificate is not found on the gateway
* Renewal delegation to :func:`_issue_single_domain` from :mod:`issue_command`
* Summary output: ``Total: N | Renewed: R | Skipped: S | Failed: F``

All failures are surfaced as :class:`RenewError`.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import click

from az_acme_tool.azure_gateway import AzureGatewayClient, AzureGatewayError
from az_acme_tool.config import AppConfig, GatewayConfig, parse_config
from az_acme_tool.issue_command import (
    IssueError,
    _issue_single_domain,
    _resolve_targets,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class RenewError(Exception):
    """Raised for failures within the renew command."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _domain_to_cert_name(domain: str) -> str:
    """Derive the Azure SSL certificate name from a domain FQDN.

    Applies the ``{domain_sanitized}-cert`` naming convention where dots are
    replaced with hyphens.

    Parameters
    ----------
    domain:
        Fully-qualified domain name (e.g. ``www.example.com``).

    Returns
    -------
    str
        Certificate name as stored in Azure Application Gateway
        (e.g. ``www-example-com-cert``).
    """
    return domain.replace(".", "-") + "-cert"


def _days_remaining(expiry: datetime) -> int:
    """Return the number of whole days until *expiry* from now (UTC).

    Negative values indicate the certificate has already expired.

    Parameters
    ----------
    expiry:
        UTC-aware expiry datetime.

    Returns
    -------
    int
        Whole days remaining (may be negative).
    """
    now = datetime.now(tz=UTC)
    delta = expiry - now
    return delta.days


def _build_gateway_client(config: AppConfig, gateway_cfg: GatewayConfig) -> AzureGatewayClient:
    """Instantiate an :class:`AzureGatewayClient` for the given gateway config.

    Parameters
    ----------
    config:
        Full application configuration (provides Azure subscription details).
    gateway_cfg:
        Gateway-specific configuration (provides the gateway name).

    Returns
    -------
    AzureGatewayClient
        A ready-to-use client for the specified gateway.
    """
    from azure.identity import DefaultAzureCredential

    credential = DefaultAzureCredential()
    return AzureGatewayClient(
        subscription_id=str(config.azure.subscription_id),
        resource_group=config.azure.resource_group,
        gateway_name=gateway_cfg.name,
        credential=credential,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_renew(
    config_path: str,
    gateway: str | None,
    domain: str | None,
    days: int,
    force: bool,
) -> None:
    """Execute the `renew` command logic.

    For each domain target resolved from the configuration:

    1. Derive the expected certificate name (``{domain_sanitized}-cert``).
    2. Look up the certificate's expiry via :meth:`AzureGatewayClient.list_certificates`.
    3. If the certificate is not found, emit a warning and skip.
    4. If remaining days > *days* threshold and *force* is ``False``, skip.
    5. Otherwise, delegate to :func:`_issue_single_domain` to perform renewal.

    A summary line is printed after all domains are processed.

    Parameters
    ----------
    config_path:
        Path to the config YAML file (from the Click group context).
    gateway:
        Optional gateway name filter.
    domain:
        Optional domain FQDN filter.
    days:
        Renewal threshold in days (default 30).  Domains with more than this
        many days remaining are skipped unless *force* is ``True``.
    force:
        When ``True``, bypass the threshold check and renew all domains.

    Raises
    ------
    RenewError
        If configuration is invalid or the specified domain is not found.
    """
    try:
        config = parse_config(Path(config_path).expanduser())
    except Exception as exc:
        raise RenewError(f"Failed to load configuration: {exc}") from exc

    try:
        targets = _resolve_targets(config, gateway, domain)
    except IssueError as exc:
        raise RenewError(str(exc)) from exc

    if not targets:
        click.echo("No domains matched the specified filters. Nothing to do.")
        return

    renewed = 0
    skipped = 0
    failed = 0

    # Cache per-gateway certificate lists to avoid redundant API calls.
    cert_cache: dict[str, list[dict[str, object]]] = {}

    for target in targets:
        cert_name = _domain_to_cert_name(target.domain)

        # Fetch certificate list for this gateway (cached per gateway).
        if target.gateway_name not in cert_cache:
            # Find the gateway config to build the client.
            gateway_cfg = next(
                (gw for gw in config.gateways if gw.name == target.gateway_name),
                None,
            )
            if gateway_cfg is None:
                click.echo(
                    f"[WARN] Gateway '{target.gateway_name}' not found in config — "
                    f"skipping {target.domain}",
                    err=True,
                )
                skipped += 1
                continue

            try:
                client = _build_gateway_client(config, gateway_cfg)
                cert_cache[target.gateway_name] = client.list_certificates()
            except AzureGatewayError as exc:
                click.echo(
                    f"[WARN] Could not fetch certificates for gateway "
                    f"'{target.gateway_name}': {exc} — skipping {target.domain}",
                    err=True,
                )
                logger.warning(
                    "Failed to list certificates for gateway '%s': %s",
                    target.gateway_name,
                    exc,
                )
                skipped += 1
                continue

        certs = cert_cache[target.gateway_name]

        # Find the expected certificate entry.
        cert_entry = next(
            (c for c in certs if c.get("name") == cert_name),
            None,
        )

        if cert_entry is None:
            click.echo(
                f"[WARN] Certificate '{cert_name}' not found on gateway "
                f"'{target.gateway_name}' — skipping {target.domain}",
                err=True,
            )
            logger.warning(
                "Certificate '%s' not found on gateway '%s' — skipping domain '%s'.",
                cert_name,
                target.gateway_name,
                target.domain,
            )
            skipped += 1
            continue

        expiry: datetime | None = cert_entry.get("expiry")  # type: ignore[assignment]

        if expiry is None:
            click.echo(
                f"[WARN] Expiry date unavailable for certificate '{cert_name}' "
                f"on gateway '{target.gateway_name}' — skipping {target.domain}",
                err=True,
            )
            skipped += 1
            continue

        remaining = _days_remaining(expiry)

        if not force and remaining > days:
            click.echo(
                f"[SKIP] {target.domain} — {remaining} days remaining " f"(threshold: {days} days)"
            )
            logger.info(
                "Skipping '%s': %d days remaining, threshold is %d.",
                target.domain,
                remaining,
                days,
            )
            skipped += 1
            continue

        # Proceed with renewal.
        logger.info(
            "Renewing certificate for '%s' on '%s' (%d days remaining).",
            target.domain,
            target.gateway_name,
            remaining,
        )
        try:
            _issue_single_domain(target, config)
            click.echo(f"[RENEWED] {target.domain} on {target.gateway_name}")
            renewed += 1
        except Exception as exc:
            click.echo(
                f"[FAILED] {target.domain} on {target.gateway_name}: {exc}",
                err=True,
            )
            logger.error(
                "Failed to renew certificate for '%s': %s",
                target.domain,
                exc,
            )
            failed += 1

    total = renewed + skipped + failed
    click.echo(f"\nTotal: {total} | Renewed: {renewed} | Skipped: {skipped} | Failed: {failed}")

    if failed > 0:
        raise RenewError(f"{failed} domain(s) failed to renew certificates.")
