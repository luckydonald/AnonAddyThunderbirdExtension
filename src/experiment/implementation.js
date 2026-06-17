"use strict";

/* global ChromeUtils, Services, Ci */

var { ExtensionCommon } = ChromeUtils.importESModule(
  "resource://gre/modules/ExtensionCommon.sys.mjs",
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
    .filter((a) => a.active && a.email.toLowerCase().includes(domain))
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
      const fieldType = addressRow?.dataset?.recipienttype || "to";

      const availableDomains = _cacheData.domainOptions?.data || [];
      const defaultDomain =
        _cacheData.domainOptions?.defaultAliasDomain ||
        availableDomains[0] ||
        "";
      const existingAliases = matchingAliasesForEmail(email);

      // Top-level menu entry
      const menu = doc.createXULElement("menu");
      menu.setAttribute("label", "Use Addy alias for sending");
      const menuPopup = doc.createXULElement("menupopup");

      // "Open alias picker…" opens the full popup window
      const pickerItem = doc.createXULElement("menuitem");
      pickerItem.setAttribute("label", "Open alias picker…");
      pickerItem.addEventListener("command", () => {
        chipMenuFire &&
          chipMenuFire.async({
            email,
            displayName,
            fieldType,
            action: "open_popup",
          });
      });
      menuPopup.appendChild(pickerItem);

      menuPopup.appendChild(doc.createXULElement("menuseparator"));

      // ── Existing… ▶ ──────────────────────────────────────────────────────────
      const existingMenu = doc.createXULElement("menu");
      existingMenu.setAttribute("label", "Existing…");
      const existingPopup = doc.createXULElement("menupopup");

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
        const pill = e.target.closest("mail-address-pill");
        if (!pill) {
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
        if (popup.tagName.toLowerCase() !== "menupopup") return;

        const pill = pendingPill;
        pendingPill = null;
        clearTimeout(pendingReset);

        const sep = doc.createXULElement("menuseparator");
        const addyMenu = buildAddyMenu(doc, win, pill);

        popup.appendChild(sep);
        popup.appendChild(addyMenu);

        popup.addEventListener(
          "popuphidden",
          () => {
            sep.remove();
            addyMenu.remove();
          },
          { once: true },
        );
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
