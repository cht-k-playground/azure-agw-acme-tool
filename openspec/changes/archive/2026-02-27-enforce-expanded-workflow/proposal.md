# enforce-expanded-workflow

## Why

This project uses the OpenSpec `spec-driven` schema, which mandates the Expanded Mode workflow:

```
/opsx:new → /opsx:ff → /opsx:apply → /opsx:verify → /opsx:archive
```

This workflow requires each artifact to be generated and reviewable as a discrete step.
`/opsx:propose` is a `core`-profile shortcut that collapses scaffold and planning into a
single unreviewed step — it is incompatible with the intent of Expanded Mode.

Both `AGENTS.md` and `ROADMAP.md` currently reference `/opsx:propose` as a recommended
starting point. These references create ambiguity: agents following the documentation may
bypass explicit artifact review, defeating the governance model the project depends on.

## What Changes

- **`AGENTS.md`**:
  - Section 1: Remove the `/opsx:propose` shortcut recommendation from the preferred
    workflow description. The five-step Expanded Mode workflow stands alone.
  - Section 6 ("Just Fix" guidance): Replace `/opsx:propose` with `/opsx:new` + `/opsx:ff`
    as the prescribed two-step approach for quick fixes.
  - Section 7 (conflict-handling script): Update the quoted agent response to reference
    `/opsx:new` + `/opsx:ff` instead of `/opsx:propose`.
  - Slash Command Reference table: Retain the `/opsx:propose` row but annotate it as a
    `core`-profile shortcut that is not used in this project.

- **`ROADMAP.md`**:
  - Lines 4, 8, and 11: Replace all occurrences of `/opsx:propose` with the equivalent
    Expanded Mode steps (`/opsx:new` → `/opsx:ff`) so the roadmap accurately reflects how
    contributors should start each change.

## Capabilities

### New Capabilities

None. This is a documentation and governance consistency change only.

### Modified Capabilities

No spec-level requirements or runtime behaviour change. The Expanded Mode workflow itself
is unchanged; this change removes documentation that contradicted it.

## Impact

- `AGENTS.md` — three sections updated (§1, §6, §7); slash command table annotated.
- `ROADMAP.md` — usage instructions updated (lines 4, 8, 11).
- No source code, tests, or `pyproject.toml` changes.
