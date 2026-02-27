## 1. Dependencies & Project Setup

- [x] 1.1 Add `acme>=2.7.0,<3.0` and `josepy>=1.14.0` to `[project.dependencies]` in `pyproject.toml`
- [x] 1.2 Install the new dependencies with `uv sync`

## 2. Core Module Implementation

- [x] 2.1 Create `src/az_acme_tool/acme_client.py` with the `AcmeError` custom exception class
- [x] 2.2 Implement `AcmeClient.__init__` accepting `directory_url: str` (ACME CA directory URL) and initializing `acme.client.ClientV2` with a `josepy.JWKRSA` account key
- [x] 2.3 Implement `register_account(email: str, account_key_path: Path) -> str` — generates RSA-2048 key (or loads existing), registers with CA, returns account URL; writes key file with `0o600` permissions
- [x] 2.4 Implement `new_order(domains: list[str]) -> acme.messages.OrderResource` — creates a new ACME order for the specified domains
- [x] 2.5 Implement `get_http01_challenge(order: acme.messages.OrderResource, domain: str) -> tuple[str, str]` — returns `(token, key_authorization)`
- [x] 2.6 Implement `answer_challenge(challenge: acme.messages.ChallengeBody) -> None` — notifies the CA that the challenge response is deployed
- [x] 2.7 Implement `poll_until_valid(order: acme.messages.OrderResource, timeout_seconds: int = 60, interval_seconds: int = 5) -> None` — polls CA until `valid` or raises `AcmeError` on timeout
- [x] 2.8 Implement `finalize_order(order: acme.messages.OrderResource, csr_pem: bytes) -> acme.messages.OrderResource` — submits CSR and finalizes the order
- [x] 2.9 Implement `download_certificate(order: acme.messages.OrderResource) -> str` — downloads and returns the PEM certificate chain
- [x] 2.10 Add exponential back-off retry (max 3 attempts, base 10 s) for transient `acme.errors.Error` in all network-facing methods

## 3. Type Annotations & Code Quality

- [x] 3.1 Ensure all public methods have complete type annotations satisfying `mypy --strict`
- [x] 3.2 Run `ruff check src/az_acme_tool/acme_client.py` and fix any linting issues
- [x] 3.3 Format with `black --line-length 100 src/az_acme_tool/acme_client.py`

## 4. Unit Tests

- [x] 4.1 Create `tests/test_acme_client.py` with fixtures using `pytest-mock` to stub `acme.client.ClientV2` and filesystem operations
- [x] 4.2 Test `register_account()`: new key generation path (no existing file) — verify key file is created with `0o600` and account URL is returned
- [x] 4.3 Test `register_account()`: key reuse path (file exists) — verify no new file is written and existing account URL is returned
- [x] 4.4 Test `new_order()`: verify CA `new_order` is called with correct domain identifiers
- [x] 4.5 Test `get_http01_challenge()`: verify returned `(token, key_authorization)` matches RFC 8555 format (`token.thumbprint`)
- [x] 4.6 Test `answer_challenge()`: verify CA `answer_challenge` is called once
- [x] 4.7 Test `poll_until_valid()`: mock CA returning `pending` for N iterations then `valid` — verify correct number of sleep calls
- [x] 4.8 Test `poll_until_valid()`: mock CA always returning `pending` past timeout — verify `AcmeError` is raised
- [x] 4.9 Test `finalize_order()`: verify CSR is passed to CA's finalize method
- [x] 4.10 Test `download_certificate()`: verify returned string starts with `-----BEGIN CERTIFICATE-----`
- [x] 4.11 Test retry logic: mock CA raising transient error on first call, succeeding on second — verify retry occurs without raising `AcmeError`
- [x] 4.12 Test retry exhaustion: mock CA raising transient error on all 3 attempts — verify `AcmeError` is raised

## 5. Coverage & Final Checks

- [x] 5.1 Run `pytest tests/test_acme_client.py --cov=src/az_acme_tool/acme_client --cov-report=term-missing` and confirm ≥80% line coverage
- [x] 5.2 Run `mypy --strict src/az_acme_tool/acme_client.py` and confirm zero errors
- [x] 5.3 Run full test suite `pytest tests/` and confirm all existing tests still pass
