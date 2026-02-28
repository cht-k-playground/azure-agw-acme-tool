"""Main CLI entry point for az-acme-tool."""

import sys
from typing import Any

import click

from az_acme_tool import __version__
from az_acme_tool.logging import setup_logging


@click.group()
@click.version_option(version=__version__, prog_name="az-acme-tool")
@click.option(
    "--config",
    default="~/.config/az-acme-tool/config.yaml",
    show_default=True,
    type=click.Path(),
    help="Path to config YAML file.",
)
@click.option("--verbose", is_flag=True, default=False, help="Enable verbose output.")
@click.pass_context
def main(ctx: click.Context, config: str, verbose: bool) -> None:
    """Azure Application Gateway ACME automated certificate management tool."""
    ctx.ensure_object(dict)
    setup_logging(verbose=verbose)
    ctx.obj["config"] = config
    ctx.obj["verbose"] = verbose


@main.command()
@click.option(
    "--config-template",
    is_flag=True,
    default=False,
    help="Print a YAML config file template to stdout.",
)
@click.pass_obj
def init(obj: dict[str, Any], config_template: bool) -> None:
    """Initialize ACME account and generate configuration template."""
    from az_acme_tool.init_command import InitError, run_init

    try:
        run_init(config_path=obj["config"], config_template=config_template)
    except InitError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@main.command()
@click.option("--gateway", default=None, help="Process only the specified gateway.")
@click.option("--domain", default=None, help="Process only the specified domain.")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Simulate execution without making changes.",
)
@click.pass_obj
def issue(obj: dict[str, Any], gateway: str | None, domain: str | None, dry_run: bool) -> None:
    """Issue and deploy certificates for configured domains."""
    from az_acme_tool.issue_command import IssueError, run_issue

    try:
        run_issue(
            config_path=obj["config"],
            gateway=gateway,
            domain=domain,
            dry_run=dry_run,
        )
    except IssueError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@main.command()
@click.option("--gateway", default=None, help="Process only the specified gateway.")
@click.option("--domain", default=None, help="Process only the specified domain.")
@click.option(
    "--days",
    default=30,
    show_default=True,
    type=int,
    help="Renew certificates expiring within this many days.",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Force renewal of all certificates regardless of expiry.",
)
@click.pass_obj
def renew(
    obj: dict[str, Any], gateway: str | None, domain: str | None, days: int, force: bool
) -> None:
    """Renew certificates that are expiring soon."""
    from az_acme_tool.renew_command import RenewError, run_renew

    try:
        run_renew(
            config_path=obj["config"],
            gateway=gateway,
            domain=domain,
            days=days,
            force=force,
        )
    except RenewError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@main.command()
@click.option(
    "--output",
    "output_format",
    default="table",
    show_default=True,
    type=click.Choice(["table", "json", "yaml"]),
    help="Output format.",
)
@click.pass_obj
def status(obj: dict[str, Any], output_format: str) -> None:
    """Query certificate status and expiry information."""
    from az_acme_tool.status_command import StatusError, run_status

    try:
        run_status(config_path=obj["config"], output_format=output_format)
    except StatusError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@main.command()
@click.option(
    "--all",
    "cleanup_all",
    is_flag=True,
    default=False,
    help="Remove all orphaned ACME challenge routing rules without prompting.",
)
@click.pass_obj
def cleanup(obj: dict[str, Any], cleanup_all: bool) -> None:
    """Remove orphaned ACME challenge routing rules left from interrupted runs."""
    from az_acme_tool.cleanup_command import CleanupError, run_cleanup

    try:
        run_cleanup(config_path=obj["config"], cleanup_all=cleanup_all)
    except CleanupError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
