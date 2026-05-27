from __future__ import annotations

import contextlib
import io
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "ai" / "settings" / "sync.py"
SPEC = importlib.util.spec_from_file_location("ai_settings_sync", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class AiSettingsSyncTests(unittest.TestCase):
    def test_render_codex_rewrites_prompt_tool_arg(self):
        shared = {
            "hooks": {
                "UserPromptSubmit": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": "python3 scripts/°base/ai/hooks/save-prompt/hook.py 'claude'",
                            }
                        ]
                    }
                ]
            }
        }

        rendered = MODULE.render_codex_hooks(shared)
        command = rendered["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]

        self.assertIn("'codex'", command)
        self.assertNotIn("'claude'", command)

    def test_render_codex_strips_async(self):
        shared = {
            "hooks": {
                "SessionStart": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": "python3 hook.py",
                                "async": True,
                            }
                        ]
                    }
                ]
            }
        }

        rendered = MODULE.render_codex_hooks(shared)
        hook = rendered["hooks"]["SessionStart"][0]["hooks"][0]

        self.assertNotIn("async", hook)

    def test_render_claude_keeps_permissions(self):
        shared = {
            "hooks": {},
            "permissions": {"allow": ["Bash(git status:*)"], "deny": ["Read(**/.env*)"]},
        }

        rendered = MODULE.render_claude(shared)

        self.assertEqual(rendered["permissions"]["allow"], ["Bash(git status:*)"])
        self.assertEqual(rendered["permissions"]["deny"], ["Read(**/.env*)"])

    def test_merge_unions_permissions_without_duplicates(self):
        base = {"permissions": {"allow": ["A", "B"], "deny": ["X"]}}
        incoming = {"permissions": {"allow": ["B", "C"], "deny": ["X", "Y"]}}

        merged = MODULE._merge(base, incoming)

        self.assertEqual(merged["permissions"]["allow"], ["A", "B", "C"])
        self.assertEqual(merged["permissions"]["deny"], ["X", "Y"])

    def test_merge_replaces_same_hook_identity(self):
        base = {
            "hooks": {
                "SessionStart": [
                    {"hooks": [{"command": "cmd"}], "matcher": "old", "extra": "old"}
                ]
            }
        }
        incoming = {
            "hooks": {
                "SessionStart": [
                    {"hooks": [{"command": "cmd"}], "matcher": "old", "extra": "new"}
                ]
            }
        }

        merged = MODULE._merge(base, incoming)

        self.assertEqual(merged["hooks"]["SessionStart"][0]["extra"], "new")

    def test_merge_preserves_missing_hook_fields_for_same_identity(self):
        base = {
            "hooks": {
                "SessionStart": [
                    {"hooks": [{"command": "cmd", "async": True}], "matcher": ""}
                ]
            }
        }
        incoming = {
            "hooks": {
                "SessionStart": [
                    {"hooks": [{"command": "cmd"}], "matcher": ""}
                ]
            }
        }

        merged = MODULE._merge(base, incoming)

        self.assertTrue(merged["hooks"]["SessionStart"][0]["hooks"][0]["async"])

    def test_rewrite_codex_feature_flag(self):
        text = "model = \"gpt-5\"\n[features]\ncodex_hooks = true\n\n[projects]\n"

        rewritten, changed = MODULE._rewrite_codex_feature_flag(text)

        self.assertTrue(changed)
        self.assertEqual(
            rewritten,
            "model = \"gpt-5\"\n[features]\nhooks = true\n\n[projects]\n",
        )

    def test_rewrite_codex_feature_flag_removes_deprecated_when_hooks_exists(self):
        text = "[features]\nhooks = true\ncodex_hooks = true\n"

        rewritten, changed = MODULE._rewrite_codex_feature_flag(text)

        self.assertTrue(changed)
        self.assertEqual(rewritten, "[features]\nhooks = true\n")

    def test_migrate_codex_feature_flag_yes_writes_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text("[features]\ncodex_hooks = true\n", encoding="utf-8")
            previous_input = getattr(MODULE, "input", None)
            MODULE.input = lambda _prompt: "y"
            out = io.StringIO()
            try:
                with contextlib.redirect_stdout(out):
                    status = MODULE._migrate_codex_feature_flag(path, True, True)
            finally:
                if previous_input is None:
                    delattr(MODULE, "input")
                else:
                    MODULE.input = previous_input

            self.assertEqual(status, 0)
            self.assertEqual(path.read_text(encoding="utf-8"), "[features]\nhooks = true\n")

    def test_migrate_codex_feature_flag_exit_prints_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            original = "[features]\ncodex_hooks = true\n"
            path.write_text(original, encoding="utf-8")
            previous_input = getattr(MODULE, "input", None)
            MODULE.input = lambda _prompt: "exit"
            out = io.StringIO()
            try:
                with contextlib.redirect_stdout(out):
                    status = MODULE._migrate_codex_feature_flag(path, True, True)
            finally:
                if previous_input is None:
                    delattr(MODULE, "input")
                else:
                    MODULE.input = previous_input

            self.assertEqual(status, 1)
            self.assertIn(str(path), out.getvalue())
            self.assertEqual(path.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
