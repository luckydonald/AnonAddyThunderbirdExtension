# ai/scripts/tests

Tests for the Python helpers in [`ai/scripts/`](/Users/user/Documents/programming/Python/base/ai/scripts).

## Run the whole test folder

From the repository root:

```bash
./.venv/bin/python -m unittest discover -s ai/scripts/tests -v
```

## Run only `git_remote_fix`

From the repository root:

```bash
./.venv/bin/python -m unittest ai.scripts.tests.test_git_remote_fix -v
```

## Run the test file directly

From the repository root:

```bash
./.venv/bin/python ai/scripts/tests/test_git_remote_fix.py
```

All commands assume the repo-local virtualenv at `./.venv/`.
