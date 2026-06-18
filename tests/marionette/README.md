# Marionette Integration Tests

End-to-end tests that drive a real Thunderbird instance via the [Marionette](https://firefox-source-docs.mozilla.org/testing/marionette/) protocol. The addy.io API is replaced by a local mock server that serves fixture JSON from `tests/fixtures/`.

## Prerequisites

- **Python 3.11+** and **uv** installed
- **Thunderbird** installed (path defaults to `thunderbird` on `$PATH`)

## Running

```bash
cd tests/marionette
uv sync                                         # create .venv, install deps
THUNDERBIRD_BIN=/usr/bin/thunderbird uv run pytest -v
```

Or from the repo root:

```bash
THUNDERBIRD_BIN=/usr/bin/thunderbird make test-marionette
```

## How it works

1. `conftest.py` builds the `.xpi` via `make`, starts the mock HTTP server on a random port, then launches Thunderbird with `--marionette --no-remote` and a temporary profile.
2. The extension is installed as a temporary add-on (no signing required).
3. Extension storage is pre-populated with `{ hostUrl: "http://127.0.0.1:<port>", apiKey: "test-key" }` so all API calls hit the mock server.
4. Tests open compose windows, interact with the UI, and assert outcomes.

## Mock server endpoints

| Method | Path | Response |
|--------|------|----------|
| GET | `/api/v1/domain-options` | `tests/fixtures/domain-options.json` |
| GET | `/api/v1/aliases` | `tests/fixtures/aliases.json` (paginated) |
| POST | `/api/v1/aliases` | Constructed alias from request body |
| PATCH | `/api/v1/aliases/{id}` | `200 {}` |
| DELETE | `/api/v1/aliases/{id}` | `204` |

Recorded requests are available at `mock_server._Handler.recorded` for assertions.

## Fixtures

Shared with the Vitest unit tests — see `tests/fixtures/`. Both test layers test under identical data assumptions.
