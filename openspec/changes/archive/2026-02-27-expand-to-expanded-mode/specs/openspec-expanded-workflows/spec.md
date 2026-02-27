## ADDED Requirements

### Requirement: New-change workflow is available
The system SHALL provide a `/opsx:new` workflow that creates a change scaffold and shows the first artifact template, then stops to wait for user direction.

#### Scenario: User initiates a new change
- **WHEN** the user invokes `/opsx:new <name>`
- **THEN** the agent creates `openspec/changes/<name>/` with `.openspec.yaml`, displays the artifact sequence, and prompts the user to provide context before creating any artifacts

#### Scenario: Change name not provided
- **WHEN** the user invokes `/opsx:new` with no argument
- **THEN** the agent asks for a kebab-case change name before proceeding

### Requirement: Fast-forward workflow is available
The system SHALL provide a `/opsx:ff` workflow that generates all planning artifacts in dependency order in a single invocation, stopping when all `applyRequires` artifacts are complete.

#### Scenario: User fast-forwards artifact creation
- **WHEN** the user invokes `/opsx:ff` on an active change
- **THEN** the agent creates proposal, specs, design, and tasks in dependency order, tracking progress with TodoWrite, and announces "Ready for implementation" when done

#### Scenario: Change already has some artifacts
- **WHEN** the user invokes `/opsx:ff` and some artifacts already exist
- **THEN** the agent skips completed artifacts and creates only the remaining ones

### Requirement: Verify workflow is available
The system SHALL provide a `/opsx:verify` workflow that validates implementation against change artifacts across three dimensions: Completeness, Correctness, and Coherence.

#### Scenario: All checks pass
- **WHEN** the user invokes `/opsx:verify` and all tasks are complete, all requirements are implemented, and design decisions are reflected in code
- **THEN** the agent outputs a verification report with zero CRITICAL issues and confirms the change is ready to archive

#### Scenario: Critical issues found
- **WHEN** incomplete tasks or unimplemented requirements are detected
- **THEN** the agent reports each issue as CRITICAL with a specific, actionable recommendation including file and line references where applicable

#### Scenario: Only warnings found
- **WHEN** no CRITICAL issues exist but spec/design divergences or untested scenarios are detected
- **THEN** the agent reports these as WARNINGs and confirms the change is ready to archive with noted improvements

### Requirement: Continue workflow is available
The system SHALL provide a `/opsx:continue` workflow that creates exactly ONE artifact per invocation based on the dependency graph, then stops.

#### Scenario: User steps through artifacts one at a time
- **WHEN** the user invokes `/opsx:continue` on a change with pending artifacts
- **THEN** the agent creates the first ready artifact, shows what is now unlocked, and stops

#### Scenario: All artifacts already complete
- **WHEN** the user invokes `/opsx:continue` and all artifacts are done
- **THEN** the agent congratulates the user and suggests running `/opsx:apply`

### Requirement: Sync-specs workflow is available
The system SHALL provide a `/opsx:sync` workflow that merges delta specs from a change into `openspec/specs/` using intelligent agent-driven merging (not wholesale file replacement).

#### Scenario: Delta specs are merged into main specs
- **WHEN** the user invokes `/opsx:sync` on a change that has delta specs
- **THEN** the agent applies ADDED/MODIFIED/REMOVED/RENAMED sections from each delta spec into the corresponding `openspec/specs/<capability>/spec.md`, preserving existing content not mentioned in the delta

#### Scenario: No delta specs exist
- **WHEN** the user invokes `/opsx:sync` and the change has no `specs/` subdirectory
- **THEN** the agent informs the user and stops without making changes

### Requirement: Bulk-archive workflow is available
The system SHALL provide a `/opsx:bulk-archive` workflow that archives multiple completed changes in a single operation, with agentic spec conflict detection and resolution.

#### Scenario: Multiple changes archived without conflicts
- **WHEN** the user invokes `/opsx:bulk-archive` and no changes touch the same spec capability
- **THEN** the agent archives all selected changes in chronological order

#### Scenario: Spec conflict detected between changes
- **WHEN** two changes both have delta specs for the same capability
- **THEN** the agent inspects the codebase to determine which requirements were implemented, resolves the conflict, and archives in chronological order
