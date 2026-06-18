"use strict";

// Selector list tried in order when looking for the text-bearing element inside
// a mail-address-pill shadow root. First match wins. Adjust after inspecting TB.
const LABEL_SELECTORS = ["label", ".pill-label", "span", "[role='option']"];

// WeakMap from ShadowRoot → CSSStyleSheet injected by decoratePillViaCSSAdopted.
// Prevents duplicate sheets when the function is called multiple times.
const _adoptedSheets = new WeakMap();

/**
 * Approach 0: update the host element's display attributes.
 *
 * Thunderbird's mail-address-pill exposes the rendered text through the host
 * label attribute in current compose windows. Keep this display-only: never
 * mutate emailAddress/fullAddress, because those are the compose data.
 *
 * @param {Element} pill
 * @param {string|null} displayText  null → restore original label
 * @returns {boolean}
 */
export function decoratePillViaAttributes(pill, displayText) {
  if (displayText === null || displayText === undefined) {
    if ("addyOrigLabel" in pill.dataset) {
      pill.setAttribute("label", pill.dataset.addyOrigLabel);
      delete pill.dataset.addyOrigLabel;
    }
    return true;
  }

  if (!("addyOrigLabel" in pill.dataset)) {
    pill.dataset.addyOrigLabel =
      pill.getAttribute("label") || pill.getAttribute("emailAddress") || "";
  }
  pill.setAttribute("label", displayText);
  return true;
}

/**
 * Approach A: directly mutate the text-bearing element inside the shadow root.
 *
 * @param {Element} pill
 * @param {string|null} displayText  null → restore original text
 * @returns {boolean} false if no shadow root or no label element found
 */
export function decoratePillViaTextNode(pill, displayText) {
  const shadow = pill.shadowRoot;
  if (!shadow) return false;

  let labelEl = null;
  for (const sel of LABEL_SELECTORS) {
    labelEl = shadow.querySelector(sel);
    if (labelEl) break;
  }
  if (!labelEl) return false;

  if (displayText === null || displayText === undefined) {
    // Restore original if we saved it.
    if ("addyOrigText" in pill.dataset) {
      labelEl.textContent = pill.dataset.addyOrigText;
      delete pill.dataset.addyOrigText;
    }
    return true;
  }

  // Save original before first override (idempotent).
  if (!("addyOrigText" in pill.dataset)) {
    pill.dataset.addyOrigText = labelEl.textContent;
  }
  labelEl.textContent = displayText;
  return true;
}

/**
 * Approach B: inject a CSSStyleSheet into the shadow root that shows the text
 * via :host::before and hides the native label.
 *
 * The data-addy-label attribute is always set (it's what the CSS attr() reads).
 * CSS injection is best-effort: skipped if adoptedStyleSheets is unavailable.
 *
 * @param {Element} pill
 * @param {string|null} displayText  null → remove decoration
 * @returns {boolean} false if pill has no shadow root
 */
export function decoratePillViaCSSAdopted(pill, displayText) {
  const shadow = pill.shadowRoot;
  if (!shadow) return false;

  if (displayText === null || displayText === undefined) {
    delete pill.dataset.addyLabel;
    const existing = _adoptedSheets.get(shadow);
    if (existing && Array.isArray(shadow.adoptedStyleSheets)) {
      shadow.adoptedStyleSheets = shadow.adoptedStyleSheets.filter(
        (s) => s !== existing,
      );
      _adoptedSheets.delete(shadow);
    }
    return true;
  }

  pill.dataset.addyLabel = displayText;

  if (Array.isArray(shadow.adoptedStyleSheets) && !_adoptedSheets.has(shadow)) {
    const sheet = new CSSStyleSheet();
    sheet.replaceSync(`
      :host::before {
        content: attr(data-addy-label);
      }
      label, .pill-label, span {
        visibility: hidden;
        width: 0;
        overflow: hidden;
      }
    `);
    shadow.adoptedStyleSheets = [...shadow.adoptedStyleSheets, sheet];
    _adoptedSheets.set(shadow, sheet);
  }

  return true;
}

/**
 * Insert or update the Addy icon <img> placed immediately before the pill.
 *
 * @param {Element} pill
 * @param {WeakMap} pillIconMap  caller-owned map tracking pill → img
 * @param {string}  iconUrl
 * @param {boolean} proxied  true → colored; false → grayscale
 */
export function upsertPillIcon(pill, pillIconMap, iconUrl, proxied) {
  const cls = proxied
    ? "addy-pill-icon addy-proxied"
    : "addy-pill-icon addy-aliased";

  if (pillIconMap.has(pill)) {
    pillIconMap.get(pill).className = cls;
    return;
  }

  const img = pill.ownerDocument.createElement("img");
  img.src = iconUrl;
  img.className = cls;
  img.alt = "";
  pill.parentNode.insertBefore(img, pill);
  pillIconMap.set(pill, img);
}

/**
 * Remove the Addy icon associated with a pill, if any.
 *
 * @param {Element} pill
 * @param {WeakMap} pillIconMap
 */
export function removePillIcon(pill, pillIconMap) {
  const img = pillIconMap.get(pill);
  if (!img) return;
  img.remove();
  pillIconMap.delete(pill);
}
