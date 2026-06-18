# Plan: Addy icon + pretty text on mail-address-pill

## Context

The compose window currently shows addy forwarding addresses in raw encoding (`alias+them=their-host.com@anon.my-mail.com`), which is hard for users to read. This plan adds two visual signals to `mail-address-pill` elements in the compose window:

1. **Colored Addy icon** — pill contains a proxied (forwarding-format) addy address
2. **Grayscale Addy icon** — pill contains a plain addy-domain address (not forwarding-encoded)
3. **Human-readable display for proxied pills**: `alias@anon.email → them@their-host.com`

All changes land in `src/experiment/implementation.js` (the privileged WebExtension Experiment). No other files need to change.

---

## Implementation

### 1. Add `parseForwardingAddress(email, addyDomainSet)` helper

Pure-JS mirror of `src/popup/utils.ts:parseForwardingAddress`. Returns `{ aliasEmail, originalEmail }` or `null`.

```javascript
function parseForwardingAddress(email, addyDomainSet) {
  const dm = email.match(/^(.+)@(.+)$/);
  if (!dm) return null;
  const [, localPart, domain] = dm;
  if (!addyDomainSet.has(domain.toLowerCase())) return null;
  const fw = localPart.match(/^(.+)\+(.+)=(.+)$/);
  if (!fw) return null;
  const [, aliasLocal, recipLocal, recipDomain] = fw;
  return { aliasEmail: `${aliasLocal}@${domain}`, originalEmail: `${recipLocal}@${recipDomain}` };
}
```

### 2. Add `getAddyDomainSet()` helper

```javascript
function getAddyDomainSet() {
  return new Set((_cacheData.domainOptions?.data || []).map(d => d.toLowerCase()));
}
```

### 3. Add `injectAddyPillStyles(doc)` (once per compose window)

Injects `<style id="addy-pill-styles">` into the compose document with:

```css
.addy-pill-icon {
  width: 12px; height: 12px;
  vertical-align: middle;
  margin-right: 3px;
  pointer-events: none;
}
.addy-pill-icon.addy-aliased {
  filter: grayscale(1) opacity(0.6);
}
```

Guard with `if (doc.getElementById("addy-pill-styles")) return;` so it runs only once.

### 4. Add per-window `pillIconMap` WeakMap

Each compose window gets its own `WeakMap<HTMLElement, HTMLElement>` mapping pill → injected `<img>` element, so icons can be updated or cleaned up without querying the DOM.

### 5. Add `decoratePill(pill, doc, pillIconMap)` function

```
email = pill.getAttribute("emailAddress") || ""
fwd   = parseForwardingAddress(email, getAddyDomainSet())
domain = email.match(/@(.+)$/?.[1] || ""

CASE proxied (fwd !== null):
  - set displayName* = `${fwd.aliasEmail} → ${fwd.originalEmail}`
  - upsert colored icon img before pill (class "addy-pill-icon addy-proxied")

CASE plain addy domain (getAddyDomainSet().has(domain)):
  - restore original displayName (if we previously overrode it)
  - upsert grayscale icon img before pill (class "addy-pill-icon addy-aliased")

CASE neither:
  - restore original displayName
  - remove existing icon img (if any)
```

"Upsert" means: if `pillIconMap.has(pill)`, update `className` on the existing img; otherwise insert a new `<img src="${ICON_ADDY}">` immediately before `pill` in the DOM and store it in `pillIconMap`.

*`displayName` note — see trade-off section below.*

### 6. Add `decorateAllPills(doc, pillIconMap)`

`doc.querySelectorAll("mail-address-pill").forEach(p => decoratePill(p, doc, pillIconMap))`

### 7. Modify `attachToWindow(win)`

After existing setup:
1. Create `const pillIconMap = new WeakMap();`
2. Call `injectAddyPillStyles(doc)`
3. Call `decorateAllPills(doc, pillIconMap)` (handles compose windows pre-filled with addresses)
4. Set up a `MutationObserver`:
   - `childList + subtree`: on added `mail-address-pill` nodes → call `decoratePill()`; on removed nodes → look up + remove icon from `pillIconMap`
   - `attributes` on `mail-address-pill` with `attributeFilter: ["emailaddress"]` → call `decoratePill()` again (address changed in-place)
5. Include `observer.disconnect()` in the window cleanup function stored in `attached`.

### 8. Modify `setCache(data)` in the returned API

After `_cacheData = data`, iterate over all entries in `attached` and re-call `decorateAllPills` for each window (requires storing `doc` and `pillIconMap` per entry, not just a cleanup function — update the `attached` Map value to `{ cleanup, doc, pillIconMap }`).

---

## Known trade-off: displayName in email headers

Setting `displayName` (or its lowercase equivalent `displayname`, whichever the custom element observes) on the pill propagates to the MIME To/CC header's display-name field. The sent email would contain:

```
To: "alias@anon.email → them@their-host.com" <alias+them=their-host.com@anon.email>
```

This doesn't break Addy's forwarding (Addy parses the address part, not the display name). However, the arrow string appears in email headers.

**Alternative** (avoidable later if desired): inject CSS into the pill's shadow root via `pill.shadowRoot.adoptedStyleSheets` to override the displayed text without touching the `displayName` attribute at all. This is more involved and more fragile across TB versions, so the `displayName` approach is recommended for now.

---

## Verification

1. `make` (or `npm run build`) — build extension
2. Reload extension in Thunderbird (about:debugging)
3. Open compose window, add a plain recipient
4. Right-click pill → "Use Addy alias" → select an existing alias → apply
   - Pill should show **colored** Addy icon + `alias@anon.email → them@their-host.com`
5. Open compose, manually type an addy-domain address (e.g. `foo@your-addy-domain.com`)
   - Pill should show **grayscale** icon, normal text
6. Remove the aliased address, re-add original → decoration should disappear cleanly
7. Trigger a cache refresh (background sync) → existing pills in open compose windows should re-evaluate
