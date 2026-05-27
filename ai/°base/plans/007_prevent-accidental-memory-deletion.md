# Prevent Accidental Memory Deletion

## Summary
Fix the memory sync behavior so `SessionStart` never deletes repo memory files just because the Claude memory source is missing or empty. Treat repo memory as the durable copy, and allow memory deletions only when explicitly marked in git history.

## Key Changes
- Update `scripts/°base/ai/hooks/record-memory/hook.py`:
  - Stop using missing source files as delete signals.
  - On `SessionStart`, if a repo memory exists but the Claude source file is missing, recreate the Claude source file as a hardlink/symlink to the repo file.
  - Keep `PostToolUse` behavior source-to-repo for newly written Claude memory files.
  - If a source file exists but the repo file was intentionally deleted, suppress resurrection only when the latest git deletion for that memory has an explicit marker.

- Add commit-message enforcement for memory deletions:
  - New commit-msg hook requiring one exact line per deleted memory:
    `Deleted Memory: <filename>.md`
  - Hook checks staged deletions under `ai/memory/` and `ai/°base/memory/`.
  - Deleting memory files without matching markers fails the commit.
  - Register the hook in `.pre-commit-config.yaml` and `.pre-commit-hooks.yaml`.

- Do not restore the files deleted by `d1b384a`; user will handle that manually. This plan only prevents the same failure from recurring.

## Tests
- Add memory sync tests proving:
  - Empty/missing Claude source does not delete tracked repo memories.
  - Repo memory files recreate missing Claude source files.
  - Fresh Claude memory files still sync into the repo and auto-commit.
  - A memory whose latest git path event is a marked deletion is not resurrected from stale local source.

- Add commit-msg tests proving:
  - Memory deletion without `Deleted Memory: <filename>.md` fails.
  - Memory deletion with the marker passes.
  - Multiple memory deletions require one marker per filename.
  - Non-memory deletions are unaffected.

- Run:
  - `python3 -m unittest scripts/°base/tests/test_ai_hooks_base_routing.py`
  - the new commit-msg hook test module
  - `python3 -m py_compile scripts/°base/ai/hooks/record-memory/hook.py`

## Assumptions
- Repo memory is authoritative when source and repo disagree due only to missing local Claude files.
- Intentional memory deletion is represented by a git deletion plus `Deleted Memory: <filename>.md` in the commit message.
- The bad `d1b384a` deletion is repaired separately, not by this implementation.
