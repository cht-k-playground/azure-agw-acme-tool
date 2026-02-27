## ADDED Requirements

### Requirement: JSON Lines file logging
The system SHALL write every log record to `~/.config/az-acme-tool/logs/az-acme-tool.log` in JSON Lines format. Each line SHALL be a valid JSON object containing exactly the fields `timestamp` (ISO 8601 UTC string), `level` (uppercase string), and `message` (string).

#### Scenario: Log file created on first run
- **WHEN** `setup_logging(verbose=False)` is called and the log directory does not exist
- **THEN** the directory `~/.config/az-acme-tool/logs/` is created and the log file is opened for appending

#### Scenario: INFO record written in JSON Lines format
- **WHEN** a logger emits an INFO message after `setup_logging()` has been called
- **THEN** the log file contains a new line with a JSON object where `level` is `"INFO"` and `message` matches the emitted string

#### Scenario: DEBUG record absent at INFO level
- **WHEN** `setup_logging(verbose=False)` is called and a logger emits a DEBUG message
- **THEN** no DEBUG record is written to the log file

#### Scenario: DEBUG record present at DEBUG level
- **WHEN** `setup_logging(verbose=True)` is called and a logger emits a DEBUG message
- **THEN** a JSON record with `level` equal to `"DEBUG"` is written to the log file

### Requirement: Rich console output to stderr
The system SHALL emit human-readable log messages to stderr using `rich.console.Console`. Messages at INFO level and above SHALL always be printed. The output SHALL NOT be in JSON format.

#### Scenario: INFO message printed to stderr in non-JSON format
- **WHEN** `setup_logging(verbose=False)` is called and a logger emits an INFO message
- **THEN** the message is printed to stderr via Rich and does not contain a leading `{` character

#### Scenario: DEBUG message absent from console at INFO level
- **WHEN** `setup_logging(verbose=False)` is called and a logger emits a DEBUG message
- **THEN** the DEBUG message is NOT printed to stderr

#### Scenario: DEBUG message present on console at DEBUG level
- **WHEN** `setup_logging(verbose=True)` is called and a logger emits a DEBUG message
- **THEN** the DEBUG message IS printed to stderr via Rich

### Requirement: setup_logging public API
The system SHALL expose `setup_logging(verbose: bool) -> None` as a public function in `az_acme_tool.logging`. The function SHALL be fully annotated and pass `mypy --strict` without error.

#### Scenario: Calling setup_logging with verbose=False configures INFO level
- **WHEN** `setup_logging(verbose=False)` is called
- **THEN** the root logger level is set to `logging.INFO`

#### Scenario: Calling setup_logging with verbose=True configures DEBUG level
- **WHEN** `setup_logging(verbose=True)` is called
- **THEN** the root logger level is set to `logging.DEBUG`
