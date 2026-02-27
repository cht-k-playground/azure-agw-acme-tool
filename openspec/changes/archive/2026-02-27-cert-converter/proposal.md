## Why

The certificate issuance and renewal pipeline requires a cryptographic utility layer to convert PEM-encoded certificates and keys into PFX format for Azure Application Gateway upload, compute certificate fingerprints for identity/deduplication, extract expiry dates for renewal scheduling, and generate CSRs for ACME order finalization. Without this layer, the CLI commands (`issue`, `renew`, `status`) and the end-to-end ACME flow cannot be implemented.

## What Changes

- New module `src/az_acme_tool/cert_converter.py` providing pure-Python certificate utility functions:
  - `pem_to_pfx(cert_pem, key_pem, password)` — converts PEM chain + private key to PFX bytes
  - `cert_fingerprint(cert_pem)` — returns SHA-256 hex digest for a PEM certificate
  - `cert_expiry(cert_pem)` — returns UTC `datetime` of certificate expiration
  - `generate_csr(domains, key_pem)` — produces a DER-encoded CSR with SANs for the given domains
- New custom exception `CertConverterError` for structured error handling
- New test file `tests/test_cert_converter.py` covering all four functions with self-signed test fixtures
- All private key material stays in memory; no keys are written to disk within these functions

## Capabilities

### New Capabilities

- `cert-converter`: PEM↔PFX conversion, SHA-256 fingerprinting, expiry extraction, and CSR generation for the certificate pipeline

### Modified Capabilities

_(none — no existing spec-level behavior changes)_

## Impact

- **New file**: `src/az_acme_tool/cert_converter.py`
- **New file**: `tests/test_cert_converter.py`
- **Dependencies**: `cryptography>=41.0` already declared in `pyproject.toml`; no new runtime dependencies required
- **Downstream**: `cli-issue`, `cli-renew`, `cli-status`, `issue-flow-core` all depend on this module being present
