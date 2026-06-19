---
name: feedback-ai-settings-sync-recovery
description: How to fix the ai-settings-sync pre-commit hook when it fails
metadata: 
  node_type: memory
  type: feedback
  originSessionId: db88cfaf-a517-456a-8851-0c020b754dc2
---

When the `ai-settings-sync` pre-commit hook fails with "AI tool settings are out of sync: ai/tool-settings/settings.local.json", run:

```bash
uv run --directory scripts/°base python -m ai.settings.sync --apply
```

Then retry the commit. The `--apply` flag writes the synchronized files. Use `--check --explain` first to see what's diverged without writing.

**Why:** Can happen after a `git reset --soft` that reverses a commit which touched settings files, or after the sync script's source changes without the generated files being updated.
