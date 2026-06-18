# Developer Guide

This extension is built with TypeScript, Vue 3, Vite, and SCSS. Source code must be
submitted alongside XPI uploads to ATN following the source submission policy.

## Prerequisites

- Node.js 18 or newer
- npm (bundled with Node.js)
- GNU Make (standard on macOS/Linux; on Windows use WSL or Git Bash)

## Build

```bash
npm ci    # install exact versions from package-lock.json (first time or after updates)
make      # runs npm run build, copies static assets into dist/, zips to AnonAddyTB.xpi
```

The resulting `AnonAddyTB.xpi` is the file to install or submit.

## Development commands

```bash
npm run build           # rebuild dist/ (Vite)
npm run typecheck       # TypeScript type check (vue-tsc --noEmit)
npm run prettier:check  # check code formatting
npm run prettier:write  # auto-format all files
npm test                # run Vitest unit tests (one-shot)
npm run test:watch      # run Vitest in watch mode
make clean              # remove AnonAddyTB.xpi and dist/
```

## Testing

### Unit tests (Vitest)

No prerequisites beyond `npm ci`. Tests run in jsdom — no Thunderbird needed.

```bash
npm test                # run all tests and exit
npm run test:watch      # watch mode for development
```

Tests live in `src/tests/`. Shared fixture data (aliases, domain options, forwarding
cases) is in `tests/fixtures/` and is also used by the Marionette integration tests.

### Integration tests (Marionette)

Drives a real Thunderbird instance via the [Marionette](https://firefox-source-docs.mozilla.org/testing/marionette/) protocol. The addy.io API is replaced by a local mock HTTP server serving the fixture JSON — no real addy.io account needed.

**Prerequisites:**

- Python 3.11+ and [uv](https://docs.astral.sh/uv/)
- Thunderbird installed

**Run:**

```bash
# from repo root — builds the .xpi, then runs pytest
THUNDERBIRD_BIN=/usr/bin/thunderbird make test-marionette

# Flatpak install
THUNDERBIRD_BIN="flatpak run org.mozilla.Thunderbird" make test-marionette
```

Or manually:

```bash
cd tests/marionette
uv sync                                          # create .venv, install deps
THUNDERBIRD_BIN=/usr/bin/thunderbird uv run pytest -v

# Flatpak
THUNDERBIRD_BIN="flatpak run org.mozilla.Thunderbird" uv run pytest -v
```

`THUNDERBIRD_BIN` defaults to `thunderbird` (i.e. whatever is on `$PATH`). Multi-word
values like the flatpak form are handled correctly — the conftest splits them with
`shlex.split` before passing to `subprocess`.

**What it tests:**

- `test_popup.py` — toolbar button opens the popup, RecipientCard renders, Apply rewrites the To: field to forwarding format.
- `test_chip_menu.py` — right-click on an address pill shows the Addy submenu, selecting an existing alias works, creating a new alias POSTs to the mock server.

See `tests/marionette/README.md` for mock server endpoint details.

## Source archive for ATN submission

The source archive must contain only source files — no `node_modules/`, `dist/`, or
`AnonAddyTB.xpi`. Use git archive or equivalent:

```bash
git archive HEAD --format=zip -o AnonAddyTB-src.zip
```

Reviewers should be able to run `npm ci && make` to reproduce the exact XPI.

## Project structure

| Path                | Role                                                   |
| ------------------- | ------------------------------------------------------ |
| `src/options/`      | Options page — Vue 3 + TypeScript                      |
| `src/popup/`        | Compose popup — Vue 3 + TypeScript                     |
| `src/background/`   | Service worker (alarm-based cache refresh)             |
| `src/api/`          | XHR-based addy.io API client                           |
| `src/experiment/`   | WebExtension Experiment (address chip context menu)    |
| `src/composables/`  | Shared Vue composables (`useI18n`)                     |
| `src/types/`        | Ambient TypeScript declarations for `messenger` global |
| `_locales/en/`      | i18n message strings                                   |
| `options.html`      | Vite entry for options page                            |
| `composePopup.html` | Vite entry for compose popup                           |
| `Makefile`          | Build orchestration                                    |
