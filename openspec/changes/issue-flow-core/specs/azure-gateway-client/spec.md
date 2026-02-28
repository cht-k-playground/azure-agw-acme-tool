## ADDED Requirements

### Requirement: upload_ssl_certificate method
The system SHALL provide an `upload_ssl_certificate(self, cert_name: str, pfx_data: bytes, password: str) -> None` method on `AzureGatewayClient` that uploads a PFX-encoded SSL certificate to the configured Application Gateway using the `azure-mgmt-network` SDK.

#### Scenario: Successfully uploads SSL certificate
- **WHEN** `upload_ssl_certificate()` is called with a valid cert_name, pfx_data, and password
- **THEN** the method adds or replaces the named SSL certificate on the gateway and calls `begin_create_or_update` to persist the change

#### Scenario: Password not logged
- **WHEN** `upload_ssl_certificate()` is called
- **THEN** the password value does NOT appear in any log output at any log level

#### Scenario: Raises AzureGatewayError on Azure API failure
- **WHEN** the Azure API call raises `HttpResponseError`
- **THEN** `upload_ssl_certificate()` raises `AzureGatewayError` with the error detail

### Requirement: add_routing_rule method
The system SHALL provide an `add_routing_rule(self, rule_name: str, domain: str, backend_fqdn: str) -> None` method on `AzureGatewayClient` that creates a temporary path-based routing rule on the configured Application Gateway for the ACME HTTP-01 challenge path `/.well-known/acme-challenge/*`.

#### Scenario: Successfully creates routing rule
- **WHEN** `add_routing_rule()` is called with a valid rule_name, domain, and backend_fqdn
- **THEN** the method creates a URL path map with a path rule for `/.well-known/acme-challenge/*` pointing to a new backend pool targeting backend_fqdn, and calls `begin_create_or_update` to persist the change

#### Scenario: Raises AzureGatewayError on Azure API failure
- **WHEN** the Azure API call raises `HttpResponseError`
- **THEN** `add_routing_rule()` raises `AzureGatewayError` with the error detail

### Requirement: get_listeners_by_cert_name method
The system SHALL provide a `get_listeners_by_cert_name(self, cert_name: str) -> list[str]` method on `AzureGatewayClient` that returns the names of all HTTP listeners on the configured Application Gateway that reference the named SSL certificate.

#### Scenario: Returns listener names when listeners use the certificate
- **WHEN** one or more HTTP listeners reference the named SSL certificate
- **THEN** `get_listeners_by_cert_name()` returns a list of those listener names

#### Scenario: Returns empty list when no listeners use the certificate
- **WHEN** no HTTP listeners reference the named SSL certificate
- **THEN** `get_listeners_by_cert_name()` returns an empty list

#### Scenario: Raises AzureGatewayError on Azure API failure
- **WHEN** the Azure API call raises `HttpResponseError`
- **THEN** `get_listeners_by_cert_name()` raises `AzureGatewayError` with the error detail
