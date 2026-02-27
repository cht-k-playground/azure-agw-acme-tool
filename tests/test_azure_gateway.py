"""Tests for AzureGatewayClient and AzureGatewayError.

All Azure SDK calls are mocked via pytest-mock; no real Azure credentials
or network access are required.
"""

from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from azure.core.exceptions import HttpResponseError

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
    m.id = cert_id or f"/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Network/applicationGateways/gw/sslCertificates/{name}"
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


def _make_gateway_mock(
    ssl_certs: list[MagicMock] | None = None,
    listeners: list[MagicMock] | None = None,
) -> MagicMock:
    """Build a mock ApplicationGateway with configurable ssl_certificates and listeners."""
    m = MagicMock()
    m.ssl_certificates = ssl_certs or []
    m.http_listeners = listeners or []
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
    """AzureGatewayClient with a patched NetworkManagementClient."""
    with patch(
        "az_acme_tool.azure_gateway.NetworkManagementClient",
        return_value=mock_network_client,
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
        with patch(
            "az_acme_tool.azure_gateway.NetworkManagementClient"
        ) as mock_cls:
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
