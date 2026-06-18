Write two new memory files to `/home/user/.claude/projects/-home-user-git-luckydonald-AnonAddyThunderbirdExtension/memory/` and update `MEMORY.md`.

---

**Memory 1** — filename `xul_popuphidden_bubbling.md`

```markdown
---
name: xul-popuphidden-bubbling
description: "XUL popuphidden bubbles: { once: true } cleanup on outer menupopup fires prematurely when a child popup closes"
metadata:
  type: feedback
---

When a cleanup listener is attached to a XUL `menupopup` with `{ once: true }`, it will
fire for ANY `popuphidden` event that bubbles up from a child/descendant popup — not just
when that outer popup itself closes.

**Why:** This caused the Addy context-menu entry to vanish as soon as the user
opened the Addy submenu and pressed Escape to close it: the submenu's
`popuphidden` bubbled to the outer `emailAddressPillPopup`, consumed the
`{ once: true }` listener, and removed `sep`/`addyMenu` while the outer popup
was still visible.  After that, the extension's state was broken until reload.

**How to apply:** Never use `{ once: true }` for `popuphidden` cleanup on a
parent menupopup that has child popups.  Use a named handler with an
`e.target === popup` guard and call `removeEventListener` manually:

```javascript
popup.addEventListener("popuphidden", function onPopupHidden(e) {
  if (e.target !== popup) return;
  popup.removeEventListener("popuphidden", onPopupHidden);
  sep.remove();
  addyMenu.remove();
});
```

Note: the `stopPropagation()` guard added to `menuPopup` for `popupshowing`
(to prevent the TB `onPillPopupShowing` crash) does NOT protect `popuphidden` —
they need separate guards.

See also: [[marionette-tb-chrome-patterns]]
```

---

**Memory 2** — filename `experiment_alias_matching.md`

```markdown
---
name: experiment-alias-matching
description: "Alias matching in the experiment must use description-based logic, not email-based, to match the popup"
metadata:
  type: feedback
---

The popup (`src/popup/utils.ts` `matchingAliases`) matches aliases by
**description containing the recipient domain** (e.g. "Shopping alias for
example.com").  AnonAddyTB sets descriptions in exactly this form when it
creates aliases.

The experiment's `matchingAliasesForEmail` was instead filtering by
`a.email.toLowerCase().includes(domain)` — finding aliases whose *own email
address* happened to contain the recipient domain (e.g. an alias at
`relay.example.com` for a recipient at `example.com`).  This returned entirely
different, usually empty, results.

**Why:** The two UI surfaces (toolbar popup and right-click chip menu) were
showing different alias candidates for the same recipient, with the chip menu
showing nothing useful.

**How to apply:** Both `matchingAliases` (popup) and `matchingAliasesForEmail`
(experiment) should filter with:
```javascript
(a.description ?? "").toLowerCase().includes(domain)
```
Keep the two implementations in sync; `src/experiment/utils.js` is the
extracted testable version of the inline function in `implementation.js`.

See also: [[marionette-tb-chrome-patterns]]
```

---

After writing both files, append these two lines to `MEMORY.md` (read it first, then edit):

```
- [XUL popuphidden bubbling fix](xul_popuphidden_bubbling.md) — { once: true } cleanup fires for child popup events; use e.target guard instead
- [Experiment alias matching](experiment_alias_matching.md) — must match by description (not email), same as popup, or Existing submenu shows nothing
```
