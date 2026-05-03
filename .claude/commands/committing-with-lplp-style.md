---
name: committing-with-lplp-style
description: Activates the lplp-pipbuck commit style for the current session. Commits after every completed task, amends the last commit if its message is `ai: updated prompt`, writes messages via ai/pending-commit.md, never commits unrelated files. Use when the user opts in to this style at session start, or explicitly asks to enable it.
---

# lplp Commit Style

Adopt these rules for every commit made this session:

1. **Commit after every completed task.** Never leave work uncommitted.

2. **Check the last commit before committing:**
   - Last message is `ai: updated prompt` → **amend** it
   - Otherwise → create a new commit

3. **Always write the message to `ai/pending-commit.md` first**, then pass it with `-F ai/pending-commit.md`. Never inline the message.

4. **Message format:**
   ```
   [scope] category: ai: Run: <short one-line summary>

   <multiline body: what changed, why, key decisions>
   ```
   Scope examples: `[github]`, `[frontend]`, `[stdb]`, `[api]`

5. **Stage only files changed by the current task.** Never stage `ai/pending-commit.md` (it is gitignored).
