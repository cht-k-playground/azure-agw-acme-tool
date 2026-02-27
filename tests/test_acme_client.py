"""Unit tests for az_acme_tool.acme_client.

All external I/O (ACME CA, filesystem where relevant) is mocked with
pytest-mock to ensure no real CA calls are made.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest
from acme import challenges, errors, messages
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from josepy.jwk import JWKRSA

from az_acme_tool.acme_client import (
    _MAX_RETRIES,
    _RETRY_BASE_DELAY_S,
    AcmeClient,
    AcmeError,
    _load_or_generate_account_key,
    _with_retry,
)

# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


def _make_rsa_key() -> rsa.RSAPrivateKey:
    """Generate a small RSA key for test speed (1024-bit)."""
    return rsa.generate_private_key(public_exponent=65537, key_size=1024)


def _make_jwkrsa() -> JWKRSA:
    return JWKRSA(key=_make_rsa_key())


def _pem_bytes(key: rsa.RSAPrivateKey) -> bytes:
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _make_http01_challb(jwk: JWKRSA) -> messages.ChallengeBody:
    """Build a minimal ChallengeBody with an HTTP01 challenge."""
    token = os.urandom(32)
    chall = challenges.HTTP01(token=token)
    challb = messages.ChallengeBody(
        chall=chall,
        uri="https://acme.example.com/challenge/1",
        status=messages.Status("pending"),
    )
    return challb


def _make_authzr(domain: str, challb: messages.ChallengeBody) -> messages.AuthorizationResource:
    """Build a minimal AuthorizationResource for *domain*."""
    identifier = messages.Identifier(
        typ=messages.IDENTIFIER_FQDN,
        value=domain,
    )
    body = messages.Authorization(
        identifier=identifier,
        challenges=[challb],
        status=messages.Status("pending"),
    )
    return messages.AuthorizationResource(
        body=body,
        uri=f"https://acme.example.com/authz/{domain}",
    )


def _make_order(domain: str, challb: messages.ChallengeBody) -> messages.OrderResource:
    """Build a minimal OrderResource for *domain*."""
    authzr = _make_authzr(domain, challb)
    order_body = messages.Order(
        identifiers=[messages.Identifier(typ=messages.IDENTIFIER_FQDN, value=domain)],
        authorizations=[f"https://acme.example.com/authz/{domain}"],
        status=messages.Status("pending"),
        finalize="https://acme.example.com/finalize/1",
    )
    return messages.OrderResource(
        body=order_body,
        uri="https://acme.example.com/order/1",
        authorizations=[authzr],
        csr_pem=b"",
    )


# ---------------------------------------------------------------------------
# Tests: _load_or_generate_account_key
# ---------------------------------------------------------------------------


class TestLoadOrGenerateAccountKey:
    def test_generates_new_key_when_file_missing(self, tmp_path: Path) -> None:
        key_path = tmp_path / "account.key"
        assert not key_path.exists()

        jwk = _load_or_generate_account_key(key_path)

        assert key_path.exists()
        # Check file mode is 0o600
        mode = stat.S_IMODE(os.stat(key_path).st_mode)
        assert mode == 0o600
        assert isinstance(jwk, JWKRSA)
        # Verify the file contains valid PEM RSA key
        loaded_key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
        assert isinstance(loaded_key, rsa.RSAPrivateKey)

    def test_reuses_existing_key(self, tmp_path: Path) -> None:
        key_path = tmp_path / "account.key"
        original_key = _make_rsa_key()
        key_path.write_bytes(_pem_bytes(original_key))
        key_path.chmod(0o600)

        # Load the existing key — should NOT regenerate
        mtime_before = key_path.stat().st_mtime
        jwk = _load_or_generate_account_key(key_path)
        mtime_after = key_path.stat().st_mtime

        assert mtime_before == mtime_after  # file not rewritten
        assert isinstance(jwk, JWKRSA)

    def test_raises_acme_error_for_non_rsa_key(self, tmp_path: Path) -> None:
        """An EC key in the file should raise AcmeError."""
        from cryptography.hazmat.primitives.asymmetric import ec

        key_path = tmp_path / "account.key"
        ec_key = ec.generate_private_key(ec.SECP256R1())
        key_path.write_bytes(
            ec_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption(),
            )
        )

        with pytest.raises(AcmeError, match="not an RSA private key"):
            _load_or_generate_account_key(key_path)


# ---------------------------------------------------------------------------
# Tests: _with_retry
# ---------------------------------------------------------------------------


class TestWithRetry:
    def test_succeeds_first_attempt(self) -> None:
        fn = MagicMock(return_value="ok")
        result = _with_retry(fn, "arg1", kw="val")
        assert result == "ok"
        fn.assert_called_once_with("arg1", kw="val")

    def test_retries_on_acme_error_and_succeeds(self) -> None:
        acme_error = errors.Error("transient")
        fn = MagicMock(side_effect=[acme_error, "ok"])

        with patch("az_acme_tool.acme_client.time.sleep") as mock_sleep:
            result = _with_retry(fn)

        assert result == "ok"
        assert fn.call_count == 2
        mock_sleep.assert_called_once_with(_RETRY_BASE_DELAY_S)

    def test_raises_acme_error_after_max_retries(self) -> None:
        acme_error = errors.Error("persistent")
        fn = MagicMock(side_effect=acme_error)

        with patch("az_acme_tool.acme_client.time.sleep"):
            with pytest.raises(AcmeError, match=f"after {_MAX_RETRIES} attempts"):
                _with_retry(fn)

        assert fn.call_count == _MAX_RETRIES

    def test_retry_uses_exponential_backoff(self) -> None:
        acme_error = errors.Error("persistent")
        fn = MagicMock(side_effect=acme_error)

        with patch("az_acme_tool.acme_client.time.sleep") as mock_sleep:
            with pytest.raises(AcmeError):
                _with_retry(fn)

        # Expect sleep calls for attempt 1 and 2 (not for the final attempt)
        expected_calls = [
            call(_RETRY_BASE_DELAY_S * (2**0)),
            call(_RETRY_BASE_DELAY_S * (2**1)),
        ]
        mock_sleep.assert_has_calls(expected_calls)


# ---------------------------------------------------------------------------
# Tests: AcmeClient.register_account
# ---------------------------------------------------------------------------


class TestRegisterAccount:
    def _make_client_with_mocks(self, tmp_path: Path, mocker: Any) -> tuple[AcmeClient, MagicMock]:
        """Return an AcmeClient with mocked ClientV2 and directory."""
        acme_cl = AcmeClient("https://acme.example.com/directory")

        mock_acme_client = MagicMock()
        mock_regr = MagicMock()
        mock_regr.uri = "https://acme.example.com/account/123"
        mock_acme_client.new_account.return_value = mock_regr

        mocker.patch("az_acme_tool.acme_client.client.ClientNetwork")
        mocker.patch(
            "az_acme_tool.acme_client.client.ClientV2.get_directory",
            return_value=MagicMock(),
        )
        mocker.patch(
            "az_acme_tool.acme_client.client.ClientV2",
            return_value=mock_acme_client,
        )

        return acme_cl, mock_acme_client

    def test_new_registration_creates_key_file(self, tmp_path: Path, mocker: Any) -> None:
        key_path = tmp_path / "account.key"
        acme_cl, mock_acme_client = self._make_client_with_mocks(tmp_path, mocker)

        url = acme_cl.register_account("test@example.com", key_path)

        assert key_path.exists()
        mode = stat.S_IMODE(os.stat(key_path).st_mode)
        assert mode == 0o600
        assert url == "https://acme.example.com/account/123"
        mock_acme_client.new_account.assert_called_once()

    def test_existing_key_is_reused(self, tmp_path: Path, mocker: Any) -> None:
        key_path = tmp_path / "account.key"
        existing_key = _make_rsa_key()
        key_path.write_bytes(_pem_bytes(existing_key))
        key_path.chmod(0o600)
        mtime_before = key_path.stat().st_mtime

        acme_cl, mock_acme_client = self._make_client_with_mocks(tmp_path, mocker)
        url = acme_cl.register_account("test@example.com", key_path)

        mtime_after = key_path.stat().st_mtime
        assert mtime_before == mtime_after  # key file NOT rewritten
        assert url == "https://acme.example.com/account/123"

    def test_conflict_error_returns_existing_account_url(self, tmp_path: Path, mocker: Any) -> None:
        """When the CA returns 409 Conflict, reuse the existing account URL."""
        key_path = tmp_path / "account.key"
        acme_cl = AcmeClient("https://acme.example.com/directory")

        mock_acme_client = MagicMock()
        conflict_url = "https://acme.example.com/account/existing"
        # ConflictError stores the URL in .location attribute
        conflict_exc = errors.ConflictError(conflict_url)
        mock_acme_client.new_account.side_effect = conflict_exc
        mock_existing_regr = MagicMock()
        mock_acme_client.query_registration.return_value = mock_existing_regr

        mocker.patch("az_acme_tool.acme_client.client.ClientNetwork")
        mocker.patch(
            "az_acme_tool.acme_client.client.ClientV2.get_directory",
            return_value=MagicMock(),
        )
        mocker.patch(
            "az_acme_tool.acme_client.client.ClientV2",
            return_value=mock_acme_client,
        )

        url = acme_cl.register_account("test@example.com", key_path)

        assert url == conflict_url
        mock_acme_client.query_registration.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: AcmeClient.new_order
# ---------------------------------------------------------------------------


class TestNewOrder:
    def _initialized_client(self, mocker: Any) -> tuple[AcmeClient, MagicMock]:
        acme_cl = AcmeClient("https://acme.example.com/directory")
        acme_cl._account_key = _make_jwkrsa()
        mock_acme_client = MagicMock()
        acme_cl._acme_client = mock_acme_client
        return acme_cl, mock_acme_client

    def test_calls_ca_new_order_with_csr(self, mocker: Any) -> None:
        acme_cl, mock_acme_client = self._initialized_client(mocker)
        mock_order = MagicMock(spec=messages.OrderResource)
        mock_acme_client.new_order.return_value = mock_order

        result = acme_cl.new_order(["www.example.com"])

        mock_acme_client.new_order.assert_called_once()
        # The CSR passed to new_order should be PEM bytes containing the domain
        call_args = mock_acme_client.new_order.call_args
        csr_pem = call_args[0][0]
        assert isinstance(csr_pem, bytes)
        assert b"BEGIN CERTIFICATE REQUEST" in csr_pem
        assert result is mock_order

    def test_raises_without_initialization(self) -> None:
        acme_cl = AcmeClient("https://acme.example.com/directory")
        with pytest.raises(AcmeError, match="not initialised"):
            acme_cl.new_order(["www.example.com"])

    def test_wraps_ca_exception_as_acme_error(self, mocker: Any) -> None:
        acme_cl, mock_acme_client = self._initialized_client(mocker)
        mock_acme_client.new_order.side_effect = RuntimeError("network failure")

        with patch("az_acme_tool.acme_client.time.sleep"):
            with pytest.raises(AcmeError, match="Failed to create ACME order"):
                acme_cl.new_order(["www.example.com"])


# ---------------------------------------------------------------------------
# Tests: AcmeClient.get_http01_challenge
# ---------------------------------------------------------------------------


class TestGetHttp01Challenge:
    def test_returns_token_and_key_authorization(self) -> None:
        jwk = _make_jwkrsa()
        acme_cl = AcmeClient("https://acme.example.com/directory")
        acme_cl._account_key = jwk
        acme_cl._acme_client = MagicMock()

        challb = _make_http01_challb(jwk)
        order = _make_order("www.example.com", challb)

        token, key_auth = acme_cl.get_http01_challenge(order, "www.example.com")

        assert isinstance(token, str)
        assert isinstance(key_auth, str)
        # RFC 8555: key_auth = token.thumbprint
        parts = key_auth.split(".")
        assert len(parts) == 2
        assert parts[0] == token

    def test_raises_when_domain_not_found(self) -> None:
        jwk = _make_jwkrsa()
        acme_cl = AcmeClient("https://acme.example.com/directory")
        acme_cl._account_key = jwk
        acme_cl._acme_client = MagicMock()

        challb = _make_http01_challb(jwk)
        order = _make_order("www.example.com", challb)

        with pytest.raises(AcmeError, match="No HTTP-01 challenge found for domain 'other.com'"):
            acme_cl.get_http01_challenge(order, "other.com")

    def test_raises_without_account_key(self) -> None:
        acme_cl = AcmeClient("https://acme.example.com/directory")
        mock_order = MagicMock(spec=messages.OrderResource)

        with pytest.raises(AcmeError, match="no account key"):
            acme_cl.get_http01_challenge(mock_order, "www.example.com")


# ---------------------------------------------------------------------------
# Tests: AcmeClient.answer_challenge
# ---------------------------------------------------------------------------


class TestAnswerChallenge:
    def test_calls_ca_answer_challenge(self) -> None:
        jwk = _make_jwkrsa()
        acme_cl = AcmeClient("https://acme.example.com/directory")
        acme_cl._account_key = jwk
        mock_acme_client = MagicMock()
        acme_cl._acme_client = mock_acme_client

        challb = _make_http01_challb(jwk)
        acme_cl.answer_challenge(challb)

        mock_acme_client.answer_challenge.assert_called_once()

    def test_raises_for_non_http01_challenge(self) -> None:
        jwk = _make_jwkrsa()
        acme_cl = AcmeClient("https://acme.example.com/directory")
        acme_cl._account_key = jwk
        acme_cl._acme_client = MagicMock()

        # Build a non-HTTP01 challenge body
        mock_challb = MagicMock(spec=messages.ChallengeBody)
        mock_challb.chall = MagicMock()  # not an HTTP01 instance

        with pytest.raises(AcmeError, match="Expected HTTP01 challenge"):
            acme_cl.answer_challenge(mock_challb)


# ---------------------------------------------------------------------------
# Tests: AcmeClient.poll_until_valid
# ---------------------------------------------------------------------------


class TestPollUntilValid:
    def test_returns_when_valid_on_first_poll(self) -> None:
        acme_cl = AcmeClient("https://acme.example.com/directory")
        acme_cl._account_key = _make_jwkrsa()
        mock_acme_client = MagicMock()
        acme_cl._acme_client = mock_acme_client

        mock_order = MagicMock(spec=messages.OrderResource)
        updated_order = MagicMock(spec=messages.OrderResource)
        mock_acme_client.poll_authorizations.return_value = updated_order

        # Should not raise
        acme_cl.poll_until_valid(mock_order, timeout_seconds=60, interval_seconds=5)

        mock_acme_client.poll_authorizations.assert_called_once()

    def test_raises_on_timeout(self) -> None:
        acme_cl = AcmeClient("https://acme.example.com/directory")
        acme_cl._account_key = _make_jwkrsa()
        mock_acme_client = MagicMock()
        acme_cl._acme_client = mock_acme_client

        # poll_authorizations raises TimeoutError (pending) each time
        mock_acme_client.poll_authorizations.side_effect = errors.TimeoutError

        mock_order = MagicMock(spec=messages.OrderResource)

        # Use a very short timeout so the loop exits quickly
        # We patch sleep to avoid real delays
        with patch("az_acme_tool.acme_client.time.sleep"):
            with pytest.raises(AcmeError, match="did not reach 'valid' status"):
                acme_cl.poll_until_valid(mock_order, timeout_seconds=0, interval_seconds=1)

    def test_raises_on_validation_error(self) -> None:
        acme_cl = AcmeClient("https://acme.example.com/directory")
        acme_cl._account_key = _make_jwkrsa()
        mock_acme_client = MagicMock()
        acme_cl._acme_client = mock_acme_client

        mock_acme_client.poll_authorizations.side_effect = errors.ValidationError([])

        mock_order = MagicMock(spec=messages.OrderResource)

        with pytest.raises(AcmeError, match="validation failed"):
            acme_cl.poll_until_valid(mock_order, timeout_seconds=30, interval_seconds=1)

    def test_sleeps_between_polls(self) -> None:
        """Verify that time.sleep is called with interval_seconds when CA is pending.

        When poll_authorizations raises TimeoutError (challenge not yet validated),
        the implementation sleeps for interval_seconds before retrying.
        We use a very short overall timeout (0s) to ensure the loop runs exactly
        once and then exits with AcmeError.
        """
        acme_cl = AcmeClient("https://acme.example.com/directory")
        acme_cl._account_key = _make_jwkrsa()
        mock_acme_client = MagicMock()
        acme_cl._acme_client = mock_acme_client

        # Always raise TimeoutError (challenge not yet valid)
        mock_acme_client.poll_authorizations.side_effect = errors.TimeoutError
        mock_order = MagicMock(spec=messages.OrderResource)

        sleep_calls: list[float] = []

        # Use timeout_seconds=0 so the while loop condition fails immediately
        # after the first sleep — but we need to allow one iteration.
        # Strategy: use a large enough timeout that the loop runs at least once,
        # but patch sleep to record calls.
        def _record_sleep(s: float) -> None:
            sleep_calls.append(s)

        with patch("az_acme_tool.acme_client.time.sleep", side_effect=_record_sleep):
            with pytest.raises(AcmeError, match="did not reach 'valid' status"):
                # Use a short real timeout; poll_authorizations always raises TimeoutError
                # so sleep(7) is called each iteration until real time runs out.
                # With timeout_seconds=1 the loop runs at least once before expiring.
                acme_cl.poll_until_valid(mock_order, timeout_seconds=1, interval_seconds=7)

        # At least one sleep(7) call must have occurred
        assert 7 in sleep_calls


# ---------------------------------------------------------------------------
# Tests: AcmeClient.finalize_order
# ---------------------------------------------------------------------------


class TestFinalizeOrder:
    def test_passes_csr_to_ca(self) -> None:
        acme_cl = AcmeClient("https://acme.example.com/directory")
        acme_cl._account_key = _make_jwkrsa()
        mock_acme_client = MagicMock()
        acme_cl._acme_client = mock_acme_client

        finalized_order = MagicMock(spec=messages.OrderResource)
        mock_acme_client.finalize_order.return_value = finalized_order

        mock_order = MagicMock(spec=messages.OrderResource)
        updated_order = MagicMock(spec=messages.OrderResource)
        mock_order.update.return_value = updated_order

        csr_pem = b"---BEGIN CERTIFICATE REQUEST---\nfake\n---END CERTIFICATE REQUEST---"
        result = acme_cl.finalize_order(mock_order, csr_pem)

        # Verify update() was called with our CSR
        mock_order.update.assert_called_once_with(csr_pem=csr_pem)
        # Verify finalize_order was called with the updated order
        mock_acme_client.finalize_order.assert_called_once()
        call_args = mock_acme_client.finalize_order.call_args[0]
        assert call_args[0] is updated_order
        assert result is finalized_order

    def test_raises_on_timeout(self) -> None:
        acme_cl = AcmeClient("https://acme.example.com/directory")
        acme_cl._account_key = _make_jwkrsa()
        mock_acme_client = MagicMock()
        acme_cl._acme_client = mock_acme_client

        mock_acme_client.finalize_order.side_effect = errors.TimeoutError

        mock_order = MagicMock(spec=messages.OrderResource)
        mock_order.update.return_value = mock_order

        with pytest.raises(AcmeError, match="finalization timed out"):
            acme_cl.finalize_order(mock_order, b"csr")


# ---------------------------------------------------------------------------
# Tests: AcmeClient.download_certificate
# ---------------------------------------------------------------------------


class TestDownloadCertificate:
    def test_returns_pem_starting_with_begin_certificate(self) -> None:
        acme_cl = AcmeClient("https://acme.example.com/directory")
        acme_cl._account_key = _make_jwkrsa()
        acme_cl._acme_client = MagicMock()

        pem = "-----BEGIN CERTIFICATE-----\nMIIFoo\n-----END CERTIFICATE-----\n"
        mock_order = MagicMock(spec=messages.OrderResource)
        mock_order.fullchain_pem = pem

        result = acme_cl.download_certificate(mock_order)

        assert result.startswith("-----BEGIN CERTIFICATE-----")
        assert result == pem

    def test_raises_when_fullchain_pem_missing(self) -> None:
        acme_cl = AcmeClient("https://acme.example.com/directory")
        acme_cl._account_key = _make_jwkrsa()
        acme_cl._acme_client = MagicMock()

        mock_order = MagicMock(spec=messages.OrderResource)
        mock_order.fullchain_pem = None

        with pytest.raises(AcmeError, match="Certificate is not available"):
            acme_cl.download_certificate(mock_order)

    def test_raises_when_pem_invalid(self) -> None:
        acme_cl = AcmeClient("https://acme.example.com/directory")
        acme_cl._account_key = _make_jwkrsa()
        acme_cl._acme_client = MagicMock()

        mock_order = MagicMock(spec=messages.OrderResource)
        mock_order.fullchain_pem = "THIS IS NOT PEM"

        with pytest.raises(AcmeError, match="does not appear to be valid PEM"):
            acme_cl.download_certificate(mock_order)
