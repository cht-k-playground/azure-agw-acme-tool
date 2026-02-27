# Spec: ACME Client

## Purpose

Defines the requirements for the ACME protocol client module (`acme_client.py`), which handles all interactions with an ACME CA (e.g., Let's Encrypt). This includes account registration, certificate order lifecycle management, HTTP-01 challenge handling, and certificate download.

---

## Requirements

### Requirement: Account registration with key reuse
The system SHALL generate a new RSA-2048 ACME account private key and register it with the ACME CA when `register_account()` is called. If `account_key_path` already exists, the system SHALL load the existing key and return the previously registered account URL without creating a new account.

#### Scenario: First-time registration
- **WHEN** `register_account(email, account_key_path)` is called and `account_key_path` does not exist
- **THEN** a new RSA-2048 PEM key is written to `account_key_path` with mode `0o600`, the account is registered with the ACME CA using the provided email, and the account URL is returned

#### Scenario: Key reuse on subsequent call
- **WHEN** `register_account(email, account_key_path)` is called and `account_key_path` already exists
- **THEN** the existing key is loaded, no new key file is written, and the account URL is returned without registering a new account

### Requirement: New ACME order creation
The system SHALL create a new ACME certificate order for one or more domains by calling the CA and returning an `Order` object.

#### Scenario: Create order for single domain
- **WHEN** `new_order(domains=["www.example.com"])` is called with a valid ACME account
- **THEN** the CA returns an order object containing HTTP-01 challenges for the domain

#### Scenario: Create order for multiple domains
- **WHEN** `new_order(domains=["a.example.com", "b.example.com"])` is called
- **THEN** the CA returns an order object containing challenges for all specified domains

### Requirement: HTTP-01 challenge extraction
The system SHALL extract the challenge token and key_authorization string for a specified domain from an existing order.

#### Scenario: Successful challenge extraction
- **WHEN** `get_http01_challenge(order, domain)` is called with a valid order containing an HTTP-01 challenge for the domain
- **THEN** a tuple `(token, key_authorization)` is returned where `key_authorization` matches the format `<token>.<key_thumbprint>` per RFC 8555

#### Scenario: key_authorization format validation
- **WHEN** `get_http01_challenge(order, domain)` returns `(token, key_authorization)`
- **THEN** `key_authorization` contains exactly one `.` separator and the part after `.` is a valid Base64url-encoded JWK thumbprint

### Requirement: Challenge answer notification
The system SHALL notify the ACME CA that the HTTP-01 challenge response is ready for verification.

#### Scenario: Notify CA of challenge readiness
- **WHEN** `answer_challenge(challenge)` is called after the challenge response has been deployed
- **THEN** the ACME CA is notified via the appropriate ACME protocol call

### Requirement: Order validation polling
The system SHALL poll the ACME CA until the order reaches `valid` status or the timeout is exceeded.

#### Scenario: Successful validation within timeout
- **WHEN** `poll_until_valid(order, timeout_seconds=60, interval_seconds=5)` is called and the CA returns `valid` status before timeout
- **THEN** the method returns without raising an exception

#### Scenario: Timeout exceeded
- **WHEN** `poll_until_valid(order, timeout_seconds=60, interval_seconds=5)` is called and the CA has not returned `valid` status after 60 seconds
- **THEN** `AcmeError` is raised with a message indicating the timeout was exceeded

#### Scenario: Polling interval
- **WHEN** the CA returns `pending` status on the first poll
- **THEN** the system waits `interval_seconds` (default 5) before polling again

### Requirement: Order finalization with CSR
The system SHALL finalize an ACME order by submitting a DER-encoded CSR to the CA.

#### Scenario: Successful finalization
- **WHEN** `finalize_order(order, csr_pem)` is called with a valid order in `valid` status and a DER-format CSR
- **THEN** the CA processes the CSR and returns the finalized order ready for certificate download

### Requirement: Certificate download
The system SHALL download the signed certificate chain from the CA after order finalization.

#### Scenario: Download PEM certificate chain
- **WHEN** `download_certificate(order)` is called on a finalized order
- **THEN** a PEM string is returned that begins with `-----BEGIN CERTIFICATE-----`

### Requirement: Structured error handling
The system SHALL raise `AcmeError` for all ACME protocol and operational failures, with a message that describes the failure.

#### Scenario: CA returns error response
- **WHEN** the ACME CA returns an error (e.g., rate limit exceeded, validation failed)
- **THEN** `AcmeError` is raised with a descriptive message

#### Scenario: Transient error retry
- **WHEN** the ACME CA returns a transient error (e.g., 429 or 503) on the first attempt
- **THEN** the operation is retried with exponential back-off, up to 3 attempts total before raising `AcmeError`
