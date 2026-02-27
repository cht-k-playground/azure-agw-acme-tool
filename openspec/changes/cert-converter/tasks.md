## 1. Module Scaffold

- [x] 1.1 Create `src/az_acme_tool/cert_converter.py` with `CertConverterError` exception class and module docstring

## 2. Core Functions

- [x] 2.1 Implement `pem_to_pfx(cert_pem: str, key_pem: str, password: str) -> bytes` using `cryptography` PKCS12 serialization
- [x] 2.2 Implement `cert_fingerprint(cert_pem: str) -> str` returning SHA-256 hex digest
- [x] 2.3 Implement `cert_expiry(cert_pem: str) -> datetime` returning UTC-aware datetime with `cryptography>=41` compatibility guard
- [x] 2.4 Implement `generate_csr(domains: list[str], key_pem: str) -> bytes` producing DER-encoded CSR with DNS SANs

## 3. Tests

- [x] 3.1 Create `tests/test_cert_converter.py` with shared self-signed certificate and RSA key fixtures (generated via `cryptography`, not stored on disk)
- [x] 3.2 Write tests for `pem_to_pfx`: valid inputs round-trip, malformed PEM raises `CertConverterError`
- [x] 3.3 Write tests for `cert_fingerprint`: determinism, length==64, malformed PEM raises `CertConverterError`
- [x] 3.4 Write tests for `cert_expiry`: future cert returns future datetime, past cert returns past datetime, result is UTC-aware
- [x] 3.5 Write tests for `generate_csr`: all domains appear as SANs, single domain, malformed key raises `CertConverterError`

## 4. Quality Gates

- [x] 4.1 Run `ruff check src/az_acme_tool/cert_converter.py tests/test_cert_converter.py` — zero violations
- [x] 4.2 Run `mypy --strict src/az_acme_tool/cert_converter.py` — zero errors
- [x] 4.3 Run `black --check --line-length 100 src/az_acme_tool/cert_converter.py tests/test_cert_converter.py` — no reformatting needed
- [x] 4.4 Run `pytest tests/test_cert_converter.py --cov=az_acme_tool.cert_converter --cov-report=term-missing` — coverage ≥80%
