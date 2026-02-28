## ADDED Requirements

### Requirement: 14-step ACME HTTP-01 certificate issuance pipeline
The system SHALL implement a complete 14-step ACME HTTP-01 certificate issuance pipeline for a single domain on a single Azure Application Gateway, executed by `_issue_single_domain()` in `src/az_acme_tool/issue_command.py`.

#### Scenario: Happy path completes all 14 steps in order
- **WHEN** `_issue_single_domain()` is called with a valid `DomainTarget` and `AppConfig`
- **THEN** the following steps execute in order: (1) resolve config, (2) new_order, (3) get_http01_challenge, (4) update_function_app_settings, (5) add_routing_rule, (6) answer_challenge, (7) poll_until_valid, (8) finalize_order, (9) download_certificate, (10) pem_to_pfx, (11) upload_ssl_certificate, (12) get_listeners_by_cert_name, (13) update_listener_certificate for each listener, (14) delete_routing_rule

#### Scenario: Temporary routing rule deleted even on failure
- **WHEN** any step between 6 and 13 raises an exception
- **THEN** `delete_routing_rule()` is still called (via `finally` block) before the exception propagates

#### Scenario: PFX password not logged or written to disk
- **WHEN** `_issue_single_domain()` executes the pipeline
- **THEN** the randomly generated PFX password does not appear in any log output or on disk

#### Scenario: SSL certificate named with domain_sanitized-cert convention
- **WHEN** `upload_ssl_certificate()` is called during the pipeline
- **THEN** the certificate name is `{domain_sanitized}-cert` where dots in the domain are replaced with hyphens (e.g., `www.example.com` → `www-example-com-cert`)

#### Scenario: Temporary routing rule named with acme-challenge- prefix
- **WHEN** `add_routing_rule()` is called during the pipeline
- **THEN** the rule name follows the pattern `acme-challenge-{domain_sanitized}-{unix_timestamp}`
