## ADDED Requirements

### Requirement: update_function_app_settings method
The system SHALL provide an `update_function_app_settings(self, function_app_name: str, settings: dict[str, str]) -> None` method on `AzureGatewayClient` that updates the named Azure Function App's Application Settings using the `azure-mgmt-web` `WebSiteManagementClient`, merging the provided key-value pairs into the existing settings.

#### Scenario: Successfully updates function app settings
- **WHEN** `update_function_app_settings()` is called with a valid `function_app_name` and a non-empty `settings` dict
- **THEN** the method calls `WebSiteManagementClient.web_apps.update_application_settings()` with the provided settings and returns without error

#### Scenario: Setting values are not logged
- **WHEN** `update_function_app_settings()` is called with settings containing sensitive values (e.g., key authorization strings)
- **THEN** the setting values do NOT appear in any log output at any log level; only the function app name and setting key names may be logged

#### Scenario: Raises AzureGatewayError on Azure API failure
- **WHEN** the `WebSiteManagementClient` call raises `HttpResponseError`
- **THEN** `update_function_app_settings()` raises `AzureGatewayError` with the error detail
