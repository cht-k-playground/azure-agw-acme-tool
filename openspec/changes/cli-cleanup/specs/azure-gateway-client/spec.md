## ADDED Requirements

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
