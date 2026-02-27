## Why

The project currently has only the OpenSpec `core` profile installed (4 commands: `explore`, `propose`, `apply`, `archive`). The Expanded Mode adds an explicit scaffold-and-verify discipline — separating change scaffolding (`/opsx:new`) from artifact generation (`/opsx:ff`), and inserting a structured verification gate (`/opsx:verify`) before archiving — which is well-suited to this project's ROADMAP where every change item has explicit Acceptance Criteria.

## What Changes

- Add 6 new workflow files to `.kilocode/workflows/`: `opsx-new.md`, `opsx-ff.md`, `opsx-verify.md`, `opsx-continue.md`, `opsx-sync.md`, `opsx-bulk-archive.md`
- Add 6 corresponding skill directories to `.kilocode/skills/`: `openspec-new-change/SKILL.md`, `openspec-ff-change/SKILL.md`, `openspec-verify-change/SKILL.md`, `openspec-continue-change/SKILL.md`, `openspec-sync-specs/SKILL.md`, `openspec-bulk-archive-change/SKILL.md`
- Update `AGENTS.md` Section 1 to document the new preferred workflow (`new → ff → apply → verify → archive`) and update Section 5 Cheat-Sheet with all new commands
- Existing `opsx-propose.md` and `openspec-propose` skill are retained as an alternative one-step shortcut

## Capabilities

### New Capabilities

- `openspec-expanded-workflows`: The set of Expanded Mode slash commands and their corresponding Kilo Code workflow + skill files

### Modified Capabilities

_(none — no existing specs to modify)_

## Impact

- `.kilocode/workflows/` gains 6 new markdown files
- `.kilocode/skills/` gains 6 new skill directories
- `AGENTS.md` Section 1 workflow table and Section 5 Cheat-Sheet are updated
- No changes to `src/`, `tests/`, or `pyproject.toml`
- `openspec` CLI is **not** required at runtime; all file content is authored manually from OpenSpec official docs and community-published SKILL.md content (`generatedBy: "1.2.0"`)
