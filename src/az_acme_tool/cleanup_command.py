"""Implementation of the `az-acme-tool cleanup` command.

Scans all URL path maps on every configured Azure Application Gateway for
orphaned ACME challenge routing rules (prefix ``acme-challenge-``) and
removes them either interactively or in batch mode.

All failures are surfaced as :class:`CleanupError`.
"""

from __future__ import annotations

import logging
from pathlib import Path

import click
from azure.identity import DefaultAzureCredential

from az_acme_tool.azure_gateway import AzureGatewayClient, AzureGatewayError
from az_acme_tool.config import parse_config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class CleanupError(Exception):
    """Raised for failures within the cleanup command."""


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_cleanup(config_path: str, cleanup_all: bool) -> None:
    """Execute the ``cleanup`` command logic.

    Scans every configured Application Gateway for URL path map rules whose
    names begin with ``acme-challenge-``.  In interactive mode (``cleanup_all
    = False``) the user is prompted to confirm each deletion individually.  In
    batch mode (``cleanup_all = True``) all matching rules are removed without
    prompting.

    Parameters
    ----------
    config_path:
        Path to the config YAML file.
    cleanup_all:
        When ``True``, remove all orphaned rules without prompting.

    Raises
    ------
    CleanupError
        If configuration loading or Azure API calls fail.
    """
    try:
        config = parse_config(Path(config_path).expanduser())
    except Exception as exc:
        raise CleanupError(f"Failed to load configuration: {exc}") from exc

    credential = DefaultAzureCredential()
    total_found = 0
    total_removed = 0

    for gateway_cfg in config.gateways:
        client = AzureGatewayClient(
            subscription_id=str(config.azure.subscription_id),
            resource_group=config.azure.resource_group,
            gateway_name=gateway_cfg.name,
            credential=credential,
        )

        try:
            rules = client.list_acme_challenge_rules()
        except AzureGatewayError as exc:
            raise CleanupError(
                f"Failed to list ACME challenge rules on gateway '{gateway_cfg.name}': {exc}"
            ) from exc

        if not rules:
            continue

        total_found += len(rules)

        for i, rule_name in enumerate(rules, start=1):
            should_delete: bool
            if cleanup_all:
                should_delete = True
            else:
                click.echo(f"  [{i}/{len(rules)}] {rule_name}")
                should_delete = click.confirm(
                    f"    Delete rule '{rule_name}'?", default=False
                )

            if should_delete:
                try:
                    client.delete_routing_rule(rule_name)
                except AzureGatewayError as exc:
                    raise CleanupError(
                        f"Failed to delete rule '{rule_name}' on gateway "
                        f"'{gateway_cfg.name}': {exc}"
                    ) from exc
                click.echo(f"Removed: {rule_name}")
                total_removed += 1
                logger.info(
                    "Removed ACME challenge rule '%s' from gateway '%s'.",
                    rule_name,
                    gateway_cfg.name,
                )

    if total_found == 0:
        click.echo("No orphaned ACME challenge rules found.")
