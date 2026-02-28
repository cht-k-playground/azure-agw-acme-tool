"""Azure Application Gateway client for TLS certificate management.

Provides a typed wrapper around the ``azure-mgmt-network`` SDK for three
operations:

- ``list_certificates()``        — enumerate SSL certificates on a gateway
- ``get_certificate_expiry()``   — read the expiry datetime of a named cert
- ``update_listener_certificate()`` — point a gateway listener at a cert

All Azure SDK errors are translated to :class:`AzureGatewayError`.
"""

from __future__ import annotations

import base64
import logging
from datetime import UTC, datetime
from typing import Any

from azure.core.credentials import TokenCredential
from azure.core.exceptions import HttpResponseError
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.network.models import ApplicationGateway, SubResource
from cryptography import x509

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class AzureGatewayError(Exception):
    """Raised for all Azure Application Gateway client failures."""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class AzureGatewayClient:
    """Typed client for Azure Application Gateway certificate operations.

    Parameters
    ----------
    subscription_id:
        Azure subscription UUID as a string.
    resource_group:
        Name of the resource group containing the Application Gateway.
    gateway_name:
        Name of the Application Gateway resource.
    credential:
        An Azure SDK ``TokenCredential`` (e.g. ``DefaultAzureCredential``).
        Constructed and injected by the caller so this client remains
        independently testable.
    """

    def __init__(
        self,
        subscription_id: str,
        resource_group: str,
        gateway_name: str,
        credential: TokenCredential,
    ) -> None:
        self._subscription_id = subscription_id
        self._resource_group = resource_group
        self._gateway_name = gateway_name
        self._network_client = NetworkManagementClient(
            credential=credential,
            subscription_id=subscription_id,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_gateway(self) -> ApplicationGateway:
        """Fetch the Application Gateway resource from ARM.

        Raises
        ------
        AzureGatewayError
            If the Azure API call fails.
        """
        try:
            return self._network_client.application_gateways.get(
                resource_group_name=self._resource_group,
                application_gateway_name=self._gateway_name,
            )
        except HttpResponseError as exc:
            raise AzureGatewayError(
                f"Failed to fetch Application Gateway '{self._gateway_name}': {exc}"
            ) from exc

    @staticmethod
    def _parse_expiry(public_cert_data: str | None, cert_name: str) -> datetime | None:
        """Parse the expiry datetime from a base-64 DER-encoded certificate.

        Parameters
        ----------
        public_cert_data:
            Base-64 encoded public certificate data as returned by the
            Azure API (``public_cert_data`` field on
            ``ApplicationGatewaySslCertificate``).  May be ``None`` for
            Key Vault–referenced certificates.
        cert_name:
            Certificate name — used only in log messages.

        Returns
        -------
        datetime | None
            The certificate's ``not_valid_after`` in UTC, or ``None`` if
            *public_cert_data* is ``None`` or cannot be parsed.
        """
        if not public_cert_data:
            return None
        try:
            der_bytes = base64.b64decode(public_cert_data)
            cert = x509.load_der_x509_certificate(der_bytes)
            expiry = cert.not_valid_after_utc
            # Ensure the datetime is timezone-aware UTC.
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=UTC)
            return expiry
        except Exception as exc:  # pragma: no cover — parsing errors are unusual
            logger.warning("Could not parse certificate data for '%s': %s", cert_name, exc)
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_certificates(self) -> list[dict[str, Any]]:
        """Return all SSL certificates attached to the Application Gateway.

        Each entry in the returned list contains:

        - ``name`` (``str``) — the certificate name as stored in Azure.
        - ``expiry`` (``datetime | None``) — UTC expiry datetime parsed
          from the public certificate data, or ``None`` if unavailable
          (e.g. Key Vault–referenced certificates).

        Returns
        -------
        list[dict[str, Any]]
            Empty list when the gateway has no SSL certificates attached.

        Raises
        ------
        AzureGatewayError
            If the Azure API call fails.
        """
        gateway = self._get_gateway()
        certs = gateway.ssl_certificates or []
        result: list[dict[str, Any]] = []
        for cert in certs:
            expiry = self._parse_expiry(cert.public_cert_data, cert.name or "")
            result.append({"name": cert.name or "", "expiry": expiry})
        return result

    def get_certificate_expiry(self, cert_name: str) -> datetime:
        """Return the expiry datetime of a named SSL certificate.

        Parameters
        ----------
        cert_name:
            Name of the SSL certificate as stored in the Application Gateway.

        Returns
        -------
        datetime
            UTC-aware expiry datetime of the certificate.

        Raises
        ------
        AzureGatewayError
            If the certificate is not found, if its expiry cannot be
            determined (e.g. Key Vault reference), or if the Azure API
            call fails.
        """
        certs = self.list_certificates()
        for entry in certs:
            if entry["name"] == cert_name:
                expiry: datetime | None = entry["expiry"]
                if expiry is None:
                    raise AzureGatewayError(
                        f"Expiry date unavailable for certificate '{cert_name}'. "
                        "This may be a Key Vault-referenced certificate whose "
                        "public data is not exposed via the gateway API."
                    )
                return expiry
        raise AzureGatewayError(
            f"Certificate '{cert_name}' not found on Application Gateway "
            f"'{self._gateway_name}'."
        )

    def update_listener_certificate(self, listener_name: str, cert_name: str) -> None:
        """Update an HTTP listener to reference a different SSL certificate.

        Fetches the current Application Gateway configuration, locates the
        named listener and the named certificate, updates the listener's
        ``ssl_certificate`` sub-resource reference, and pushes the full
        gateway configuration back to ARM, waiting for the operation to
        complete.

        Parameters
        ----------
        listener_name:
            Name of the HTTP listener to update.
        cert_name:
            Name of the SSL certificate to assign to the listener.

        Raises
        ------
        AzureGatewayError
            If the listener is not found, if the certificate is not found,
            or if the Azure API call fails.
        """
        gateway = self._get_gateway()

        # Locate the target listener.
        listeners = gateway.http_listeners or []
        target_listener = next(
            (ln for ln in listeners if ln.name == listener_name),
            None,
        )
        if target_listener is None:
            raise AzureGatewayError(
                f"Listener '{listener_name}' not found on Application Gateway "
                f"'{self._gateway_name}'."
            )

        # Locate the target certificate to build its ARM sub-resource ID.
        ssl_certs = gateway.ssl_certificates or []
        target_cert = next((c for c in ssl_certs if c.name == cert_name), None)
        if target_cert is None:
            raise AzureGatewayError(
                f"Certificate '{cert_name}' not found on Application Gateway "
                f"'{self._gateway_name}'."
            )

        if target_cert.id is None:
            raise AzureGatewayError(
                f"Certificate '{cert_name}' has no ARM resource ID — cannot build "
                "sub-resource reference."
            )

        # Update the listener's ssl_certificate reference.
        target_listener.ssl_certificate = SubResource(id=target_cert.id)

        logger.info(
            "Updating listener '%s' on gateway '%s' to use certificate '%s'.",
            listener_name,
            self._gateway_name,
            cert_name,
        )

        try:
            poller = self._network_client.application_gateways.begin_create_or_update(
                resource_group_name=self._resource_group,
                application_gateway_name=self._gateway_name,
                parameters=gateway,
            )
            poller.result(timeout=600)  # 10-minute hard limit
        except HttpResponseError as exc:
            raise AzureGatewayError(
                f"Failed to update listener '{listener_name}' on Application Gateway "
                f"'{self._gateway_name}': {exc}"
            ) from exc

    def list_acme_challenge_rules(self) -> list[str]:
        """Return names of all URL path map rules prefixed with ``acme-challenge-``.

        Scans every URL path map on the Application Gateway and collects the
        names of path rules whose names begin with ``acme-challenge-``.

        Returns
        -------
        list[str]
            Possibly-empty list of matching rule names.

        Raises
        ------
        AzureGatewayError
            If the Azure API call fails.
        """
        gateway = self._get_gateway()
        url_path_maps = gateway.url_path_maps or []
        matching: list[str] = []
        for upm in url_path_maps:
            for rule in upm.path_rules or []:
                if rule.name and rule.name.startswith("acme-challenge-"):
                    matching.append(rule.name)
        return matching

    def delete_routing_rule(self, rule_name: str) -> None:
        """Remove a named path rule from all URL path maps on the gateway.

        Fetches the current Application Gateway configuration, removes every
        occurrence of *rule_name* from all URL path maps, and pushes the
        updated configuration back to ARM.

        Parameters
        ----------
        rule_name:
            Name of the path rule to delete.

        Raises
        ------
        AzureGatewayError
            If the rule is not found in any URL path map, or if the Azure
            API call fails.
        """
        gateway = self._get_gateway()
        url_path_maps = gateway.url_path_maps or []

        found = False
        for upm in url_path_maps:
            original = list(upm.path_rules or [])
            filtered = [r for r in original if r.name != rule_name]
            if len(filtered) < len(original):
                found = True
                upm.path_rules = filtered

        if not found:
            raise AzureGatewayError(
                f"Path rule '{rule_name}' not found on Application Gateway "
                f"'{self._gateway_name}'."
            )

        logger.info(
            "Deleting path rule '%s' from gateway '%s'.",
            rule_name,
            self._gateway_name,
        )

        try:
            poller = self._network_client.application_gateways.begin_create_or_update(
                resource_group_name=self._resource_group,
                application_gateway_name=self._gateway_name,
                parameters=gateway,
            )
            poller.result(timeout=600)
        except HttpResponseError as exc:
            raise AzureGatewayError(
                f"Failed to delete path rule '{rule_name}' on Application Gateway "
                f"'{self._gateway_name}': {exc}"
            ) from exc
