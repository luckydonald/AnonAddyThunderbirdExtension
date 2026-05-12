# Hook Smoke Test — Plan

## Context

This is a no-op plan used to exercise the new `save-plan` PostToolUse hook
(`scripts/°base/ai/hooks/save-plan/hook.py`). Exiting plan mode should:

1. Fire `PostToolUse` matcher `ExitPlanMode`.
2. Snapshot this plan's body into `ai/plans/001_hook-smoke-test-plan.md` (or
   the next `NNN_` if `001_` already exists).
3. Produce a commit `ai: save plan NNN_hook-smoke-test-plan`.

## Verification

After ExitPlanMode returns:

- `ls ai/plans/` shows the new file.
- `git log --oneline -1` shows the new commit, touching only that one file.
- File body matches this plan's text.

No code changes are part of this plan — it's the test.
