# Issues 11–16 fix plan

## Context

After the merge of Batch 2 commits, six issues remain. Each is filed separately; some are trivially small and some need care.

---

## Issue 11 — "Sends via:" hidden when recipient has no display name

**Root cause**: `CreateAliasForm.vue:201` has `v-if="forwardingPreview && targetName"`. The `&&
targetName` gate hides the forwarding-address row when there is no display name — at which point the two rows show identical content, so the previous implementor removed one. The user wants both rows always visible.

**Fix** (`src/popup/components/CreateAliasForm.vue`):

- Line 201: change `v-if="forwardingPreview && targetName"` → `v-if="forwardingPreview"`.

---

## Issue 12 — Context menu injection still not working

**Diagnosis**: `implementation.js` has no syntax errors (the summary's "duplicate `const menuPopup`" claim was wrong — the file is clean). The code paths look correct. The most likely failure modes are:

1. `e.composedPath()` returns an array that doesn't include `mail-address-pill` in this chrome context (either shadow mode difference or Thunderbird version quirk).
2. `onPopupShowing` fires for a non-context menupopup first (autocomplete, tooltip, etc.) which consumes `pendingPill`, so when the real context menupopup fires `pendingPill` is already null.

**Fix** (`src/experiment/implementation.js`):

- In `onContextMenu`: add a `console.log` showing the composedPath tag names so the user can verify the pill is being found. Also add fallback: after the `composedPath().find(...)`, if `pill` is null AND `e.target?.tagName?.toLowerCase() === "mail-address-pill"`, use `e.target` directly.

    ```javascript
    let pill =
        e
            .composedPath()
            .find(
                (el) =>
                    el.tagName &&
                    el.tagName.toLowerCase() === "mail-address-pill",
            ) ?? null;
    // Fallback for cases where composedPath doesn't surface the host element.
    if (!pill && e.target?.tagName?.toLowerCase() === "mail-address-pill") {
        pill = e.target;
    }
    ```

- In `onPopupShowing`: guard against consuming `pendingPill` for unrelated menupopups by checking `popup.triggerNode`. For a right-click context menu the triggerNode is set to the clicked element; for autocomplete popups it is typically null or a text input. Add:

    ```javascript
    // Only inject into the context menu triggered by our pill.
    const trigger = popup.triggerNode;
    if (trigger) {
        // composedPath-safe containment: check whether the trigger is the pill or
        // is inside it (open shadow DOM).
        const inPill =
            trigger === pendingPill ||
            pendingPill.contains(trigger) ||
            trigger.getRootNode?.()?.host === pendingPill;
        if (!inPill) return; // don't consume pendingPill; keep it for the real popup
    }
    ```

    If `triggerNode` is null (rare cases) we fall through and inject anyway (unchanged behaviour).

- Add a `console.log("AnonAddyTB contextmenu path:", ...)` and `console.log("AnonAddyTB popupshowing:", ...)` so the user can paste the output into an errors file.

---

## Issue 13 — Disable / Delete buttons missing from all aliases (only on freshly-created one)

**Root cause**: Disable/Delete/Restore buttons exist only inside the `v-if="createdAlias"` block in RecipientCard. After popup reopen `createdAlias` is null, so no buttons appear. Regular aliases from `existingAliases` have no buttons at all.

**Fix**:

`src/popup/components/RecipientCard.vue`:

- Change emits to carry an alias ID:
    ```typescript
    disable: [id: string]
    delete: [id: string]
    restore: [id: string]
    ```
- In the `displayAliases` template block, change `<label>` wrapper to `<div class="alias-option">` with radio + label inside, and add an `alias-option__actions` div with Disable/Delete buttons (`@click.stop` on the actions div). Inactive aliases get a Re-enable button instead of Disable.
- The existing `createdAlias` block already has correct buttons — update it to emit the ID: `$emit('disable', createdAlias.id)` etc.
- `existingAliases` items are `Alias` objects which have `active`, `id`, `email`. Use those to drive the button visibility (`v-if="alias.active"` for Disable vs Re-enable).

`src/popup/App.vue`:

- Update `handleDisable`, `handleRestore`, `handleDelete` to accept `(recipientIdx: number, aliasId: string)` instead of `(recipientIdx: number)`. They should no longer check `r.createdAlias` exclusively:
    - Locate the alias by ID from `r.createdAlias` first, then from `r.existingAliases`.
    - If found in `r.existingAliases`, update `r.existingAliases[idx].active` (disable/restore) or splice it out (delete), plus clear `r.selectedAlias` if it matches.
    - If found in `r.createdAlias`, keep existing `r.createdAlias` mutation.
- Update the event handlers in the template: `@disable="(id) => handleDisable(idx, id)"` etc.
- `applyAndClose`: the current check `r.createdAlias?.active ? r.createdAlias.email : r.selectedAlias` should be generalised — check the actual active state of `r.selectedAlias` by looking it up across both `r.createdAlias` and `r.existingAliases`.

---

## Issue 14 — "Existing aliases" list shows unrelated aliases; add typeahead for any alias

**Root cause** (`src/popup/App.vue:83-95`): `matchingAliases` uses `a.email.toLowerCase().includes(lower)` — this matches any alias whose addy-domain happens to contain the recipient domain as a substring (e.g., alias `x@alias.company.com` when recipient is `user@company.com`).

**Fix, part A — tighten matching**:

- Remove the `a.email.toLowerCase().includes(lower)` branch entirely.
- Keep only the description match: `(a.description ?? "").toLowerCase().includes(lower)`.
- Sort/slice unchanged.
- This means pre-filtered aliases are only those the extension created for that domain.

**Fix, part B — typeahead for any alias**:

`src/popup/components/RecipientCard.vue`:

- Add `allAliases: Alias[]` prop.
- Add `aliasSearch = ref("")` and computed `searchResults`:
    ```typescript
    const searchResults = computed(() => {
        const q = aliasSearch.value.trim().toLowerCase();
        if (!q) return [];
        return props.allAliases
            .filter(
                (a) =>
                    a.email.toLowerCase().includes(q) ||
                    (a.description ?? "").toLowerCase().includes(q),
            )
            .slice(0, 15);
    });
    ```
- In the template, above the alias list, add a small `<input>` placeholder `"Search all aliases…"` bound to `aliasSearch`.
- When `searchResults.length > 0` (search active), show `searchResults` instead of `displayAliases` + `createdAlias`. Clicking an item sets `selectedAlias`. Clear search on selection.
- When search is empty, show the normal list (pre-filtered + created alias).

`src/popup/App.vue`:

- Pass `:all-aliases="allAliases"` to RecipientCard.

---

## Issue 15 — Domain dropdown shows no entries

**Root cause**: `domainOptions.data` is empty in storage when the popup opens (background hasn't fetched yet, first install, or background failed). The combobox renders but `filteredDomains` is an empty array.

The `@blur.self` / `@mousedown.prevent` combo in the combobox is correct and not the issue.

**Fix** (`src/popup/App.vue` — `refreshAliasesInBackground`):

- After the existing alias refresh loop, if `domainOptions.value.data.length === 0`, fetch domain options inline:
    ```typescript
    if (domainOptions.value.data.length === 0) {
        const fresh = await addyApiRequest<DomainOptions>(
            "GET",
            "domain-options",
        );
        domainOptions.value = fresh;
        await messenger.storage.local.set({ domainOptions: fresh });
    }
    ```
- This runs in the background after the popup is visible (same as alias refresh) so the combobox will populate within a second of opening.

---

## Issue 16 — "Replace … with:" → "Send … from:"

**Fix** (`_locales/en/messages.json`):

- `"replaceWithPrefix": { "message": "Send" }` (was "Replace")
- `"replaceWithSuffix": { "message": "from:" }` (was "with:")

---

## Commit order (one per issue, lplp-pipbuck)

1. `[extension] CreateAliasForm: ai: Run: Always show "Sends via:" preview row.`
2. `[extension] experiment: ai: Run: Harden context-menu injection; add diagnostics.`
3. `[extension] popup: ai: Run: Add disable/delete controls to all alias entries.`
4. `[extension] popup: ai: Run: Fix alias matching and add typeahead for all aliases.`
5. `[extension] popup: ai: Run: Fetch domain-options when cache is empty.`
6. `[extension] popup: ai: Run: Rename "Replace … with:" → "Send … from:".`

---

## Verification

- **Issue 11**: Open compose, type a recipient with no display name, open CreateAliasForm → both "Sends via:" and "Sends as:" rows appear with the same forwarding address.
- **Issue 12**: Open Thunderbird console → right-click a To: pill → look for `AnonAddyTB contextmenu path:` log. Confirm `mail-address-pill` is in the path. Confirm "Use Addy alias for sending" submenu appears in the context menu.
- **Issue 13**: Open popup → pick any existing alias from the list → Disable / Delete buttons are visible. Disable → alias is greyed out. Reopen popup → list still shows the alias (it's in `existingAliases`) with a Re-enable button.
- **Issue 14**: Alias list shows only aliases whose description mentions the recipient domain. Type in the search box → all aliases matching the query appear.
- **Issue 15**: Open popup immediately after installing / clearing storage → domain dropdown populates within a second.
- **Issue 16**: RecipientCard header reads "Send alice@example.com from:" instead of "Replace alice@example.com with:".
