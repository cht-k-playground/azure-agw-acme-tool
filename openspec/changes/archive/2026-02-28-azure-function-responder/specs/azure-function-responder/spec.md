## ADDED Requirements

### Requirement: HTTP trigger serves ACME challenge response
The system SHALL provide an Azure Functions HTTP trigger at route `/.well-known/acme-challenge/{token}` (GET method) that reads the `ACME_CHALLENGE_RESPONSE` environment variable and returns its value as the HTTP response body with Content-Type `text/plain` and HTTP status 200.

#### Scenario: Valid challenge response returned
- **WHEN** an HTTP GET request is made to `/.well-known/acme-challenge/{token}` and `ACME_CHALLENGE_RESPONSE` is set to a non-empty string
- **THEN** the function returns HTTP 200 with the value of `ACME_CHALLENGE_RESPONSE` as the body and Content-Type `text/plain`

#### Scenario: Returns 404 when ACME_CHALLENGE_RESPONSE is not set
- **WHEN** an HTTP GET request is made to `/.well-known/acme-challenge/{token}` and `ACME_CHALLENGE_RESPONSE` is not set or is an empty string
- **THEN** the function returns HTTP 404

### Requirement: Azure Function deployment files
The system SHALL provide `azure-function/host.json` and `azure-function/requirements.txt` files required for Azure Functions deployment.

#### Scenario: host.json is valid Azure Functions v2 configuration
- **WHEN** `azure-function/host.json` is inspected
- **THEN** it contains a valid Azure Functions host configuration with `extensionBundle` for HTTP triggers

#### Scenario: requirements.txt contains azure-functions dependency
- **WHEN** `azure-function/requirements.txt` is inspected
- **THEN** it contains `azure-functions` pinned to a specific version compatible with Python 3.11

### Requirement: Function passes ruff and mypy checks
The system SHALL ensure `azure-function/function_app.py` passes `ruff check` and `mypy --strict` without errors.

#### Scenario: ruff lint passes
- **WHEN** `ruff check azure-function/function_app.py` is run
- **THEN** no lint errors are reported

#### Scenario: mypy strict passes
- **WHEN** `mypy --strict azure-function/function_app.py` is run
- **THEN** no type errors are reported
