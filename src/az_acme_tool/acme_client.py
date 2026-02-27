"""ACME HTTP-01 challenge client for az-acme-tool.

Wraps the ``acme`` + ``josepy`` libraries to provide a high-level interface
for the ACME v2 protocol certificate issuance flow (RFC 8555).

All ACME-related failures are surfaced as :class:`AcmeError`.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from acme import challenges, client, errors, messages
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509 import (
    CertificateSigningRequestBuilder,
    DNSName,
    Name,
    NameAttribute,
    NameOID,
    SubjectAlternativeName,
)
from josepy.jwk import JWKRSA

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class AcmeError(Exception):
    """Raised for all ACME protocol and operational failures."""


# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------

_MAX_RETRIES = 3
_RETRY_BASE_DELAY_S = 10


def _with_retry(fn: Any, *args: Any, **kwargs: Any) -> Any:
    """Call *fn* with exponential back-off on transient ACME errors.

    Retries up to :data:`_MAX_RETRIES` times (total attempts = ``_MAX_RETRIES``)
    with delays of ``_RETRY_BASE_DELAY_S``, ``2 * _RETRY_BASE_DELAY_S``, etc.

    Parameters
    ----------
    fn:
        Callable to invoke.
    *args, **kwargs:
        Forwarded to *fn*.

    Raises
    ------
    AcmeError
        If all retry attempts are exhausted.
    """
    last_exc: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except errors.Error as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES:
                delay = _RETRY_BASE_DELAY_S * (2 ** (attempt - 1))
                logger.warning(
                    "ACME transient error (attempt %d/%d): %s — retrying in %ds",
                    attempt,
                    _MAX_RETRIES,
                    exc,
                    delay,
                )
                time.sleep(delay)
            else:
                logger.error(
                    "ACME error after %d attempts: %s",
                    _MAX_RETRIES,
                    exc,
                )
    raise AcmeError(
        f"ACME operation failed after {_MAX_RETRIES} attempts: {last_exc}"
    ) from last_exc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _generate_rsa_key() -> rsa.RSAPrivateKey:
    """Generate a new RSA-2048 private key."""
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )


def _load_or_generate_account_key(account_key_path: Path) -> JWKRSA:
    """Load an existing RSA key from *account_key_path* or generate a new one.

    If the file does not exist, a new RSA-2048 key is generated and written
    to *account_key_path* with mode ``0o600``.

    Parameters
    ----------
    account_key_path:
        Path to the PEM-encoded RSA private key file.

    Returns
    -------
    JWKRSA
        The loaded or freshly generated JWK-wrapped RSA key.
    """
    if account_key_path.exists():
        logger.debug("Loading existing account key from %s", account_key_path)
        pem_bytes = account_key_path.read_bytes()
        private_key = serialization.load_pem_private_key(pem_bytes, password=None)
        if not isinstance(private_key, rsa.RSAPrivateKey):
            raise AcmeError(f"Account key at {account_key_path} is not an RSA private key")
        return JWKRSA(key=private_key)

    logger.debug("Generating new RSA-2048 account key -> %s", account_key_path)
    private_key = _generate_rsa_key()
    pem_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    account_key_path.parent.mkdir(parents=True, exist_ok=True)
    account_key_path.write_bytes(pem_bytes)
    account_key_path.chmod(0o600)
    return JWKRSA(key=private_key)


def _build_temp_csr(domains: list[str]) -> bytes:
    """Build a self-signed CSR (PEM) with the given DNS SANs.

    Used internally by :meth:`AcmeClient.new_order` so that the ACME library
    can extract identifiers from the CSR.  The real CSR (with the production
    private key) is supplied at :meth:`AcmeClient.finalize_order` time.
    """
    temp_key = _generate_rsa_key()
    # Use the first domain as the CN
    cn = domains[0] if domains else "acme"
    csr = (
        CertificateSigningRequestBuilder()
        .subject_name(Name([NameAttribute(NameOID.COMMON_NAME, cn)]))
        .add_extension(
            SubjectAlternativeName([DNSName(d) for d in domains]),
            critical=False,
        )
        .sign(temp_key, hashes.SHA256())
    )
    return csr.public_bytes(serialization.Encoding.PEM)


# ---------------------------------------------------------------------------
# AcmeClient
# ---------------------------------------------------------------------------


class AcmeClient:
    """High-level ACME v2 client for HTTP-01 certificate issuance.

    Parameters
    ----------
    directory_url:
        ACME CA directory URL, e.g.
        ``"https://acme-v02.api.letsencrypt.org/directory"`` or the staging
        equivalent.
    """

    def __init__(self, directory_url: str) -> None:
        self._directory_url = directory_url
        # These are set after register_account() is called
        self._account_key: JWKRSA | None = None
        self._acme_client: client.ClientV2 | None = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_client(self) -> client.ClientV2:
        """Return the underlying ``acme.client.ClientV2`` instance.

        Raises
        ------
        AcmeError
            If :meth:`register_account` has not yet been called.
        """
        if self._acme_client is None:
            raise AcmeError("AcmeClient is not initialised — call register_account() first")
        return self._acme_client

    def _get_account_key(self) -> JWKRSA:
        """Return the account JWK key.

        Raises
        ------
        AcmeError
            If :meth:`register_account` has not yet been called.
        """
        if self._account_key is None:
            raise AcmeError("AcmeClient has no account key — call register_account() first")
        return self._account_key

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def register_account(self, email: str, account_key_path: Path) -> str:
        """Register (or resume) an ACME account.

        Generates a new RSA-2048 account key and registers with the CA.
        If *account_key_path* already exists, the key is reused and no new
        account is created.

        Parameters
        ----------
        email:
            Contact email address for the ACME account.
        account_key_path:
            Filesystem path where the PEM-encoded account key is stored.
            Created with mode ``0o600`` if it does not exist.

        Returns
        -------
        str
            The account URL returned by the CA.

        Raises
        ------
        AcmeError
            On ACME protocol or key file errors.
        """
        self._account_key = _load_or_generate_account_key(account_key_path)
        net = client.ClientNetwork(key=self._account_key)
        directory = client.ClientV2.get_directory(self._directory_url, net)
        self._acme_client = client.ClientV2(directory, net)

        new_reg = messages.NewRegistration.from_data(
            email=email,
            terms_of_service_agreed=True,
        )
        # Call new_account directly — ConflictError (409) means the account
        # already exists and must not be retried as a transient error.
        try:
            regr = self._acme_client.new_account(new_reg)
        except errors.ConflictError as exc:
            # Account already exists — update the client's account reference
            account_url: str = exc.location
            logger.info("ACME account already exists at %s", account_url)
            # Fetch the existing registration
            existing = self._acme_client.query_registration(
                messages.RegistrationResource(uri=account_url, body=messages.Registration())
            )
            self._acme_client.net.account = existing
            return account_url
        except errors.Error as exc:
            raise AcmeError(f"Failed to register ACME account: {exc}") from exc
        except Exception as exc:
            raise AcmeError(f"Failed to register ACME account: {exc}") from exc

        account_url = regr.uri or ""
        logger.info("ACME account registered at %s", account_url)
        return account_url

    def new_order(self, domains: list[str]) -> messages.OrderResource:
        """Create a new ACME certificate order for the given domains.

        Internally generates a temporary CSR (with the domain list as SANs)
        so that the ACME library can extract identifiers.  The production
        private key and final CSR are supplied at :meth:`finalize_order` time.

        Parameters
        ----------
        domains:
            List of FQDNs to include in the order.

        Returns
        -------
        acme.messages.OrderResource
            The newly created order resource.

        Raises
        ------
        AcmeError
            On ACME protocol or network errors.
        """
        acme_cl = self._get_client()
        csr_pem = _build_temp_csr(domains)
        try:
            order: messages.OrderResource = _with_retry(acme_cl.new_order, csr_pem)
        except AcmeError:
            raise
        except Exception as exc:
            raise AcmeError(f"Failed to create ACME order: {exc}") from exc
        logger.debug("Created ACME order at %s for domains %s", order.uri, domains)
        return order

    def get_http01_challenge(self, order: messages.OrderResource, domain: str) -> tuple[str, str]:
        """Extract the HTTP-01 challenge token and key_authorization for *domain*.

        Parameters
        ----------
        order:
            An :class:`acme.messages.OrderResource` that contains an
            authorisation for *domain*.
        domain:
            The FQDN whose challenge to extract.

        Returns
        -------
        tuple[str, str]
            ``(token, key_authorization)`` where *key_authorization* is in the
            format ``<token>.<key_thumbprint>`` (RFC 8555 §8.3).

        Raises
        ------
        AcmeError
            If no HTTP-01 challenge is found for *domain*.
        """
        account_key = self._get_account_key()

        for authzr in order.authorizations:
            if authzr.body.identifier.value == domain:
                for challb in authzr.body.challenges:
                    if isinstance(challb.chall, challenges.HTTP01):
                        token = challb.chall.encode("token")
                        key_auth = challb.chall.key_authorization(account_key)
                        logger.debug("Got HTTP-01 challenge for %s: token=%s", domain, token)
                        return token, key_auth
        raise AcmeError(f"No HTTP-01 challenge found for domain '{domain}' in order {order.uri}")

    def answer_challenge(self, challb: messages.ChallengeBody) -> None:
        """Notify the ACME CA that the challenge response has been deployed.

        Parameters
        ----------
        challb:
            The :class:`acme.messages.ChallengeBody` representing the HTTP-01
            challenge to answer.

        Raises
        ------
        AcmeError
            On ACME protocol errors.
        """
        acme_cl = self._get_client()
        account_key = self._get_account_key()

        if not isinstance(challb.chall, challenges.HTTP01):
            raise AcmeError(f"Expected HTTP01 challenge, got {type(challb.chall).__name__}")

        response, _ = challb.chall.response_and_validation(account_key)
        try:
            _with_retry(acme_cl.answer_challenge, challb, response)
        except AcmeError:
            raise
        except Exception as exc:
            raise AcmeError(f"Failed to answer ACME challenge: {exc}") from exc
        logger.debug("Answered ACME challenge for %s", challb.uri)

    def poll_until_valid(
        self,
        order: messages.OrderResource,
        timeout_seconds: int = 60,
        interval_seconds: int = 5,
    ) -> None:
        """Poll the ACME CA until the order reaches ``valid`` status.

        Parameters
        ----------
        order:
            The order to poll.
        timeout_seconds:
            Maximum total time (in seconds) to wait before raising
            :class:`AcmeError`.  Defaults to 60.
        interval_seconds:
            Sleep interval between polls in seconds.  Defaults to 5.

        Raises
        ------
        AcmeError
            If the order does not reach ``valid`` status within
            *timeout_seconds*.
        """
        acme_cl = self._get_client()
        deadline = datetime.now(tz=UTC) + timedelta(seconds=timeout_seconds)

        while datetime.now(tz=UTC) < deadline:
            try:
                # Pass a short per-attempt deadline so poll_authorizations
                # makes one pass and returns, allowing us to control the
                # inter-poll sleep.
                short_dt = datetime.now(tz=UTC) + timedelta(seconds=interval_seconds + 1)
                short_deadline = short_dt.replace(tzinfo=None)
                updated = acme_cl.poll_authorizations(order, deadline=short_deadline)
                # If poll_authorizations returns without raising, all are valid
                order = updated
                logger.debug("ACME order authorizations validated successfully")
                return
            except errors.TimeoutError:
                # Not yet valid — sleep and retry
                logger.debug("ACME challenge not yet validated; retrying in %ds", interval_seconds)
                time.sleep(interval_seconds)
            except errors.ValidationError as exc:
                raise AcmeError(f"ACME validation failed: {exc}") from exc
            except errors.Error as exc:
                raise AcmeError(f"ACME polling error: {exc}") from exc

        raise AcmeError(f"ACME order did not reach 'valid' status within {timeout_seconds}s")

    def finalize_order(
        self, order: messages.OrderResource, csr_pem: bytes
    ) -> messages.OrderResource:
        """Finalize an ACME order by submitting the production CSR.

        Parameters
        ----------
        order:
            An order whose authorizations have been validated.
        csr_pem:
            The DER-encoded (or PEM-encoded) Certificate Signing Request with
            the target domains as Subject Alternative Names.

        Returns
        -------
        acme.messages.OrderResource
            The finalized order (with certificate available for download).

        Raises
        ------
        AcmeError
            On ACME protocol errors or finalization timeout.
        """
        acme_cl = self._get_client()
        deadline_dt = datetime.now() + timedelta(seconds=90)
        # Rebuild the order with the real CSR so the library sends the correct one
        updated_order = order.update(csr_pem=csr_pem)
        try:
            # Call finalize_order directly — TimeoutError is not a transient error
            # that should be retried, so we bypass _with_retry here.
            finalized: messages.OrderResource = acme_cl.finalize_order(updated_order, deadline_dt)
        except errors.TimeoutError as exc:
            raise AcmeError("ACME order finalization timed out") from exc
        except errors.Error as exc:
            raise AcmeError(f"Failed to finalize ACME order: {exc}") from exc
        except Exception as exc:
            raise AcmeError(f"Failed to finalize ACME order: {exc}") from exc
        logger.debug("ACME order finalized: %s", finalized.uri)
        return finalized

    def download_certificate(self, order: messages.OrderResource) -> str:
        """Download the certificate chain for a finalized order.

        Parameters
        ----------
        order:
            A finalized :class:`acme.messages.OrderResource` that contains
            the ``fullchain_pem`` field populated by :meth:`finalize_order`.

        Returns
        -------
        str
            PEM-encoded certificate chain starting with
            ``-----BEGIN CERTIFICATE-----``.

        Raises
        ------
        AcmeError
            If the certificate is not available in the order.
        """
        if not order.fullchain_pem:
            raise AcmeError(
                "Certificate is not available in the order — "
                "ensure finalize_order() completed successfully"
            )
        pem: str = order.fullchain_pem
        if not pem.strip().startswith("-----BEGIN CERTIFICATE-----"):
            raise AcmeError(
                "Downloaded certificate does not appear to be valid PEM: "
                f"starts with {pem[:50]!r}"
            )
        logger.debug("Downloaded certificate (%d bytes PEM)", len(pem))
        return pem
