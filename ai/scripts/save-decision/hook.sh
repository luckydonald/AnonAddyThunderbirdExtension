#!/usr/bin/env bash
# PostToolUse hook (AskUserQuestion): appends plan-mode decisions to ai/decisions.md and commits it.

DECISION_LOG="ai/decisions.md"
DECISION_COMMIT_TEMPLATE="ai/commit-templates/decision.md"

# Read full stdin once
INPUT=$(cat)

# Extract fields from tool_input / tool_response
QUESTION=$(printf '%s' "$INPUT" | jq -r '.tool_input.questions[0].question // "(unknown)"')
OPTIONS=$(printf '%s' "$INPUT" | jq -r '[.tool_input.questions[0].options[]?.label] | join(" | ")' 2>/dev/null)
ANSWER=$(printf '%s' "$INPUT" | jq -r '.tool_response // "(unknown)"')

# Skip if nothing meaningful was captured
if [ "$QUESTION" = "(unknown)" ] && [ "$ANSWER" = "(unknown)" ]; then
  exit 0
fi

# Work from the git root
ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 1
cd "$ROOT" || exit 2

mkdir -p ai

# If decisions.md has staged changes, save blobs to re-apply after commit
STAGED_HASH=$(git ls-files --stage "${DECISION_LOG}" 2>/dev/null | awk '{print $2}')
HEAD_HASH=$(git ls-tree HEAD "${DECISION_LOG}" 2>/dev/null | awk '{print $3}')
TMP_BASE="" TMP_STAGED=""
if [ -n "$STAGED_HASH" ] && [ "$STAGED_HASH" != "$HEAD_HASH" ]; then
  TMP_BASE=$(mktemp)
  TMP_STAGED=$(mktemp)
  git cat-file blob "$HEAD_HASH"   > "$TMP_BASE"   2>/dev/null || true
  git cat-file blob "$STAGED_HASH" > "$TMP_STAGED" 2>/dev/null || true
fi

# Append entry
{
  printf '? %s\n' "$QUESTION"
  if [ -n "$OPTIONS" ]; then
    printf '  %s\n' "$OPTIONS"
  fi
  printf '  -> %s\n\n' "$ANSWER"
} >> "${DECISION_LOG}"

# Determine commit message
COMMIT_MSG=""
if [ -f "${DECISION_COMMIT_TEMPLATE}" ]; then
  COMMIT_MSG=$(< "${DECISION_COMMIT_TEMPLATE}" tr -d '\n\r' | xargs)
fi
if [ -z "$COMMIT_MSG" ]; then
  COMMIT_MSG="ai: recorded decision"
fi

# Commit only decisions.md; leave other staged files untouched
git commit --only "${DECISION_LOG}" -m "${COMMIT_MSG}" 2>/dev/null || true

# Re-apply any pre-existing staged changes on top of new HEAD
if [ -n "$TMP_BASE" ]; then
  TMP_NEW_HEAD=$(mktemp)
  TMP_MERGED=$(mktemp)
  git show "HEAD:${DECISION_LOG}" > "$TMP_NEW_HEAD" 2>/dev/null || true

  if python3 .claude/hooks/merge-staged.py \
      "$TMP_BASE" "$TMP_STAGED" "$TMP_NEW_HEAD" "$TMP_MERGED" 2>/dev/null; then
    NEW_BLOB=$(git hash-object -w "$TMP_MERGED")
    git update-index --cacheinfo "100644,${NEW_BLOB},${DECISION_LOG}" 2>/dev/null || true
  fi

  rm -f "$TMP_BASE" "$TMP_STAGED" "$TMP_NEW_HEAD" "$TMP_MERGED"
fi
