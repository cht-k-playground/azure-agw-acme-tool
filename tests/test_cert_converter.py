"""Tests for az_acme_tool.cert_converter.

All cryptographic fixtures are generated in memory at test time using the
`cryptography` library. No private key material is stored on disk.
"""

from __future__ import annotations

import datetime
from datetime import UTC

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from az_acme_tool.cert_converter import (
    CertConverterError,
    cert_expiry,
    cert_fingerprint,
    generate_csr,
    pem_to_pfx,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _generate_rsa_key() -> rsa.RSAPrivateKey:
    """Generate a 2048-bit RSA key pair in memory."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _key_to_pem(key: rsa.RSAPrivateKey) -> str:
    """Serialize an RSA private key to PEM string (no encryption)."""
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


def _self_signed_cert_pem(
    key: rsa.RSAPrivateKey,
    not_valid_before: datetime.datetime,
    not_valid_after: datetime.datetime,
    common_name: str = "test.example.com",
) -> str:
    """Create a self-signed certificate PEM string."""
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_valid_before)
        .not_valid_after(not_valid_after)
        .sign(key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode()


@pytest.fixture()
def rsa_key() -> rsa.RSAPrivateKey:
    """Fresh RSA-2048 private key."""
    return _generate_rsa_key()


@pytest.fixture()
def rsa_key_pem(rsa_key: rsa.RSAPrivateKey) -> str:
    """PEM string of a fresh RSA-2048 private key."""
    return _key_to_pem(rsa_key)


@pytest.fixture()
def future_cert_pem(rsa_key: rsa.RSAPrivateKey) -> str:
    """Self-signed cert valid for the next 365 days."""
    now = datetime.datetime.now(tz=UTC)
    return _self_signed_cert_pem(
        rsa_key,
        not_valid_before=now - datetime.timedelta(seconds=1),
        not_valid_after=now + datetime.timedelta(days=365),
    )


@pytest.fixture()
def expired_cert_pem(rsa_key: rsa.RSAPrivateKey) -> str:
    """Self-signed cert that expired 30 days ago."""
    now = datetime.datetime.now(tz=UTC)
    return _self_signed_cert_pem(
        rsa_key,
        not_valid_before=now - datetime.timedelta(days=60),
        not_valid_after=now - datetime.timedelta(days=30),
    )


# ---------------------------------------------------------------------------
# pem_to_pfx
# ---------------------------------------------------------------------------


class TestPemToPfx:
    def test_valid_inputs_produce_decodable_pfx(
        self, future_cert_pem: str, rsa_key_pem: str
    ) -> None:
        password = "test-password-123"
        pfx_bytes = pem_to_pfx(future_cert_pem, rsa_key_pem, password)
        # Must be non-empty bytes
        assert isinstance(pfx_bytes, bytes)
        assert len(pfx_bytes) > 0
        # Must be decodable with the same password
        private_key, cert, _ = pkcs12.load_key_and_certificates(pfx_bytes, password.encode())
        assert cert is not None
        assert private_key is not None

    def test_malformed_cert_pem_raises_error(self, rsa_key_pem: str) -> None:
        with pytest.raises(CertConverterError, match="Failed to convert PEM to PFX"):
            pem_to_pfx("not-valid-pem", rsa_key_pem, "password")

    def test_malformed_key_pem_raises_error(self, future_cert_pem: str) -> None:
        with pytest.raises(CertConverterError, match="Failed to convert PEM to PFX"):
            pem_to_pfx(future_cert_pem, "not-valid-key", "password")

    def test_wrong_password_does_not_raise_on_creation(
        self, future_cert_pem: str, rsa_key_pem: str
    ) -> None:
        # pem_to_pfx itself should succeed; failure happens on decryption
        pfx_bytes = pem_to_pfx(future_cert_pem, rsa_key_pem, "correct-password")
        assert isinstance(pfx_bytes, bytes)


# ---------------------------------------------------------------------------
# cert_fingerprint
# ---------------------------------------------------------------------------


class TestCertFingerprint:
    def test_returns_64_char_hex_string(self, future_cert_pem: str) -> None:
        fp = cert_fingerprint(future_cert_pem)
        assert isinstance(fp, str)
        assert len(fp) == 64  # 32 bytes × 2 hex chars

    def test_deterministic(self, future_cert_pem: str) -> None:
        fp1 = cert_fingerprint(future_cert_pem)
        fp2 = cert_fingerprint(future_cert_pem)
        assert fp1 == fp2

    def test_different_certs_have_different_fingerprints(self) -> None:
        key1 = _generate_rsa_key()
        key2 = _generate_rsa_key()
        now = datetime.datetime.now(tz=UTC)
        delta_before = datetime.timedelta(seconds=1)
        delta_after = datetime.timedelta(days=1)
        pem1 = _self_signed_cert_pem(key1, now - delta_before, now + delta_after)
        pem2 = _self_signed_cert_pem(key2, now - delta_before, now + delta_after)
        assert cert_fingerprint(pem1) != cert_fingerprint(pem2)

    def test_malformed_pem_raises_error(self) -> None:
        with pytest.raises(CertConverterError, match="Failed to compute certificate fingerprint"):
            cert_fingerprint("not-valid-pem")


# ---------------------------------------------------------------------------
# cert_expiry
# ---------------------------------------------------------------------------


class TestCertExpiry:
    def test_future_cert_returns_future_datetime(self, future_cert_pem: str) -> None:
        expiry = cert_expiry(future_cert_pem)
        assert expiry > datetime.datetime.now(tz=UTC)

    def test_expired_cert_returns_past_datetime(self, expired_cert_pem: str) -> None:
        expiry = cert_expiry(expired_cert_pem)
        assert expiry < datetime.datetime.now(tz=UTC)

    def test_returned_datetime_is_utc_aware(self, future_cert_pem: str) -> None:
        expiry = cert_expiry(future_cert_pem)
        assert expiry.tzinfo is not None

    def test_malformed_pem_raises_error(self) -> None:
        with pytest.raises(CertConverterError, match="Failed to extract certificate expiry"):
            cert_expiry("not-valid-pem")


# ---------------------------------------------------------------------------
# generate_csr
# ---------------------------------------------------------------------------


class TestGenerateCsr:
    def test_all_domains_appear_as_sans(self, rsa_key_pem: str) -> None:
        domains = ["www.example.com", "api.example.com"]
        csr_der = generate_csr(domains, rsa_key_pem)
        assert isinstance(csr_der, bytes)
        assert len(csr_der) > 0
        # Decode DER and inspect SANs
        csr = x509.load_der_x509_csr(csr_der)
        san_ext = csr.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        dns_names = san_ext.value.get_values_for_type(x509.DNSName)
        for domain in domains:
            assert domain in dns_names

    def test_single_domain_csr(self, rsa_key_pem: str) -> None:
        csr_der = generate_csr(["example.com"], rsa_key_pem)
        csr = x509.load_der_x509_csr(csr_der)
        san_ext = csr.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        dns_names = san_ext.value.get_values_for_type(x509.DNSName)
        assert dns_names == ["example.com"]

    def test_first_domain_is_common_name(self, rsa_key_pem: str) -> None:
        csr_der = generate_csr(["primary.example.com", "secondary.example.com"], rsa_key_pem)
        csr = x509.load_der_x509_csr(csr_der)
        cn_attrs = csr.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        assert cn_attrs[0].value == "primary.example.com"

    def test_malformed_key_raises_error(self) -> None:
        with pytest.raises(CertConverterError, match="Failed to generate CSR"):
            generate_csr(["example.com"], "not-a-key")

    def test_returns_bytes(self, rsa_key_pem: str) -> None:
        result = generate_csr(["test.example.com"], rsa_key_pem)
        assert isinstance(result, bytes)
