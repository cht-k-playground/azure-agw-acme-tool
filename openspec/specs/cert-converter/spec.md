## ADDED Requirements

### Requirement: PEM to PFX conversion
The system SHALL convert a PEM-encoded certificate chain and a PEM-encoded private key into PKCS#12 (PFX) bytes using the supplied password. The private key SHALL NOT be written to disk or appear in any log output.

#### Scenario: Valid PEM inputs produce decodable PFX
- **WHEN** `pem_to_pfx(cert_pem, key_pem, password)` is called with a valid self-signed certificate PEM and matching private key PEM
- **THEN** the returned `bytes` object SHALL be decodable by `cryptography.hazmat.primitives.serialization.pkcs12.load_key_and_certificates` using the same `password`

#### Scenario: Malformed PEM raises CertConverterError
- **WHEN** `pem_to_pfx` is called with an invalid `cert_pem` string that is not valid PEM
- **THEN** a `CertConverterError` SHALL be raised with a descriptive message

### Requirement: Certificate SHA-256 fingerprint
The system SHALL compute the SHA-256 fingerprint of a PEM-encoded certificate and return it as a lowercase hexadecimal string.

#### Scenario: Deterministic fingerprint
- **WHEN** `cert_fingerprint(cert_pem)` is called twice with the same PEM string
- **THEN** both calls SHALL return identical strings of length 64 (256 bits as hex)

#### Scenario: Malformed PEM raises CertConverterError
- **WHEN** `cert_fingerprint` is called with an invalid PEM string
- **THEN** a `CertConverterError` SHALL be raised

### Requirement: Certificate expiry extraction
The system SHALL parse a PEM-encoded certificate and return its `notAfter` field as a timezone-aware UTC `datetime` object.

#### Scenario: Future expiry returns future datetime
- **WHEN** `cert_expiry(cert_pem)` is called with a certificate whose `notAfter` is in the future
- **THEN** the returned `datetime` SHALL be greater than `datetime.now(tz=timezone.utc)`

#### Scenario: Past expiry returns past datetime
- **WHEN** `cert_expiry(cert_pem)` is called with a certificate whose `notAfter` is in the past
- **THEN** the returned `datetime` SHALL be less than `datetime.now(tz=timezone.utc)`

#### Scenario: Returned datetime is UTC-aware
- **WHEN** `cert_expiry(cert_pem)` is called with any valid certificate PEM
- **THEN** the returned `datetime.tzinfo` SHALL NOT be `None`

### Requirement: CSR generation with Subject Alternative Names
The system SHALL generate a DER-encoded Certificate Signing Request (CSR) that contains all supplied domains as Subject Alternative Names (SANs). The private key used to sign the CSR SHALL NOT be written to disk.

#### Scenario: All domains appear as SANs
- **WHEN** `generate_csr(["www.example.com", "api.example.com"], key_pem)` is called with a valid RSA private key PEM
- **THEN** the returned `bytes` SHALL be a valid DER-encoded CSR where both `www.example.com` and `api.example.com` appear as DNS SANs

#### Scenario: Single domain CSR
- **WHEN** `generate_csr(["example.com"], key_pem)` is called
- **THEN** the returned DER bytes SHALL decode to a CSR with exactly one SAN: `DNS:example.com`

#### Scenario: Malformed key PEM raises CertConverterError
- **WHEN** `generate_csr(["example.com"], "not-a-key")` is called
- **THEN** a `CertConverterError` SHALL be raised

### Requirement: Structured exception for all cryptographic errors
The system SHALL define a `CertConverterError` exception class that wraps all cryptographic library exceptions raised within `cert_converter.py`.

#### Scenario: CertConverterError is raised on internal failure
- **WHEN** any internal cryptographic operation raises an unexpected exception
- **THEN** the caller SHALL receive a `CertConverterError` rather than a raw `ValueError` or `cryptography` library exception
