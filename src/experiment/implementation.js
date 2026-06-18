"use strict";

/* global ChromeUtils, Services, Ci */

var { ExtensionCommon } = ChromeUtils.importESModule(
  "resource://gre/modules/ExtensionCommon.sys.mjs",
);
// setTimeout/clearTimeout are not in scope in privileged extension JS.
var { setTimeout, clearTimeout } = ChromeUtils.importESModule(
  "resource://gre/modules/Timer.sys.mjs",
);

// Alias and domain-option data pushed from the background after each cache refresh.
let _cacheData = {
  aliases: [],
  domainOptions: {
    data: [],
    defaultAliasDomain: "",
    defaultAliasFormat: "random_characters",
  },
};

const FORMAT_ITEMS = [
  { value: "random_characters", label: "Characters" },
  { value: "random_words", label: "Words" },
  { value: "random_male_name", label: "Male name" },
  { value: "random_female_name", label: "Female name" },
  { value: "random_noun", label: "Noun" },
  { value: "custom", label: "Custom…" },
];

function matchingAliasesForEmail(email) {
  const m = email.match(/@(.+)$/);
  if (!m) return [];
  const domain = m[1].toLowerCase();
  return (_cacheData.aliases || [])
    .filter((a) => a.active && (a.description ?? "").toLowerCase().includes(domain))
    .slice(0, 20);
}

// AddressChipMenu Experiment API
//
// Injects an "Use Addy alias for sending" submenu into the existing right-click
// context menu on <mail-address-pill> elements in compose windows.
this.AddressChipMenu = class extends ExtensionCommon.ExtensionAPI {
  getAPI(context) {
    let chipMenuFire = null;
    const attached = new Map();

    // Icon URLs — the Addy extension icon and built-in TB address-book icons.
    const ICON_ADDY = context.extension.baseURI.spec + "icon.svg";
    // chrome://messenger/skin icons available in all TB themes.
    const ICON_EXISTING = "chrome://messenger/skin/addressbook/icons/addressbook.png";
    const ICON_NEW = "chrome://messenger/skin/icons/addcontact16.png";

    function buildFormatItems(parentPopup, doc, win, email, displayName, fieldType, domain) {
      for (const fmt of FORMAT_ITEMS) {
        const item = doc.createXULElement("menuitem");
        item.setAttribute("label", fmt.label);
        if (fmt.value === "custom") {
          item.addEventListener(
            "command",
            (function (d) {
              return () => {
                const valueObj = { value: "" };
                const ok = Services.prompt.prompt(
                  win,
                  "Custom alias prefix",
                  `Prefix for new alias on @${d}:`,
                  valueObj,
                  null,
                  { value: false },
                );
                if (!ok || !valueObj.value.trim()) return;
                chipMenuFire &&
                  chipMenuFire.async({
                    email,
                    displayName,
                    fieldType,
                    action: "create_alias",
                    domain: d,
                    format: "custom",
                    customPrefix: valueObj.value.trim(),
                  });
              };
            })(domain),
          );
        } else {
          item.addEventListener(
            "command",
            (function (f, d) {
              return () => {
                chipMenuFire &&
                  chipMenuFire.async({
                    email,
                    displayName,
                    fieldType,
                    action: "create_alias",
                    domain: d,
                    format: f,
                    customPrefix: "",
                  });
              };
            })(fmt.value, domain),
          );
        }
        parentPopup.appendChild(item);
      }
    }

    function buildAddyMenu(doc, win, pill) {
      const email = pill.getAttribute("emailAddress") || "";
      const displayName = pill.getAttribute("displayName") || "";
      const addressRow = pill.closest(".address-row");
      const fieldType = (addressRow?.dataset?.recipienttype || "to").toLowerCase();

      const availableDomains = _cacheData.domainOptions?.data || [];
      const defaultDomain =
        _cacheData.domainOptions?.defaultAliasDomain ||
        availableDomains[0] ||
        "";
      const existingAliases = matchingAliasesForEmail(email);

      // Top-level menu entry — direct click opens popup, hover/arrow unfolds submenu.
      const menu = doc.createXULElement("menu");
      menu.setAttribute("label", "Use Addy alias for sending");
      menu.setAttribute("image", ICON_ADDY);
      const menuPopup = doc.createXULElement("menupopup");
      // Thunderbird's onpopupshowing runs on all menupopup events in the compose window
      // and crashes when triggerNode is not a pill (pill is null → pill.hasAttribute fails).
      // Stop all popupshowing events from menuPopup and its descendant popups from bubbling
      // up to Thunderbird's handler. The outer pill context menu is unaffected.
      menuPopup.addEventListener("popupshowing", (e) => e.stopPropagation());

      // Direct click on the <menu> element itself (not on a submenu item) opens popup.
      menu.addEventListener("click", (e) => {
        if (e.target === menu) {
          chipMenuFire &&
            chipMenuFire.async({ email, displayName, fieldType, action: "open_popup" });
          e.preventDefault();
        }
      });

      // ── Existing… ▶ ──────────────────────────────────────────────────────────
      const existingMenu = doc.createXULElement("menu");
      existingMenu.setAttribute("label", "Existing…");
      existingMenu.setAttribute("image", ICON_EXISTING);
      const existingPopup = doc.createXULElement("menupopup");

      // "Open alias picker…" is first in Existing; provides easy access to full GUI.
      const pickerItem = doc.createXULElement("menuitem");
      pickerItem.setAttribute("label", "Open alias picker…");
      pickerItem.addEventListener("command", () => {
        chipMenuFire &&
          chipMenuFire.async({ email, displayName, fieldType, action: "open_popup" });
      });
      existingPopup.appendChild(pickerItem);
      existingPopup.appendChild(doc.createXULElement("menuseparator"));

      if (existingAliases.length === 0) {
        const noItem = doc.createXULElement("menuitem");
        noItem.setAttribute("label", "No existing aliases for this domain");
        noItem.setAttribute("disabled", "true");
        existingPopup.appendChild(noItem);
      } else if (existingAliases.length > 5) {
        // Group by alias domain when there are many
        const domainGroups = new Map();
        for (const alias of existingAliases) {
          const dm = alias.email.match(/@(.+)$/)?.[1] ?? "";
          if (!domainGroups.has(dm)) domainGroups.set(dm, []);
          domainGroups.get(dm).push(alias);
        }

        if (domainGroups.size > 1) {
          for (const [dm, aliases] of domainGroups) {
            const dmMenu = doc.createXULElement("menu");
            dmMenu.setAttribute("label", `…@${dm}`);
            const dmPopup = doc.createXULElement("menupopup");
            for (const alias of aliases) {
              const item = doc.createXULElement("menuitem");
              item.setAttribute("label", alias.email);
              item.addEventListener(
                "command",
                (function (ae) {
                  return () =>
                    chipMenuFire &&
                    chipMenuFire.async({
                      email,
                      displayName,
                      fieldType,
                      action: "select_alias",
                      aliasEmail: ae,
                    });
                })(alias.email),
              );
              dmPopup.appendChild(item);
            }
            dmMenu.appendChild(dmPopup);
            existingPopup.appendChild(dmMenu);
          }
        } else {
          // Same domain, flat list
          for (const alias of existingAliases) {
            const item = doc.createXULElement("menuitem");
            item.setAttribute("label", alias.email);
            item.addEventListener(
              "command",
              (function (ae) {
                return () =>
                  chipMenuFire &&
                  chipMenuFire.async({
                    email,
                    displayName,
                    fieldType,
                    action: "select_alias",
                    aliasEmail: ae,
                  });
              })(alias.email),
            );
            existingPopup.appendChild(item);
          }
        }
      } else {
        for (const alias of existingAliases) {
          const item = doc.createXULElement("menuitem");
          item.setAttribute("label", alias.email);
          item.addEventListener(
            "command",
            (function (ae) {
              return () =>
                chipMenuFire &&
                chipMenuFire.async({
                  email,
                  displayName,
                  fieldType,
                  action: "select_alias",
                  aliasEmail: ae,
                });
            })(alias.email),
          );
          existingPopup.appendChild(item);
        }
      }

      existingMenu.appendChild(existingPopup);
      menuPopup.appendChild(existingMenu);

      // ── New… ▶ ───────────────────────────────────────────────────────────────
      const newMenu = doc.createXULElement("menu");
      newMenu.setAttribute("label", "New…");
      newMenu.setAttribute("image", ICON_NEW);
      const newPopup = doc.createXULElement("menupopup");

      if (availableDomains.length > 1) {
        for (const domain of availableDomains) {
          const dmMenu = doc.createXULElement("menu");
          dmMenu.setAttribute("label", `@${domain}`);
          const dmPopup = doc.createXULElement("menupopup");
          buildFormatItems(dmPopup, doc, win, email, displayName, fieldType, domain);
          dmMenu.appendChild(dmPopup);
          newPopup.appendChild(dmMenu);
        }
      } else {
        buildFormatItems(newPopup, doc, win, email, displayName, fieldType, defaultDomain);
      }

      newMenu.appendChild(newPopup);
      menuPopup.appendChild(newMenu);

      menu.appendChild(menuPopup);
      return menu;
    }

    function attachToWindow(win) {
      if (attached.has(win)) return;
      const doc = win.document;

      let pendingPill = null;
      let pendingReset = null;

      function onContextMenu(e) {
        // composedPath() crosses shadow-DOM boundaries; closest() does not.
        let pill = e.composedPath().find(
          (el) => el.tagName && el.tagName.toLowerCase() === "mail-address-pill",
        ) ?? null;
        // Fallback: in some chrome contexts composedPath may not surface the host.
        if (!pill && e.target?.tagName?.toLowerCase() === "mail-address-pill") {
          pill = e.target;
        }
        console.log(
          "AnonAddyTB contextmenu path:",
          e.composedPath().map((el) => el.tagName).filter(Boolean),
          "pill:", pill,
        );
        if (!pill) {
          pendingPill = null;
          return;
        }
        // Skip Reply-To pills — Addy alias sending doesn't apply there.
        const addressRow = pill.closest(".address-row");
        const fieldType = (addressRow?.dataset?.recipienttype || "").toLowerCase();
        if (fieldType === "reply-to" || fieldType === "replyto") {
          pendingPill = null;
          return;
        }
        pendingPill = pill;
        clearTimeout(pendingReset);
        pendingReset = setTimeout(() => {
          pendingPill = null;
        }, 500);
      }

      function onPopupShowing(e) {
        if (!pendingPill) return;
        const popup = e.target;
        console.log("AnonAddyTB popupshowing tag:", popup.tagName, "triggerNode:", popup.triggerNode);
        if (popup.tagName.toLowerCase() !== "menupopup") return;

        // Guard against consuming pendingPill for unrelated menupopups (e.g.
        // autocomplete dropdowns). For right-click context menus triggerNode is
        // the element that was right-clicked; for other popups it is often null
        // or a text input.  Only skip if triggerNode is set but NOT our pill.
        const trigger = popup.triggerNode;
        if (trigger) {
          const inPill =
            trigger === pendingPill ||
            pendingPill.contains(trigger) ||
            trigger.getRootNode?.()?.host === pendingPill;
          if (!inPill) return; // not the pill's context menu — keep pendingPill
        }

        const pill = pendingPill;
        pendingPill = null;
        clearTimeout(pendingReset);

        const sep = doc.createXULElement("menuseparator");
        const addyMenu = buildAddyMenu(doc, win, pill);

        popup.appendChild(sep);
        popup.appendChild(addyMenu);

        // Use a named handler (no { once: true }) so we can guard against
        // popuphidden events that bubble up from child popups (e.g. the Addy
        // submenu closing).  { once: true } would be consumed by the first
        // bubbled child-popup event and never fire for the outer popup close.
        popup.addEventListener("popuphidden", function onPopupHidden(e) {
          if (e.target !== popup) return;
          popup.removeEventListener("popuphidden", onPopupHidden);
          sep.remove();
          addyMenu.remove();
        });
      }

      doc.addEventListener("contextmenu", onContextMenu, true);
      doc.addEventListener("popupshowing", onPopupShowing, true);

      attached.set(win, () => {
        doc.removeEventListener("contextmenu", onContextMenu, true);
        doc.removeEventListener("popupshowing", onPopupShowing, true);
        clearTimeout(pendingReset);
      });
    }

    const windowListener = {
      onOpenWindow(xulWin) {
        const win = xulWin
          .QueryInterface(Ci.nsIInterfaceRequestor)
          .getInterface(Ci.nsIDOMWindow);
        win.addEventListener(
          "load",
          () => {
            if (
              win.document.documentElement.getAttribute("windowtype") !==
              "msgcompose"
            )
              return;
            attachToWindow(win);
          },
          { once: true },
        );
      },
      onCloseWindow(xulWin) {
        const win = xulWin
          .QueryInterface(Ci.nsIInterfaceRequestor)
          .getInterface(Ci.nsIDOMWindow);
        const cleanup = attached.get(win);
        if (cleanup) {
          cleanup();
          attached.delete(win);
        }
      },
    };

    return {
      AddressChipMenu: {
        setCache(data) {
          _cacheData = data;
        },

        onChipMenuClicked: new ExtensionCommon.EventManager({
          context,
          name: "AddressChipMenu.onChipMenuClicked",
          register(fire) {
            chipMenuFire = fire;

            Services.wm.addListener(windowListener);

            const iter = Services.wm.getEnumerator("msgcompose");
            while (iter.hasMoreElements()) {
              const win = iter.getNext();
              if (win.document.readyState === "complete") {
                attachToWindow(win);
              }
            }

            return () => {
              chipMenuFire = null;
              Services.wm.removeListener(windowListener);
              for (const cleanup of attached.values()) cleanup();
              attached.clear();
            };
          },
        }).api(),
      },
    };
  }
};
