# Spec: Workflow Governance

## ADDED Requirements

### Requirement: Expanded Mode workflow is the sole prescribed workflow

All project governance documents SHALL prescribe the five-step Expanded Mode workflow as the sole standard entry point for any change:

```
/opsx:new → /opsx:ff → /opsx:apply → /opsx:verify → /opsx:archive
```

- `/opsx:propose` SHALL NOT be referenced as a recommended or default starting point in any governance document.
- Where `/opsx:propose` appears in command reference tables, it MUST be annotated to indicate it is a `core`-profile shortcut not used in this project.

#### Scenario: AGENTS.md reflects Expanded Mode workflow

WHEN an agent reads `AGENTS.md`,  
THEN the preferred workflow section shows only the five-step Expanded Mode sequence (`/opsx:new → /opsx:ff → /opsx:apply → /opsx:verify → /opsx:archive`) with no `/opsx:propose` shortcut recommendation anywhere in the workflow guidance.

#### Scenario: ROADMAP.md reflects Expanded Mode workflow

WHEN a contributor reads `ROADMAP.md` usage instructions,  
THEN all workflow references use `/opsx:new → /opsx:ff` as the starting steps (not `/opsx:propose`), consistent with the five-step Expanded Mode workflow.

#### Scenario: propose command annotated as non-default

WHEN `/opsx:propose` appears in the slash command reference table in `AGENTS.md`,  
THEN it is annotated to indicate it is a `core`-profile shortcut not used in this project, so the table remains a complete reference without endorsing the shortcut as a workflow entry point.
