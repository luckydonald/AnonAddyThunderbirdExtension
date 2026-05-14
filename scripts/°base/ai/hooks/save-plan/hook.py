#!/usr/bin/env python3
"""PostToolUse hook for Write and ExitPlanMode: snapshot the plan into
``ai/plans/NNN_slug.md`` (or ``ai/°base/plans/...`` inside the base meta-repo)
and commit just that new file.

Fires on:
- ``Write`` — when the plan file (~/.claude/plans/*.md) is written during
  plan mode; updates the session's plan file in-place (amending the commit).
- ``ExitPlanMode`` — when the user approves the plan; deduplicates against
  the last Write commit so approval doesn't produce a second file.

Session tracking: the first Write in a session creates a new numbered file;
subsequent Writes overwrite it and amend the commit.  A state file keyed by
session_id persists across async hook invocations.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _lib import read_payload, resolve_log_path, slugify  # noqa: E402

_STATE_FILE = Path(tempfile.gettempdir()) / "save-plan-state.json"


def _load_state() -> dict:
    try:
        return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    _STATE_FILE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")


def _next_prefix(plans_dir: Path) -> str:
    highest = 0
    for entry in plans_dir.glob("[0-9]*_*.md"):
        m = re.match(r"^(\d+)_", entry.name)
        if m:
            highest = max(highest, int(m.group(1)))
    return f"{highest + 1:03d}"


def _plan_from_response(tool_response) -> str:
    """Extract plan text from the ExitPlanMode tool_response dict."""
    if tool_response is None:
        return ""
    if isinstance(tool_response, dict):
        plan = tool_response.get("plan") or ""
        if plan.strip():
            return plan.strip()
        file_path = tool_response.get("filePath") or ""
        if file_path:
            p = Path(file_path)
            if p.is_file():
                return p.read_text(encoding="utf-8").strip()
        return ""
    if isinstance(tool_response, str):
        return tool_response.strip()
    return ""


def _plan_from_write(tool_input: dict) -> str:
    """Extract plan text when the Write tool writes to ~/.claude/plans/*.md."""
    file_path = tool_input.get("file_path") or ""
    if not re.search(r"/\.claude/plans/[^/]+\.md$", file_path):
        return ""
    return (tool_input.get("content") or "").strip()


def _commit_plan(relpath: str, slug: str, amend: bool) -> None:
    msg = f"ai: save plan {Path(relpath).stem}"
    subprocess.run(["git", "add", "--", relpath], capture_output=True)
    cmd = ["git", "commit"]
    if amend:
        cmd += ["--amend"]
    cmd += ["--only", relpath, "-m", msg]
    subprocess.run(cmd, capture_output=True)


def main() -> int:
    payload = read_payload()
    session_id = payload.get("session_id", "")
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

    sentinel = resolve_log_path("ai/plans/.dir", "ai/°base/plans/.dir")
    plans_dir = sentinel.parent
    plans_dir.mkdir(parents=True, exist_ok=True)

    state = _load_state()
    existing_relpath = state.get(session_id) if session_id else None
    existing_path = Path(existing_relpath) if existing_relpath else None

    if existing_path and existing_path.is_file():
        # Same session: skip if identical, otherwise overwrite + amend.
        if existing_path.read_text(encoding="utf-8").strip() == plan:
            return 0
        body = plan if plan.endswith("\n") else plan + "\n"
        existing_path.write_text(body, encoding="utf-8")
        _commit_plan(existing_relpath, slugify(plan), amend=True)
    else:
        # New session (or ExitPlanMode before any Write): create numbered file.
        prefix = _next_prefix(plans_dir)
        slug = slugify(plan, fallback="plan")
        out_path = plans_dir / f"{prefix}_{slug}.md"
        body = plan if plan.endswith("\n") else plan + "\n"
        out_path.write_text(body, encoding="utf-8")
        relpath = str(out_path.relative_to(Path.cwd()))
        _commit_plan(relpath, slug, amend=False)
        if session_id:
            state[session_id] = relpath
            _save_state(state)

    return 0


if __name__ == "__main__":
    sys.exit(main())
