## 1. New-Change Workflow

- [x] 1.1 Create `.kilocode/workflows/opsx-new.md` with the `/opsx:new` scaffold-and-wait workflow instructions
- [x] 1.2 Create `.kilocode/skills/openspec-new-change/SKILL.md` with YAML frontmatter (`name: openspec-new-change`, `generatedBy: "1.2.0"`) and the same body as 1.1

## 2. Fast-Forward Workflow

- [x] 2.1 Create `.kilocode/workflows/opsx-ff.md` with the `/opsx:ff` artifact fast-forward workflow instructions
- [x] 2.2 Create `.kilocode/skills/openspec-ff-change/SKILL.md` with YAML frontmatter (`name: openspec-ff-change`, `generatedBy: "1.2.0"`) and the same body as 2.1

## 3. Verify Workflow

- [x] 3.1 Create `.kilocode/workflows/opsx-verify.md` with the `/opsx:verify` three-dimension verification workflow instructions (Completeness / Correctness / Coherence)
- [x] 3.2 Create `.kilocode/skills/openspec-verify-change/SKILL.md` with YAML frontmatter (`name: openspec-verify-change`, `generatedBy: "1.2.0"`) and the same body as 3.1

## 4. Continue Workflow

- [x] 4.1 Create `.kilocode/workflows/opsx-continue.md` with the `/opsx:continue` one-artifact-at-a-time workflow instructions
- [x] 4.2 Create `.kilocode/skills/openspec-continue-change/SKILL.md` with YAML frontmatter (`name: openspec-continue-change`, `generatedBy: "1.2.0"`) and the same body as 4.1

## 5. Sync-Specs Workflow

- [x] 5.1 Create `.kilocode/workflows/opsx-sync.md` with the `/opsx:sync` intelligent delta-spec merge workflow instructions
- [x] 5.2 Create `.kilocode/skills/openspec-sync-specs/SKILL.md` with YAML frontmatter (`name: openspec-sync-specs`, `generatedBy: "1.2.0"`) and the same body as 5.1

## 6. Bulk-Archive Workflow

- [x] 6.1 Create `.kilocode/workflows/opsx-bulk-archive.md` with the `/opsx:bulk-archive` batch-archive-with-conflict-resolution workflow instructions
- [x] 6.2 Create `.kilocode/skills/openspec-bulk-archive-change/SKILL.md` with YAML frontmatter (`name: openspec-bulk-archive-change`, `generatedBy: "1.2.0"`) and the same body as 6.1

## 7. AGENTS.md Update

- [x] 7.1 Replace Section 1 workflow table (`propose → apply → archive`) with the 5-step Expanded Mode table (`new → ff → apply → verify → archive`); add a note that `/opsx:propose` remains as a one-step shortcut for quick changes
- [x] 7.2 Update Section 5 Cheat-Sheet to include all new commands: `new change`, `ff`, `verify`, `continue`, `sync`, `bulk-archive`
