# AI query log file

#### General AI development guidelines:
- Create `ai/PROGRESS.md`, and keep it updated when you complete steps.
- You may refer to `ai/refrences` for code examples of other plugins or extra documentation provided for this task.
- When writing code, follow these guidelines:
  - Always prefer the early-return pattern to reduce nesting of `if`s, etc.
  - Similarly, prefer `if …` -> `continue`/`return`/`break` early in loops over large nested blocks.
- _If_ the project requires a frontend, use Vue, TS, and SCSS for that.
  - Prefer using `<script setup lang="ts">` style single file components.
  - Use proper TypeScript type hinting.
- _If_ the project requires a backend, use modern Python `3.14+` for that.
  - Do proper type hinting with full type annotations.
  - For type-hinting, prefer the native types (e.g. `dict[str, int]` over the older `typing.*` aliases like `Dict[AnyStr, int]`)
  - Prefer async programming where possible.
  - For web stuff: `FastApi`
  - For postgres: typed `sqlalchemy`
    - For migrations: `alembic`
- Write tests for both frontend and backend parts.
- Remember to update the `/CHANGELOG.md` and `/README.md` if existent (including other pre-existing documentation).
- If you want to write Markdown summaries of the task you just did (only if specifically asked for by the user!) write those to `ai/summaries/` folder, and never into the root folder.
  - However, usually you don't need to write Markdown summaries.
- Please prefer to use the read file tool over weird constructs with `cat` etc. Terminal should not be needed for searches most of the time, either.

----

#### Previous user prompts:
❯ The problem with the failed commit (which is not relevant) is `Co-Authored-By`. There should be a git commit hook - which would prevent this - and should be made sure to work by claude's init script - but never triggers?
Ah, I figured that the "deny" in the claude settings is executed first.
Is there a "on-deny" hook or similar we can hook into, to enhance it with that information that the `Co-Authored-By' and git actions which blindly add all files (`git add . …`, `git add -A …` etc.) are not allowed, instead of just the `Error: Permission to use Bash with command … has been denied.`.
So like our git hook would, if it were to run first/regardless (but it clearly shouldn't. Again, enrich the deny output)

❯ Yes, support both `git commit -m "*Co-Authored-By*"` and `git commit -F` where the file with the commit message is given, which we can then look into as well, to make sure. Support multiple variants of those flags, combined, too. If everything else fails, we still got the commit hook after all.

❯ _The only way to get rich messages is to remove the deny entries and let the `PermissionRequest` hook own the decision. The hook still denies — it just does so with explanation_ so the `PermissionRequest` hook only runs after the `deny` list?

❯ _PermissionRequest hook is effectively "runs before the *interactive* permission prompt, but after the *automatic* deny check."_ This is speculative, right? Can we check that in docs or somewhere?

❯ Create a hook for logging the plan mode decisions. Similar as we hook into `UserPromptSubmit`, I want to document the decisions taken when those multiple choice questions are asked - if possible with the full options to choose from - so it's clear later what the reasoning looked like.

❯ Commit, with prefix `[base] ai: Run: …`.

