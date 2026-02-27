"""Main CLI entry point for az-acme-tool."""

from typing import Any

import click

from az_acme_tool import __version__


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
    raise NotImplementedError("init command is not yet implemented")


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
    raise NotImplementedError("issue command is not yet implemented")


@main.command()
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
def renew(obj: dict[str, Any], days: int, force: bool) -> None:
    """Renew certificates that are expiring soon."""
    raise NotImplementedError("renew command is not yet implemented")


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
    raise NotImplementedError("status command is not yet implemented")


@main.command()
@click.option(
    "--all",
    "cleanup_all",
    is_flag=True,
    default=False,
    help="Clean up all temporary routing rules.",
)
@click.pass_obj
def cleanup(obj: dict[str, Any], cleanup_all: bool) -> None:
    """Clean up temporary ACME challenge routing rules left from interrupted runs."""
    raise NotImplementedError("cleanup command is not yet implemented")
