# Plan: Automated Testing — Vitest + Marionette Python

## Context

No tests exist today. CI only runs Prettier. Two complementary layers are needed:
- **Vitest** — fast, in-process unit tests for pure logic and Vue components (no Thunderbird needed)
- **Marionette Python** — end-to-end chrome tests that drive a real Thunderbird instance

Both layers use a shared fixture directory so they test under identical assumptions. No real addy.io instance is needed: Vitest mocks `addyApiRequest` directly; Marionette spins up a local mock HTTP server that serves the same fixture JSON.

---

## Shared Fixtures: `tests/fixtures/`

All mock data lives here as JSON. Both JS (`import`) and Python (`json.load`) consume it.

```
tests/fixtures/
  aliases.json           # Alias[] — includes active/inactive, multiple domains,
                         # some with description matching "example.com"
  domain-options.json    # DomainOptions — a few domains, defaultAliasDomain, defaultAliasFormat
  compose-details.json   # { to: ["User <user@example.com>"], cc: [], bcc: [] }
  forwarding-cases.json  # pre-aliased addresses for round-trip parseForwardingAddress tests
                         # e.g. "alias+user=example.com@anonaddy.me"
```

Design the aliases fixture to cover:
- 3 active aliases whose description contains "example.com" (for `matchingAliases`)
- 2 aliases whose email contains "example.com" (for `matchingAliasesForEmail` in experiment)
- 1 inactive alias (should be filtered out)
- Aliases on two different addy domains (for grouped-submenu branch in experiment)

---

## Part 1: Vitest — Unit + Component Tests

### 1a. Extract pure functions

**`src/popup/utils.ts`** — extract from `App.vue` (`src/popup/App.vue:83`, `src/popup/App.vue:95`):
- `matchingAliases(aliases: Alias[], domain: string): Alias[]` — filters by description, caps at 10
- `parseForwardingAddress(email: string, addyDomainSet: Set<string>)` — parses `alias+local=domain@addydomain`
- `buildForwardingAddress(aliasEmail: string, originalEmail: string): string | null` — constructs `${aliasLocal}+${recipLocal}=${recipDomain}@${aliasDomain}`

**`src/experiment/utils.js`** — extract from `implementation.js` (`src/experiment/implementation.js:32`):
- `matchingAliasesForEmail(aliases, email)` — filters by email containing domain, caps at 20
  (Note: different logic from `matchingAliases` — tests must reflect this distinction)

`App.vue` and `implementation.js` import from their respective utils files. The experiment file stays `.js` since it runs in privileged Thunderbird context without a TS build step.

### 1b. Install Vitest

```bash
npm install -D vitest @vue/test-utils jsdom
```

**`vite.config.ts`** — add `test` block (Vitest reads the same config file):
```ts
test: {
  environment: 'jsdom',
  globals: true,
  setupFiles: ['./src/tests/setup.ts'],
}
```

**`package.json`** — add scripts:
```json
"test": "vitest run",
"test:watch": "vitest"
```

### 1c. Global mock: `src/tests/setup.ts`

Mock `globalThis.messenger` with `vi.fn()` stubs:
- `storage.local.get` / `set`
- `messengerUtilities.parseMailboxString`
- `compose.getComposeDetails` / `setComposeDetails`
- `runtime.openOptionsPage`
- `tabs.getCurrent`

Also mock `browser.i18n.getMessage` (used by `useI18n` in components).

### 1d. Test files

**`src/tests/popup-utils.test.ts`** — pure function tests, loads fixtures via `import`:
- `matchingAliases`: matches by description (case-insensitive), caps at 10, skips inactive
- `parseForwardingAddress`: parses forwarding cases from `forwarding-cases.json`; rejects non-addy domains, malformed input
- `buildForwardingAddress`: correct `aliasLocal+recipLocal=recipDomain@aliasDomain` output; null on bad input

**`src/tests/experiment-utils.test.js`** — unit tests for `matchingAliasesForEmail`:
- Matches by email containing domain (not description — different from popup logic)
- Skips inactive aliases
- Caps at 20
- Uses `aliases.json` fixture

**`src/tests/api.test.ts`** — tests for `addyApiRequest` (`src/api/index.ts`):
- Mock `globalThis.XMLHttpRequest` with a fake that resolves controlled status/text
- Mock `messenger.storage.local.get` with `{ options: { apiKey: "test-key", hostUrl: "http://localhost" } }`
- Tests: correct URL + query params, Bearer header present, 429 → `RateLimitError`, 4xx → `Error`, 2xx → parsed JSON

### 1e. CI: add `test.yml` GitHub Actions workflow

New `.github/workflows/test.yml` — runs on PR and push to main, Node 22, `npm ci && npm test`.

---

## Part 2: Marionette Python — Thunderbird Chrome Tests

### 2a. Structure

```
tests/
  fixtures/              ← shared fixture JSON (used by both JS and Python)
  marionette/
    pyproject.toml       # uv-managed project: marionette_driver, pytest as dependencies
    mock_server.py       # simple http.server that serves fixture JSON for addy API endpoints
    conftest.py          # session fixture: build xpi, start mock server, launch TB, yield client
    test_popup.py        # toolbar button → popup loads, alias shown, apply rewrites address
    test_chip_menu.py    # right-click pill → Addy submenu present; select existing alias;
                         # create alias (mock server records POST)
    README.md            # prereqs, THUNDERBIRD_BIN env var, how to run
```

### 2b. `mock_server.py`

A `threading.Thread`-based `http.server.HTTPServer` that handles:
| Endpoint | Method | Response |
|---|---|---|
| `/api/v1/domain-options` | GET | `domain-options.json` |
| `/api/v1/aliases` | GET | paginated aliases from `aliases.json` |
| `/api/v1/aliases` | POST | echo back a constructed `{ data: Alias }` using request body |
| `/api/v1/aliases/{id}` | PATCH | `200 {}` |
| `/api/v1/aliases/{id}` | DELETE | `204` |

Started in `conftest.py` before Thunderbird launches; port written to env so the fixture sets `hostUrl`.

### 2c. `conftest.py` session fixture

```python
@pytest.fixture(scope="session")
def tb(tmp_path_factory):
    # 1. subprocess.run(["make"], cwd=repo_root)  — build .xpi
    # 2. start mock_server on a random port
    # 3. create temp profile; write prefs to set hostUrl + apiKey
    # 4. subprocess.Popen([THUNDERBIRD_BIN, "--marionette", "--no-remote",
    #        "--profile", profile_dir])
    # 5. client = Marionette(host="localhost", port=2828); client.start_session()
    # 6. client.addon_install(xpi_path, temp=True)
    # 7. yield client
    # 8. teardown: client.cleanup(); proc.terminate(); server.shutdown()
```

Extension `options` storage is set via a startup script injected through Marionette before tests run, pointing `hostUrl` to the mock server.

### 2d. `test_popup.py`

1. Open compose window (File → New Message via chrome menu or `messenger.compose.beginNew()`).
2. Add `user@example.com` to the To: field.
3. Click the Addy toolbar button (find by `id="addy-button"` or similar from manifest).
4. Switch context to the popup window.
5. Assert: `RecipientCard` renders — card for `user@example.com` is visible.
6. Select one of the existing aliases (from `aliases.json`).
7. Click Apply. Assert compose To: field now contains the forwarding address.

### 2e. `test_chip_menu.py`

1. Open compose, add `user@example.com` as a pill.
2. Right-click the pill. Assert: "Use Addy alias for sending" menu item appears.
3. Hover "Existing…" submenu. Assert: alias emails from fixture appear.
4. Click one alias. Assert: no error; `onChipMenuClicked` fires with `action: "select_alias"`.
   (Verified by checking compose address via `messenger.compose.getComposeDetails`.)
5. Right-click again → "New…" → "Characters". Assert: POST recorded by mock server;
   compose address rewritten to forwarding format.

### 2f. Running locally

```bash
cd tests/marionette
uv sync                                        # creates .venv, installs from pyproject.toml
THUNDERBIRD_BIN=/usr/bin/thunderbird uv run pytest -v
```

Marionette tests are **not added to CI** initially — they need a real Thunderbird binary and display. A `Makefile` target `make test-marionette` documents the invocation.

---

## Files to create / modify

| Action | Path |
|---|---|
| **Create** | `tests/fixtures/aliases.json` |
| **Create** | `tests/fixtures/domain-options.json` |
| **Create** | `tests/fixtures/compose-details.json` |
| **Create** | `tests/fixtures/forwarding-cases.json` |
| **Create** | `src/popup/utils.ts` |
| **Create** | `src/experiment/utils.js` |
| **Modify** | `src/popup/App.vue` — import from `utils.ts` |
| **Modify** | `src/experiment/implementation.js` — import from `utils.js` |
| **Modify** | `vite.config.ts` — add `test` block |
| **Modify** | `package.json` — add `test` / `test:watch` scripts |
| **Create** | `src/tests/setup.ts` |
| **Create** | `src/tests/popup-utils.test.ts` |
| **Create** | `src/tests/experiment-utils.test.js` |
| **Create** | `src/tests/api.test.ts` |
| **Create** | `.github/workflows/test.yml` |
| **Create** | `tests/marionette/pyproject.toml` |
| **Create** | `tests/marionette/mock_server.py` |
| **Create** | `tests/marionette/conftest.py` |
| **Create** | `tests/marionette/test_popup.py` |
| **Create** | `tests/marionette/test_chip_menu.py` |
| **Modify** | `Makefile` — add `test-marionette` target |

---

## Verification

```bash
npm test                               # all Vitest tests pass
npm run typecheck                      # no type errors after extracting utils.ts
cd tests/marionette && THUNDERBIRD_BIN=... uv run pytest -v   # Marionette suite passes with mock server
```
