# ai/scripts/tests

Tests for the Python helpers in [`ai/scripts/`](/Users/user/Documents/programming/Python/base/ai/scripts).

The local project environment for these helpers lives in [`ai/scripts/pyproject.toml`](/Users/user/Documents/programming/Python/base/ai/scripts/pyproject.toml).

## Run the whole test folder

From the repository root:

```bash
uv run --project ai/scripts python -m unittest discover -s ai/scripts/tests -v
```

## Run only `git_remote_fix`

From the repository root:

```bash
uv run --project ai/scripts python -m unittest ai.scripts.tests.test_git_remote_fix -v
```

## Run the test file directly

From the repository root:

```bash
uv run --project ai/scripts python ai/scripts/tests/test_git_remote_fix.py
```

## Run the interactive helper

From the repository root:

```bash
uv run --project ai/scripts python ai/scripts/git/remote/git_remote_fix.py
```

All commands assume `uv` will resolve dependencies from [`ai/scripts/pyproject.toml`](/Users/user/Documents/programming/Python/base/ai/scripts/pyproject.toml).
