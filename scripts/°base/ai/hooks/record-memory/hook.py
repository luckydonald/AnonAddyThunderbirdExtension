#!/usr/bin/env python3
"""Hardlink Claude memory files into the project tree and auto-commit them.

Source:  ~/.claude/projects/<encoded-subproject-path>/memory/<name>.md
Target:  <subproject>/ai/memory/<name>.md
         (or <base>/ai/°base/memory/<name>.md inside the base meta-repo)

Fires on:
  - PostToolUse(Write|Edit): sync the single file the tool just touched, if
    it lives inside the source memory dir.
  - SessionStart: bulk-sync every `*.md` under the source memory dir as a
    catch-up.

Linking strategy mirrors `scripts/°base/memories/hardlink_memories.sh` but for
single files: hardlink first, fall back to symlink when hardlinks aren't
supported (e.g. the project and Claude state live on different filesystems).
Bind mounts are skipped — they only make sense at directory granularity.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _lib import (  # noqa: E402
    _chdir_to_git_root,
    _is_inside_base_repo,
    _subproject_root,
    read_payload,
)


def _encoded_project_dir(subproject: Path) -> Path:
    """Claude Code stores per-project state at ~/.claude/projects/<encoded>/,
    where <encoded> is the absolute project path with `/` replaced by `-`."""
    encoded = str(subproject).replace("/", "-")
    return Path.home() / ".claude" / "projects" / encoded


def _memory_dirs(subproject: Path) -> tuple[Path, Path]:
    src = _encoded_project_dir(subproject) / "memory"
    rel = "ai/°base/memory" if _is_inside_base_repo(subproject) else "ai/memory"
    return src, subproject / rel


def _same_inode(a: Path, b: Path) -> bool:
    try:
        return a.stat().st_ino == b.stat().st_ino and a.stat().st_dev == b.stat().st_dev
    except OSError:
        return False


def _sync_file(src: Path, dst: Path) -> bool:
    """Make ``dst`` a hardlink (or symlink fallback) of ``src``.
    Returns True if something changed; False if already in sync."""
    if not src.is_file():
        # Source went away — remove dst so the working tree mirrors reality.
        if dst.is_symlink() or dst.exists():
            dst.unlink()
            return True
        return False

    if dst.is_symlink():
        try:
            if dst.resolve() == src.resolve():
                return False
        except OSError:
            pass
    elif dst.exists() and _same_inode(dst, src):
        return False

    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.is_symlink() or dst.exists():
        dst.unlink()

    try:
        os.link(src, dst)
    except OSError:
        # Cross-filesystem or other hardlink restriction → symlink fallback.
        os.symlink(src, dst)
    return True


def _sync_all(src_dir: Path, dst_dir: Path) -> list[str]:
    """Sync every `*.md` in src_dir into dst_dir, and remove any orphaned
    `*.md` files in dst_dir that no longer exist in src_dir."""
    changed: list[str] = []
    src_names: set[str] = set()
    if src_dir.is_dir():
        for src in sorted(src_dir.glob("*.md")):
            src_names.add(src.name)
            if _sync_file(src, dst_dir / src.name):
                changed.append(src.name)
    if dst_dir.is_dir():
        for dst in sorted(dst_dir.glob("*.md")):
            if dst.name in src_names:
                continue
            if _sync_file(src_dir / dst.name, dst):
                changed.append(dst.name)
    return changed


def _commit(dst_dir_rel: str, names: list[str]) -> None:
    if not names:
        return
    subprocess.run(["git", "add", "--", dst_dir_rel], capture_output=True)
    if len(names) == 1:
        msg = f"ai: record memory {Path(names[0]).stem}"
    else:
        head = ", ".join(Path(n).stem for n in names[:3])
        extra = f" (+{len(names) - 3} more)" if len(names) > 3 else ""
        msg = f"ai: record memories {head}{extra}"
    subprocess.run(["git", "commit", "--only", dst_dir_rel, "-m", msg], capture_output=True)


def _git_root() -> Path | None:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return Path(result.stdout.strip())


def main() -> int:
    if _git_root() is None:
        return 0
    subproject = _subproject_root()
    src_dir, dst_dir = _memory_dirs(subproject)
    _chdir_to_git_root()
    dst_dir_rel = str(dst_dir.relative_to(Path.cwd()))

    payload = read_payload()
    event = payload.get("hook_event_name") or ""

    if event == "PostToolUse":
        tool_input = payload.get("tool_input") or {}
        raw = tool_input.get("file_path") or ""
        if not raw:
            return 0
        src_file = Path(raw).resolve()
        try:
            rel = src_file.relative_to(src_dir.resolve())
        except (OSError, ValueError):
            return 0
        if _sync_file(src_file, dst_dir / rel):
            _commit(dst_dir_rel, [str(rel)])
        return 0

    # SessionStart (and any other event) — full catch-up sync.
    changed = _sync_all(src_dir, dst_dir)
    _commit(dst_dir_rel, changed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
