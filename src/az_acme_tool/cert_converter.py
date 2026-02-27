"""Certificate conversion and inspection utilities for az-acme-tool.

Provides pure-in-memory helpers for the certificate pipeline:
- PEM → PFX conversion (for Azure Application Gateway upload)
- SHA-256 fingerprinting (for identity / deduplication)
- Expiry extraction (for renewal-window comparisons)
- CSR generation (for ACME order finalization)

Private key material is never written to disk within this module.
All Azure SDK and ACME library integrations are the responsibility of callers.
"""

from __future__ import annotations

from datetime import UTC, datetime

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.types import (
    CertificateIssuerPrivateKeyTypes,
)
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID


class CertConverterError(Exception):
    """Raised when a certificate conversion or inspection operation fails."""


def pem_to_pfx(cert_pem: str, key_pem: str, password: str) -> bytes:
    """Convert a PEM-encoded certificate and private key to PKCS#12 (PFX) bytes.

    Args:
        cert_pem: PEM-encoded certificate (may include intermediate chain).
        key_pem: PEM-encoded private key matching the certificate.
        password: Passphrase used to encrypt the resulting PFX.

    Returns:
        Raw PKCS#12 bytes suitable for upload to Azure Application Gateway.

    Raises:
        CertConverterError: If the PEM data is malformed or serialization fails.
    """
    try:
        certificate = x509.load_pem_x509_certificate(cert_pem.encode())
        private_key: CertificateIssuerPrivateKeyTypes = serialization.load_pem_private_key(  # type: ignore[assignment]
            key_pem.encode(), password=None
        )
        pfx_bytes: bytes = pkcs12.serialize_key_and_certificates(
            name=None,
            key=private_key,
            cert=certificate,
            cas=None,
            encryption_algorithm=serialization.BestAvailableEncryption(password.encode()),
        )
    except (ValueError, TypeError, Exception) as exc:
        raise CertConverterError(f"Failed to convert PEM to PFX: {exc}") from exc
    return pfx_bytes


def cert_fingerprint(cert_pem: str) -> str:
    """Return the SHA-256 fingerprint of a PEM-encoded certificate.

    Args:
        cert_pem: PEM-encoded X.509 certificate.

    Returns:
        Lowercase hexadecimal string of length 64 (SHA-256 digest).

    Raises:
        CertConverterError: If the PEM data is malformed.
    """
    try:
        certificate = x509.load_pem_x509_certificate(cert_pem.encode())
        fingerprint: bytes = certificate.fingerprint(hashes.SHA256())
    except (ValueError, TypeError, Exception) as exc:
        raise CertConverterError(f"Failed to compute certificate fingerprint: {exc}") from exc
    return fingerprint.hex()


def cert_expiry(cert_pem: str) -> datetime:
    """Extract the notAfter expiry date from a PEM-encoded certificate.

    Args:
        cert_pem: PEM-encoded X.509 certificate.

    Returns:
        UTC-aware :class:`datetime` representing the certificate's expiry.

    Raises:
        CertConverterError: If the PEM data is malformed.
    """
    try:
        certificate = x509.load_pem_x509_certificate(cert_pem.encode())
        # cryptography>=42 exposes a timezone-aware attribute directly.
        # For cryptography 41.x compatibility, fall back to the naive attribute
        # and attach UTC tzinfo explicitly.
        if hasattr(certificate, "not_valid_after_utc"):
            expiry: datetime = certificate.not_valid_after_utc
        else:
            naive = getattr(certificate, "not_valid_after")
            expiry = naive.replace(tzinfo=UTC)
    except (ValueError, TypeError, Exception) as exc:
        raise CertConverterError(f"Failed to extract certificate expiry: {exc}") from exc
    return expiry


def generate_csr(domains: list[str], key_pem: str) -> bytes:
    """Generate a DER-encoded CSR with the supplied domains as Subject Alternative Names.

    Args:
        domains: One or more fully-qualified domain names to include as DNS SANs.
            The first domain is also used as the Common Name.
        key_pem: PEM-encoded private key (RSA or EC) used to sign the CSR.

    Returns:
        DER-encoded Certificate Signing Request bytes for use with
        :func:`acme.client.ClientV2.finalize_order`.

    Raises:
        CertConverterError: If the key PEM is malformed or CSR generation fails.
    """
    try:
        private_key: CertificateIssuerPrivateKeyTypes = serialization.load_pem_private_key(  # type: ignore[assignment]
            key_pem.encode(), password=None
        )
        san_names = [x509.DNSName(domain) for domain in domains]
        csr = (
            x509.CertificateSigningRequestBuilder()
            .subject_name(
                x509.Name(
                    [
                        x509.NameAttribute(NameOID.COMMON_NAME, domains[0]),
                    ]
                )
            )
            .add_extension(
                x509.SubjectAlternativeName(san_names),
                critical=False,
            )
            .sign(private_key, hashes.SHA256())
        )
        csr_der: bytes = csr.public_bytes(serialization.Encoding.DER)
    except (ValueError, TypeError, Exception) as exc:
        raise CertConverterError(f"Failed to generate CSR: {exc}") from exc
    return csr_der
