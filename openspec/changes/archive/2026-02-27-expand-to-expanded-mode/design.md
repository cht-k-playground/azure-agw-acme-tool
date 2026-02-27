## Context

Kilo Code loads agent skills from `.kilocode/skills/<name>/SKILL.md` and workflow trigger files from `.kilocode/workflows/opsx-*.md`. The current installation reflects the OpenSpec `core` profile, which ships 4 commands. The Expanded Mode adds 6 more commands. Since the `openspec` CLI is not installed in this environment, all files are authored manually using content sourced from the OpenSpec official documentation (workflows.md, commands.md) and community-published SKILL.md files verified against `generatedBy: "1.2.0"`.

## Goals / Non-Goals

**Goals:**
- Add all 6 Expanded Mode workflow files and their paired SKILL.md files
- Update `AGENTS.md` to document `new → ff → apply → verify → archive` as the preferred workflow
- Keep existing `opsx-propose` / `openspec-propose` intact as an alternative shortcut
- All new files use `generatedBy: "1.2.0"` in frontmatter metadata

**Non-Goals:**
- Installing or upgrading the `openspec` CLI
- Adding `/opsx:onboard` (tutorial command, not needed)
- Modifying `src/`, `tests/`, or `pyproject.toml`

## Decisions

**Decision: Workflow file content mirrors SKILL.md body**
Each `.kilocode/workflows/opsx-<x>.md` file contains the same instructional content as the corresponding `.kilocode/skills/openspec-<x>-change/SKILL.md` body (without the YAML frontmatter). This mirrors what `openspec update` generates for Kilo Code. Rationale: Kilo Code uses the workflow files as slash command triggers and the skill files as on-demand context; keeping them in sync avoids divergence.

**Decision: Retain `/opsx:propose` as alternative**
The existing `opsx-propose.md` and `openspec-propose/SKILL.md` are not removed. They remain valid for quick changes where the user wants a one-step artifact generation. The AGENTS.md documents this as the "alternative shortcut" rather than the preferred flow.

**Decision: `generatedBy: "1.2.0"` for all new files**
All new SKILL.md frontmatter metadata will use `generatedBy: "1.2.0"` to reflect the current OpenSpec version, even though the files are manually authored. This ensures consistency with the existing skill files in the repo.

**Decision: AGENTS.md Section 1 table replaces the 3-step flow with a 5-step flow**
The `propose → apply → archive` table in Section 1 is replaced with `new → ff → apply → verify → archive`. The `/opsx:propose` shortcut is mentioned in a note below the table rather than removed, to maintain backwards compatibility for anyone already familiar with the core flow.

## Risks / Trade-offs

- **Manual content drift** → If the upstream OpenSpec project updates SKILL.md content, these manually-authored files will not auto-update. Mitigation: when `openspec` CLI is eventually available, run `openspec update` to refresh all files to the latest version.
- **Two paths in AGENTS.md** → Documenting both `propose` (shortcut) and `new + ff` (preferred) may cause confusion. Mitigation: AGENTS.md clearly marks `new → ff → apply → verify → archive` as the preferred flow and `propose` as the shortcut, with a one-line explanation of when each is appropriate.

## Open Questions

_(none — all decisions above are resolved)_
