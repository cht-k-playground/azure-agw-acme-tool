# Spec: Agent Git Workflow

## ADDED Requirements

### Requirement: Push immediately after every commit

After every `git commit`, the agent SHALL immediately run `git push` to the remote tracking branch. No commit SHALL be left unpushed at the end of any operation.

#### Scenario: Commit followed by push

- **WHEN** the agent creates a git commit
- **THEN** the agent immediately runs `git push origin <branch>` before completing the task

#### Scenario: No orphaned local commits

- **WHEN** a cloud agent session ends
- **THEN** no commits exist locally that have not been pushed to the remote repository
