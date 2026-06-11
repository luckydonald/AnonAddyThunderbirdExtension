#!/usr/bin/env bash
# scripts/°base/init/checkout.sh
#
# One-shot repo setup: installs git hooks (pre-commit framework + git-lfs)
# and cleans up stale yorkie hooks left behind by the old Vue CLI tooling.
#
# Intended to be run:
#   - By the Claude SessionStart hooks (automatic)
#   - After `git clone` / `git checkout` (manual or via post-checkout)
#   - Idempotent: safe to run multiple times.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"

# ─── 1. Remove stale yorkie hooks ───────────────────────────────────────────
# Yorkie is no longer installed. Its hooks reference node_modules/yorkie which
# doesn't exist. Remove them so they don't interfere with pre-commit or git-lfs.
remove_yorkie_hooks() {
  local hook_file
  for hook_file in "$HOOKS_DIR"/*; do
    [ -f "$hook_file" ] || continue
    # Skip .sample files
    [[ "$hook_file" == *.sample ]] && continue
    # Check if it's a yorkie hooks
    if head -2 "$hook_file" | grep -q '#yorkie'; then
      rm "$hook_file"
    fi
  done
}

remove_yorkie_hooks

# ─── 2. Make generated git-lfs hooks optional ───────────────────────────────
# git-lfs installs hooks that fail hard if the binary is unavailable in the
# hook environment. That breaks generic git operations such as
# `git checkout -- .`, so keep the hooks functional when possible and skip
# them cleanly when git-lfs is not on PATH.
make_git_lfs_hooks_optional() {
  local hook_name hook_file lfs_command
  for hook_name in post-checkout post-commit post-merge pre-push; do
    hook_file="$HOOKS_DIR/$hook_name"
    [ -f "$hook_file" ] || continue
    if grep -q 'git lfs' "$hook_file" && grep -q 'git-lfs' "$hook_file"; then
      lfs_command="$hook_name"
      cat >"$hook_file" <<EOF
#!/bin/sh
if command -v git-lfs >/dev/null 2>&1; then
  git lfs $lfs_command "\$@"
fi
exit 0
EOF
      chmod +x "$hook_file"
    fi
  done
}

# ─── 3. Unset core.hooksPath if set ─────────────────────────────────────────
# Some tools (e.g. husky v9) set core.hooksPath which prevents .git/hooks from
# being used. We want .git/hooks to be the canonical hooks directory.
git config --unset-all core.hooksPath 2>/dev/null || true

# ─── 4. Install git-lfs hooks ───────────────────────────────────────────────
# git-lfs install writes its hooks (post-checkout, post-commit, post-merge, pre-push)
if command -v git-lfs >/dev/null 2>&1; then
  git lfs install --local >/dev/null 2>&1 || true
fi
make_git_lfs_hooks_optional

# GitHub's LFS lock API can reject pushes when credentials are valid for git
# push but not for lock verification. This repo does not use LFS locks, so keep
# the generated pre-push hook from checking them for local GitHub HTTPS remotes.
if command -v python3 >/dev/null 2>&1; then
  python3 "$REPO_ROOT/scripts/°base/git/remote/fix_username.py" --fix-lfs-locks-only >/dev/null 2>&1 || true
fi

# ─── 5. Install pre-commit hooks ────────────────────────────────────────────
# Installs commit-msg and pre-commit hooks types as configured in
# .pre-commit-config.yaml
if command -v pre-commit >/dev/null 2>&1; then
  pre-commit install --hook-type pre-commit >/dev/null 2>&1 || true
  pre-commit install --hook-type commit-msg >/dev/null 2>&1 || true
fi
