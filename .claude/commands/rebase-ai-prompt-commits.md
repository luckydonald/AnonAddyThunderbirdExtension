---
name: rebase-ai-prompt-commits
description: Rebases the current branch to group stray `ai: updated prompt` commits (ai/query.md-only) into their neighboring code commits using non-interactive rebase. Fixes mislabeled commits. Optionally rewrites HEAD as a branch summary. Invoke on demand before merging or reviewing a branch.
---

# Rebase: Group `ai: updated prompt` Commits

## Procedure

**1. Audit the branch**
```bash
git log --oneline origin/<upstream>..HEAD
for sha in <shas>; do
  echo "$sha $(git log -1 --format='%s' $sha): $(git show --name-only --format='' $sha | tr '\n' ' ')"
done
```

**2. Plan groups.** For each `ai: updated prompt` commit (only `ai/query.md`), assign it as `fixup` under its nearest code commit. Flag mislabeled commits (wrong message for actual file content).

**3. Write renamed commit messages** to `/ai/git/rebase-msg-<sha>.md` for any commits needing a label fix.

**4. Write the rebase todo script**
```bash
cat > /tmp/git-rebase-todo.sh << 'SCRIPT'
cat > "$1" << 'REBASE'
pick <first-code-commit>
fixup <query-commit>
fixup <query-commit>
exec git commit --amend -F /ai/git/rebase-msg-<sha>.md
pick <next-code-commit>
fixup <query-commit>
...
REBASE
SCRIPT
chmod +x /tmp/git-rebase-todo.sh
```
Put `exec git commit --amend -F ...` **after** all fixups for that group to rename the squashed result.

**5. Run**
```bash
GIT_SEQUENCE_EDITOR=/tmp/git-rebase-todo.sh git rebase -i origin/<upstream>
```

**6. Optional — rewrite HEAD as branch summary**
Write to `ai/git/pending-commit.md`:
```
[scope] category: ai: Run: <summary>

Branch <name> based on origin/<upstream> @ <sha>.

- bullet: what changed and why
- bullet: key decisions
```
Then: `git commit --amend -F ai/git/pending-commit.md`
