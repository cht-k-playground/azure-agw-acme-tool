"""Implementation of the `az-acme-tool issue` command.

Provides :func:`run_issue` which is called by the thin Click command wiring in
``cli.py``.  This module handles:

* Config loading and gateway/domain filtering
* Dry-run mode (print planned steps, no Azure/ACME calls)
* Per-domain orchestration (delegates to :func:`_issue_single_domain`)
* Summary output (total / succeeded / failed)

The actual 14-step ACME pipeline is stubbed in :func:`_issue_single_domain`;
it is replaced by the ``issue-flow-core`` change.

All failures are surfaced as :class:`IssueError`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import click

from az_acme_tool.config import AppConfig, parse_config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class IssueError(Exception):
    """Raised for failures within the issue command."""


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DomainTarget:
    """Identifies a single domain to process on a specific gateway."""

    gateway_name: str
    domain: str


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_targets(
    config: AppConfig,
    gateway_filter: str | None,
    domain_filter: str | None,
) -> list[DomainTarget]:
    """Flatten the config into a list of :class:`DomainTarget` objects.

    Applies optional gateway and domain filters.

    Parameters
    ----------
    config:
        Parsed application configuration.
    gateway_filter:
        If provided, only include domains from the gateway with this name.
    domain_filter:
        If provided, only include the domain matching this FQDN.

    Returns
    -------
    list[DomainTarget]
        Filtered, flat list of domain targets to process.

    Raises
    ------
    IssueError
        If ``domain_filter`` is set but no matching domain exists in the
        (possibly gateway-filtered) config.
    """
    targets: list[DomainTarget] = []
    for gateway in config.gateways:
        if gateway_filter is not None and gateway.name != gateway_filter:
            continue
        for domain_cfg in gateway.domains:
            if domain_filter is not None and domain_cfg.domain != domain_filter:
                continue
            targets.append(DomainTarget(gateway_name=gateway.name, domain=domain_cfg.domain))

    if domain_filter is not None and not targets:
        raise IssueError(
            f"Domain '{domain_filter}' not found in configuration"
            + (f" for gateway '{gateway_filter}'" if gateway_filter else "")
            + "."
        )

    return targets


def _issue_single_domain(
    target: DomainTarget,
    config: AppConfig,  # noqa: ARG001
) -> None:
    """Issue a certificate for a single domain on a gateway.

    .. note::
        This function is a placeholder stub.  The ``issue-flow-core`` change
        replaces it with the real 14-step ACME pipeline.

    Parameters
    ----------
    target:
        The domain/gateway pair to issue a certificate for.
    config:
        The full application configuration (passed for future use).

    Raises
    ------
    NotImplementedError
        Always — replaced by ``issue-flow-core``.
    """
    raise NotImplementedError(
        f"Certificate issuance for {target.domain} on {target.gateway_name} "
        "is not yet implemented — awaiting issue-flow-core."
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_issue(
    config_path: str,
    gateway: str | None,
    domain: str | None,
    dry_run: bool,
) -> None:
    """Execute the `issue` command logic.

    Parameters
    ----------
    config_path:
        Path to the config YAML file (from the Click group context).
    gateway:
        Optional gateway name filter.
    domain:
        Optional domain FQDN filter.
    dry_run:
        When ``True``, print planned steps without making any Azure/ACME calls.

    Raises
    ------
    IssueError
        If configuration is invalid or the specified domain is not found.
    SystemExit
        Via :func:`sys.exit` on fatal errors in the CLI wrapper.
    """
    try:
        config = parse_config(Path(config_path).expanduser())
    except Exception as exc:
        raise IssueError(f"Failed to load configuration: {exc}") from exc

    try:
        targets = _resolve_targets(config, gateway, domain)
    except IssueError:
        raise

    if not targets:
        click.echo("No domains matched the specified filters. Nothing to do.")
        return

    succeeded = 0
    failed = 0

    for target in targets:
        if dry_run:
            click.echo(
                f"[DRY-RUN] Would issue certificate for {target.domain} on {target.gateway_name}"
            )
            succeeded += 1
            continue

        logger.info("Issuing certificate for %s on %s", target.domain, target.gateway_name)
        try:
            _issue_single_domain(target, config)
            click.echo(f"[OK] {target.domain} on {target.gateway_name}")
            succeeded += 1
        except Exception as exc:
            click.echo(f"[FAILED] {target.domain} on {target.gateway_name}: {exc}", err=True)
            logger.error("Failed to issue certificate for %s: %s", target.domain, exc)
            failed += 1

    total = succeeded + failed
    click.echo(f"\nSummary: {total} domain(s) — {succeeded} succeeded, {failed} failed.")
    if failed > 0:
        raise IssueError(f"{failed} domain(s) failed to issue certificates.")
