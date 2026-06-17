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

| Path                       | Contents                                                                  |
| -------------------------- | ------------------------------------------------------------------------- |
| `src/api/index.ts`         | `addyApiRequest()` — XHR-based, reads `hostUrl`/`apiKey` from storage     |
| `src/api/types.ts`         | Addy API types (`Alias`, `DomainOptions`, `AliasFormat`, …)               |
| `src/background/index.ts`  | Alarm setup, domain-options + full alias list caching                     |
| `src/options/App.vue`      | Options: form state, permission-request flow, status banners              |
| `src/popup/App.vue`        | Popup: load → spinner → per-recipient cards → apply/close                 |
| `src/popup/components/`    | `RecipientCard`, `CreateAliasForm`, `LoadingSpinner`, `FooterBar`, …      |
| `src/types/messenger.d.ts` | Ambient `messenger` global (storage, compose, alarms, messengerUtilities) |

**Data flow:**

1. `background.js` on install, hourly alarm, or options change: fetches `GET /api/v1/domain-options` and paginates through `GET /api/v1/aliases`, storing both in `messenger.storage.local` (`domainOptions`, `aliasCache`).
2. Popup opens → reads cached data immediately (shows spinner during first-load), then re-fetches aliases for relevant domains from the API.
3. User selects or creates an alias per recipient. `applyAndClose()` transforms addresses to the `local+original=domain@addydomain` forwarding format and calls `messenger.compose.setComposeDetails()`.
4. Created aliases can be disabled (`PATCH /api/v1/aliases/{id}`) or deleted (`DELETE /api/v1/aliases/{id}`) from the popup.

**Popup resize workaround:** `App.vue` uses a `setTimeout` loop to nudge a hidden `#spacer` element for ~1 second after mount. This forces Thunderbird to recalculate popup window size (same race-condition fix as the original plain-JS popup).

## Settings storage

All user settings live in `messenger.storage.local`:

| Key             | Contents                                                            |
| --------------- | ------------------------------------------------------------------- |
| `options`       | `{ hostUrl, apiKey }` — set by options page                         |
| `domainOptions` | Cached `GET /api/v1/domain-options` response                        |
| `aliasCache`    | `{ aliases: Alias[], fetchedAt: number }` — all user aliases, paged |
