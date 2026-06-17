# AnonAddyThunderbirdExtension Overhaul Plan

## Context

The extension is a plain-JS Thunderbird MV3 extension (4 JS files, 2 HTML files, simple Makefile zip build). The goal is a phased overhaul:

- **Phase 1** (this plan): Vue 3 + TypeScript + SCSS build system via Vite; options page rewrite with proper permission-request feedback.
- **Phase 2**: Compose popup full UI overhaul — domain picker, generation type, custom prefix, spinner animation, alias disable/delete, background alias caching.
- **Phase 3**: GitHub Actions release workflow for tagged XPI releases.
- **Phase 4**: Research and attempt compose-window address-field dropdown.

---

## Phase 1: Build System + Options Page

### 1. npm package changes

Update `package.json` — move `prettier` to `devDependencies`, add:

```json
"devDependencies": {
  "prettier": "^3.4.2",
  "vite": "^5.x",
  "@vitejs/plugin-vue": "^5.x",
  "vite-plugin-web-extension": "^3.x",
  "vue": "^3.x",
  "typescript": "^5.x",
  "sass": "^1.x",
  "vue-tsc": "^2.x",
  "@types/webextension-polyfill": "^0.x"
}
```

Add `scripts`:
```json
"scripts": {
  "build": "vite build",
  "typecheck": "vue-tsc --noEmit",
  "prettier:check": "prettier --check .",
  "prettier:write": "prettier --write ."
}
```

### 2. New file structure

Only the options page moves to `src/` in Phase 1. All other JS/HTML files stay at the root unchanged.

```
src/
  options/
    index.html        ← Vite entry HTML (replaces options.html)
    main.ts           ← createApp(App).mount('#app')
    App.vue           ← root: holds all state, coordinates form + banner
    components/
      OptionsForm.vue ← form inputs, save/reset buttons
      StatusBanner.vue← success/error/permission feedback
    styles/
      _variables.scss ← colour + spacing tokens
      _forms.scss     ← form element styles
  types/
    messenger.d.ts    ← ambient declare: `declare const messenger: typeof Browser`
vite.config.ts
tsconfig.json
```

### 3. `vite.config.ts` (root)

```ts
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import webExtension from "vite-plugin-web-extension";

export default defineConfig({
  plugins: [vue(), webExtension({ browser: "firefox" })],
  build: { outDir: "dist", emptyOutDir: true },
});
```

`vite-plugin-web-extension` reads `manifest.json` and derives all entry points automatically. Background, composePopup, and options all become entries.

### 4. `tsconfig.json` (root)

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "lib": ["ES2020", "DOM"],
    "strict": true,
    "jsx": "preserve",
    "jsxImportSource": "vue",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "baseUrl": ".",
    "paths": { "@/*": ["src/*"] }
  },
  "include": ["src/**/*.ts", "src/**/*.d.ts", "src/**/*.vue", "vite.config.ts"]
}
```

Root plain-JS files are excluded from type-checking (they stay as-is in Phase 1).

### 5. Makefile update

Replace the current strict-allowlist zip with a build-then-zip approach:

```makefile
target = AnonAddyTB.xpi

$(target): dist/
	cd dist && zip -r ../$(target) .

dist/: src/ manifest.json $(wildcard *.js) $(wildcard *.html) icon.svg
	npm run build

clean:
	-rm -f $(target)
	-rm -rf dist/
```

The old "extra files" guard is removed — Vite's explicit output takes over that role.

### 6. `manifest.json` changes

Only one line changes — point `options_ui.page` at the new Vite entry:

```json
"options_ui": {
  "page": "src/options/index.html"
}
```

Everything else (`background.scripts`, `compose_action.default_popup`, `host_permissions`, `optional_host_permissions`, `permissions`, `icons`) stays identical. The plugin rewrites the path in `dist/manifest.json` to the built output filename.

Note: The existing JS comment `// "default_locale": "en"` in manifest.json is fine — `vite-plugin-web-extension` uses a JSON5-tolerant parser.

### 7. Options page: Vue component design

#### State model (`App.vue`)

```ts
type SaveStatus =
  | { kind: "idle" }
  | { kind: "success" }
  | { kind: "error"; message: string }
  | { kind: "permission_denied"; hostUrl: string }
  | { kind: "permission_granted"; hostUrl: string };
```

Reactive state: `hostUrl`, `apiKey`, `savedHostUrl`, `savedApiKey`, `saveStatus`.  
Computed: `isDirty` (form differs from saved values).

#### `save()` flow in `App.vue`

1. Validate format (http/https, apiKey non-empty) → `{ kind: "error" }` and return on failure.
2. If `hostUrl` set, check if permission already granted via `messenger.permissions.contains`.
3. If not already granted, call `messenger.permissions.request({ origins: [hostUrl + "/"] })`.
   - Denied → set `{ kind: "permission_denied", hostUrl }`, **do not save**, return.
   - Granted → note that permission was just granted.
4. `await messenger.storage.local.set({ options: { hostUrl, apiKey } })`.
5. Set status: `permission_granted` if step 3 applied, else `success`.

This fixes the current bug in `options.js:48` where a permission denial silently returned without saving but also without clearly distinguishing "denied" vs. "first-time request needed".

#### `StatusBanner.vue` messages

| Status kind | Color | Message |
|---|---|---|
| `success` | green | "Settings saved." |
| `error` | red | `{message}` |
| `permission_denied` | amber | "Permission to access {hostUrl} was denied. Settings were not saved. Grant the host permission to use a custom server URL." |
| `permission_granted` | green | "Host permission for {hostUrl} granted. Settings saved." |

#### `OptionsForm.vue`

- Props: `hostUrl`, `apiKey`, `isDirty`, `saveStatus`
- Emits: `update:hostUrl`, `update:apiKey`, `save`, `reset`
- Save button disabled when not dirty or validation fails
- Reset button disabled when not dirty
- Uses `<style lang="scss" scoped>`

### 8. Files to delete in Phase 1

Delete `options.js` and `options.html` in the same commit that introduces `src/options/`. Manifest is updated simultaneously. Never leave both old and new options in place at the same time.

---

## Phase 2: Popup UI Overhaul + Background Caching

Migrate `composePopup.js/html` and `background.js` to `src/` as Vue + TypeScript.

### Popup features

- **Domain dropdown with search**: replace static default domain with `<select>` (or custom searchable dropdown component) populated from cached `domainOptions`.
- **Generation type picker**: radio-button group — `random_characters`, `random_words`, `random_male_name`, `random_female_name`, `random_noun`, `custom`.
- **Custom prefix field**: split-display input — `[ custom ] @example.com` rendered as a flex row where the domain suffix is a different-colored non-editable segment after the input box.
- **Existing alias list**: keep but improve UX (clearer labels, better selection state).
- **Allow disable/delete** of the alias just created (call `PATCH /api/v1/aliases/{id}` with `active: false`, or `DELETE /api/v1/aliases/{id}`).
- **Spinner**: CSS animation using `icon.svg` — scale+rotate keyframe loop imitating a Batman logo swirl transition (zooms in and out repeatedly), shown while loading.
- **"Go to addy.io" link**: use `options.hostUrl ?? "https://app.addy.io"` as the base URL.
- **Settings link**: open `messenger.runtime.openOptionsPage()`.
- **No recipients error**: replace generic text with "Add at least one address to the To/CC/BCC field first."
- **Fix checkboxes**: make alias selection behave like radio buttons per recipient (already partially done via `fixCheckboxes()` but needs visual polish).

### Background caching changes

- Extend `background.js` to also pre-fetch `GET /api/v1/aliases` (with pagination, storing all pages) and cache in `messenger.storage.local` under key `aliasCache`.
- Cache refreshes on the same 60-minute alarm that refreshes `domainOptions`.
- Popup reads from `aliasCache` on open, then triggers a fresh fetch in the background; UI updates reactively when storage changes (Vue watch on `messenger.storage.onChanged`).

---

## Phase 3: GitHub Actions Release Workflow

Add `.github/workflows/release.yml`:

- Trigger: `on: push: tags: ["v*"]`
- Steps: checkout → `npm ci` → `make` → upload `AnonAddyTB.xpi` as a GitHub Release asset.
- Release created via `gh release create ${{ github.ref_name }} AnonAddyTB.xpi`.
- Note in release body: "Unsigned — install manually via Thunderbird Add-on Manager > Install from file."

---

## Phase 4: Compose Window Address-Field Dropdown

Research whether Thunderbird's WebExtension API or content scripts allow injecting a context menu or dropdown into the individual email address "pill" widgets in the compose window address bar.

Approach:
1. Check `messenger.menus` API — it supports `compose_action` context, but not individual address fields.
2. Investigate whether a compose content script (via `content_scripts` with `matches: ["*"]` in compose windows) can reach the DOM of the address bar and inject a trigger element.
3. If feasible: implement the nested submenu structure from the spec (Existing > by-domain grouping, New > by-server > by-domain > by-generation-type, custom uses `prompt()` or a Thunderbird native dialog).
4. If not feasible with current Thunderbird APIs: document the limitation and defer.

---

## Verification

### Phase 1
1. `npm ci && npm run build` — `dist/` produced without errors.
2. `npm run typecheck` — no type errors.
3. `npx prettier --check .` — no formatting issues.
4. `make` — `AnonAddyTB.xpi` produced.
5. Install in Thunderbird (`Install from file`):
   - Open options: form loads with saved values.
   - Enter a self-hosted URL + API key → browser permission dialog appears.
   - Deny → amber banner shown, nothing saved.
   - Grant → green "permission granted + saved" banner.
   - Change API key only (no custom host) → saved without any permission dialog.
   - Reset → reverts to stored values.
   - Compose popup still works (composePopup unchanged).

### Phase 2
- Open compose window → popup spinner shows briefly, then content renders.
- Domain dropdown populates from cache; updates within 60 min alarm cycle.
- Generation type selection changes what gets sent to the API.
- Custom prefix field shows `[ text ] @domain.com` with correct styling.
- Created alias can be disabled/deleted from the popup.
- "Go to addy.io" link uses configured host.
- "Settings" link opens options page.

### Phase 3
- Push a `v0.1.0` tag → Actions run → Release created with `.xpi` attached.

### Phase 4
- Content script injection tested in Thunderbird compose window dev tools.
