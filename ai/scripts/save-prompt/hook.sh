#!/usr/bin/env bash
# UserPromptSubmit hook: appends the user's prompt to ai/query.md and commits it.

PROMPT_LOG="ai/query.md"
PROMPT_COMMIT_TEMPLATE="ai/commit-templates/prompt.md"

AI_TOOL=${1:-unknown}

case "$AI_TOOL" in
  claude)
    PREFIX="❯"
    ;;
  codex)
    PREFIX="›"
    ;;
  *)
    PREFIX="⩼"
    ;;
esac

echo "PREFIX=$PREFIX"

PROMPT=$(jq -r '.prompt // ""')
if [ -z "$PROMPT" ]; then
  exit 0
fi

# Work from the git root
ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 1
cd "$ROOT" || exit 2

mkdir -p ai
env

# If query.md has staged changes, save old HEAD + staged blobs to re-apply after commit
STAGED_HASH=$(git ls-files --stage "${PROMPT_LOG}" 2>/dev/null | awk '{print $2}')
HEAD_HASH=$(git ls-tree HEAD "${PROMPT_LOG}" 2>/dev/null | awk '{print $3}')
TMP_BASE="" TMP_STAGED=""
if [ -n "$STAGED_HASH" ] && [ "$STAGED_HASH" != "$HEAD_HASH" ]; then
  TMP_BASE=$(mktemp)
  TMP_STAGED=$(mktemp)
  git cat-file blob "$HEAD_HASH"   > "$TMP_BASE"   2>/dev/null || true
  git cat-file blob "$STAGED_HASH" > "$TMP_STAGED" 2>/dev/null || true
fi

printf '%s %s\n\n' "${PREFIX}" "${PROMPT}" >> "${PROMPT_LOG}"

# Determine commit message
COMMIT_MSG=""
if [ -f "${PROMPT_COMMIT_TEMPLATE}" ]; then
  COMMIT_MSG=$(< "${PROMPT_COMMIT_TEMPLATE}" tr -d '\n\r' | xargs)
fi
if [ -z "$COMMIT_MSG" ]; then
  COMMIT_MSG="ai: updated prompt"
fi

# Commit only query.md from working tree; other staged files are untouched
git commit --only "${PROMPT_LOG}" -m "${COMMIT_MSG}" 2>/dev/null || true

# Re-apply the user's staged changes on top of new HEAD.
# Uses merge-staged.py which places end-of-file insertions after our appended query
# instead of conflicting with it.
if [ -n "$TMP_BASE" ]; then
  TMP_NEW_HEAD=$(mktemp)
  TMP_MERGED=$(mktemp)
  git show "HEAD:${PROMPT_LOG}" > "$TMP_NEW_HEAD" 2>/dev/null || true

  if python3 .claude/hooks/merge-staged.py \
      "$TMP_BASE" "$TMP_STAGED" "$TMP_NEW_HEAD" "$TMP_MERGED" 2>/dev/null; then
    NEW_BLOB=$(git hash-object -w "$TMP_MERGED")
    git update-index --cacheinfo "100644,${NEW_BLOB},${PROMPT_LOG}" 2>/dev/null || true
  fi

  rm -f "$TMP_BASE" "$TMP_STAGED" "$TMP_NEW_HEAD" "$TMP_MERGED"
fi
