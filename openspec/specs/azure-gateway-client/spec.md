# azure-gateway-client Specification

## Purpose
TBD - created by archiving change azure-gateway-client. Update Purpose after archive.
## Requirements
### Requirement: AzureGatewayClient class
The system SHALL provide an `AzureGatewayClient` class in `src/az_acme_tool/azure_gateway.py` that is instantiated with `subscription_id: str`, `resource_group: str`, `gateway_name: str`, and `credential: TokenCredential`. It SHALL use `azure-mgmt-network` `NetworkManagementClient` for all Azure API calls.

#### Scenario: Client instantiation succeeds with valid parameters
- **WHEN** `AzureGatewayClient` is constructed with a valid subscription_id, resource_group, gateway_name, and a `TokenCredential`
- **THEN** the client is created without error and holds references to the provided parameters

#### Scenario: Client uses injected credential
- **WHEN** `AzureGatewayClient` is constructed with a mock `TokenCredential`
- **THEN** the underlying `NetworkManagementClient` is initialised with that credential and the given subscription_id

### Requirement: AzureGatewayError exception class
The system SHALL define an `AzureGatewayError` exception class in `src/az_acme_tool/azure_gateway.py` that is raised for all Azure SDK and operational failures, carrying a human-readable message.

#### Scenario: AzureGatewayError carries descriptive message
- **WHEN** an Azure SDK `HttpResponseError` is caught during any client operation
- **THEN** `AzureGatewayError` is raised with a message that includes the original error detail

### Requirement: list_certificates method
The system SHALL provide a `list_certificates(self) -> list[dict[str, Any]]` method on `AzureGatewayClient` that retrieves all SSL certificates attached to the configured Application Gateway and returns a list of dicts, each containing at minimum `name: str` and `expiry: datetime | None`.

#### Scenario: Returns all certificates when gateway has SSL certificates
- **WHEN** the Application Gateway has one or more SSL certificates attached
- **THEN** `list_certificates()` returns a list with one entry per certificate, each containing `name` and `expiry`

#### Scenario: Returns empty list when no certificates exist
- **WHEN** the Application Gateway has no SSL certificates attached
- **THEN** `list_certificates()` returns an empty list

#### Scenario: Raises AzureGatewayError on Azure API failure
- **WHEN** the Azure API call raises `HttpResponseError`
- **THEN** `list_certificates()` raises `AzureGatewayError` with the error detail

### Requirement: get_certificate_expiry method
The system SHALL provide a `get_certificate_expiry(self, cert_name: str) -> datetime` method on `AzureGatewayClient` that returns the expiry `datetime` of the named SSL certificate on the configured gateway.

#### Scenario: Returns expiry datetime for a known certificate
- **WHEN** a certificate with the given `cert_name` exists on the gateway and has a non-None `expiration_date`
- **THEN** `get_certificate_expiry()` returns a `datetime` object representing the certificate's expiry

#### Scenario: Raises AzureGatewayError when certificate not found
- **WHEN** no certificate with the given `cert_name` exists on the gateway
- **THEN** `get_certificate_expiry()` raises `AzureGatewayError` with a message identifying the missing certificate name

#### Scenario: Raises AzureGatewayError when expiry date is unavailable
- **WHEN** the certificate exists but its `expiration_date` field is None (e.g., Key Vault reference)
- **THEN** `get_certificate_expiry()` raises `AzureGatewayError` with a message explaining that expiry is unavailable

#### Scenario: Raises AzureGatewayError on Azure API failure
- **WHEN** the underlying Azure API call raises `HttpResponseError`
- **THEN** `get_certificate_expiry()` raises `AzureGatewayError` with the error detail

### Requirement: update_listener_certificate method
The system SHALL provide an `update_listener_certificate(self, listener_name: str, cert_name: str) -> None` method on `AzureGatewayClient` that updates the named HTTP listener on the configured Application Gateway to reference the named SSL certificate, then waits for the update to complete.

#### Scenario: Successfully updates listener certificate
- **WHEN** a listener with `listener_name` and a certificate with `cert_name` both exist on the gateway
- **THEN** `update_listener_certificate()` updates the listener's `ssl_certificate` reference to the named certificate, calls `begin_create_or_update`, and awaits the poller result without error

#### Scenario: Raises AzureGatewayError when listener not found
- **WHEN** no listener with `listener_name` exists on the gateway
- **THEN** `update_listener_certificate()` raises `AzureGatewayError` with a message identifying the missing listener name

#### Scenario: Raises AzureGatewayError when certificate not found
- **WHEN** no certificate with `cert_name` exists on the gateway's ssl_certificates list
- **THEN** `update_listener_certificate()` raises `AzureGatewayError` with a message identifying the missing certificate name

#### Scenario: Raises AzureGatewayError on Azure API failure during update
- **WHEN** the `begin_create_or_update` call or the poller raises `HttpResponseError`
- **THEN** `update_listener_certificate()` raises `AzureGatewayError` with the error detail

### Requirement: azure-mgmt-network and azure-identity dependencies
The system SHALL declare `azure-mgmt-network>=28.0.0` and `azure-identity>=1.16.0` as runtime dependencies in `pyproject.toml` under `[project.dependencies]`.

#### Scenario: Dependencies are present in pyproject.toml
- **WHEN** `pyproject.toml` is inspected
- **THEN** both `azure-mgmt-network>=28.0.0` and `azure-identity>=1.16.0` appear in `[project.dependencies]`

### Requirement: list_acme_challenge_rules method
The system SHALL provide a `list_acme_challenge_rules(self) -> list[str]` method on `AzureGatewayClient` that scans all URL path maps on the configured Application Gateway and returns the names of all path rules whose names begin with the prefix `acme-challenge-`.

#### Scenario: Returns matching rule names when orphaned rules exist
- **WHEN** the Application Gateway has URL path maps containing path rules with names starting with `acme-challenge-`
- **THEN** `list_acme_challenge_rules()` returns a list of those rule names as strings

#### Scenario: Returns empty list when no orphaned rules exist
- **WHEN** the Application Gateway has no path rules with names starting with `acme-challenge-`
- **THEN** `list_acme_challenge_rules()` returns an empty list

#### Scenario: Raises AzureGatewayError on Azure API failure
- **WHEN** the Azure API call raises `HttpResponseError`
- **THEN** `list_acme_challenge_rules()` raises `AzureGatewayError` with the error detail

### Requirement: delete_routing_rule method
The system SHALL provide a `delete_routing_rule(self, rule_name: str) -> None` method on `AzureGatewayClient` that removes the named path rule from all URL path maps on the configured Application Gateway and persists the change via `begin_create_or_update`.

#### Scenario: Successfully deletes an existing path rule
- **WHEN** a path rule with `rule_name` exists in a URL path map on the gateway
- **THEN** `delete_routing_rule()` removes the rule from the URL path map, calls `begin_create_or_update`, and awaits the poller result without error

#### Scenario: Raises AzureGatewayError when rule not found
- **WHEN** no path rule with `rule_name` exists in any URL path map on the gateway
- **THEN** `delete_routing_rule()` raises `AzureGatewayError` with a message identifying the missing rule name

#### Scenario: Raises AzureGatewayError on Azure API failure during delete
- **WHEN** the `begin_create_or_update` call or the poller raises `HttpResponseError`
- **THEN** `delete_routing_rule()` raises `AzureGatewayError` with the error detail

