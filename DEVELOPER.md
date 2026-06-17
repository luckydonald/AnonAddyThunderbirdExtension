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
make clean              # remove AnonAddyTB.xpi and dist/
```

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
