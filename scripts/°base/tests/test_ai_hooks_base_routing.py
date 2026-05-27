from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PROMPT_HOOK = ROOT / "scripts" / "°base" / "ai" / "hooks" / "save-prompt" / "hook.py"
PLAN_HOOK = ROOT / "scripts" / "°base" / "ai" / "hooks" / "save-plan" / "hook.py"
MEMORY_HOOK = ROOT / "scripts" / "°base" / "ai" / "hooks" / "record-memory" / "hook.py"


def run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )


def init_repo(repo: Path, origin: str) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    run_git(repo, "init")
    run_git(repo, "config", "user.email", "tester@example.com")
    run_git(repo, "config", "user.name", "Test User")
    run_git(repo, "remote", "add", "origin", origin)
    (repo / "README.md").write_text("test repo\n", encoding="utf-8")
    run_git(repo, "add", "README.md")
    run_git(repo, "commit", "-m", "init")


def run_hook(
    repo: Path,
    hook: Path,
    payload: dict,
    *args: str,
    extra_env: dict[str, str] | None = None,
) -> None:
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(repo)
    if extra_env:
        env.update(extra_env)
    result = subprocess.run(
        [sys.executable, str(hook), *args],
        cwd=repo,
        env=env,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"hook failed with {result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


def last_subject(repo: Path) -> str:
    return run_git(repo, "log", "-1", "--pretty=%s").stdout.strip()


class AiHooksBaseRoutingTests(unittest.TestCase):
    def test_codex_prompt_in_base_repo_with_only_origin_routes_and_prefixes(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "base"
            init_repo(repo, "https://luckydonald@github.com/luckydonald/base.git")

            run_hook(repo, PROMPT_HOOK, {"prompt": "Capture this prompt"}, "codex")

            self.assertEqual(
                (repo / "ai" / "°base" / "query.md").read_text(encoding="utf-8"),
                "› Capture this prompt\n\n",
            )
            self.assertFalse((repo / "ai" / "query.md").exists())
            self.assertEqual(last_subject(repo), "[base] ai: updated prompt")

    def test_codex_plan_in_base_repo_routes_and_prefixes(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "base"
            init_repo(repo, "https://luckydonald@github.com/luckydonald/base.git")
            session_id = f"test-{uuid.uuid4()}"

            run_hook(
                repo,
                PLAN_HOOK,
                {
                    "hook_event_name": "Stop",
                    "session_id": session_id,
                    "last_assistant_message": (
                        "<proposed_plan>\n"
                        "# Base Route Plan\n"
                        "Write the routed plan artifact.\n"
                        "</proposed_plan>"
                    ),
                },
            )

            plan_path = repo / "ai" / "°base" / "plans" / "001_base-route-plan.md"
            self.assertEqual(
                plan_path.read_text(encoding="utf-8"),
                "# Base Route Plan\nWrite the routed plan artifact.\n",
            )
            self.assertFalse((repo / "ai" / "plans").exists())
            self.assertEqual(last_subject(repo), "[base] ai: save plan 001_base-route-plan")

    def test_memory_in_base_repo_routes_and_prefixes(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "base"
            home = Path(tmp) / "home"
            init_repo(repo, "https://luckydonald@github.com/luckydonald/base.git")
            encoded = str(repo).replace("/", "-")
            src_dir = home / ".claude" / "projects" / encoded / "memory"
            src_dir.mkdir(parents=True)
            (src_dir / "note.md").write_text("remember this\n", encoding="utf-8")

            run_hook(
                repo,
                MEMORY_HOOK,
                {"hook_event_name": "SessionStart"},
                extra_env={"HOME": str(home)},
            )

            self.assertEqual(
                (repo / "ai" / "°base" / "memory" / "note.md").read_text(encoding="utf-8"),
                "remember this\n",
            )
            self.assertFalse((repo / "ai" / "memory").exists())
            self.assertEqual(last_subject(repo), "[base] ai: record memory note")

    def test_prompt_in_repo_named_base_with_different_origin_is_unprefixed(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "base"
            init_repo(repo, "https://github.com/example/consumer.git")

            run_hook(repo, PROMPT_HOOK, {"prompt": "Capture downstream prompt"}, "codex")

            self.assertEqual(
                (repo / "ai" / "query.md").read_text(encoding="utf-8"),
                "› Capture downstream prompt\n\n",
            )
            self.assertFalse((repo / "ai" / "°base" / "query.md").exists())
            self.assertEqual(last_subject(repo), "ai: updated prompt")


if __name__ == "__main__":
    unittest.main()
