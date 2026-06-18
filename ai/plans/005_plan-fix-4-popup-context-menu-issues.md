# Plan: Fix 4 Popup/Context-Menu Issues

## Context

Four regressions/gaps reported after the previous session's work on alias matching, shared code,
and experiment bug fixes. Each has a concrete root cause identified via code inspection.

---

## Issue 1 — Horizontal scrollbar / not responsive

**Root cause:** `src/popup/App.vue` line 546 sets `min-width: $window-min-width` (540 px) on
`.popup`. When TB opens the window narrower than 540 px the div forces the body wider than the
viewport, producing a scrollbar.

**Fix (two files):**

`src/popup/App.vue` — remove the `min-width` line; keep `max-width` and `width: 100%`:
```scss
.popup {
  /* min-width: $window-min-width;  ← remove */
  max-width: $window-min-width;
  width: 100%;
  …
}
```

`src/popup/styles/main.scss` — add to `body`:
```scss
overflow-x: hidden;
```

---

## Issue 2 — Create-alias must open as its own TB window (not inline panel)

**Root cause:** Current `RecipientCard.vue` toggles a `showCreateForm` ref to show/hide an inline
`<CreateAliasForm>` panel. User wants `messenger.windows.create()` — a real separate popup window.

**New entry point:**
- `createAlias.html` — HTML shell (mirrors `composePopup.html`)
- `src/createAlias/main.ts` — Vue mount
- `src/createAlias/App.vue` — reads `?tabId=X&email=Y&name=Z` from URL, loads `domainOptions`
  from `messenger.storage.local`, renders `CreateAliasForm`, calls `addyApiRequest POST aliases`,
  then calls `applyAliasToCompose` (duplicate the same logic from `background/index.ts` or send
  a `runtime.sendMessage` to background), then `window.close()`.

**`vite.config.ts`** — add `createAlias: resolve(__dirname, "createAlias.html")` to rollup inputs.

**`RecipientCard.vue`** — replace the `showCreateForm` toggle block with a single emit:
```ts
emit("open-create-window", { email: editableAddress.value, name: props.name });
```
Remove the `CreateAliasForm` import, the `showCreateForm` ref, `watch(createdAlias)`, and the
`create-alias-panel` template block. Also remove `create` from the emits list.

**`App.vue`** — handle `open-create-window` from `RecipientCard`: open the window:
```ts
messenger.windows.create({
  url: messenger.runtime.getURL("createAlias.html")
    + `?tabId=${tabId}&email=${encodeURIComponent(email)}&name=${encodeURIComponent(name)}`,
  type: "popup",
  width: 520,
  height: 460,
});
```
Remove the `handleCreate` / `handleDisable` / `handleDelete` / `handleRestore` wiring that fed
`RecipientCard`'s `create` event (those now live in the create-alias window directly).

For background communication: the simplest path is to make the create-alias window call
`messenger.runtime.sendMessage({ action: "create_alias_and_apply", ... })` and add a handler in
`background/index.ts` that runs the same logic already present in the
`AddressChipMenu.onChipMenuClicked` `create_alias` branch. That keeps the API call and
`applyAliasToCompose` in one place.

---

## Issue 3 — Icons not visible in context menu

**Root cause:** The `chrome://messenger/skin/…` URLs used for `ICON_EXISTING` and `ICON_NEW` in
`src/experiment/implementation.js` do not exist in the user's TB version. The addy icon
(`context.extension.baseURI.spec + "icon.svg"`) is correct but may also not render on `<menu>`
nodes via `setAttribute("image", …)` in modern TB.

**Fix:** Replace chrome:// URLs with inline SVG data URIs. Also apply icons to format-item
`<menuitem>` elements (per `ai/initial.md`).

Icon set (all inline `data:image/svg+xml,…`):

| Constant | Description |
|---|---|
| `ICON_ADDY` | keep as `context.extension.baseURI.spec + "icon.svg"` — extension-owned, always valid |
| `ICON_EXISTING` | arrows/recycle SVG (reuse symbol) |
| `ICON_NEW` | plus/server SVG (new symbol) |
| `ICON_FMT_CHARS` | letter "A" SVG |
| `ICON_FMT_WORDS` | text-lines SVG |
| `ICON_FMT_MALE` | person SVG |
| `ICON_FMT_FEMALE` | person SVG (or alternative) |
| `ICON_FMT_NOUN` | tag SVG |
| `ICON_FMT_CUSTOM` | pencil SVG |

Apply via `setAttribute("image", ICON_…)` as already done; if that still doesn't render on
`<menu>`, also set `item.style.listStyleImage = "url('…')"` as a fallback.

---

## Issue 4 — Alias list empty in context menu after background restart

**Root cause:** `background/index.ts` line 123:
```ts
messenger.runtime.onStartup.addListener(() => {});
```
This is empty — it does nothing. `_cacheData` in `implementation.js` is module-level and resets
to `{ aliases: [], domainOptions: { … } }` every time the MV3 service worker restarts. `setCache`
is only called inside `refreshCache()`, which only runs on install, hourly alarm, or settings
change. After a plain TB restart, `_cacheData` stays empty until the next hourly tick.

**Fix in `src/background/index.ts`:**

Extract a `syncCacheToExperiment()` that reads stored data and calls `setCache` without doing
any API fetch:
```ts
async function syncCacheToExperiment(): Promise<void> {
  const storage = await messenger.storage.local.get({
    domainOptions: { data: [], defaultAliasDomain: "", defaultAliasFormat: "random_characters" },
    aliasCache: { aliases: [], fetchedAt: 0 },
  });
  try {
    messenger.AddressChipMenu.setCache({
      aliases: (storage.aliasCache as { aliases: Alias[] }).aliases,
      domainOptions: storage.domainOptions as DomainOptions,
    });
  } catch { /* non-fatal */ }
}
```

Call it in two places:
1. **Module top-level** (runs on every service-worker activation):
   ```ts
   void syncCacheToExperiment();
   ```
2. **`onStartup` listener** (belt-and-suspenders for TB restart):
   ```ts
   messenger.runtime.onStartup.addListener(() => { void syncCacheToExperiment(); });
   ```

Also call `syncCacheToExperiment()` inside `refreshCache()` (replace the inline `setCache` block
with a call to the extracted function) to keep one code path.

---

## Commit strategy

Four separate commits, one per issue, in order. Each commit message follows the `[extension] area: verb: description` style already in the log.

## Verification

- **Issue 1:** Build the extension, open the popup in a window narrower than 540 px (or resize
  the TB window); confirm no horizontal scrollbar.
- **Issue 2:** Click `+ Create alias` in the popup; confirm a separate TB window opens.
- **Issue 3:** Right-click an address pill in a compose window; confirm icons appear next to each
  menu entry.
- **Issue 4:** Restart TB (or reload the extension), right-click a pill, open "Existing…";
  confirm aliases are populated.
