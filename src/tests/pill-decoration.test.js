import { describe, it, expect, afterEach } from "vitest";
import {
  decoratePillViaAttributes,
  decoratePillViaTextNode,
  decoratePillViaCSSAdopted,
  upsertPillIcon,
  removePillIcon,
} from "../experiment/pillDecoration.js";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function makePill(shadowHtml = "<label>original@raw.com</label>") {
  const el = document.createElement("div");
  el.setAttribute("emailAddress", "alias+user=example.com@anon.email");
  el.setAttribute("fullAddress", "alias+user=example.com@anon.email");
  el.setAttribute("label", "alias+user=example.com@anon.email");
  const shadow = el.attachShadow({ mode: "open" });
  shadow.innerHTML = shadowHtml;
  document.body.appendChild(el);
  return el;
}

function makePillNoShadow() {
  const el = document.createElement("div");
  document.body.appendChild(el);
  return el;
}

afterEach(() => {
  document.body.innerHTML = "";
});

// ─── decoratePillViaAttributes ───────────────────────────────────────────────

describe("decoratePillViaAttributes", () => {
  it("updates the pill label without changing compose address attributes", () => {
    const pill = makePill();
    decoratePillViaAttributes(pill, "alias@anon.email → user@example.com");

    expect(pill.getAttribute("label")).toBe(
      "alias@anon.email → user@example.com",
    );
    expect(pill.getAttribute("emailAddress")).toBe(
      "alias+user=example.com@anon.email",
    );
    expect(pill.getAttribute("fullAddress")).toBe(
      "alias+user=example.com@anon.email",
    );
  });

  it("restores the original label when called with null", () => {
    const pill = makePill();
    decoratePillViaAttributes(pill, "alias@anon.email → user@example.com");
    decoratePillViaAttributes(pill, null);

    expect(pill.getAttribute("label")).toBe(
      "alias+user=example.com@anon.email",
    );
    expect(pill.dataset.addyOrigLabel).toBeUndefined();
  });

  it("keeps outgoing compose address attributes intact after any label replacement", () => {
    const pill = makePill("<label>mail -> mail</label>");
    const originalEmail = pill.getAttribute("emailAddress");
    const originalFullAddress = pill.getAttribute("fullAddress");

    decoratePillViaAttributes(pill, "mail -> mail");
    decoratePillViaTextNode(pill, "mail -> mail");
    decoratePillViaCSSAdopted(pill, "mail -> mail");
    decoratePillViaAttributes(pill, null);
    decoratePillViaTextNode(pill, null);
    decoratePillViaCSSAdopted(pill, null);

    expect(pill.getAttribute("emailAddress")).toBe(originalEmail);
    expect(pill.getAttribute("fullAddress")).toBe(originalFullAddress);
  });
});

// ─── decoratePillViaTextNode ──────────────────────────────────────────────────

describe("decoratePillViaTextNode", () => {
  it("sets the label text to the provided display string", () => {
    const pill = makePill("<label>old@raw.com</label>");
    decoratePillViaTextNode(pill, "alias@anon.email → old@raw.com");
    expect(pill.shadowRoot.querySelector("label").textContent).toBe(
      "alias@anon.email → old@raw.com",
    );
  });

  it("stores original text in dataset.addyOrigText before first change", () => {
    const pill = makePill("<label>original@raw.com</label>");
    decoratePillViaTextNode(pill, "new text");
    expect(pill.dataset.addyOrigText).toBe("original@raw.com");
  });

  it("does not overwrite dataset.addyOrigText on subsequent calls", () => {
    const pill = makePill("<label>original@raw.com</label>");
    decoratePillViaTextNode(pill, "first override");
    decoratePillViaTextNode(pill, "second override");
    expect(pill.dataset.addyOrigText).toBe("original@raw.com");
  });

  it("restores original text when called with null", () => {
    const pill = makePill("<label>original@raw.com</label>");
    decoratePillViaTextNode(pill, "alias@anon.email → original@raw.com");
    decoratePillViaTextNode(pill, null);
    expect(pill.shadowRoot.querySelector("label").textContent).toBe(
      "original@raw.com",
    );
  });

  it("removes dataset.addyOrigText after restoration", () => {
    const pill = makePill("<label>original@raw.com</label>");
    decoratePillViaTextNode(pill, "override");
    decoratePillViaTextNode(pill, null);
    expect(pill.dataset.addyOrigText).toBeUndefined();
  });

  it("returns false and does nothing when pill has no shadow root", () => {
    const pill = makePillNoShadow();
    const result = decoratePillViaTextNode(pill, "something");
    expect(result).toBe(false);
    expect(pill.dataset.addyOrigText).toBeUndefined();
  });

  it("falls back through LABEL_SELECTORS and finds a <span> when no <label>", () => {
    const pill = makePill("<span>from-span@raw.com</span>");
    decoratePillViaTextNode(pill, "new text");
    expect(pill.shadowRoot.querySelector("span").textContent).toBe("new text");
  });

  it("returns false when shadow root has no matching element", () => {
    const pill = makePill("<div>no match here</div>");
    const result = decoratePillViaTextNode(pill, "something");
    expect(result).toBe(false);
  });

  it("null is a no-op when no original was saved", () => {
    const pill = makePill("<label>untouched</label>");
    decoratePillViaTextNode(pill, null);
    expect(pill.shadowRoot.querySelector("label").textContent).toBe(
      "untouched",
    );
  });
});

// ─── decoratePillViaCSSAdopted ────────────────────────────────────────────────

describe("decoratePillViaCSSAdopted", () => {
  // jsdom does not support adoptedStyleSheets on shadow roots, so CSS injection
  // is skipped in all tests that don't explicitly set up the array.  The dataset
  // attribute (read by CSS attr()) must still be set regardless.

  it("sets dataset.addyLabel to the display string", () => {
    const pill = makePill("<label>x@y.com</label>");
    decoratePillViaCSSAdopted(pill, "alias@anon.email → x@y.com");
    expect(pill.dataset.addyLabel).toBe("alias@anon.email → x@y.com");
  });

  it("adds exactly one stylesheet to shadowRoot.adoptedStyleSheets when supported", () => {
    const pill = makePill("<label>x@y.com</label>");
    pill.shadowRoot.adoptedStyleSheets = [];
    decoratePillViaCSSAdopted(pill, "some text");
    expect(pill.shadowRoot.adoptedStyleSheets).toHaveLength(1);
  });

  it("does not add a duplicate sheet on a second call to the same pill", () => {
    const pill = makePill("<label>x@y.com</label>");
    pill.shadowRoot.adoptedStyleSheets = [];
    decoratePillViaCSSAdopted(pill, "first");
    decoratePillViaCSSAdopted(pill, "second");
    expect(pill.shadowRoot.adoptedStyleSheets).toHaveLength(1);
    expect(pill.dataset.addyLabel).toBe("second");
  });

  it("clears dataset.addyLabel and removes the sheet when called with null", () => {
    const pill = makePill("<label>x@y.com</label>");
    pill.shadowRoot.adoptedStyleSheets = [];
    decoratePillViaCSSAdopted(pill, "some text");
    decoratePillViaCSSAdopted(pill, null);
    expect(pill.dataset.addyLabel).toBeUndefined();
    expect(pill.shadowRoot.adoptedStyleSheets).toHaveLength(0);
  });

  it("still sets dataset.addyLabel when adoptedStyleSheets is not supported", () => {
    // CSS injection is skipped (no adoptedStyleSheets in jsdom), but the data
    // attribute must be set so attr(data-addy-label) works in TB at runtime.
    const pill = makePill("<label>x@y.com</label>");
    const result = decoratePillViaCSSAdopted(
      pill,
      "alias@anon.email → x@y.com",
    );
    expect(result).toBe(true);
    expect(pill.dataset.addyLabel).toBe("alias@anon.email → x@y.com");
  });

  it("returns false when pill has no shadow root", () => {
    const pill = makePillNoShadow();
    expect(decoratePillViaCSSAdopted(pill, "text")).toBe(false);
  });
});

// ─── upsertPillIcon / removePillIcon ─────────────────────────────────────────

describe("upsertPillIcon / removePillIcon", () => {
  const ICON_URL = "moz-extension://test-id/icon.svg";

  it("inserts an <img> immediately before the pill in the DOM", () => {
    const pill = makePill();
    const map = new WeakMap();
    upsertPillIcon(pill, map, ICON_URL, true);
    expect(pill.previousElementSibling?.tagName).toBe("IMG");
  });

  it("img has class addy-pill-icon addy-proxied when proxied=true", () => {
    const pill = makePill();
    const map = new WeakMap();
    upsertPillIcon(pill, map, ICON_URL, true);
    expect(pill.previousElementSibling.className).toBe(
      "addy-pill-icon addy-proxied",
    );
  });

  it("img has class addy-pill-icon addy-aliased when proxied=false", () => {
    const pill = makePill();
    const map = new WeakMap();
    upsertPillIcon(pill, map, ICON_URL, false);
    expect(pill.previousElementSibling.className).toBe(
      "addy-pill-icon addy-aliased",
    );
  });

  it("updates img class without inserting a second img on repeat call", () => {
    const pill = makePill();
    const map = new WeakMap();
    upsertPillIcon(pill, map, ICON_URL, true);
    upsertPillIcon(pill, map, ICON_URL, false);
    // Only one sibling img.
    const imgs = document.body.querySelectorAll("img");
    expect(imgs).toHaveLength(1);
    expect(imgs[0].className).toBe("addy-pill-icon addy-aliased");
  });

  it("removePillIcon removes the img from the DOM", () => {
    const pill = makePill();
    const map = new WeakMap();
    upsertPillIcon(pill, map, ICON_URL, true);
    removePillIcon(pill, map);
    expect(document.body.querySelector("img")).toBeNull();
  });

  it("removePillIcon clears the WeakMap entry", () => {
    const pill = makePill();
    const map = new WeakMap();
    upsertPillIcon(pill, map, ICON_URL, true);
    removePillIcon(pill, map);
    expect(map.has(pill)).toBe(false);
  });

  it("removePillIcon is a no-op when no icon exists for the pill", () => {
    const pill = makePill();
    const map = new WeakMap();
    expect(() => removePillIcon(pill, map)).not.toThrow();
  });
});
