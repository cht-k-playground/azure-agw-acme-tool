"""Implementation of the `az-acme-tool init` command.

Provides :func:`run_init` which is called by the thin Click command wiring in
``cli.py``.  Two modes of operation:

* **Template mode** (``--config-template``): print a YAML skeleton to stdout
  and return immediately without any side effects.
* **Registration mode** (default): generate an RSA-2048 ACME account key,
  write it to the default key path with ``0o600`` permissions, register with
  the ACME CA, and print confirmation to the console.

All failures are surfaced as :class:`InitError`.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import click
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from az_acme_tool.acme_client import AcmeClient, AcmeError
from az_acme_tool.config import parse_config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_KEY_PATH: Path = Path("~/.config/az-acme-tool/account.key").expanduser()

_ACME_DIRECTORY_URL: str = "https://acme-v02.api.letsencrypt.org/directory"

_CONFIG_TEMPLATE: str = """\
# az-acme-tool configuration file
# Place this file at ~/.config/az-acme-tool/config.yaml
# or pass --config <path> to any command.

acme:
  email: "your-email@example.com"  # Required: ACME account contact email

azure:
  subscription_id: "00000000-0000-0000-0000-000000000000"  # Required: Azure subscription UUID
  resource_group: "my-resource-group"  # Required: Azure resource group name
  auth_method: "default"  # Options: default | service_principal | managed_identity

gateways:
  - name: "my-app-gateway"  # Required: Application Gateway name
    domains:
      - domain: "www.example.com"
        cert_store: "agw_direct"
"""

# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class InitError(Exception):
    """Raised for failures within the init command."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _generate_and_write_key(key_path: Path) -> None:
    """Generate an RSA-2048 private key and write it to *key_path* with 0o600 permissions.

    Creates parent directories as needed.

    Parameters
    ----------
    key_path:
        Destination path for the PEM-encoded RSA private key.
    """
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_bytes(pem_bytes)
    os.chmod(key_path, 0o600)
    logger.debug("Wrote account key to %s", key_path)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_init(config_path: str, config_template: bool) -> None:  # noqa: ARG001
    """Execute the `init` command logic.

    Parameters
    ----------
    config_path:
        Path to the config YAML file (passed from the Click group context).
        Not used in template mode; reserved for future use in registration mode
        to derive the account key path from the config file.
    config_template:
        When ``True``, print :data:`_CONFIG_TEMPLATE` to stdout and return.

    Raises
    ------
    InitError
        If key generation, file I/O, or ACME registration fails.
    SystemExit
        Via :func:`click.echo` / :func:`sys.exit` on user-declined overwrite.
    """
    if config_template:
        click.echo(_CONFIG_TEMPLATE, nl=False)
        return

    key_path = _DEFAULT_KEY_PATH

    # Overwrite guard
    if key_path.exists():
        if not click.confirm(
            f"Account key already exists at {key_path}. Overwrite?", default=False
        ):
            click.echo("Aborted — existing key file left unchanged.", err=True)
            return

    # Generate key
    try:
        _generate_and_write_key(key_path)
    except OSError as exc:
        raise InitError(f"Failed to write account key to {key_path}: {exc}") from exc

    click.echo(f"Account key written to: {key_path}")

    # Extract email from the config file for ACME registration.
    # For Phase 1, we require the config file to exist for registration mode
    # so we can read the ACME email. If the file is missing, surface a clear error.
    try:
        cfg = parse_config(Path(config_path).expanduser())
        email: str = str(cfg.acme.email)
    except Exception as exc:
        raise InitError(
            f"Could not read ACME email from config file '{config_path}': {exc}\n"
            "Tip: Use --config-template to generate a config file first."
        ) from exc

    # Register with ACME CA
    acme_client = AcmeClient(directory_url=_ACME_DIRECTORY_URL)
    try:
        account_url = acme_client.register_account(email=email, account_key_path=key_path)
    except AcmeError as exc:
        raise InitError(f"ACME account registration failed: {exc}") from exc

    click.echo(f"ACME account registered: {account_url}")
    click.echo("\nNext steps:")
    click.echo("  1. Ensure your config file is complete (use --config-template if needed).")
    click.echo("  2. Configure your Azure Application Gateway and Azure Function responder.")
    click.echo("  3. Run `az-acme-tool issue` to issue certificates.")
