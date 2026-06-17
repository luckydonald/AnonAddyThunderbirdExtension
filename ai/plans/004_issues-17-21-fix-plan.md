# Issues 17–21 fix plan

## Context

Issues 11–16 are complete (commits `ca58735`–`bb293c6`). The error log at `ai/errors/9.log` revealed that the context menu injection (issue 12) still does not work — and **why**: the pill IS found (`composedPath()` now surfaces it), `popupshowing` fires with the correct `triggerNode`, but `ReferenceError: clearTimeout is not defined` at `implementation.js:316` crashes inside `onPopupShowing` BEFORE the menu injection code runs. This is the actual remaining context-menu bug, filed here as a follow-up alongside five new issues (17–21).

---

## Issue 12 follow-up — `clearTimeout` not defined in experiment context

**Root cause**: The experiment JS runs in a Mozilla privileged JS context where the browser globals `setTimeout`/`clearTimeout` are NOT in scope. Three crash points in the log:
- line 289 (`onContextMenu`) — non-fatal, `pendingPill` was already set before it
- line 316 (`onPopupShowing`) — **fatal**: crashes before `buildAddyMenu`/`popup.appendChild` run → no menu injected
- line 340 (cleanup) — cleanup doesn't fire properly

**Fix** (`src/experiment/implementation.js`, after the `ChromeUtils.importESModule` for `ExtensionCommon` at top of file):
```javascript
const { setTimeout, clearTimeout } = ChromeUtils.importESModule(
  "resource://gre/modules/Timer.sys.mjs",
);
```
No other logic changes needed — the pill detection and triggerNode guard are already correct.

---

## Issue 17 — "Sends as:" shows forwarding address instead of outward-facing alias

**Root cause** (`CreateAliasForm.vue:67-72`): `sendsAsPreview` is built from `forwardingPreview` (the full SMTP forwarding address `local+orig=domain@aliasdomain`). The user wants "Sends as:" to show only the alias email (`local@aliasdomain`), optionally wrapped with the display name.

**Fix** (`src/popup/components/CreateAliasForm.vue`):
- Add new computed `aliasEmail`:
  ```typescript
  const aliasEmail = computed(() => `${aliasLocalPreview.value}@${domain.value}`);
  ```
- Update `sendsAsPreview` to use `aliasEmail` instead of `forwardingPreview`:
  ```typescript
  const sendsAsPreview = computed(() => {
    if (!forwardingPreview.value) return null;
    return props.targetName
      ? `${props.targetName} <${aliasEmail.value}>`
      : aliasEmail.value;
  });
  ```

---

## Issue 18 — Punycode domains: show both ASCII and unicode form in dropdown

**Fix**:

1. Install `punycode` npm package (tiny, ~3.5 KB): `npm install punycode`

2. In `src/popup/components/CreateAliasForm.vue`, add import and helper:
   ```typescript
   import { toUnicode } from "punycode/";

   function domainLabel(d: string): { ascii: string; unicode: string | null } {
     if (!d.includes("xn--")) return { ascii: d, unicode: null };
     const uni = toUnicode(d);
     return { ascii: d, unicode: uni !== d ? uni : null };
   }
   ```

3. Combobox trigger: show unicode form when present:
   ```vue
   <span>{{ domainLabel(domain).unicode ?? domain }}</span>
   ```

4. Combobox option `li`: show both forms:
   ```vue
   <li v-for="(d, i) in filteredDomains" ...>
     <span>{{ domainLabel(d).unicode ?? d }}</span>
     <span v-if="domainLabel(d).unicode" class="combobox__option-ascii">{{ d }}</span>
   </li>
   ```
   Add `.combobox__option-ascii { font-size: $font-size-sm; color: $color-muted; margin-left: $spacing-xs; }` to the SCSS.

---

## Issue 19 — Selected alias + "Don't replace" disappear during search

**Root cause** (`RecipientCard.vue`): "Don't replace" lives inside the `v-else` block that only shows when `searchResults.length === 0`. When search is active the entire normal list (including the current selection and Don't replace) is hidden.

**Fix** (`src/popup/components/RecipientCard.vue`):

1. Add `pinnedAlias` computed — returns the currently selected alias object when it is NOT already in `searchResults`:
   ```typescript
   const pinnedAlias = computed(() => {
     if (!props.selectedAlias || !aliasSearch.value.trim()) return null;
     if (searchResults.value.some((a) => a.email === props.selectedAlias)) return null;
     if (props.createdAlias?.email === props.selectedAlias)
       return { id: props.createdAlias.id, email: props.createdAlias.email, active: props.createdAlias.active };
     return props.allAliases.find((a) => a.email === props.selectedAlias) ?? null;
   });
   ```

2. In the template:
   - Move "Don't replace" `<label>` **out** of the `v-else` block so it sits after both conditional list divs, shown with:
     `v-if="createdAlias || displayAliases.length > 0 || selectedAlias !== null"`
   - In the search-results list, prepend a pinned row for `pinnedAlias` (when non-null) above the `v-for` results, styled `selected alias-option--pinned` with a `tag--selected` badge.

3. Add `.tag--selected` SCSS (same blue as `tag--new`).

---

## Issue 20 — Format chips don't wrap

**Root cause**: `.popup` has `min-width: 540px` but no `max-width`. Thunderbird opens the popup at whatever size it chooses; `.popup` grows to fill it. When the window is wider than ~450 px the `.format-pills` container has enough room that `flex-wrap: wrap` never triggers.

**Fix** (`src/popup/App.vue` `<style>`):
```scss
.popup {
  min-width: $window-min-width;
  max-width: $window-min-width;   // add
  width: 100%;                    // add
  box-sizing: border-box;         // add
  ...
}
```
The `flex-wrap: wrap` on `.format-pills` and `white-space: nowrap` on each pill are already correct — the only missing piece was the width cap.

---

## Commit order (one per issue, lplp-pipbuck)

1. `[extension] experiment: ai: Run: Fix clearTimeout — import Timer from Mozilla's Timer module.`
2. `[extension] popup: ai: Run: Fix "Sends as:" to show outward-facing alias address.`
3. `[extension] popup: ai: Run: Show unicode form alongside punycode domain labels.`
4. `[extension] popup: ai: Run: Keep selected alias and "Don't replace" visible during search.`
5. `[extension] popup: ai: Run: Cap popup max-width so format pills can wrap.`

---

## Verification

- **Issue 12 fix**: Reload extension, right-click address pill → "Use Addy alias for sending" menu appears; no `clearTimeout` error in console.
- **Issue 17**: Open alias form, enter recipient with display name → "Sends as:" shows `Name <alias@domain>`. Without display name → shows plain `alias@domain`.
- **Issue 18**: On domain dropdown with a `xn--` domain, the dropdown option shows the unicode form with the punycode form alongside. Trigger button also shows unicode form.
- **Issue 19**: Type in search box, select a result → selected alias stays pinned at top + "Don't replace" always visible below the list.
- **Issue 20**: Open compose popup → resize Thunderbird window narrower → format chips wrap to a second line.
