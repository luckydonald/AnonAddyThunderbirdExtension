import { parseForwardingAddress } from "../shared/forwardingAddress.js";
import {
  decoratePillViaTextNode,
  decoratePillViaCSSAdopted,
  upsertPillIcon,
  removePillIcon,
} from "./pillDecoration.js";
import { createMenuIconUrls } from "./menuIcons.js";
import { createWindowAttachmentLifecycle } from "./windowAttachmentLifecycle.js";

// ChromeUtils, Services, Ci are privileged TB globals; see src/types/experiment.d.ts.
const { ExtensionCommon } = ChromeUtils.importESModule(
  "resource://gre/modules/ExtensionCommon.sys.mjs",
) as any;
// setTimeout/clearTimeout are not in scope in privileged extension JS.
const { setTimeout, clearTimeout } = ChromeUtils.importESModule(
  "resource://gre/modules/Timer.sys.mjs",
) as any;

// Alias and domain-option data pushed from the background after each cache refresh.
let _cacheData: {
  aliases: any[];
  domainOptions: {
    data: string[];
    defaultAliasDomain: string;
    defaultAliasFormat: string;
  };
} = {
  aliases: [],
  domainOptions: {
    data: [],
    defaultAliasDomain: "",
    defaultAliasFormat: "random_characters",
  },
};

function getAddyDomainSet(): Set<string> {
  return new Set(
    (_cacheData.domainOptions?.data || []).map((d) => d.toLowerCase()),
  );
}

const FORMAT_ITEMS = [
  { value: "random_characters", label: "Characters" },
  { value: "random_words", label: "Words" },
  { value: "random_male_name", label: "Male name" },
  { value: "random_female_name", label: "Female name" },
  { value: "random_noun", label: "Noun" },
  { value: "custom", label: "Custom…" },
] as const;

// Inline version of aliasSearch.ts matchingAliasesForEmail.
// Keep in sync with src/shared/aliasSearch.ts.
function matchingAliasesForEmail(email: string): any[] {
  const m = email.match(/@(.+)$/);
  if (!m) return [];
  const domain = m[1].toLowerCase();
  return (_cacheData.aliases || [])
    .filter(
      (a: any) =>
        a.active && (a.description ?? "").toLowerCase().includes(domain),
    )
    .slice(0, 20);
}

// AddressChipMenu Experiment API
//
// Injects an "Use Addy alias for sending" submenu into the existing right-click
// context menu on <mail-address-pill> elements in compose windows.
//
// Compiled to IIFE by vite.experiment.config.ts. TB loads the experiment via
// loadSubScript(url, sandbox): in that context globalThis IS the sandbox, so
// assigning below registers the class where TB's experiment loader looks for it.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
(globalThis as any).AddressChipMenu = class extends (
  (ExtensionCommon as any).ExtensionAPI
) {
  getAPI(context: any) {
    let chipMenuFire: any = null;
    // Each value is { cleanup, doc, pillIconMap } so setCache can re-decorate.
    const attached = new Map<
      any,
      {
        cleanup(): void;
        doc: any;
        pillIconMap: WeakMap<Element, HTMLImageElement>;
      }
    >();

    const ICONS = createMenuIconUrls(context.extension.baseURI.spec);

    // ── Pill decoration ───────────────────────────────────────────────────────

    function injectAddyPillStyles(doc: any): void {
      if (doc.getElementById("addy-pill-styles")) return;
      const style = doc.createElement("style");
      style.id = "addy-pill-styles";
      style.textContent = `
        .addy-pill-icon {
          width: 12px;
          height: 12px;
          vertical-align: middle;
          margin-right: 3px;
          pointer-events: none;
        }
        .addy-pill-icon.addy-aliased {
          filter: grayscale(1) opacity(0.6);
        }
      `;
      doc.head.appendChild(style);
    }

    function decoratePill(
      pill: Element,
      pillIconMap: WeakMap<Element, HTMLImageElement>,
    ): void {
      const email = pill.getAttribute("emailAddress") || "";
      const fwd = parseForwardingAddress(email, getAddyDomainSet());
      const domain = email.match(/@(.+)$/)?.[1]?.toLowerCase() ?? "";

      if (fwd) {
        const label = `${fwd.aliasEmail} → ${fwd.originalEmail}`;
        decoratePillViaTextNode(pill, label);
        decoratePillViaCSSAdopted(pill, label);
        upsertPillIcon(pill, pillIconMap, ICONS.addy, true);
      } else if (getAddyDomainSet().has(domain)) {
        decoratePillViaTextNode(pill, null);
        decoratePillViaCSSAdopted(pill, null);
        upsertPillIcon(pill, pillIconMap, ICONS.addy, false);
      } else {
        decoratePillViaTextNode(pill, null);
        decoratePillViaCSSAdopted(pill, null);
        removePillIcon(pill, pillIconMap);
      }
    }

    function decorateAllPills(
      doc: any,
      pillIconMap: WeakMap<Element, HTMLImageElement>,
    ): void {
      doc.querySelectorAll("mail-address-pill").forEach((pill: Element) => {
        decoratePill(pill, pillIconMap);
      });
    }

    // ── Context menu ──────────────────────────────────────────────────────────

    function buildFormatItems(
      parentPopup: any,
      doc: any,
      win: any,
      email: string,
      displayName: string,
      fieldType: string,
      domain: string,
    ): void {
      for (const fmt of FORMAT_ITEMS) {
        const item = doc.createXULElement("menuitem");
        item.setAttribute("label", fmt.label);
        const fmtIcon = ICONS.format[fmt.value];
        if (fmtIcon) item.setAttribute("image", fmtIcon);
        if (fmt.value === "custom") {
          item.addEventListener(
            "command",
            (function (d: string) {
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
            (function (f: string, d: string) {
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

    function buildAddyMenu(doc: any, win: any, pill: Element): any {
      const email = pill.getAttribute("emailAddress") || "";
      const displayName = pill.getAttribute("displayName") || "";
      const addressRow = pill.closest(".address-row");
      const fieldType = (
        (addressRow as any)?.dataset?.recipienttype || "to"
      ).toLowerCase();

      const availableDomains = _cacheData.domainOptions?.data || [];
      const defaultDomain =
        _cacheData.domainOptions?.defaultAliasDomain ||
        availableDomains[0] ||
        "";
      const existingAliases = matchingAliasesForEmail(email);

      // Top-level menu entry — direct click opens popup, hover/arrow unfolds submenu.
      const menu = doc.createXULElement("menu");
      menu.setAttribute("label", "Use Addy alias for sending");
      menu.setAttribute("image", ICONS.addy);
      const menuPopup = doc.createXULElement("menupopup");
      // Thunderbird's onpopupshowing runs on all menupopup events in the compose window
      // and crashes when triggerNode is not a pill (pill is null → pill.hasAttribute fails).
      // Stop all popupshowing events from menuPopup and its descendant popups from bubbling
      // up to Thunderbird's handler. The outer pill context menu is unaffected.
      menuPopup.addEventListener("popupshowing", (e: Event) =>
        e.stopPropagation(),
      );

      // Direct click on the <menu> element itself (not on a submenu item) opens popup.
      menu.addEventListener("click", (e: Event) => {
        if (e.target === menu) {
          chipMenuFire &&
            chipMenuFire.async({
              email,
              displayName,
              fieldType,
              action: "open_popup",
            });
          e.preventDefault();
        }
      });

      // ── Existing… ▶ ──────────────────────────────────────────────────────────
      const existingMenu = doc.createXULElement("menu");
      existingMenu.setAttribute("label", "Existing…");
      existingMenu.setAttribute("image", ICONS.existing);
      const existingPopup = doc.createXULElement("menupopup");

      // "Open alias picker…" is first in Existing; provides easy access to full GUI.
      const pickerItem = doc.createXULElement("menuitem");
      pickerItem.setAttribute("label", "Open alias picker…");
      pickerItem.setAttribute("image", ICONS.picker);
      pickerItem.addEventListener("command", () => {
        chipMenuFire &&
          chipMenuFire.async({
            email,
            displayName,
            fieldType,
            action: "open_popup",
          });
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
        const domainGroups = new Map<string, any[]>();
        for (const alias of existingAliases) {
          const dm = alias.email.match(/@(.+)$/)?.[1] ?? "";
          if (!domainGroups.has(dm)) domainGroups.set(dm, []);
          domainGroups.get(dm)!.push(alias);
        }

        if (domainGroups.size > 1) {
          for (const [dm, aliases] of domainGroups) {
            const dmMenu = doc.createXULElement("menu");
            dmMenu.setAttribute("label", `…@${dm}`);
            dmMenu.setAttribute("image", ICONS.domain);
            const dmPopup = doc.createXULElement("menupopup");
            for (const alias of aliases) {
              const item = doc.createXULElement("menuitem");
              item.setAttribute("label", alias.email);
              item.setAttribute("image", ICONS.alias);
              item.addEventListener(
                "command",
                (function (ae: string) {
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
            item.setAttribute("image", ICONS.alias);
            item.addEventListener(
              "command",
              (function (ae: string) {
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
          item.setAttribute("image", ICONS.alias);
          item.addEventListener(
            "command",
            (function (ae: string) {
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
      newMenu.setAttribute("image", ICONS.newAlias);
      const newPopup = doc.createXULElement("menupopup");

      if (availableDomains.length > 1) {
        for (const domain of availableDomains) {
          const dmMenu = doc.createXULElement("menu");
          dmMenu.setAttribute("label", `@${domain}`);
          dmMenu.setAttribute("image", ICONS.domain);
          const dmPopup = doc.createXULElement("menupopup");
          buildFormatItems(
            dmPopup,
            doc,
            win,
            email,
            displayName,
            fieldType,
            domain,
          );
          dmMenu.appendChild(dmPopup);
          newPopup.appendChild(dmMenu);
        }
      } else {
        buildFormatItems(
          newPopup,
          doc,
          win,
          email,
          displayName,
          fieldType,
          defaultDomain,
        );
      }

      newMenu.appendChild(newPopup);
      menuPopup.appendChild(newMenu);

      menu.appendChild(menuPopup);
      return menu;
    }

    // ── Window attachment ─────────────────────────────────────────────────────

    function attachToWindow(win: any): void {
      if (attached.has(win)) return;
      const doc = win.document;
      const pillIconMap = new WeakMap<Element, HTMLImageElement>();

      injectAddyPillStyles(doc);
      decorateAllPills(doc, pillIconMap);

      const observer = new win.MutationObserver((mutations: any[]) => {
        for (const mutation of mutations) {
          for (const node of mutation.addedNodes) {
            if (node.tagName?.toLowerCase() === "mail-address-pill") {
              decoratePill(node, pillIconMap);
            }
          }
          for (const node of mutation.removedNodes) {
            if (node.tagName?.toLowerCase() === "mail-address-pill") {
              removePillIcon(node, pillIconMap);
            }
          }
          if (
            mutation.type === "attributes" &&
            mutation.target.tagName?.toLowerCase() === "mail-address-pill"
          ) {
            decoratePill(mutation.target, pillIconMap);
          }
        }
      });

      // Observe the whole document body for pill additions/removals/changes.
      observer.observe(doc.body, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ["emailaddress"],
      });

      let pendingPill: Element | null = null;
      let pendingReset: any = null;

      function onContextMenu(e: Event): void {
        // composedPath() crosses shadow-DOM boundaries; closest() does not.
        let pill =
          (e as any)
            .composedPath()
            .find(
              (el: any) =>
                el.tagName && el.tagName.toLowerCase() === "mail-address-pill",
            ) ?? null;
        // Fallback: in some chrome contexts composedPath may not surface the host.
        if (
          !pill &&
          (e.target as any)?.tagName?.toLowerCase() === "mail-address-pill"
        ) {
          pill = e.target as Element;
        }
        console.log(
          "AnonAddyTB contextmenu path:",
          (e as any)
            .composedPath()
            .map((el: any) => el.tagName)
            .filter(Boolean),
          "pill:",
          pill,
        );
        if (!pill) {
          pendingPill = null;
          return;
        }
        // Skip Reply-To pills — Addy alias sending doesn't apply there.
        const addressRow = pill.closest(".address-row");
        const fieldType = (
          (addressRow as any)?.dataset?.recipienttype || ""
        ).toLowerCase();
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

      function onPopupShowing(e: Event): void {
        if (!pendingPill) return;
        const popup = e.target as any;
        console.log(
          "AnonAddyTB popupshowing tag:",
          popup.tagName,
          "triggerNode:",
          popup.triggerNode,
        );
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
            (trigger as any).getRootNode?.()?.host === pendingPill;
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
        popup.addEventListener("popuphidden", function onPopupHidden(e: Event) {
          if (e.target !== popup) return;
          popup.removeEventListener("popuphidden", onPopupHidden);
          sep.remove();
          addyMenu.remove();
        });
      }

      doc.addEventListener("contextmenu", onContextMenu, true);
      doc.addEventListener("popupshowing", onPopupShowing, true);

      attached.set(win, {
        cleanup() {
          doc.removeEventListener("contextmenu", onContextMenu, true);
          doc.removeEventListener("popupshowing", onPopupShowing, true);
          observer.disconnect();
          clearTimeout(pendingReset);
        },
        doc,
        pillIconMap,
      });
    }

    const windowListener = {
      onOpenWindow(xulWin: any) {
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
      onCloseWindow(xulWin: any) {
        const win = xulWin
          .QueryInterface(Ci.nsIInterfaceRequestor)
          .getInterface(Ci.nsIDOMWindow);
        const entry = attached.get(win);
        if (entry) {
          entry.cleanup();
          attached.delete(win);
        }
      },
    };

    const lifecycle = createWindowAttachmentLifecycle({
      addWindowListener() {
        Services.wm.addListener(windowListener);
      },
      removeWindowListener() {
        Services.wm.removeListener(windowListener);
      },
      attachExistingWindows() {
        const iter = Services.wm.getEnumerator("msgcompose");
        while (iter.hasMoreElements()) {
          const win = iter.getNext();
          if (win.document.readyState === "complete") {
            attachToWindow(win);
          }
        }
      },
      cleanupAttachedWindows() {
        for (const entry of attached.values()) entry.cleanup();
        attached.clear();
      },
    });

    return {
      AddressChipMenu: {
        setCache(data: typeof _cacheData) {
          _cacheData = data;
          lifecycle.ensureAttached();
          for (const { doc, pillIconMap } of attached.values()) {
            decorateAllPills(doc, pillIconMap);
          }
        },

        onChipMenuClicked: new ExtensionCommon.EventManager({
          context,
          name: "AddressChipMenu.onChipMenuClicked",
          register(fire: any) {
            chipMenuFire = fire;
            lifecycle.ensureAttached();

            return () => {
              chipMenuFire = null;
              lifecycle.releaseEventListener();
            };
          },
        }).api(),
      },
    };
  }
};
