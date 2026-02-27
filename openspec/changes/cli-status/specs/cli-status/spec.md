## ADDED Requirements

### Requirement: Certificate status classification
The system SHALL classify each certificate's status based on days remaining until expiry: `valid` (>30 days), `expiring_soon` (≤30 and >0 days), or `expired` (≤0 days).

#### Scenario: Valid classification
- **WHEN** a certificate has 31 days remaining
- **THEN** its status SHALL be `valid`

#### Scenario: Expiring soon classification
- **WHEN** a certificate has 29 days remaining
- **THEN** its status SHALL be `expiring_soon`

#### Scenario: Expired classification
- **WHEN** a certificate has -1 days remaining (past expiry)
- **THEN** its status SHALL be `expired`

### Requirement: Table output format
The system SHALL, when `--output table` (default), render certificate status as a Rich table with columns: `Gateway | Certificate | Expiry Date | Days Remaining | Status`.

#### Scenario: Table output rendered
- **WHEN** `az-acme-tool status` is invoked (default output)
- **THEN** stdout SHALL contain the column headers and one row per certificate

### Requirement: JSON output format
The system SHALL, when `--output json`, print a JSON array where each object contains `gateway`, `resource_group`, `name`, `expiry_date` (ISO 8601 string or null), `days_remaining` (int or null), and `status` fields.

#### Scenario: JSON parseable output
- **WHEN** `az-acme-tool status --output json` is invoked
- **THEN** stdout SHALL be valid JSON parseable by `json.loads()` and each object SHALL contain the required fields

### Requirement: YAML output format
The system SHALL, when `--output yaml`, print a YAML representation with `expiry_date` in ISO 8601 format.

#### Scenario: YAML output valid
- **WHEN** `az-acme-tool status --output yaml` is invoked
- **THEN** stdout SHALL be valid YAML parseable by `yaml.safe_load()`
