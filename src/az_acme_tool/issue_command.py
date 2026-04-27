"""Implementation of the `az-acme-tool issue` command.

Provides :func:`run_issue` which is called by the thin Click command wiring in
``cli.py``.  This module handles:

* Config loading and gateway/domain filtering
* Dry-run mode (print planned steps, no Azure/ACME calls)
* Per-domain orchestration via the 14-step ACME HTTP-01 pipeline in
  :func:`_issue_single_domain`
* Summary output (total / succeeded / failed)

All failures are surfaced as :class:`IssueError`.
"""

from __future__ import annotations

import concurrent.futures
import logging
import secrets
import time
from dataclasses import dataclass
from pathlib import Path

import click
from azure.identity import DefaultAzureCredential
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from az_acme_tool.acme_client import AcmeClient
from az_acme_tool.azure_gateway import AzureGatewayClient
from az_acme_tool.cert_converter import generate_csr, pem_to_pfx
from az_acme_tool.config import AppConfig, GatewayConfig, parse_config

logger = logging.getLogger(__name__)

# Maximum number of domains processed concurrently in the batch issue flow.
# Fixed by ROADMAP `issue-flow-batch` AC1 — see openspec spec `cli-issue`.
_MAX_BATCH_WORKERS = 3

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


def _domain_to_cert_name(domain: str) -> str:
    """Return the AGW SSL certificate name for *domain* (``foo.bar`` → ``foo-bar-cert``)."""
    return domain.replace(".", "-") + "-cert"


def _domain_sanitized(domain: str) -> str:
    """Return *domain* with dots replaced by hyphens (for resource naming)."""
    return domain.replace(".", "-")


def _generate_domain_key_pem() -> str:
    """Generate a fresh RSA-2048 private key in PEM form (in-memory only)."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return pem.decode("ascii")


def _build_acme_client(config: AppConfig) -> AcmeClient:
    """Construct an :class:`AcmeClient` from the parsed configuration."""
    return AcmeClient(directory_url=config.acme.directory_url)


def _build_gateway_client(
    config: AppConfig, gateway_cfg: GatewayConfig
) -> AzureGatewayClient:
    """Construct an :class:`AzureGatewayClient` for the given gateway."""
    return AzureGatewayClient(
        subscription_id=str(config.azure.subscription_id),
        resource_group=config.azure.resource_group,
        gateway_name=gateway_cfg.name,
        credential=DefaultAzureCredential(),
    )


def _issue_single_domain(
    target: DomainTarget,
    config: AppConfig,
) -> None:
    """Issue an ACME HTTP-01 certificate for one domain on one gateway.

    Implements the 14-step pipeline:

    1. Resolve config + gateway entry
    2. Register/resume ACME account
    3. Create new ACME order
    4. Extract HTTP-01 challenge (token + key_authorization)
    5. Write key_authorization to the Azure Function App Settings
    6. Add the temporary path-based routing rule on the AGW
    7. Notify the ACME CA (answer_challenge)
    8. Poll until the authorization is valid
    9. Finalize the order with the production CSR
    10. Download the issued certificate (PEM)
    11. Convert PEM → PFX with a random in-memory password
    12. Upload the PFX to the AGW as a named SSL certificate
    13. Update every listener that referenced the old certificate
    14. Delete the temporary routing rule (always — guaranteed by ``finally``)

    Parameters
    ----------
    target:
        The domain/gateway pair to issue a certificate for.
    config:
        The full application configuration.
    """
    domain = target.domain
    gateway_cfg = next(
        (gw for gw in config.gateways if gw.name == target.gateway_name),
        None,
    )
    if gateway_cfg is None:
        # Defensive: _resolve_targets only returns targets that exist in config.
        raise IssueError(
            f"Gateway '{target.gateway_name}' not found in configuration."
        )

    cert_name = _domain_to_cert_name(domain)
    rule_name = f"acme-challenge-{_domain_sanitized(domain)}-{int(time.time())}"
    backend_fqdn = f"{gateway_cfg.acme_function_name}.azurewebsites.net"

    acme = _build_acme_client(config)
    agw = _build_gateway_client(config, gateway_cfg)

    # Step 2: register/resume ACME account.
    acme.register_account(
        email=str(config.acme.email),
        account_key_path=config.acme.account_key_path,
    )

    # Step 3: create order.
    order = acme.new_order([domain])

    # Step 4: extract HTTP-01 challenge (token, key_authorization).
    _token, key_auth = acme.get_http01_challenge(order, domain)

    # Locate the actual ChallengeBody we'll answer in step 7.
    challb = None
    for authzr in order.authorizations:
        if authzr.body.identifier.value == domain:
            for cb in authzr.body.challenges:
                # Match by class name to avoid an extra import; HTTP01 is the
                # only challenge type extracted by get_http01_challenge.
                if type(cb.chall).__name__ == "HTTP01":
                    challb = cb
                    break
        if challb is not None:
            break
    if challb is None:
        raise IssueError(
            f"No HTTP-01 challenge body found for domain '{domain}' in order."
        )

    rule_added = False
    try:
        # Step 5: write key_authorization to the Azure Function App Settings.
        agw.update_function_app_settings(
            function_app_name=gateway_cfg.acme_function_name,
            settings={"ACME_CHALLENGE_RESPONSE": key_auth},
        )

        # Step 6: add the temporary path-based routing rule.
        agw.add_routing_rule(
            rule_name=rule_name,
            domain=domain,
            backend_fqdn=backend_fqdn,
        )
        rule_added = True

        # Step 7: notify the ACME CA.
        acme.answer_challenge(challb)

        # Step 8: poll until valid.
        acme.poll_until_valid(order)

        # Step 9: finalize with the production CSR (with a domain-specific key).
        domain_key_pem = _generate_domain_key_pem()
        csr_der = generate_csr([domain], domain_key_pem)

        finalized = acme.finalize_order(order, csr_der)

        # Step 10: download cert PEM.
        cert_pem = acme.download_certificate(finalized)

        # Step 11: PEM → PFX with a random in-memory password.
        pfx_password = secrets.token_urlsafe(32)
        pfx_data = pem_to_pfx(cert_pem, domain_key_pem, pfx_password)

        # Step 12: upload PFX as a named SSL certificate.
        agw.upload_ssl_certificate(
            cert_name=cert_name,
            pfx_data=pfx_data,
            password=pfx_password,
        )

        # Steps 12-13: update every listener that referenced the cert.
        listeners = agw.get_listeners_by_cert_name(cert_name)
        if not listeners:
            logger.warning(
                "No listeners reference certificate '%s' on gateway '%s' — "
                "skipping listener update (first issuance).",
                cert_name,
                target.gateway_name,
            )
        for listener_name in listeners:
            agw.update_listener_certificate(listener_name, cert_name)
    finally:
        # Step 14: always delete the temporary routing rule if we created it.
        if rule_added:
            try:
                agw.delete_routing_rule(rule_name)
            except Exception as cleanup_exc:
                # Don't mask the original failure; log and continue.
                logger.error(
                    "Failed to delete temporary routing rule '%s' on gateway '%s': %s",
                    rule_name,
                    target.gateway_name,
                    cleanup_exc,
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

    if dry_run:
        # Dry-run remains serial: no I/O, output ordering preserved for tests.
        for target in targets:
            click.echo(
                f"[DRY-RUN] Would issue certificate for {target.domain} on {target.gateway_name}"
            )
        total = len(targets)
        click.echo(
            f"\nTotal: {total} | Succeeded: {total} | Failed: 0 | Duration: 0.0s"
        )
        return

    succeeded = 0
    failed = 0
    failures: list[tuple[DomainTarget, Exception]] = []

    start = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=_MAX_BATCH_WORKERS) as executor:
        future_to_target: dict[concurrent.futures.Future[None], DomainTarget] = {
            executor.submit(_issue_single_domain, target, config): target
            for target in targets
        }
        for future in concurrent.futures.as_completed(future_to_target):
            target = future_to_target[future]
            try:
                future.result()
            except Exception as exc:
                click.echo(
                    f"[FAILED] {target.domain} on {target.gateway_name}: {exc}",
                    err=True,
                )
                logger.error("Failed to issue certificate for %s: %s", target.domain, exc)
                failures.append((target, exc))
                failed += 1
            else:
                click.echo(f"[OK] {target.domain} on {target.gateway_name}")
                succeeded += 1
    duration = time.monotonic() - start

    total = succeeded + failed
    click.echo(
        f"\nTotal: {total} | Succeeded: {succeeded} | Failed: {failed} "
        f"| Duration: {duration:.1f}s"
    )

    if failed > 0:
        # Re-list failures in submission order (sorted by `targets`) so operators
        # see a stable summary regardless of completion order.
        failure_lookup: dict[int, Exception] = {id(t): err for t, err in failures}
        click.echo("\nFailed domains:")
        for target in targets:
            err = failure_lookup.get(id(target))
            if err is not None:
                click.echo(f"  - {target.domain} on {target.gateway_name}: {err}")
        raise IssueError(f"{failed} domain(s) failed to issue certificates.")
