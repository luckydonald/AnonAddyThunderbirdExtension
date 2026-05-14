#!/usr/bin/env python3
"""PostToolUse hook for ExitPlanMode: snapshot the plan into
``ai/plans/NNN_slug.md`` (or ``ai/°base/plans/...`` inside the base meta-repo)
and commit just that new file.

Each ExitPlanMode call produces a new numbered file; revisions don't overwrite
prior plans, so the directory reads as a chronological log.
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
    """Read plan content from the ExitPlanMode tool_response.

    The harness writes the plan to a file and embeds the path in the response
    as "Your plan has been saved to: <path>".  We parse that path and read
    the file so we don't have to reproduce the full plan text in tool_input.
    """
    if tool_response is None:
        return ""
    if isinstance(tool_response, str):
        text = tool_response
    elif isinstance(tool_response, dict):
        raw = tool_response.get("content") or tool_response.get("result") or ""
        if isinstance(raw, list):
            text = "\n".join(
                item.get("text", "") for item in raw
                if isinstance(item, dict) and item.get("type") == "text"
            )
        else:
            text = str(raw)
    else:
        text = json.dumps(tool_response, ensure_ascii=False)

    m = re.search(r"Your plan has been saved to:\s*(\S+)", text)
    if not m:
        return ""
    plan_file = Path(m.group(1).strip())
    if plan_file.is_file():
        return plan_file.read_text(encoding="utf-8").strip()
    return ""


def _debug_dump(payload: dict) -> None:
    import tempfile
    dbg = Path(tempfile.gettempdir()) / "save-plan-debug.json"
    dbg.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    payload = read_payload()
    _debug_dump(payload)
    tool_input = payload.get("tool_input") or {}
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
