# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Thunderbird extension (Manifest V3) that integrates [addy.io](https://addy.io/) / AnonAddy into the Thunderbird compose window. It adds an "Addy" button to the compose toolbar that lets users replace recipient addresses with their corresponding AnonAddy aliases before sending.

## Build

```bash
make              # produces AnonAddyTB.xpi (zip of JS/HTML/manifest/icon)
make clean        # remove built artifact
```

The Makefile intentionally fails if any unexpected files are present in the root directory.

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

The extension has four source files:

| File | Role |
|------|------|
| `background.js` | Service worker: fetches `domain-options` from the Addy API on an hourly alarm and re-fetches when options change; opens options page on first install if no API key |
| `api.js` | Single exported function `addyApiRequest(method, endpoint, params, body)` — reads `hostUrl`/`apiKey` from `messenger.storage.local`, calls the Addy REST API via XHR, returns parsed JSON |
| `composePopup.js` | Main popup logic: reads compose recipients, queries the Addy API for matching aliases per domain, renders dynamic HTML with checkboxes, then rewrites recipients using the AnonAddy forwarding address format (`local+original=domain@addydomain`) |
| `options.js` | Options page: saves `hostUrl` and `apiKey` to `messenger.storage.local`; requests optional host permission for self-hosted servers |

**Data flow:**
1. `background.js` pre-fetches and caches Addy domain options in `messenger.storage.local` (key: `domainOptions`).
2. `composePopup.js` reads cached domain options to filter out Addy-owned domains from recipients, then queries `GET /api/v1/aliases?filter[search]=<domain>` for each remaining domain.
3. User selects aliases; `fixRecipients()` transforms addresses to `local+original=domain@addydomain` forwarding format.
4. `messenger.compose.setComposeDetails()` applies the changes.

**Popup resize workaround:** `composePopup.js` uses a `messenger.alarms` loop to repeatedly nudge a hidden `#spacer` element for ~1 second after content renders. This forces Thunderbird to recalculate and correct the popup window size, working around a race condition in Thunderbird.

## Settings storage

All user settings live in `messenger.storage.local` under the key `options`:
- `options.apiKey` — Addy API token
- `options.hostUrl` — base URL for self-hosted servers (defaults to `https://app.addy.io`)
- `domainOptions` — cached response from `GET /api/v1/domain-options`
