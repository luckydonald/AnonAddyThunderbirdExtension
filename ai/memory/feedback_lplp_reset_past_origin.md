---
name: feedback-lplp-reset-past-origin
description: "lplp commit style: never git reset --soft past commits already on origin"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: db88cfaf-a517-456a-8851-0c020b754dc2
---

Before `git reset --soft HEAD~N` to fold ai: auto-commits, always check how many commits are LOCAL only:

```bash
git log --oneline origin/<branch>..HEAD
```

Only reset commits that appear in that list. Resetting past `origin/<branch>` leaves the local branch behind origin, causing a confusing diverged state.

**Why:** This happened in practice — reset 6 commits to fold auto-commits, but 3 of those were already on origin. Result: local branch was 3 commits behind origin and couldn't commit cleanly until the situation was clarified by the user.

**How to apply:** Always run the `git log origin/<branch>..HEAD` audit step before any `reset --soft` for lplp folding. If `N` would exceed the count in that list, stop at `origin/<branch>` as the floor.
