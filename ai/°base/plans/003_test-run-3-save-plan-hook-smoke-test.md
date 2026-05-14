# Test run 3: save-plan hook smoke test

Verifying that the fixed `save-plan` hook correctly reads the plan content
from the ExitPlanMode `tool_response` ("Your plan has been saved to: <path>")
and commits it to `ai/°base/plans/003_*.md`.

No code changes needed — pure hook integration test.
