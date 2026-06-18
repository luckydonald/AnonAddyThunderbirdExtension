# Plan: Addy icon + pretty text on mail-address-pill

## Context

The compose window currently shows addy forwarding addresses in raw encoding (`alias+them=their-host.com@anon.my-mail.com`), which is hard for users to read. This plan adds two visual signals to `mail-address-pill` elements in the compose window:

1. **Colored Addy icon** — pill contains a proxied (forwarding-format) addy address
2. **Grayscale Addy icon** — pill contains a plain addy-domain address (not forwarding-encoded)
3. **Human-readable display for proxied pills**: `alias@anon.email → them@their-host.com`

Two text-decoration approaches are implemented as separate functions so they can be compared at runtime. Setting `displayName` on the pill is intentionally avoided — it would contaminate email headers.

---

## New / changed files

| File                                | Change                                                                                            |
| ----------------------------------- | ------------------------------------------------------------------------------------------------- |
| `src/shared/forwardingAddress.ts`   | **New** — pure forwarding-address logic, no non-type imports                                      |
| `src/popup/utils.ts`                | Re-export `parseForwardingAddress` + `buildForwardingAddress` from above                          |
| `src/experiment/pillDecoration.js`  | **New** — both decoration approaches + icon helpers, importable by tests                          |
| `src/tests/pill-decoration.test.js` | **New** — vitest tests for both approaches                                                        |
| `vite.config.ts`                    | Add `utils` entry → `dist/utils.js`                                                               |
| `src/experiment/implementation.js`  | Import from `pillDecoration.js`; import `parseForwardingAddress` via `ChromeUtils.importESModule` |

---

## Implementation

### 1. `src/shared/forwardingAddress.ts` (new)

Move `parseForwardingAddress` and `buildForwardingAddress` verbatim from `src/popup/utils.ts`. Both functions are pure — their only imports are `import type { ... }` lines that are erased at compile time, so the compiled JS has no runtime dependencies.

Update `src/popup/utils.ts` to re-export both from `../shared/forwardingAddress.js`.

### 2. Vite entry → `dist/utils.js`

In `vite.config.ts`:

- Add `utils: resolve(__dirname, "src/shared/forwardingAddress.ts")` to `rollupOptions.input`
- Extend `entryFileNames` to emit `utils.js` for this chunk (alongside the existing `background` case)
- Add `preserveEntrySignatures: "strict"` to `rollupOptions` to keep named exports intact

### 3. `src/experiment/pillDecoration.js` (new)

This file exports all DOM-manipulation helpers. `implementation.js` imports from it; tests import from it directly. No TB-specific globals used here — pure DOM only.

#### Selector list for text-node approach

```javascript
// Tried in order; first match wins. Discovered by inspecting TB's mail-address-pill shadow DOM.
const LABEL_SELECTORS = ["label", ".pill-label", "span", "[role='option']"];
```

#### `decoratePillViaTextNode(pill, displayText)`

- Access `pill.shadowRoot`; if absent, return false (not decorate-able)
- Find the label element using `LABEL_SELECTORS`
- Save `labelEl.textContent` in `pill.dataset.addyOrigText` before the first override (guard: only if attribute not yet set)
- Set `labelEl.textContent = displayText`
- Return true on success

Passing `null` as `displayText` restores from `pill.dataset.addyOrigText` and removes the dataset key.

#### `decoratePillViaCSSAdopted(pill, displayText)`

- Access `pill.shadowRoot`; if absent or `adoptedStyleSheets` unsupported, return false
- Set `pill.dataset.addyLabel = displayText` (the CSS reads this via `attr()`)
- On first call per pill (guard: check if our sheet is already in `adoptedStyleSheets`), build and attach a `CSSStyleSheet`:
    ```css
    :host::before {
        content: attr(data-addy-label);
        /* inherits font from host so the pill resizes naturally */
    }
    /* hide the native label so text doesn't double-render */
    label,
    .pill-label,
    span {
        visibility: hidden;
        width: 0;
    }
    ```
    Store the sheet in a module-level `WeakMap<shadowRoot, CSSStyleSheet>` to avoid duplicates.
- Return true on success

Passing `null` removes `pill.dataset.addyLabel` and removes the sheet from `adoptedStyleSheets`.

> **Note on the hide-native-label rule**: the `visibility: hidden; width: 0` rule needs to target exactly the right element, or it will hide too much. Tests will reveal whether the selector list matches TB's actual structure. Adjust selectors after first live test in TB.

#### `upsertPillIcon(pill, pillIconMap, iconUrl, proxied)`

- If `pillIconMap.has(pill)`, update `img.className` on the existing element; else create `<img>` and insert before pill in the DOM
- `proxied=true` → class `addy-pill-icon addy-proxied`; `false` → class `addy-pill-icon addy-aliased`
- Store img in `pillIconMap`

#### `removePillIcon(pill, pillIconMap)`

- Remove the img from the DOM and delete from `pillIconMap`

### 4. `src/experiment/implementation.js` changes

At the top of `getAPI(context)`:

```javascript
const { parseForwardingAddress } = ChromeUtils.importESModule(
    context.extension.baseURI.spec + "utils.js",
);
const {
    decoratePillViaTextNode,
    decoratePillViaCSSAdopted,
    upsertPillIcon,
    removePillIcon,
} = ChromeUtils.importESModule(
    context.extension.baseURI.spec + "experiment/pillDecoration.js",
);
```

Add `getAddyDomainSet()` inline helper (closes over `_cacheData`):

```javascript
function getAddyDomainSet() {
    return new Set(
        (_cacheData.domainOptions?.data || []).map((d) => d.toLowerCase()),
    );
}
```

#### `injectAddyPillStyles(doc)` (once per window)

Injects `<style id="addy-pill-styles">` for the icon:

```css
.addy-pill-icon {
    width: 12px;
    height: 12px;
    vertical-align: middle;
    margin-right: 3px;
    pointer-events: none;
}
.addy-pill-icon.addy-aliased {
    filter: grayscale(1) opacity(0.6);
}
```

#### `decoratePill(pill, doc, pillIconMap)`

```
email = pill.getAttribute("emailAddress") || ""
fwd = parseForwardingAddress(email, getAddyDomainSet())
domain = email match /@(.+)$/ → group 1

CASE fwd !== null (proxied):
  label = `${fwd.aliasEmail} → ${fwd.originalEmail}`
  decoratePillViaTextNode(pill, label)          ← approach A
  decoratePillViaCSSAdopted(pill, label)        ← approach B  (both active; compare in TB)
  upsertPillIcon(pill, pillIconMap, ICON_ADDY, true)

CASE domain in addyDomainSet (plain addy alias):
  decoratePillViaTextNode(pill, null)           ← restore
  decoratePillViaCSSAdopted(pill, null)         ← restore
  upsertPillIcon(pill, pillIconMap, ICON_ADDY, false)

DEFAULT:
  decoratePillViaTextNode(pill, null)
  decoratePillViaCSSAdopted(pill, null)
  removePillIcon(pill, pillIconMap)
```

> Running both approaches simultaneously in TB will show which one actually renders — whichever wins, the other can be deleted.

#### `attachToWindow(win)` additions

After existing setup, store `{ cleanup, doc, pillIconMap: new WeakMap() }` (update the `attached` Map value type). Then:

1. Call `injectAddyPillStyles(doc)`
2. Call `decorateAllPills(doc, pillIconMap)`
3. Set up `MutationObserver` on the recipients container (`subtree: true`):
    - `childList`: added `mail-address-pill` → `decoratePill()`; removed → `removePillIcon()`
    - `attributes` with `attributeFilter: ["emailaddress"]` on `mail-address-pill` → `decoratePill()`
4. Include `observer.disconnect()` in cleanup

#### `setCache(data)` addition

After `_cacheData = data`, re-run `decorateAllPills(win.doc, win.pillIconMap)` for all entries in `attached`.

---

## Tests — `src/tests/pill-decoration.test.js`

Style matches existing test files (vitest, jsdom, no external mocking library).

```javascript
import { describe, it, expect, beforeEach } from "vitest";
import {
    decoratePillViaTextNode,
    decoratePillViaCSSAdopted,
    upsertPillIcon,
    removePillIcon,
} from "../experiment/pillDecoration.js";
```

Helper:

```javascript
function makePill(shadowHtml = "<label>original@raw.com</label>") {
    const el = document.createElement("div");
    el.setAttribute("emailAddress", "alias+user=example.com@anon.email");
    const shadow = el.attachShadow({ mode: "open" });
    shadow.innerHTML = shadowHtml;
    document.body.appendChild(el);
    return el;
}
```

### `decoratePillViaTextNode`

- sets the label text to the provided display string
- stores original text in `dataset.addyOrigText` before first change
- does not overwrite `dataset.addyOrigText` on subsequent calls (idempotent save)
- restores original text when called with `null`
- removes `dataset.addyOrigText` after restoration
- returns `false` and does nothing when pill has no shadow root
- falls back through `LABEL_SELECTORS` and finds a `<span>` when no `<label>` present
- returns `false` when shadow root has no matching element at all

### `decoratePillViaCSSAdopted`

- sets `dataset.addyLabel` to the display string
- adds exactly one stylesheet to `shadowRoot.adoptedStyleSheets`
- the injected stylesheet contains `:host::before`
- does not add a duplicate sheet on a second call to the same pill
- clears `dataset.addyLabel` and removes the sheet when called with `null`
- returns `false` gracefully when `adoptedStyleSheets` is not supported (simulated by deleting the property from the shadow root)

### `upsertPillIcon` / `removePillIcon`

- `upsertPillIcon` inserts an `<img>` before the pill in the DOM
- img has class `addy-pill-icon addy-proxied` when `proxied=true`
- img has class `addy-pill-icon addy-aliased` when `proxied=false`
- calling `upsertPillIcon` again updates the img class without inserting a second img
- `removePillIcon` removes the img from the DOM and clears the WeakMap entry
- `removePillIcon` is a no-op when no icon exists for the pill

---

## Verification

1. `make` — build
2. Reload extension in TB (about:debugging)
3. Open compose, add a recipient, apply an alias
    - Pill should show colored Addy icon
    - One of the two text approaches will render `alias@anon.email → them@their-host.com` (the other may be invisible or double — that's the point of the comparison)
4. Manually type a plain addy-domain address → grayscale icon, unmodified text
5. Run `npx vitest run src/tests/pill-decoration.test.js` to verify unit tests pass
