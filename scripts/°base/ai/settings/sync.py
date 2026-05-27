#!/usr/bin/env python3
"""Synchronize Claude and Codex project settings through a neutral JSON file.

The neutral files under ``ai/tool-settings/`` are meant to be readable and
editable by humans. Native files remain editable too: this script imports
entries from both sides, unions them by stable identity, then renders the
native formats back out.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any


TRACKED_SHARED = Path("ai/tool-settings/settings.json")
LOCAL_SHARED = Path("ai/tool-settings/settings.local.json")
CLAUDE_SETTINGS = Path(".claude/settings.json")
CLAUDE_LOCAL = Path(".claude/settings.local.json")
CODEX_HOOKS = Path(".codex/hooks.json")
CODEX_LOCAL_HOOKS = Path(".codex/hooks.local.json")
CLAUDE_COMMANDS = Path(".claude/commands")
CODEX_COMMANDS = Path(".codex/commands")


def _git_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0 and result.stdout.strip():
        return Path(result.stdout.strip())
    return Path.cwd()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


def _hook_id(event: str, entry: dict[str, Any]) -> str:
    matcher = entry.get("matcher") or ""
    commands = []
    for hook in entry.get("hooks") or []:
        if isinstance(hook, dict):
            commands.append(_neutralize_command(hook.get("command") or ""))
    return "\0".join([event, matcher, "\0".join(commands)])


def _matcher_tokens(entry: dict[str, Any]) -> set[str]:
    matcher = str(entry.get("matcher") or "")
    return {part for part in matcher.split("|") if part} or {""}


def _entry_commands(entry: dict[str, Any]) -> set[str]:
    commands: set[str] = set()
    for hook in entry.get("hooks") or []:
        if isinstance(hook, dict):
            commands.add(_neutralize_command(str(hook.get("command") or "")))
    return commands


def _subsumes(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """True when entry ``a`` covers everything entry ``b`` covers."""
    return _matcher_tokens(a).issuperset(_matcher_tokens(b)) and _entry_commands(a).issuperset(_entry_commands(b))


def _overlay_entry(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(existing)
    for key, value in incoming.items():
        if key != "hooks":
            merged[key] = deepcopy(value)

    existing_hooks = merged.get("hooks") if isinstance(merged.get("hooks"), list) else []
    incoming_hooks = incoming.get("hooks") if isinstance(incoming.get("hooks"), list) else []
    hooks = []
    for index, hook in enumerate(incoming_hooks):
        if not isinstance(hook, dict):
            continue
        if index < len(existing_hooks) and isinstance(existing_hooks[index], dict):
            merged_hook = deepcopy(existing_hooks[index])
            merged_hook.update(deepcopy(hook))
            hooks.append(merged_hook)
        else:
            hooks.append(deepcopy(hook))
    if hooks:
        merged["hooks"] = hooks
    return merged


def _unique(values: list[Any]) -> list[Any]:
    seen: set[str] = set()
    out: list[Any] = []
    for value in values:
        key = json.dumps(value, sort_keys=True, ensure_ascii=False)
        if key in seen:
            continue
        seen.add(key)
        out.append(value)
    return out


def _normalize_native(data: dict[str, Any]) -> dict[str, Any]:
    hooks = deepcopy(data.get("hooks") or {})
    for entries in hooks.values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            for hook in entry.get("hooks") or []:
                if isinstance(hook, dict):
                    hook["command"] = _neutralize_command(str(hook.get("command") or ""))
    return {
        "version": 1,
        "hooks": hooks,
        "permissions": deepcopy(data.get("permissions") or {}),
    }


def _merge(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = _normalize_native(base)
    incoming = _normalize_native(incoming)

    hooks = deepcopy(merged.get("hooks") or {})
    for event, entries in (incoming.get("hooks") or {}).items():
        if not isinstance(entries, list):
            continue
        current = [deepcopy(entry) for entry in hooks.get(event, []) if isinstance(entry, dict)]
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            entry_id = _hook_id(event, entry)
            replaced = False
            for index, existing in enumerate(current):
                if _hook_id(event, existing) == entry_id:
                    current[index] = _overlay_entry(existing, entry)
                    replaced = True
                    break
            if replaced:
                continue
            if any(_subsumes(existing, entry) for existing in current):
                continue
            current = [existing for existing in current if not _subsumes(entry, existing)]
            by_id = {_hook_id(event, existing): existing for existing in current}
            by_id[entry_id] = deepcopy(entry)
            current = list(by_id.values())
        hooks[event] = current
    merged["hooks"] = hooks

    permissions = deepcopy(merged.get("permissions") or {})
    incoming_permissions = incoming.get("permissions") or {}
    for key in ("allow", "deny"):
        values = list(permissions.get(key) or [])
        values.extend(incoming_permissions.get(key) or [])
        permissions[key] = _unique(values)
    merged["permissions"] = permissions
    return merged


def _replace_tool_arg(command: str, tool: str) -> str:
    if "save-prompt/hook.py" in command or "save-decision/hook.py" in command:
        command = command.replace("'claude'", f"'{tool}'")
        command = command.replace('"claude"', f'"{tool}"')
    return command


def _normalize_command_path(command: str) -> str:
    command = command.replace("python3 .claude/hooks/permission-check.py", 'python3 "$(git rev-parse --show-toplevel)/.claude/hooks/permission-check.py"')
    return command


def _neutralize_command(command: str) -> str:
    command = _normalize_command_path(command)
    if "save-prompt/hook.py" in command or "save-decision/hook.py" in command:
        command = command.replace("'codex'", "'claude'")
        command = command.replace('"codex"', '"claude"')
    return command


def _render_hooks(shared: dict[str, Any], tool: str) -> dict[str, Any]:
    rendered: dict[str, Any] = {"hooks": {}}
    for event, entries in (shared.get("hooks") or {}).items():
        if not isinstance(entries, list):
            continue
        rendered_entries = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            new_entry = deepcopy(entry)
            hooks = []
            for hook in new_entry.get("hooks") or []:
                if not isinstance(hook, dict):
                    continue
                new_hook = deepcopy(hook)
                command = str(new_hook.get("command") or "")
                command = _normalize_command_path(_replace_tool_arg(command, tool))
                new_hook["command"] = command
                if tool == "codex":
                    new_hook.pop("async", None)
                hooks.append(new_hook)
            new_entry["hooks"] = hooks
            rendered_entries.append(new_entry)
        if rendered_entries:
            rendered["hooks"][event] = rendered_entries
    return rendered


def render_claude(shared: dict[str, Any]) -> dict[str, Any]:
    data = _render_hooks(shared, "claude")
    permissions = shared.get("permissions")
    if permissions:
        data["permissions"] = deepcopy(permissions)
    return data


def render_codex_hooks(shared: dict[str, Any]) -> dict[str, Any]:
    return _render_hooks(shared, "codex")


def _same_json(path: Path, data: dict[str, Any]) -> bool:
    if not path.is_file():
        return False
    return _read_json(path) == data


def _sync_commands(apply: bool) -> list[str]:
    changed: list[str] = []
    if not CLAUDE_COMMANDS.is_dir():
        return changed
    for src in sorted(CLAUDE_COMMANDS.glob("*.md")):
        dst = CODEX_COMMANDS / src.name
        if dst.is_file() and dst.read_bytes() == src.read_bytes():
            continue
        changed.append(str(dst))
        if apply:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
    return changed


def _load_layer(shared_path: Path, claude_path: Path, codex_path: Path) -> dict[str, Any]:
    shared = _read_json(shared_path)
    if shared:
        shared = _merge({}, shared)
    native_sources: list[tuple[float, dict[str, Any]]] = []
    for path in (claude_path, codex_path):
        if path.is_file():
            native_sources.append((path.stat().st_mtime, _read_json(path)))
    if not shared and native_sources:
        shared = _normalize_native(sorted(native_sources, key=lambda item: item[0])[-1][1])
    for _, data in sorted(native_sources, key=lambda item: item[0]):
        shared = _merge(shared, data)
    return shared or {"version": 1, "hooks": {}, "permissions": {"allow": [], "deny": []}}


def _apply_or_check(shared_path: Path, claude_path: Path, codex_path: Path, apply: bool) -> list[str]:
    changed: list[str] = []
    shared = _load_layer(shared_path, claude_path, codex_path)
    claude = render_claude(shared)
    codex = render_codex_hooks(shared)

    for path, data in (
        (shared_path, shared),
        (claude_path, claude),
        (codex_path, codex),
    ):
        if _same_json(path, data):
            continue
        changed.append(str(path))
        if apply:
            _write_json(path, data)

    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write synchronized files")
    parser.add_argument("--check", action="store_true", help="fail if files are out of sync")
    parser.add_argument("--explain", action="store_true", help="print changed paths")
    args = parser.parse_args(argv)

    os.chdir(_git_root())
    apply = args.apply and not args.check

    changed = []
    changed.extend(_apply_or_check(TRACKED_SHARED, CLAUDE_SETTINGS, CODEX_HOOKS, apply))
    if LOCAL_SHARED.is_file() or CLAUDE_LOCAL.is_file() or CODEX_LOCAL_HOOKS.is_file():
        changed.extend(_apply_or_check(LOCAL_SHARED, CLAUDE_LOCAL, CODEX_LOCAL_HOOKS, apply))
    changed.extend(_sync_commands(apply))

    if changed and (args.explain or args.check):
        print("AI tool settings are out of sync:")
        for path in changed:
            print(f"  {path}")
    if args.check and changed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
