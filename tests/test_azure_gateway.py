"""Tests for AzureGatewayClient and AzureGatewayError.

All Azure SDK calls are mocked via pytest-mock; no real Azure credentials
or network access are required.
"""

from __future__ import annotations

import base64
import logging
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from azure.core.exceptions import HttpResponseError
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from az_acme_tool.azure_gateway import AzureGatewayClient, AzureGatewayError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cert_der_b64(
    cn: str = "test.example.com",
    days_valid: int = 90,
) -> tuple[str, datetime]:
    """Generate a self-signed DER certificate and return (base64, expiry_utc)."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    expiry = datetime.now(UTC) + timedelta(days=days_valid)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(UTC))
        .not_valid_after(expiry)
        .sign(key, hashes.SHA256())
    )
    der = cert.public_bytes(serialization.Encoding.DER)
    return base64.b64encode(der).decode(), cert.not_valid_after_utc


def _make_ssl_cert_mock(
    name: str,
    cert_id: str | None = None,
    public_cert_data: str | None = None,
) -> MagicMock:
    """Build a mock ApplicationGatewaySslCertificate."""
    m = MagicMock()
    m.name = name
    default_id = (
        f"/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Network"
        f"/applicationGateways/gw/sslCertificates/{name}"
    )
    m.id = cert_id or default_id
    m.public_cert_data = public_cert_data
    return m


def _make_listener_mock(name: str, cert_id: str | None = None) -> MagicMock:
    """Build a mock ApplicationGatewayHttpListener."""
    m = MagicMock()
    m.name = name
    if cert_id:
        m.ssl_certificate = MagicMock()
        m.ssl_certificate.id = cert_id
    else:
        m.ssl_certificate = None
    return m


def _make_path_rule_mock(name: str) -> MagicMock:
    """Build a mock ApplicationGatewayPathRule."""
    m = MagicMock()
    m.name = name
    return m


def _make_url_path_map_mock(path_rules: list[MagicMock] | None = None) -> MagicMock:
    """Build a mock ApplicationGatewayUrlPathMap."""
    m = MagicMock()
    m.path_rules = path_rules or []
    return m


def _make_gateway_mock(
    ssl_certs: list[MagicMock] | None = None,
    listeners: list[MagicMock] | None = None,
    url_path_maps: list[MagicMock] | None = None,
) -> MagicMock:
    """Build a mock ApplicationGateway with configurable ssl_certificates and listeners."""
    m = MagicMock()
    m.ssl_certificates = ssl_certs or []
    m.http_listeners = listeners or []
    m.url_path_maps = url_path_maps or []
    return m


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_credential() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def mock_network_client() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def client(mock_credential: MagicMock, mock_network_client: MagicMock) -> AzureGatewayClient:
    """AzureGatewayClient with patched NetworkManagementClient and WebSiteManagementClient."""
    with (
        patch(
            "az_acme_tool.azure_gateway.NetworkManagementClient",
            return_value=mock_network_client,
        ),
        patch("az_acme_tool.azure_gateway.WebSiteManagementClient"),
    ):
        return AzureGatewayClient(
            subscription_id="00000000-0000-0000-0000-000000000001",
            resource_group="my-rg",
            gateway_name="my-gw",
            credential=mock_credential,
        )


# ---------------------------------------------------------------------------
# Instantiation tests
# ---------------------------------------------------------------------------


class TestAzureGatewayClientInit:
    def test_network_client_created_with_correct_args(
        self, mock_credential: MagicMock
    ) -> None:
        """NetworkManagementClient receives the injected credential and subscription_id."""
        with (
            patch("az_acme_tool.azure_gateway.NetworkManagementClient") as mock_cls,
            patch("az_acme_tool.azure_gateway.WebSiteManagementClient"),
        ):
            AzureGatewayClient(
                subscription_id="sub-123",
                resource_group="rg",
                gateway_name="gw",
                credential=mock_credential,
            )
        mock_cls.assert_called_once_with(
            credential=mock_credential,
            subscription_id="sub-123",
        )

    def test_fields_stored(
        self, client: AzureGatewayClient
    ) -> None:
        """Constructor stores subscription_id, resource_group, and gateway_name."""
        assert client._subscription_id == "00000000-0000-0000-0000-000000000001"
        assert client._resource_group == "my-rg"
        assert client._gateway_name == "my-gw"


# ---------------------------------------------------------------------------
# list_certificates tests
# ---------------------------------------------------------------------------


class TestListCertificates:
    def test_returns_certificates_with_expiry(
        self,
        client: AzureGatewayClient,
        mock_network_client: MagicMock,
    ) -> None:
        """Returns a list with name and expiry for each certificate."""
        b64, expected_expiry = _make_cert_der_b64()
        cert_mock = _make_ssl_cert_mock("my-cert", public_cert_data=b64)
        gateway = _make_gateway_mock(ssl_certs=[cert_mock])
        mock_network_client.application_gateways.get.return_value = gateway

        result = client.list_certificates()

        assert len(result) == 1
        assert result[0]["name"] == "my-cert"
        assert isinstance(result[0]["expiry"], datetime)
        # Allow a 2-second tolerance for cert generation timing
        assert abs((result[0]["expiry"] - expected_expiry).total_seconds()) < 2

    def test_returns_empty_list_when_no_certs(
        self,
        client: AzureGatewayClient,
        mock_network_client: MagicMock,
    ) -> None:
        """Returns an empty list when the gateway has no SSL certificates."""
        gateway = _make_gateway_mock(ssl_certs=[])
        mock_network_client.application_gateways.get.return_value = gateway

        result = client.list_certificates()

        assert result == []

    def test_expiry_is_none_for_keyvault_cert(
        self,
        client: AzureGatewayClient,
        mock_network_client: MagicMock,
    ) -> None:
        """Returns expiry=None when public_cert_data is None (Key Vault reference)."""
        cert_mock = _make_ssl_cert_mock("kv-cert", public_cert_data=None)
        gateway = _make_gateway_mock(ssl_certs=[cert_mock])
        mock_network_client.application_gateways.get.return_value = gateway

        result = client.list_certificates()

        assert result[0]["expiry"] is None

    def test_raises_azure_gateway_error_on_api_failure(
        self,
        client: AzureGatewayClient,
        mock_network_client: MagicMock,
    ) -> None:
        """Raises AzureGatewayError when the Azure API returns HttpResponseError."""
        mock_network_client.application_gateways.get.side_effect = HttpResponseError(
            message="Gateway not found"
        )

        with pytest.raises(AzureGatewayError, match="Failed to fetch Application Gateway"):
            client.list_certificates()


# ---------------------------------------------------------------------------
# get_certificate_expiry tests
# ---------------------------------------------------------------------------


class TestGetCertificateExpiry:
    def test_returns_expiry_for_known_cert(
        self,
        client: AzureGatewayClient,
        mock_network_client: MagicMock,
    ) -> None:
        """Returns expiry datetime when certificate exists with public_cert_data."""
        b64, expected_expiry = _make_cert_der_b64(days_valid=60)
        cert_mock = _make_ssl_cert_mock("tls-cert", public_cert_data=b64)
        gateway = _make_gateway_mock(ssl_certs=[cert_mock])
        mock_network_client.application_gateways.get.return_value = gateway

        expiry = client.get_certificate_expiry("tls-cert")

        assert isinstance(expiry, datetime)
        assert expiry.tzinfo is not None
        assert abs((expiry - expected_expiry).total_seconds()) < 2

    def test_raises_when_cert_not_found(
        self,
        client: AzureGatewayClient,
        mock_network_client: MagicMock,
    ) -> None:
        """Raises AzureGatewayError when no certificate with the given name exists."""
        gateway = _make_gateway_mock(ssl_certs=[])
        mock_network_client.application_gateways.get.return_value = gateway

        with pytest.raises(AzureGatewayError, match="not found"):
            client.get_certificate_expiry("missing-cert")

    def test_raises_when_expiry_unavailable(
        self,
        client: AzureGatewayClient,
        mock_network_client: MagicMock,
    ) -> None:
        """Raises AzureGatewayError when certificate has no public_cert_data."""
        cert_mock = _make_ssl_cert_mock("kv-cert", public_cert_data=None)
        gateway = _make_gateway_mock(ssl_certs=[cert_mock])
        mock_network_client.application_gateways.get.return_value = gateway

        with pytest.raises(AzureGatewayError, match="Expiry date unavailable"):
            client.get_certificate_expiry("kv-cert")

    def test_raises_on_api_error(
        self,
        client: AzureGatewayClient,
        mock_network_client: MagicMock,
    ) -> None:
        """Raises AzureGatewayError when the underlying Azure API fails."""
        mock_network_client.application_gateways.get.side_effect = HttpResponseError(
            message="Unauthorized"
        )

        with pytest.raises(AzureGatewayError, match="Failed to fetch Application Gateway"):
            client.get_certificate_expiry("any-cert")


# ---------------------------------------------------------------------------
# update_listener_certificate tests
# ---------------------------------------------------------------------------


class TestUpdateListenerCertificate:
    def test_updates_listener_successfully(
        self,
        client: AzureGatewayClient,
        mock_network_client: MagicMock,
    ) -> None:
        """Updates listener ssl_certificate reference and calls begin_create_or_update."""
        cert_id = "/subscriptions/sub/rg/gw/sslCertificates/new-cert"
        cert_mock = _make_ssl_cert_mock("new-cert", cert_id=cert_id)
        listener_mock = _make_listener_mock("https-listener")
        gateway = _make_gateway_mock(ssl_certs=[cert_mock], listeners=[listener_mock])
        mock_network_client.application_gateways.get.return_value = gateway

        poller_mock = MagicMock()
        mock_network_client.application_gateways.begin_create_or_update.return_value = (
            poller_mock
        )

        client.update_listener_certificate("https-listener", "new-cert")

        # listener's ssl_certificate must have been updated to the cert's ARM id
        assert listener_mock.ssl_certificate.id == cert_id
        mock_network_client.application_gateways.begin_create_or_update.assert_called_once()
        poller_mock.result.assert_called_once_with(timeout=600)

    def test_raises_when_listener_not_found(
        self,
        client: AzureGatewayClient,
        mock_network_client: MagicMock,
    ) -> None:
        """Raises AzureGatewayError when listener name does not exist on gateway."""
        cert_mock = _make_ssl_cert_mock("cert")
        gateway = _make_gateway_mock(ssl_certs=[cert_mock], listeners=[])
        mock_network_client.application_gateways.get.return_value = gateway

        with pytest.raises(AzureGatewayError, match="Listener 'missing-listener' not found"):
            client.update_listener_certificate("missing-listener", "cert")

    def test_raises_when_cert_not_found(
        self,
        client: AzureGatewayClient,
        mock_network_client: MagicMock,
    ) -> None:
        """Raises AzureGatewayError when certificate name does not exist on gateway."""
        listener_mock = _make_listener_mock("https-listener")
        gateway = _make_gateway_mock(ssl_certs=[], listeners=[listener_mock])
        mock_network_client.application_gateways.get.return_value = gateway

        with pytest.raises(AzureGatewayError, match="Certificate 'missing-cert' not found"):
            client.update_listener_certificate("https-listener", "missing-cert")

    def test_raises_on_api_error_during_update(
        self,
        client: AzureGatewayClient,
        mock_network_client: MagicMock,
    ) -> None:
        """Raises AzureGatewayError when begin_create_or_update raises HttpResponseError."""
        cert_id = "/subscriptions/sub/rg/gw/sslCertificates/cert"
        cert_mock = _make_ssl_cert_mock("cert", cert_id=cert_id)
        listener_mock = _make_listener_mock("https-listener")
        gateway = _make_gateway_mock(ssl_certs=[cert_mock], listeners=[listener_mock])
        mock_network_client.application_gateways.get.return_value = gateway
        mock_network_client.application_gateways.begin_create_or_update.side_effect = (
            HttpResponseError(message="Conflict")
        )

        with pytest.raises(AzureGatewayError, match="Failed to update listener"):
            client.update_listener_certificate("https-listener", "cert")

    def test_raises_when_cert_has_no_arm_id(
        self,
        client: AzureGatewayClient,
        mock_network_client: MagicMock,
    ) -> None:
        """Raises AzureGatewayError when cert exists but has no ARM resource ID."""
        cert_mock = _make_ssl_cert_mock("cert", cert_id=None)
        cert_mock.id = None  # explicitly set to None
        listener_mock = _make_listener_mock("https-listener")
        gateway = _make_gateway_mock(ssl_certs=[cert_mock], listeners=[listener_mock])
        mock_network_client.application_gateways.get.return_value = gateway

        with pytest.raises(AzureGatewayError, match="has no ARM resource ID"):
            client.update_listener_certificate("https-listener", "cert")


# ---------------------------------------------------------------------------
# list_acme_challenge_rules tests
# ---------------------------------------------------------------------------


class TestListAcmeChallengeRules:
    def test_returns_matching_rule_names(
        self,
        client: AzureGatewayClient,
        mock_network_client: MagicMock,
    ) -> None:
        """Returns names of path rules prefixed with acme-challenge-."""
        rule1 = _make_path_rule_mock("acme-challenge-www-example-com-1709030400")
        rule2 = _make_path_rule_mock("acme-challenge-api-example-com-1709030401")
        rule_other = _make_path_rule_mock("normal-rule")
        upm = _make_url_path_map_mock(path_rules=[rule1, rule2, rule_other])
        gateway = _make_gateway_mock(url_path_maps=[upm])
        mock_network_client.application_gateways.get.return_value = gateway

        result = client.list_acme_challenge_rules()

        assert sorted(result) == sorted(
            [
                "acme-challenge-www-example-com-1709030400",
                "acme-challenge-api-example-com-1709030401",
            ]
        )

    def test_returns_empty_list_when_no_matching_rules(
        self,
        client: AzureGatewayClient,
        mock_network_client: MagicMock,
    ) -> None:
        """Returns empty list when no acme-challenge- prefixed rules exist."""
        rule = _make_path_rule_mock("normal-rule")
        upm = _make_url_path_map_mock(path_rules=[rule])
        gateway = _make_gateway_mock(url_path_maps=[upm])
        mock_network_client.application_gateways.get.return_value = gateway

        result = client.list_acme_challenge_rules()

        assert result == []

    def test_returns_empty_list_when_no_url_path_maps(
        self,
        client: AzureGatewayClient,
        mock_network_client: MagicMock,
    ) -> None:
        """Returns empty list when gateway has no URL path maps."""
        gateway = _make_gateway_mock(url_path_maps=[])
        mock_network_client.application_gateways.get.return_value = gateway

        result = client.list_acme_challenge_rules()

        assert result == []

    def test_raises_azure_gateway_error_on_api_failure(
        self,
        client: AzureGatewayClient,
        mock_network_client: MagicMock,
    ) -> None:
        """Raises AzureGatewayError when the Azure API returns HttpResponseError."""
        mock_network_client.application_gateways.get.side_effect = HttpResponseError(
            message="Forbidden"
        )

        with pytest.raises(AzureGatewayError, match="Failed to fetch Application Gateway"):
            client.list_acme_challenge_rules()


# ---------------------------------------------------------------------------
# delete_routing_rule tests
# ---------------------------------------------------------------------------


class TestDeleteRoutingRule:
    def test_deletes_existing_rule_successfully(
        self,
        client: AzureGatewayClient,
        mock_network_client: MagicMock,
    ) -> None:
        """Removes the named path rule and calls begin_create_or_update."""
        rule = _make_path_rule_mock("acme-challenge-www-example-com-1709030400")
        upm = _make_url_path_map_mock(path_rules=[rule])
        gateway = _make_gateway_mock(url_path_maps=[upm])
        mock_network_client.application_gateways.get.return_value = gateway
        poller_mock = MagicMock()
        mock_network_client.application_gateways.begin_create_or_update.return_value = (
            poller_mock
        )

        client.delete_routing_rule("acme-challenge-www-example-com-1709030400")

        # Rule should have been removed from the URL path map
        assert upm.path_rules == []
        mock_network_client.application_gateways.begin_create_or_update.assert_called_once()
        poller_mock.result.assert_called_once_with(timeout=600)

    def test_raises_when_rule_not_found(
        self,
        client: AzureGatewayClient,
        mock_network_client: MagicMock,
    ) -> None:
        """Raises AzureGatewayError when the named rule does not exist."""
        rule = _make_path_rule_mock("other-rule")
        upm = _make_url_path_map_mock(path_rules=[rule])
        gateway = _make_gateway_mock(url_path_maps=[upm])
        mock_network_client.application_gateways.get.return_value = gateway

        with pytest.raises(AzureGatewayError, match="Path rule 'missing-rule' not found"):
            client.delete_routing_rule("missing-rule")

    def test_raises_on_api_error_during_delete(
        self,
        client: AzureGatewayClient,
        mock_network_client: MagicMock,
    ) -> None:
        """Raises AzureGatewayError when begin_create_or_update raises HttpResponseError."""
        rule = _make_path_rule_mock("acme-challenge-www-example-com-1709030400")
        upm = _make_url_path_map_mock(path_rules=[rule])
        gateway = _make_gateway_mock(url_path_maps=[upm])
        mock_network_client.application_gateways.get.return_value = gateway
        mock_network_client.application_gateways.begin_create_or_update.side_effect = (
            HttpResponseError(message="Conflict")
        )

        with pytest.raises(AzureGatewayError, match="Failed to delete path rule"):
            client.delete_routing_rule("acme-challenge-www-example-com-1709030400")


# ---------------------------------------------------------------------------
# update_function_app_settings tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_web_client() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def client_with_web(
    mock_credential: MagicMock,
    mock_network_client: MagicMock,
    mock_web_client: MagicMock,
) -> AzureGatewayClient:
    """AzureGatewayClient with both NetworkManagementClient and WebSiteManagementClient patched."""
    with (
        patch(
            "az_acme_tool.azure_gateway.NetworkManagementClient",
            return_value=mock_network_client,
        ),
        patch(
            "az_acme_tool.azure_gateway.WebSiteManagementClient",
            return_value=mock_web_client,
        ),
    ):
        return AzureGatewayClient(
            subscription_id="00000000-0000-0000-0000-000000000001",
            resource_group="my-rg",
            gateway_name="my-gw",
            credential=mock_credential,
        )


class TestUploadSslCertificate:
    def test_uploads_certificate_successfully(
        self,
        client: AzureGatewayClient,
        mock_network_client: MagicMock,
    ) -> None:
        """Adds the new cert to gateway.ssl_certificates and calls begin_create_or_update."""
        gateway = _make_gateway_mock(ssl_certs=[])
        mock_network_client.application_gateways.get.return_value = gateway
        poller_mock = MagicMock()
        mock_network_client.application_gateways.begin_create_or_update.return_value = (
            poller_mock
        )

        pfx_bytes = b"\x00\x01\x02\x03 fake pfx data"
        client.upload_ssl_certificate(
            cert_name="www-example-com-cert",
            pfx_data=pfx_bytes,
            password="hunter2",
        )

        assert len(gateway.ssl_certificates) == 1
        new_cert = gateway.ssl_certificates[0]
        assert new_cert.name == "www-example-com-cert"
        assert new_cert.data == base64.b64encode(pfx_bytes).decode("ascii")
        assert new_cert.password == "hunter2"
        mock_network_client.application_gateways.begin_create_or_update.assert_called_once()
        poller_mock.result.assert_called_once_with(timeout=600)

    def test_replaces_existing_certificate_with_same_name(
        self,
        client: AzureGatewayClient,
        mock_network_client: MagicMock,
    ) -> None:
        """An existing cert with the same name is replaced rather than duplicated."""
        existing = _make_ssl_cert_mock("www-example-com-cert")
        other = _make_ssl_cert_mock("other-cert")
        gateway = _make_gateway_mock(ssl_certs=[existing, other])
        mock_network_client.application_gateways.get.return_value = gateway
        poller_mock = MagicMock()
        mock_network_client.application_gateways.begin_create_or_update.return_value = (
            poller_mock
        )

        client.upload_ssl_certificate(
            cert_name="www-example-com-cert",
            pfx_data=b"new",
            password="pw",
        )

        names = [c.name for c in gateway.ssl_certificates]
        assert names.count("www-example-com-cert") == 1
        assert "other-cert" in names

    def test_password_not_logged(
        self,
        client: AzureGatewayClient,
        mock_network_client: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """The PFX password must not appear in any log message."""
        gateway = _make_gateway_mock(ssl_certs=[])
        mock_network_client.application_gateways.get.return_value = gateway
        mock_network_client.application_gateways.begin_create_or_update.return_value = (
            MagicMock()
        )

        secret_password = "SUPER_SECRET_PFX_PASSWORD_xyz"
        with caplog.at_level(logging.DEBUG, logger="az_acme_tool.azure_gateway"):
            client.upload_ssl_certificate(
                cert_name="cert",
                pfx_data=b"pfx-bytes",
                password=secret_password,
            )

        assert secret_password not in caplog.text

    def test_raises_on_api_error(
        self,
        client: AzureGatewayClient,
        mock_network_client: MagicMock,
    ) -> None:
        """begin_create_or_update raising HttpResponseError surfaces AzureGatewayError."""
        gateway = _make_gateway_mock(ssl_certs=[])
        mock_network_client.application_gateways.get.return_value = gateway
        mock_network_client.application_gateways.begin_create_or_update.side_effect = (
            HttpResponseError(message="Conflict")
        )

        with pytest.raises(AzureGatewayError, match="Failed to upload SSL certificate"):
            client.upload_ssl_certificate(
                cert_name="cert",
                pfx_data=b"pfx",
                password="pw",
            )


class TestAddRoutingRule:
    def test_creates_path_rule_with_correct_pattern(
        self,
        client: AzureGatewayClient,
        mock_network_client: MagicMock,
    ) -> None:
        """A new URL path map / backend pool / HTTP settings is appended with the ACME path."""
        gateway = _make_gateway_mock(url_path_maps=[])
        gateway.backend_address_pools = []
        gateway.backend_http_settings_collection = []
        mock_network_client.application_gateways.get.return_value = gateway
        poller_mock = MagicMock()
        mock_network_client.application_gateways.begin_create_or_update.return_value = (
            poller_mock
        )

        client.add_routing_rule(
            rule_name="acme-challenge-www-example-com-1709030400",
            domain="www.example.com",
            backend_fqdn="my-acme-func.azurewebsites.net",
        )

        # New URL path map appended with the ACME challenge path rule.
        assert len(gateway.url_path_maps) == 1
        upm = gateway.url_path_maps[0]
        assert upm.name == "acme-challenge-www-example-com-1709030400"
        assert len(upm.path_rules) == 1
        path_rule = upm.path_rules[0]
        assert path_rule.name == "acme-challenge-www-example-com-1709030400"
        assert path_rule.paths == ["/.well-known/acme-challenge/*"]

        # Backend pool & HTTP settings appended with the function FQDN / HTTPS:443.
        assert len(gateway.backend_address_pools) == 1
        pool = gateway.backend_address_pools[0]
        assert pool.backend_addresses[0].fqdn == "my-acme-func.azurewebsites.net"
        assert len(gateway.backend_http_settings_collection) == 1
        settings = gateway.backend_http_settings_collection[0]
        assert settings.protocol == "Https"
        assert settings.port == 443
        assert settings.pick_host_name_from_backend_address is True

        mock_network_client.application_gateways.begin_create_or_update.assert_called_once()
        poller_mock.result.assert_called_once_with(timeout=600)

    def test_raises_on_api_error(
        self,
        client: AzureGatewayClient,
        mock_network_client: MagicMock,
    ) -> None:
        """HttpResponseError from begin_create_or_update is surfaced as AzureGatewayError."""
        gateway = _make_gateway_mock(url_path_maps=[])
        gateway.backend_address_pools = []
        gateway.backend_http_settings_collection = []
        mock_network_client.application_gateways.get.return_value = gateway
        mock_network_client.application_gateways.begin_create_or_update.side_effect = (
            HttpResponseError(message="Forbidden")
        )

        with pytest.raises(AzureGatewayError, match="Failed to add routing rule"):
            client.add_routing_rule(
                rule_name="acme-challenge-www-example-com-1709030400",
                domain="www.example.com",
                backend_fqdn="fn.azurewebsites.net",
            )


class TestGetListenersByCertName:
    def test_returns_listener_names_when_referenced(
        self,
        client: AzureGatewayClient,
        mock_network_client: MagicMock,
    ) -> None:
        """Returns names of listeners whose ssl_certificate ARM ID ends with /{cert_name}."""
        cert_id = (
            "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Network"
            "/applicationGateways/gw/sslCertificates/www-example-com-cert"
        )
        listener1 = _make_listener_mock("https-443-www", cert_id=cert_id)
        listener2 = _make_listener_mock("https-443-api", cert_id=cert_id)
        listener3 = _make_listener_mock("https-443-other", cert_id=cert_id.replace(
            "www-example-com-cert", "other-cert"
        ))
        gateway = _make_gateway_mock(listeners=[listener1, listener2, listener3])
        mock_network_client.application_gateways.get.return_value = gateway

        result = client.get_listeners_by_cert_name("www-example-com-cert")

        assert sorted(result) == ["https-443-api", "https-443-www"]

    def test_returns_empty_list_when_no_match(
        self,
        client: AzureGatewayClient,
        mock_network_client: MagicMock,
    ) -> None:
        """Returns empty list when no listener references the named certificate."""
        listener = _make_listener_mock("https-443", cert_id=None)
        gateway = _make_gateway_mock(listeners=[listener])
        mock_network_client.application_gateways.get.return_value = gateway

        result = client.get_listeners_by_cert_name("missing-cert")

        assert result == []

    def test_raises_on_api_error(
        self,
        client: AzureGatewayClient,
        mock_network_client: MagicMock,
    ) -> None:
        """HttpResponseError from get propagates as AzureGatewayError."""
        mock_network_client.application_gateways.get.side_effect = HttpResponseError(
            message="Forbidden"
        )

        with pytest.raises(AzureGatewayError, match="Failed to fetch Application Gateway"):
            client.get_listeners_by_cert_name("any-cert")


class TestUpdateFunctionAppSettings:
    def test_calls_update_application_settings_with_correct_args(
        self,
        client_with_web: AzureGatewayClient,
        mock_web_client: MagicMock,
    ) -> None:
        """Calls WebSiteManagementClient.web_apps.update_application_settings with correct args."""
        settings = {"ACME_CHALLENGE_RESPONSE": "TOKEN.KEY_AUTH"}

        client_with_web.update_function_app_settings(
            function_app_name="my-func-app",
            settings=settings,
        )

        mock_web_client.web_apps.update_application_settings.assert_called_once()
        call_kwargs = mock_web_client.web_apps.update_application_settings.call_args
        assert call_kwargs.kwargs["resource_group_name"] == "my-rg"
        assert call_kwargs.kwargs["name"] == "my-func-app"
        # Verify the StringDictionary properties contain the settings
        string_dict = call_kwargs.kwargs["app_settings"]
        assert string_dict.properties == settings

    def test_setting_values_not_in_log_output(
        self,
        client_with_web: AzureGatewayClient,
        mock_web_client: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Setting values (key authorization) must not appear in any log output."""
        secret_value = "SUPER_SECRET_KEY_AUTH_VALUE"
        settings = {"ACME_CHALLENGE_RESPONSE": secret_value}

        with caplog.at_level(logging.DEBUG, logger="az_acme_tool.azure_gateway"):
            client_with_web.update_function_app_settings(
                function_app_name="my-func-app",
                settings=settings,
            )

        assert secret_value not in caplog.text

    def test_raises_azure_gateway_error_on_api_failure(
        self,
        client_with_web: AzureGatewayClient,
        mock_web_client: MagicMock,
    ) -> None:
        """Raises AzureGatewayError when WebSiteManagementClient raises HttpResponseError."""
        mock_web_client.web_apps.update_application_settings.side_effect = (
            HttpResponseError(message="Unauthorized")
        )

        with pytest.raises(
            AzureGatewayError, match="Failed to update Application Settings"
        ):
            client_with_web.update_function_app_settings(
                function_app_name="my-func-app",
                settings={"ACME_CHALLENGE_RESPONSE": "value"},
            )
