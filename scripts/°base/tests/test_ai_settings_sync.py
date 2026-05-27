from __future__ import annotations

import importlib.util
import sys
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


if __name__ == "__main__":
    unittest.main()
