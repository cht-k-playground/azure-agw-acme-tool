"""Main CLI entry point for az-acme-tool."""

import click

from az_acme_tool import __version__


@click.group()
@click.version_option(version=__version__, prog_name="az-acme-tool")
def main() -> None:
    """Azure Application Gateway ACME automated certificate management tool."""


@main.command()
@click.option("--email", required=True, help="ACME account email address.")
@click.option(
    "--ca-url",
    default="https://acme-v02.api.letsencrypt.org/directory",
    show_default=True,
    help="ACME CA directory URL.",
)
@click.option(
    "--account-key",
    default="~/.config/az-acme-tool/account.key",
    show_default=True,
    type=click.Path(),
    help="Path to store the ACME account private key.",
)
@click.option(
    "--config-template",
    is_flag=True,
    default=False,
    help="Print a YAML config file template to stdout.",
)
def init(email: str, ca_url: str, account_key: str, config_template: bool) -> None:
    """Initialize ACME account and generate configuration template."""
    raise NotImplementedError("init command is not yet implemented")


@main.command()
@click.option(
    "--config",
    required=True,
    type=click.Path(exists=True),
    help="Path to the YAML configuration file.",
)
@click.option("--gateway", default=None, help="Process only the specified gateway.")
@click.option("--domain", default=None, help="Process only the specified domain.")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Simulate execution without making changes.",
)
@click.option("--verbose", is_flag=True, default=False, help="Enable verbose output.")
def issue(
    config: str,
    gateway: str | None,
    domain: str | None,
    dry_run: bool,
    verbose: bool,
) -> None:
    """Issue and deploy certificates for configured domains."""
    raise NotImplementedError("issue command is not yet implemented")


@main.command()
@click.option(
    "--config",
    required=True,
    type=click.Path(exists=True),
    help="Path to the YAML configuration file.",
)
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
def renew(config: str, days: int, force: bool) -> None:
    """Renew certificates that are expiring soon."""
    raise NotImplementedError("renew command is not yet implemented")


@main.command()
@click.option(
    "--config",
    required=True,
    type=click.Path(exists=True),
    help="Path to the YAML configuration file.",
)
@click.option(
    "--format",
    "output_format",
    default="table",
    show_default=True,
    type=click.Choice(["table", "json", "yaml"]),
    help="Output format.",
)
def status(config: str, output_format: str) -> None:
    """Query certificate status and expiry information."""
    raise NotImplementedError("status command is not yet implemented")


@main.command()
@click.option(
    "--config",
    required=True,
    type=click.Path(exists=True),
    help="Path to the YAML configuration file.",
)
@click.option(
    "--all",
    "cleanup_all",
    is_flag=True,
    default=False,
    help="Clean up all temporary routing rules.",
)
def cleanup(config: str, cleanup_all: bool) -> None:
    """Clean up temporary ACME challenge routing rules left from interrupted runs."""
    raise NotImplementedError("cleanup command is not yet implemented")
