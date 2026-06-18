# Issues 21–23 fix plan

## Context

Issues 17–20 are committed. Two new issues (21–22) plus a follow-up on issue 22 (issue 23):

- **21**: Existing alias entries in RecipientCard don't show the forwarding address that will appear in the To: field — only the alias email itself.
- **22**: After our context menu appears and the user hovers over a submenu, Thunderbird crashes: `can't access property "hasAttribute", pill is null` in its own `onPillPopupShowing` at `addressingWidgetOverlay.js:1044`. Root cause: Thunderbird's `onpopupshowing` attribute handler fires for ALL menupopup openings and tries to find a pill from `popup.triggerNode` — but our submenus have a `<menu>` element as `triggerNode`, not a pill.
- **23**: After the crash in issue 22, `errors/11.txt` shows right-clicks firing (`onContextMenu` logs the pill) but `popupshowing` never fires — meaning Thunderbird's `emailAddressPillPopup` stopped opening entirely. This is a direct consequence of the issue 22 crash leaving Thunderbird's popup system in a bad state. Fixing issue 22 fixes issue 23.

---

## Issue 22 + 23 — Thunderbird's onPillPopupShowing crashes on our submenus

**Root cause** (`src/experiment/implementation.js` — `buildAddyMenu`):

Thunderbird has `onpopupshowing="onPillPopupShowing(event)"` on an ancestor element in `messengercompose.xhtml`. This fires for every `menupopup` opening in the compose window (in bubble phase). When our `menuPopup` / `existingPopup` / `newPopup` / domain `dmPopup` open, Thunderbird's handler runs, calls `popup.triggerNode?.closest("mail-address-pill")` (or similar), gets null, and crashes at `pill.hasAttribute(...)`.

The outer `emailAddressPillPopup` (Thunderbird's real pill context menu) must still let Thunderbird's handler run — that's what adds the pill-specific Edit/Remove items. Only our injected subpopups need to be isolated.

**Fix**: Add a single **bubbling** listener to `menuPopup` that calls `stopPropagation()`. Because our subpopups (`existingPopup`, `newPopup`, every `dmPopup`) are descendants of `menuPopup` in the XUL DOM, their `popupshowing` events bubble through `menuPopup`, where our listener intercepts and stops them. The outer `emailAddressPillPopup`'s `popupshowing` is unaffected (it's a different event).

In `buildAddyMenu`, immediately after `const menuPopup = doc.createXULElement("menupopup");`:

```javascript
const menuPopup = doc.createXULElement("menupopup");
// Prevent Thunderbird's onPillPopupShowing from crashing when our submenus open.
// It runs on all menupopup events in the compose window (bubble phase) and crashes
// when triggerNode is not a pill. The outer pill context menu is unaffected.
menuPopup.addEventListener("popupshowing", (e) => e.stopPropagation());
```

This is a single-line change; no logic changes elsewhere.

---

## Issue 21 — Existing alias entries lack forwarding-address preview

**Root cause** (`src/popup/components/RecipientCard.vue`): Each alias option shows `alias.email` (the Addy alias) but not the SMTP forwarding address (`aliasLocal+recipLocal=recipDomain@aliasDomain`) that actually ends up in the To: field. The "Sends via:" preview is only shown in `CreateAliasForm` for newly-created aliases.

**Fix** (`src/popup/components/RecipientCard.vue`):

1. Add helper function (after `pinnedAlias` computed):

    ```typescript
    function forwardingFor(aliasEmail: string): string | null {
        const am = aliasEmail.match(/^(.+)@(.+)$/);
        const rm = props.address.match(/^(.+)@(.+)$/);
        if (!am || !rm) return null;
        return `${am[1]}+${rm[1]}=${rm[2]}@${am[2]}`;
    }
    ```

    Uses the `address` prop (the recipient email) which is already available.

2. Add a forwarding preview row to each alias option — `createdAlias`, `displayAliases`, `pinnedAlias`, and `searchResults` blocks. Below the existing `alias-option__row`:

    ```vue
    <div
        v-if="forwardingFor(alias.email)"
        class="alias-option__row alias-option__row--fwd"
    >
      <span class="alias-option__fwd-label">{{ t("aliasPreviewLabel") }}</span>
      <code class="alias-option__fwd">{{ forwardingFor(alias.email) }}</code>
    </div>
    ```

    For `createdAlias` substitute `createdAlias.email`; for the rest use `alias.email`.

3. Add SCSS rules:

    ```scss
    &__row--fwd {
        margin-top: $spacing-xs;
    }

    &__fwd-label {
        color: $color-muted;
        font-size: $font-size-sm;
        flex-shrink: 0;
    }

    &__fwd {
        font-family: monospace;
        font-size: $font-size-sm;
        color: $color-muted;
        word-break: break-all;
    }
    ```

Reuses `aliasPreviewLabel` ("Sends via:") i18n key from `_locales/en/messages.json`.

---

## Commit order (one per issue, lplp-pipbuck)

1. `[extension] experiment: ai: Run: Stop submenu popupshowing from reaching Thunderbird's onPillPopupShowing.`
2. `[extension] popup: ai: Run: Show forwarding address preview on existing alias entries.`

---

## Verification

- **Issue 22/23**: Reload extension → right-click pill → "Use Addy alias for sending" appears → hover over "Existing…" submenu → submenu opens without crash → right-clicking again continues to work normally.
- **Issue 21**: Open popup → existing alias entries each show "Sends via: aliasLocal+recipLocal=recipDomain@aliasDomain" below the alias email.
