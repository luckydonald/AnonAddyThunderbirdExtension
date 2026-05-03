#!/usr/bin/env python3
"""PermissionRequest hook: enforces git add and Co-Authored-By policies."""

import json
import shlex
import sys


def deny(reason):
    return {
        "hookSpecificOutput": {
            "hookEventName": "PermissionRequest",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def check_git_add(argv):
    """Return denial reason if git add targets all files, else None."""
    # argv[0] == 'git', argv[1] == 'add'
    flags_all = {"-A", "--all", "-u", "--update"}
    for arg in argv[2:]:
        if arg in flags_all:
            return (
                "Use explicit file paths with 'git add' — staging all files risks "
                "committing secrets or unintended changes. Instead of 'git add -A', "
                "list files explicitly."
            )
        if arg in (".", ":/"):
            return (
                "Use explicit file paths with 'git add' — staging all files risks "
                "committing secrets or unintended changes. Instead of 'git add .', "
                "list files explicitly."
            )
    return None


def collect_commit_messages(argv):
    """Parse git commit argv and return all message text to inspect."""
    messages = []
    i = 2
    while i < len(argv):
        arg = argv[i]
        # -m MSG or --message MSG or --message=MSG
        if arg in ("-m", "--message"):
            if i + 1 < len(argv):
                messages.append(argv[i + 1])
                i += 2
            else:
                i += 1
        elif arg.startswith("--message="):
            messages.append(arg[len("--message="):])
            i += 1
        # -F FILE or --file FILE or --file=FILE
        elif arg in ("-F", "--file"):
            if i + 1 < len(argv):
                path = argv[i + 1]
                i += 2
                if path == "-":
                    # stdin — cannot inspect
                    continue
                try:
                    with open(path) as f:
                        messages.append(f.read())
                except OSError:
                    pass
            else:
                i += 1
        elif arg.startswith("--file="):
            path = arg[len("--file="):]
            i += 1
            if path == "-":
                continue
            try:
                with open(path) as f:
                    messages.append(f.read())
            except OSError:
                pass
        else:
            i += 1
    return messages


def check_git_commit(argv):
    """Return denial reason if commit message contains Co-Authored-By, else None."""
    messages = collect_commit_messages(argv)
    combined = "\n".join(messages)
    if "co-authored-by:" in combined.lower():
        return (
            "Co-Authored-By attribution is not allowed. Remove the 'Co-Authored-By: ...' "
            "trailer from the commit message. Attribution is controlled via the "
            "'attribution' key in settings.json."
        )
    return None


def main():
    try:
        data = json.load(sys.stdin)
        tool_name = data.get("tool_name", "")
        if tool_name != "Bash":
            print("{}")
            return

        command = data.get("tool_input", {}).get("command", "")
        if not command:
            print("{}")
            return

        # Fast path: if the raw command string looks like a git commit and contains
        # Co-Authored-By (colon required, matching the trailer format), deny immediately
        # before shlex parsing. When the message is passed via a heredoc like
        # `git commit -m "$(cat <<'EOF'\n...\nEOF\n)"`, shlex parses successfully but
        # yields the unexpanded `$(...)` expression as the -m value — the actual message
        # text is invisible to collect_commit_messages. Scanning the raw command string
        # catches those cases because the heredoc body is present verbatim.
        stripped = command.strip()
        if "git commit" in stripped and "co-authored-by:" in stripped.lower():
            print(json.dumps(deny(
                "Co-Authored-By attribution is not allowed. Remove the 'Co-Authored-By: ...' "
                "trailer from the commit message. Attribution is controlled via the "
                "'attribution' key in settings.json."
            )))
            return

        try:
            argv = shlex.split(command)
        except ValueError:
            print("{}")
            return

        if len(argv) < 2 or argv[0] != "git":
            print("{}")
            return

        subcommand = argv[1]
        reason = None

        if subcommand == "add":
            reason = check_git_add(argv)
        elif subcommand == "commit":
            reason = check_git_commit(argv)

        if reason:
            print(json.dumps(deny(reason)))
        else:
            print("{}")
    except Exception:
        print("{}")


if __name__ == "__main__":
    main()