#!/usr/bin/env bash
# PostToolUse hook (AskUserQuestion): appends the asked question(s) to ai/query.md
# as a markdown blockquote, then commits it.

PROMPT_LOG="ai/query.md"
PROMPT_COMMIT_TEMPLATE="ai/commit-templates/prompt.md"

# Read full stdin once
INPUT=$(cat)

# Pull out the bits we render verbatim, plus the raw tool_input for the JSON dump
NUM_QUESTIONS=$(printf '%s' "$INPUT" | jq '.tool_input.questions | length // 0')
QUESTIONS_JSON=$(printf '%s' "$INPUT" | jq '.tool_input')

# Picked answer(s). Accept both a bare string and the harness's `{answers: {q: a}}`
# shape; fall back to a tostring so we never silently drop an unfamiliar payload.
ANSWER=$(printf '%s' "$INPUT" | jq -r '
  if (.tool_response // null) == null then empty
  elif (.tool_response | type) == "string" then .tool_response
  elif (.tool_response.answers // null | type) == "object" then
    (.tool_response.answers | to_entries | map(.value) | join("\n"))
  else (.tool_response | tostring)
  end
')

# Skip if nothing meaningful was captured
if [ -z "$NUM_QUESTIONS" ] || [ "$NUM_QUESTIONS" = "0" ] || [ "$NUM_QUESTIONS" = "null" ]; then
  exit 0
fi

# Work from the git root
ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 1
cd "$ROOT" || exit 2

# Reroute log path when running inside the `base` repo
_ORIGIN_URL=$(git remote get-url origin 2>/dev/null)
_REMOTE_NAMES=$(git remote | sort | tr '\n' ' ' | xargs)
if [ "$(basename "$ROOT")" = "base" ] \
  && [ "$_REMOTE_NAMES" = "empty origin" ] \
  && printf '%s' "$_ORIGIN_URL" | grep -qE 'luckydonald/base(\.git)?$'; then
  PROMPT_LOG="ai/°base/query.md"
fi

mkdir -p "$(dirname "${PROMPT_LOG}")"

# If query.md has staged changes, save blobs to re-apply after commit
STAGED_HASH=$(git ls-files --stage "${PROMPT_LOG}" 2>/dev/null | awk '{print $2}')
HEAD_HASH=$(git ls-tree HEAD "${PROMPT_LOG}" 2>/dev/null | awk '{print $3}')
TMP_BASE="" TMP_STAGED=""
if [ -n "$STAGED_HASH" ] && [ "$STAGED_HASH" != "$HEAD_HASH" ]; then
  TMP_BASE=$(mktemp)
  TMP_STAGED=$(mktemp)
  git cat-file blob "$HEAD_HASH"   > "$TMP_BASE"   2>/dev/null || true
  git cat-file blob "$STAGED_HASH" > "$TMP_STAGED" 2>/dev/null || true
fi

# Append blockquote entry: question(s) → option labels → fenced JSON dump
{
  for (( i = 0; i < NUM_QUESTIONS; i++ )); do
    if [ "$i" -gt 0 ]; then
      printf '> \n'
    fi
    Q=$(printf '%s' "$INPUT" | jq -r ".tool_input.questions[$i].question // \"\"")
    printf '> %s\n' "$Q"
    printf '%s' "$INPUT" \
      | jq -r ".tool_input.questions[$i].options[]?.label" \
      | while IFS= read -r opt; do
          [ -n "$opt" ] && printf '> - %s\n' "$opt"
        done
  done
  if [ -n "$ANSWER" ]; then
    first=1
    while IFS= read -r line; do
      if [ "$first" -eq 1 ]; then
        printf '> → %s\n' "$line"
        first=0
      else
        printf '>   %s\n' "$line"
      fi
    done <<< "$ANSWER"
  fi
  printf '> ```json\n'
  printf '%s\n' "$QUESTIONS_JSON" | sed 's/^/> /'
  printf '> ```\n'
  printf '> \n'
  printf '\n'
} >> "${PROMPT_LOG}"

# Determine commit message (shared with save-prompt so rebase-ai-prompt-commits groups them)
COMMIT_MSG=""
if [ -f "${PROMPT_COMMIT_TEMPLATE}" ]; then
  COMMIT_MSG=$(< "${PROMPT_COMMIT_TEMPLATE}" tr -d '\n\r' | xargs)
fi
if [ -z "$COMMIT_MSG" ]; then
  COMMIT_MSG="ai: updated prompt"
fi

# Commit only query.md; leave other staged files untouched
git commit --only "${PROMPT_LOG}" -m "${COMMIT_MSG}" 2>/dev/null || true

# Re-apply any pre-existing staged changes on top of new HEAD
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
