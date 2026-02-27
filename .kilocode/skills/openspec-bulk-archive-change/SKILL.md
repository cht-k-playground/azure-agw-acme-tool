---
name: openspec-bulk-archive-change
description: Archive multiple completed OpenSpec changes at once. Use when the user wants to batch-archive parallel changes with agentic spec conflict detection and resolution.
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: openspec
  version: "1.0"
  generatedBy: "1.2.0"
---

Archive multiple completed changes at once with agentic spec conflict resolution.

**Input**: Optionally specify change names. If omitted, list all active changes and prompt for selection.

**Steps**

1. **List available changes**

   Run `openspec list --json` to get all active changes.

   Present the list to the user. Use the **AskUserQuestion tool** (multiple: true) to let the user select which changes to archive.

   Show for each change:
   - Change name
   - Schema
   - Task completion (N/M tasks complete)
   - Whether delta specs exist

   **IMPORTANT**: Do NOT auto-select. Always let the user confirm the selection.

2. **Validate each selected change**

   For each selected change:
   ```bash
   openspec status --change "<name>" --json
   ```

   Check:
   - Artifact completion status
   - Task completion: read `tasks.md`, count `- [x]` vs `- [ ]`

   Collect warnings for:
   - Changes with incomplete tasks
   - Changes with missing required artifacts

   Display a combined pre-archive summary showing all warnings before proceeding.

   Use **AskUserQuestion tool** to confirm: "Proceed with archive? (Changes with warnings will be noted)"

3. **Detect spec conflicts**

   For each selected change with delta specs in `openspec/changes/<name>/specs/`:
   - Collect the capability names (directory names under `specs/`)

   Check for conflicts: if two or more changes touch the same capability, flag as conflict.

   **If conflicts detected**:
   - Display: "⚠ Spec conflict: `<change-A>` and `<change-B>` both touch `specs/<capability>/`"
   - For each conflict, inspect the codebase to determine which requirements were actually implemented
   - Determine merge order (chronological by change creation date)
   - Report resolution plan to user before proceeding

4. **Archive changes in order**

   Archive each change in chronological order (oldest first):

   For each change:

   a. **Sync delta specs** if not already synced:
      - Apply the delta spec merge (same logic as `/opsx:sync`)
      - When multiple changes touch the same capability, apply in chronological order
      - Later changes' MODIFIED/REMOVED operations apply on top of earlier changes' additions

   b. **Move the change to archive**:
      ```bash
      mkdir -p openspec/changes/archive
      mv openspec/changes/<name> openspec/changes/archive/YYYY-MM-DD-<name>
      ```
      Use today's date in `YYYY-MM-DD` format.

      If the target path already exists, report an error for that change and skip it.

   c. **Report progress**: "✓ Archived <change-name>"

5. **Show final summary**

   ```
   ## Bulk Archive Complete

   Archived N changes:
   ✓ <change-1> → openspec/changes/archive/YYYY-MM-DD-<change-1>/
   ✓ <change-2> → openspec/changes/archive/YYYY-MM-DD-<change-2>/
   ✗ <change-3> — skipped: <reason>

   Specs merged: <capability-1>, <capability-2>
   Conflicts resolved: <count>
   ```

**Conflict Resolution Heuristics**

When two changes touch the same capability:
1. Check which requirements from each change are present in the codebase
2. If both are implemented: merge in chronological order (earlier change first, later change on top)
3. If only one is implemented: apply only that change's delta, note the skipped delta
4. If neither is implemented: apply both in chronological order, note for review

**Guardrails**
- Never archive without user confirmation
- Always resolve conflicts before archiving
- Preserve all artifacts in archive (move, don't delete)
- If a target archive path already exists, skip that change and report — do not overwrite
- Changes with CRITICAL issues in `openspec validate` output should be flagged (but not blocked)
- Show what you're doing at each step
