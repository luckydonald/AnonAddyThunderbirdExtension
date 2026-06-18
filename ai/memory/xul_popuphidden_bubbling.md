---
name: xul-popuphidden-bubbling
description: "XUL popuphidden bubbles: { once: true } cleanup on outer menupopup fires prematurely when a child popup closes"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: b3c2110f-ae97-47f6-bf3d-647bd0eaab60
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
