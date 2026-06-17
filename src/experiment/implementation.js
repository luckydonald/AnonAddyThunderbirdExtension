"use strict";

/* global ChromeUtils, Services, Ci, browser */

var { ExtensionCommon } = ChromeUtils.importESModule(
  "resource://gre/modules/ExtensionCommon.sys.mjs",
);

// AddressChipMenu Experiment API
//
// Hooks contextmenu on <mail-address-pill> elements in every compose window.
// When the user right-clicks a chip and selects "Replace with Addy alias…",
// fires AddressChipMenu.onChipMenuClicked to the WebExtension background.
this.AddressChipMenu = class extends ExtensionCommon.ExtensionAPI {
  getAPI(context) {
    return {
      AddressChipMenu: {
        onChipMenuClicked: new ExtensionCommon.EventManager({
          context,
          name: "AddressChipMenu.onChipMenuClicked",
          register(fire) {
            // Map from nsIDOMWindow → cleanup function for that window
            const attached = new Map();

            function attachToWindow(win) {
              if (attached.has(win)) return;
              const doc = win.document;

              // Capture phase so we run before the browser's default context menu
              function onContextMenu(e) {
                const pill = e.target.closest("mail-address-pill");
                if (!pill) return;

                e.preventDefault();
                e.stopPropagation();

                const email = pill.getAttribute("emailAddress") || "";
                const displayName = pill.getAttribute("displayName") || "";
                const addressRow = pill.closest(".address-row");
                const fieldType = addressRow?.dataset?.recipienttype || "to";

                // Build a minimal XUL menupopup for our action
                const popup = doc.createXULElement("menupopup");
                const item = doc.createXULElement("menuitem");
                item.setAttribute(
                  "label",
                  browser.i18n.getMessage("replaceWithAddyAlias"),
                );

                item.addEventListener(
                  "command",
                  () => {
                    fire.async({ email, displayName, fieldType });
                    popup.remove();
                  },
                  { once: true },
                );

                popup.appendChild(item);
                doc.documentElement.appendChild(popup);

                popup.addEventListener("popuphidden", () => popup.remove(), {
                  once: true,
                });

                popup.openPopupAtScreen(e.screenX, e.screenY, true);
              }

              doc.addEventListener("contextmenu", onContextMenu, true);
              attached.set(win, () =>
                doc.removeEventListener("contextmenu", onContextMenu, true),
              );
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
                      win.document.documentElement.getAttribute(
                        "windowtype",
                      ) !== "msgcompose"
                    ) {
                      return;
                    }
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

            Services.wm.addListener(windowListener);

            // Attach to any compose windows that are already open
            const iter = Services.wm.getEnumerator("msgcompose");
            while (iter.hasMoreElements()) {
              const win = iter.getNext();
              if (win.document.readyState === "complete") {
                attachToWindow(win);
              }
            }

            return () => {
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
