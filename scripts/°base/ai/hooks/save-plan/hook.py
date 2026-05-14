#!/usr/bin/env python3
"""PostToolUse hook for Write and ExitPlanMode: snapshot the plan into
``ai/plans/NNN_slug.md`` (or ``ai/°base/plans/...`` inside the base meta-repo)
and commit just that new file.

Fires on:
- ``Write`` — when the plan file (~/.claude/plans/*.md) is written during
  plan mode; captures intermediate saves.
- ``ExitPlanMode`` — when the user approves the plan.

Deduplication: if the most-recent plan file already has identical content
(e.g. Write and ExitPlanMode fire for the same text), the second call is a
no-op.  Each distinct content version gets its own numbered file.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _lib import read_payload, resolve_log_path, slugify  # noqa: E402


def _next_prefix(plans_dir: Path) -> str:
    highest = 0
    for entry in plans_dir.glob("[0-9]*_*.md"):
        m = re.match(r"^(\d+)_", entry.name)
        if m:
            highest = max(highest, int(m.group(1)))
    return f"{highest + 1:03d}"


def _plan_from_response(tool_response) -> str:
    """Extract plan text from the ExitPlanMode tool_response dict.

    The harness sends tool_response as a dict with a "plan" key (the plan
    text) and an optional "filePath" key.  Older/unknown shapes are handled
    as fallbacks.
    """
    if tool_response is None:
        return ""
    if isinstance(tool_response, dict):
        # Primary: harness puts the plan text directly in tool_response["plan"]
        plan = tool_response.get("plan") or ""
        if plan.strip():
            return plan.strip()
        # Secondary: read the file if a path was provided
        file_path = tool_response.get("filePath") or ""
        if file_path:
            p = Path(file_path)
            if p.is_file():
                return p.read_text(encoding="utf-8").strip()
        return ""
    if isinstance(tool_response, str):
        # Legacy/fallback: plain-string response containing the plan
        return tool_response.strip()
    return ""


def _plan_from_write(tool_input: dict) -> str:
    """Extract plan text when the Write tool writes to ~/.claude/plans/*.md."""
    file_path = tool_input.get("file_path") or ""
    if not re.search(r"/\.claude/plans/[^/]+\.md$", file_path):
        return ""
    return (tool_input.get("content") or "").strip()


def _already_saved(plans_dir: Path, plan: str) -> bool:
    """True if the most-recent numbered plan file has identical content."""
    files = sorted(plans_dir.glob("[0-9]*_*.md"))
    if not files:
        return False
    return files[-1].read_text(encoding="utf-8").strip() == plan


def main() -> int:
    payload = read_payload()
    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}

    if tool_name == "Write":
        plan = _plan_from_write(tool_input)
    else:
        plan = (tool_input.get("plan") or "").strip()
        if not plan:
            plan = _plan_from_response(payload.get("tool_response"))

    if not plan:
        return 0

    # resolve_log_path cd's to the git root and applies the base-repo reroute.
    # We pass a sentinel filename just to obtain the correct plans directory.
    sentinel = resolve_log_path("ai/plans/.dir", "ai/°base/plans/.dir")
    plans_dir = sentinel.parent
    plans_dir.mkdir(parents=True, exist_ok=True)

    if _already_saved(plans_dir, plan):
        return 0

    prefix = _next_prefix(plans_dir)
    slug = slugify(plan, fallback="plan")
    out_path = plans_dir / f"{prefix}_{slug}.md"

    body = plan if plan.endswith("\n") else plan + "\n"
    out_path.write_text(body, encoding="utf-8")

    relpath = str(out_path.relative_to(Path.cwd()))
    subprocess.run(["git", "add", "--", relpath], capture_output=True)
    subprocess.run(
        ["git", "commit", "--only", relpath, "-m", f"ai: save plan {prefix}_{slug}"],
        capture_output=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
