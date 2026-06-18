# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Thunderbird extension (Manifest V3) that integrates [addy.io](https://addy.io/) / AnonAddy into the Thunderbird compose window. It adds an "Addy" button to the compose toolbar that lets users replace recipient addresses with their corresponding AnonAddy aliases before sending.

## Build

```bash
npm install       # install dev dependencies (first time only)
make              # npm run build → dist/ → AnonAddyTB.xpi
make clean        # remove built artifact and dist/
```

All source is now TypeScript + Vue 3. Vite builds all entry points; the Makefile copies only non-built static assets (icon, manifest, license) then zips `dist/`.

## Formatting

Prettier is the only formatter. It runs as a CI check on PRs and pushes to `main`.

```bash
npx prettier --write .   # format all files
npx prettier --check .   # check only (what CI runs)
```

## Pre-commit hooks

Three hooks run on commit:

- **no-co-authored-by** — rejects `Co-Authored-By:` lines in commit messages
- **require-memory-delete-marker** — enforces a marker when memory files are deleted
- **ai-settings-sync** — checks that Claude/Codex settings files are in sync

These use `uv` / Python scripts under `scripts/°base/`.

## Architecture

All source lives under `src/`. Vite builds three entry points into `dist/`.

| Entry HTML / TS                    | Output                   | Role                                                                |
| ---------------------------------- | ------------------------ | ------------------------------------------------------------------- |
| `options.html` → `src/options/`    | `dist/options.html`      | Options page Vue app (host URL, API key, permission request)        |
| `composePopup.html` → `src/popup/` | `dist/composePopup.html` | Compose popup Vue app (alias selection, creation, disable/delete)   |
| `src/background/index.ts`          | `dist/background.js`     | Service worker: hourly cache refresh (domain-options + all aliases) |

**Key source directories:**

| Path                           | Contents                                                                  |
| ------------------------------ | ------------------------------------------------------------------------- |
| `src/api/index.ts`             | `addyApiRequest()` — XHR-based, reads `hostUrl`/`apiKey` from storage     |
| `src/api/types.ts`             | Addy API types (`Alias`, `DomainOptions`, `AliasFormat`, …)               |
| `src/background/index.ts`      | Alarm setup, domain-options + full alias list caching                     |
| `src/options/App.vue`          | Options: form state, permission-request flow, status banners              |
| `src/popup/App.vue`            | Popup: load → spinner → per-recipient cards → apply/close                 |
| `src/popup/components/`        | `RecipientCard`, `CreateAliasForm`, `LoadingSpinner`, `FooterBar`, …      |
| `src/types/messenger.d.ts`     | Ambient `messenger` global (storage, compose, alarms, messengerUtilities) |
| `src/experiment/`              | WebExtension Experiment API (`AddressChipMenu`) — XUL context menu        |
| `src/experiment/schema.json`   | Experiment schema declaring `AddressChipMenu` namespace                   |

**Data flow:**

1. `background.js` on install, hourly alarm, or options change: fetches `GET /api/v1/domain-options` and paginates through `GET /api/v1/aliases`, storing both in `messenger.storage.local` (`domainOptions`, `aliasCache`).
2. Popup opens → reads cached data immediately (shows spinner during first-load), then re-fetches aliases for relevant domains from the API.
3. User selects or creates an alias per recipient. `applyAndClose()` transforms addresses to the `local+original=domain@addydomain` forwarding format and calls `messenger.compose.setComposeDetails()`.
4. Created aliases can be disabled (`PATCH /api/v1/aliases/{id}`) or deleted (`DELETE /api/v1/aliases/{id}`) from the popup.

**Forwarding address format:** `aliasLocal+recipientLocal=recipientDomain@aliasDomain`. Example: alias `foo@anon.email`, recipient `bar@example.com` → To: field gets `foo+bar=example.com@anon.email`. This format is both written by `applyAndClose()` and parsed back by `parseForwardingAddress()` (so reopening the popup on an already-aliased message recovers the original recipient).

## Quirks

**Popup resize workaround:** `App.vue` uses a `setTimeout` loop to nudge a hidden `#spacer` element for ~1 second after mount. This forces Thunderbird to recalculate popup window size (same race-condition fix as the original plain-JS popup).

**Popup max-width:** `.popup` has both `min-width` and `max-width` set to `$window-min-width` (540 px). Without the `max-width`, Thunderbird opens the window wider than the CSS min, which gives the format-pills container so much room that `flex-wrap: wrap` never triggers.

## Experiment API (AddressChipMenu)

`src/experiment/implementation.js` is a privileged Mozilla JS file — **not bundled by Vite**. It is loaded directly by Thunderbird as a WebExtension Experiment. Key constraints and quirks:

- **`setTimeout`/`clearTimeout` are not in global scope.** Must import them:
  ```javascript
  var { setTimeout, clearTimeout } = ChromeUtils.importESModule(
    "resource://gre/modules/Timer.sys.mjs",
  );
  ```
  Without this import, any call to `clearTimeout` throws `ReferenceError` at runtime.

- **`composedPath()` vs `closest()` for shadow DOM.** Address pills are custom elements. Use `e.composedPath().find(el => el.tagName?.toLowerCase() === "mail-address-pill")` to find the pill across shadow-DOM boundaries. `closest()` does not cross shadow-DOM boundaries.

- **`popup.triggerNode`** is the XUL property set to the element that triggered a `<menupopup>`. Use it in `popupshowing` to distinguish the real pill context menu from unrelated popups (autocomplete, tooltips, etc.).

- **Thunderbird's `onPillPopupShowing` crash.** Thunderbird registers `onpopupshowing="onPillPopupShowing(event)"` on an ancestor element in `messengercompose.xhtml`. It fires (bubble phase) for every `menupopup` opening in the compose window and tries to find a `mail-address-pill` from `popup.triggerNode`. When our injected submenus open, their `triggerNode` is not a pill → `pill` is null → crash at `pill.hasAttribute(…)`. **Fix:** add a single bubbling `stopPropagation()` listener on the top-level `menuPopup` we inject; all descendant subpopups bubble through it, so one listener blocks them all without affecting the outer `emailAddressPillPopup` event:
  ```javascript
  menuPopup.addEventListener("popupshowing", (e) => e.stopPropagation());
  ```
  After this crash Thunderbird's popup system is left broken and no further context menus open at all — so fixing this crash also fixes "context menu doesn't appear on right-click" symptoms.

- **The experiment is NOT reloaded by Vite.** Changes to `src/experiment/implementation.js` require a manual extension reload in Thunderbird (Developer Tools → about:debugging, or reload the `.xpi`). The Vite dev server only covers the popup/options/background TS files.

## Settings storage

All user settings live in `messenger.storage.local`:

| Key             | Contents                                                            |
| --------------- | ------------------------------------------------------------------- |
| `options`       | `{ hostUrl, apiKey }` — set by options page                         |
| `domainOptions` | Cached `GET /api/v1/domain-options` response                        |
| `aliasCache`    | `{ aliases: Alias[], fetchedAt: number }` — all user aliases, paged |
