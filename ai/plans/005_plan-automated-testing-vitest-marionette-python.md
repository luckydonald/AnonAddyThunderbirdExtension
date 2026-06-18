# Plan: Automated Testing — Vitest + Marionette Python

## Context

No tests exist today. CI only runs Prettier. Two complementary layers are needed:
- **Vitest** — fast, in-process unit tests for pure logic and Vue components (no Thunderbird needed)
- **Marionette Python** — end-to-end chrome tests that drive a real Thunderbird instance

---

## Part 1: Vitest — Unit + Component Tests

### 1a. Extract pure functions from App.vue → `src/popup/utils.ts`

Three functions in `App.vue` are pure and highly testable, but currently trapped inside `<script setup>` and therefore unexportable. Extract them:

| Function | Signature | Where used |
|---|---|---|
| `matchingAliases` | `(aliases: Alias[], domain: string) => Alias[]` | `App.vue` buildRecipients, refreshAliasesInBackground |
| `parseForwardingAddress` | `(email: string, addyDomainSet: Set<string>) => {originalEmail, aliasEmail} \| null` | `App.vue` buildRecipients |
| `buildForwardingAddress` | `(aliasEmail: string, originalEmail: string) => string \| null` | currently inline in `applyAndClose()` — the `${am[1]}+${om[1]}=${om[2]}@${am[2]}` construct |

`App.vue` imports and calls them from `utils.ts`. All three have no side effects and no `messenger` dependency.

### 1b. Install Vitest

```bash
npm install -D vitest @vue/test-utils jsdom
```

`vite.config.ts` — add `test` block (Vitest reads the same config file):
```ts
test: {
  environment: 'jsdom',
  globals: true,
  setupFiles: ['./src/tests/setup.ts'],
}
```

`package.json` — add scripts:
```json
"test": "vitest run",
"test:watch": "vitest"
```

### 1c. Global mock: `src/tests/setup.ts`

Mock `globalThis.messenger` with jest-compatible `vi.fn()` stubs for:
- `storage.local.get` / `set`
- `messengerUtilities.parseMailboxString`
- `compose.getComposeDetails` / `setComposeDetails`
- `runtime.openOptionsPage`
- `tabs.getCurrent`

Also mock `globalThis.browser` (same shape — some Vite imports use it).

### 1d. Test files

**`src/tests/popup-utils.test.ts`** — unit tests for the three extracted functions:
- `matchingAliases`: matches by description substring (case-insensitive), caps at 10, skips inactive
- `parseForwardingAddress`: parses `alias+local=domain@addydomain`, rejects non-addy domains, rejects malformed
- `buildForwardingAddress`: produces correct `aliasLocal+recipLocal=recipDomain@aliasDomain` format, returns null on bad input

**`src/tests/api.test.ts`** — tests for `addyApiRequest` (`src/api/index.ts`):
- Mock `globalThis.XMLHttpRequest` with a fake that resolves with controlled status/text
- Mock `messenger.storage.local.get` to return a known `apiKey` / `hostUrl`
- Test: correct URL construction, Bearer header, 429 → `RateLimitError`, 4xx → `Error`, 2xx → parsed JSON

### 1e. CI: add `test.yml` GitHub Actions workflow

New file `.github/workflows/test.yml` — runs on PR and push to main, Node 22, `npm ci && npm test`.

---

## Part 2: Marionette Python — Thunderbird Chrome Tests

### 2a. Structure

```
tests/marionette/
  requirements.txt     # marionette_driver, pytest
  conftest.py          # pytest fixture: build xpi, launch Thunderbird, yield Marionette client
  test_popup.py        # open compose, click Addy button, verify popup loads
  README.md            # prereqs: Thunderbird binary, THUNDERBIRD_BIN env var
```

### 2b. `conftest.py` fixture

```python
@pytest.fixture(scope="session")
def marionette():
    # 1. subprocess.run(["make"], cwd=repo_root) — build the .xpi
    # 2. Create a temp profile dir
    # 3. subprocess.Popen(["thunderbird", "--marionette", "--no-remote",
    #        "--profile", profile_dir]) — respects THUNDERBIRD_BIN env var
    # 4. marionette_driver.Marionette(host="localhost", port=2828)
    #    client.start_session()
    # 5. Install extension: client.addon_install(xpi_path)
    # 6. yield client
    # 7. teardown: client.cleanup(); proc.terminate()
```

### 2c. `test_popup.py`

1. Open a compose window via `client.execute_script("openComposeWindow()")` or by driving the menu (File → New Message) via `find_element` on the chrome.
2. Switch context to the compose window.
3. Add a To: address (`user@example.com`) via the compose field.
4. Find and click the Addy toolbar button (identified by its `id` or `class` from `manifest.json`'s `browser_action`).
5. Switch context to the popup window (`moz-extension://…/composePopup.html`).
6. Assert: either `LoadingSpinner` visible briefly, or `RecipientCard` renders (shows `user@example.com`).

### 2d. Running locally

```bash
cd tests/marionette
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
THUNDERBIRD_BIN=/usr/bin/thunderbird pytest -v
```

Marionette tests are **not added to CI** initially — they need a real Thunderbird binary and display (Xvfb). A `Makefile` target `make test-marionette` will document the invocation.

---

## Files to create / modify

| Action | Path |
|---|---|
| **Create** | `src/popup/utils.ts` |
| **Modify** | `src/popup/App.vue` — import from utils.ts |
| **Modify** | `vite.config.ts` — add `test` block |
| **Modify** | `package.json` — add `test` / `test:watch` scripts |
| **Create** | `src/tests/setup.ts` |
| **Create** | `src/tests/popup-utils.test.ts` |
| **Create** | `src/tests/api.test.ts` |
| **Create** | `.github/workflows/test.yml` |
| **Create** | `tests/marionette/requirements.txt` |
| **Create** | `tests/marionette/conftest.py` |
| **Create** | `tests/marionette/test_popup.py` |
| **Modify** | `Makefile` — add `test-marionette` target |

---

## Verification

```bash
npm test                          # all Vitest tests pass
npm run typecheck                 # no type errors after extracting utils.ts
THUNDERBIRD_BIN=... pytest tests/marionette/ -v   # Marionette suite passes
```
