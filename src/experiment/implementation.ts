import { parseForwardingAddress } from "../shared/forwardingAddress.js";
import {
  decoratePillViaAttributes,
  decoratePillViaTextNode,
  decoratePillViaCSSAdopted,
  upsertPillIcon,
  removePillIcon,
} from "./pillDecoration.js";
import { createMenuIconUrls } from "./menuIcons.js";
import { createWindowAttachmentLifecycle } from "./windowAttachmentLifecycle.js";
import {
  aliasesForContextMenuEmail,
  domainForContextMenuAliasLookup,
} from "./aliasMatching.js";
import { setXulIcon } from "./xulIcon.js";

// ChromeUtils, Services, Ci are privileged TB globals; see src/types/experiment.d.ts.
const { ExtensionCommon } = ChromeUtils.importESModule(
  "resource://gre/modules/ExtensionCommon.sys.mjs",
) as any;
const { ExtensionStorageIDB } = ChromeUtils.importESModule(
  "resource://gre/modules/ExtensionStorageIDB.sys.mjs",
) as any;
// setTimeout/clearTimeout are not in scope in privileged extension JS.
const { setTimeout, clearTimeout } = ChromeUtils.importESModule(
  "resource://gre/modules/Timer.sys.mjs",
) as any;
const { NetUtil } = ChromeUtils.importESModule(
  "resource://gre/modules/NetUtil.sys.mjs",
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
let chipMenuFire: any = null;

function getAddyDomainSet(): Set<string> {
  return new Set(
    (_cacheData.domainOptions?.data || []).map((d) => d.toLowerCase()),
  );
}

function fetchJson(
  method: string,
  url: string,
  headers: Record<string, string>,
  body: string | null = null,
): Promise<any> {
  return new Promise((resolve, reject) => {
    const channel = NetUtil.newChannel({
      uri: url,
      loadUsingSystemPrincipal: true,
    }).QueryInterface(Ci.nsIHttpChannel);
    for (const [key, value] of Object.entries(headers)) {
      channel.setRequestHeader(key, value, false);
    }
    if (body !== null) {
      const stream = Components.classes[
        "@mozilla.org/io/string-input-stream;1"
      ].createInstance(Ci.nsIStringInputStream);
      stream.setByteStringData(body);
      channel
        .QueryInterface(Ci.nsIUploadChannel)
        .setUploadStream(stream, "application/json", -1);
    }
    channel.requestMethod = method;
    NetUtil.asyncFetch(channel, (inputStream: any, status: any) => {
      if (!Components.isSuccessCode(status)) {
        reject(new Error(`HTTP fetch failed: ${status}`));
        return;
      }
      const text = NetUtil.readInputStreamToString(
        inputStream,
        inputStream.available(),
      );
      const httpStatus = channel.responseStatus;
      if (httpStatus < 200 || httpStatus >= 300) {
        reject(new Error(`HTTP ${httpStatus}: ${text}`));
        return;
      }
      resolve(JSON.parse(text));
    });
  });
}

const FORMAT_ITEMS = [
  { value: "random_characters", label: "Characters" },
  { value: "random_words", label: "Words" },
  { value: "random_male_name", label: "Male name" },
  { value: "random_female_name", label: "Female name" },
  { value: "random_noun", label: "Noun" },
  { value: "custom", label: "Custom…" },
] as const;

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
    // Each value is { cleanup, doc, pillIconMap } so setCache can re-decorate.
    const attached = new Map<
      any,
      {
        cleanup(): void;
        doc: any;
        pillIconMap: WeakMap<Element, HTMLImageElement>;
      }
    >();
    const activeExistingMenuRenderers = new Set<() => void>();

    const ICONS = createMenuIconUrls(context.extension.baseURI.spec);

    async function refreshAliasesForDomainInExperiment(
      domain: string,
    ): Promise<void> {
      const principal = ExtensionStorageIDB.getStoragePrincipal(
        context.extension,
      );
      const db = await ExtensionStorageIDB.open(principal);
      const storage = await db.get(["options", "aliasCache", "domainOptions"]);
      const options = (storage.options ?? {}) as {
        hostUrl?: string | null;
        apiKey?: string;
      };
      const hostUrl = options.hostUrl || "https://app.addy.io";
      if (!options.apiKey) throw new Error("No API key configured");

      const params = `filter%5Bsearch%5D=${encodeURIComponent(domain)}&filter%5Bactive%5D=true`;
      const response = await fetchJson(
        "GET",
        `${hostUrl}/api/v1/aliases?${params}`,
        {
          Authorization: `Bearer ${options.apiKey}`,
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest",
        },
      );

      const storedCache = storage.aliasCache ?? { aliases: [], fetchedAt: 0 };
      const aliases = [...(storedCache.aliases ?? [])];
      for (const fresh of response.data ?? []) {
        const index = aliases.findIndex((alias: any) => alias.id === fresh.id);
        if (index >= 0) aliases[index] = fresh;
        else aliases.push(fresh);
      }

      const aliasCache = { aliases, fetchedAt: Date.now() };
      await db.set({ aliasCache });
      _cacheData = {
        aliases,
        domainOptions: storage.domainOptions ?? _cacheData.domainOptions,
      };
      activeExistingMenuRenderers.forEach((render) => render());
      for (const { doc, pillIconMap } of attached.values()) {
        decorateAllPills(doc, pillIconMap);
      }
    }

    async function createAliasInExperiment(body: any): Promise<any> {
      const principal = ExtensionStorageIDB.getStoragePrincipal(
        context.extension,
      );
      const db = await ExtensionStorageIDB.open(principal);
      const storage = await db.get(["options", "aliasCache", "domainOptions"]);
      const options = (storage.options ?? {}) as {
        hostUrl?: string | null;
        apiKey?: string;
      };
      const hostUrl = options.hostUrl || "https://app.addy.io";
      if (!options.apiKey) throw new Error("No API key configured");

      const response = await fetchJson(
        "POST",
        `${hostUrl}/api/v1/aliases`,
        {
          Authorization: `Bearer ${options.apiKey}`,
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest",
        },
        JSON.stringify(body),
      );
      const alias = response.data;
      const storedCache = storage.aliasCache ?? { aliases: [], fetchedAt: 0 };
      const aliases = [...(storedCache.aliases ?? [])];
      if (alias) {
        const index = aliases.findIndex((item: any) => item.id === alias.id);
        if (index >= 0) aliases[index] = alias;
        else aliases.push(alias);
      }
      const aliasCache = { aliases, fetchedAt: Date.now() };
      await db.set({ aliasCache });
      _cacheData = {
        aliases,
        domainOptions: storage.domainOptions ?? _cacheData.domainOptions,
      };
      activeExistingMenuRenderers.forEach((render) => render());
      return alias;
    }

    function fireChipMenuAction(info: Record<string, unknown>): void {
      const wakeAndRetry = () => {
        Promise.resolve(context.extension.wakeupBackground?.())
          .then(() => {
            chipMenuFire && chipMenuFire.async(info);
          })
          .catch((e) => {
            console.error("AddyTB: could not wake chip menu listener", e);
          });
      };

      if (!chipMenuFire) {
        wakeAndRetry();
        return;
      }
      try {
        const result = chipMenuFire.sync(info);
        Promise.resolve(result).catch((e) => {
          console.error("AddyTB: chip menu action rejected", e);
          wakeAndRetry();
        });
      } catch (e) {
        console.error("AddyTB: could not dispatch chip menu action", e);
        wakeAndRetry();
      }
    }

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
        decoratePillViaAttributes(pill, label);
        decoratePillViaTextNode(pill, label);
        decoratePillViaCSSAdopted(pill, label);
        upsertPillIcon(pill, pillIconMap, ICONS.addy, true);
      } else if (getAddyDomainSet().has(domain)) {
        decoratePillViaAttributes(pill, null);
        decoratePillViaTextNode(pill, null);
        decoratePillViaCSSAdopted(pill, null);
        upsertPillIcon(pill, pillIconMap, ICONS.addy, false);
      } else {
        decoratePillViaAttributes(pill, null);
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
        if (fmtIcon) setXulIcon(item, fmtIcon);
        if (fmt.value === "custom") {
          const createCustomAlias = (d: string) => {
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
            fireChipMenuAction({
              email,
              displayName,
              fieldType,
              action: "create_alias",
              domain: d,
              format: "custom",
              customPrefix: valueObj.value.trim(),
            });
            createAliasInExperiment({
              domain: d,
              description: `Created by AddyTB for sending to ${email}`,
              format: "custom",
              local_part: valueObj.value.trim(),
            }).catch((e) => {
              item.setAttribute(
                "data-addy-create-error",
                e instanceof Error ? e.message : String(e),
              );
              console.error("AddyTB: could not create alias in menu", e);
            });
          };
          (item as any)._addyRunCommand = () => createCustomAlias(domain);
          item.addEventListener(
            "command",
            (function (d: string) {
              return () => createCustomAlias(d);
            })(domain),
          );
        } else {
          const createAlias = (f: string, d: string) => {
            fireChipMenuAction({
              email,
              displayName,
              fieldType,
              action: "create_alias",
              domain: d,
              format: f,
              customPrefix: "",
            });
            createAliasInExperiment({
              domain: d,
              description: `Created by AddyTB for sending to ${email}`,
              format: f,
            }).catch((e) => {
              item.setAttribute(
                "data-addy-create-error",
                e instanceof Error ? e.message : String(e),
              );
              console.error("AddyTB: could not create alias in menu", e);
            });
          };
          (item as any)._addyRunCommand = () => createAlias(fmt.value, domain);
          item.addEventListener(
            "command",
            (function (f: string, d: string) {
              return () => createAlias(f, d);
            })(fmt.value, domain),
          );
        }
        parentPopup.appendChild(item);
      }
    }

    function addOpenPickerItem(
      existingPopup: any,
      doc: any,
      email: string,
      displayName: string,
      fieldType: string,
    ): void {
      const pickerItem = doc.createXULElement("menuitem");
      pickerItem.setAttribute("label", "Open alias picker…");
      setXulIcon(pickerItem, ICONS.picker);
      pickerItem.addEventListener("command", () => {
        fireChipMenuAction({
          email,
          displayName,
          fieldType,
          action: "open_popup",
        });
      });
      existingPopup.appendChild(pickerItem);
      existingPopup.appendChild(doc.createXULElement("menuseparator"));
    }

    function addExistingAliasItem(
      parentPopup: any,
      doc: any,
      email: string,
      displayName: string,
      fieldType: string,
      aliasEmail: string,
    ): void {
      const item = doc.createXULElement("menuitem");
      item.setAttribute("label", aliasEmail);
      setXulIcon(item, ICONS.alias);
      item.addEventListener(
        "command",
        (function (ae: string) {
          return () =>
            fireChipMenuAction({
              email,
              displayName,
              fieldType,
              action: "select_alias",
              aliasEmail: ae,
            });
        })(aliasEmail),
      );
      parentPopup.appendChild(item);
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
      const lookupDomain = domainForContextMenuAliasLookup(
        email,
        getAddyDomainSet(),
      );

      // Top-level menu entry — direct click opens popup, hover/arrow unfolds submenu.
      const menu = doc.createXULElement("menu");
      menu.setAttribute("label", "Use Addy alias for sending");
      setXulIcon(menu, ICONS.addy);
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
          fireChipMenuAction({
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
      setXulIcon(existingMenu, ICONS.existing);
      const existingPopup = doc.createXULElement("menupopup");

      const renderExistingItems = () => {
        existingPopup.replaceChildren();
        addOpenPickerItem(existingPopup, doc, email, displayName, fieldType);

        const aliases = aliasesForContextMenuEmail(
          _cacheData.aliases,
          email,
          getAddyDomainSet(),
        );
        if (aliases.length === 0) {
          const noItem = doc.createXULElement("menuitem");
          noItem.setAttribute("label", "No existing aliases for this domain");
          noItem.setAttribute("disabled", "true");
          existingPopup.appendChild(noItem);
          return;
        }

        if (aliases.length > 5) {
          const domainGroups = new Map<string, any[]>();
          for (const alias of aliases) {
            const dm = alias.email.match(/@(.+)$/)?.[1] ?? "";
            if (!domainGroups.has(dm)) domainGroups.set(dm, []);
            domainGroups.get(dm)!.push(alias);
          }

          if (domainGroups.size > 1) {
            for (const [dm, groupAliases] of domainGroups) {
              const dmMenu = doc.createXULElement("menu");
              dmMenu.setAttribute("label", `…@${dm}`);
              setXulIcon(dmMenu, ICONS.domain);
              const dmPopup = doc.createXULElement("menupopup");
              for (const alias of groupAliases) {
                addExistingAliasItem(
                  dmPopup,
                  doc,
                  email,
                  displayName,
                  fieldType,
                  alias.email,
                );
              }
              dmMenu.appendChild(dmPopup);
              existingPopup.appendChild(dmMenu);
            }
            return;
          }
        }

        for (const alias of aliases) {
          addExistingAliasItem(
            existingPopup,
            doc,
            email,
            displayName,
            fieldType,
            alias.email,
          );
        }
      };
      renderExistingItems();
      activeExistingMenuRenderers.add(renderExistingItems);
      (menu as any)._addyCleanup = () => {
        activeExistingMenuRenderers.delete(renderExistingItems);
      };
      const refreshExistingAliases = () => {
        if (!lookupDomain) return;
        fireChipMenuAction({
          email,
          displayName,
          fieldType,
          action: "refresh_aliases",
          domain: lookupDomain,
        });
        refreshAliasesForDomainInExperiment(lookupDomain)
          .catch((e) => {
            console.error("AddyTB: could not refresh aliases in menu", e);
          });
      };
      existingPopup.addEventListener("popupshowing", refreshExistingAliases);
      refreshExistingAliases();

      existingMenu.appendChild(existingPopup);
      menuPopup.appendChild(existingMenu);

      // ── New… ▶ ───────────────────────────────────────────────────────────────
      const newMenu = doc.createXULElement("menu");
      newMenu.setAttribute("label", "New…");
      setXulIcon(newMenu, ICONS.newAlias);
      const newPopup = doc.createXULElement("menupopup");

      if (availableDomains.length > 1) {
        for (const domain of availableDomains) {
          const dmMenu = doc.createXULElement("menu");
          dmMenu.setAttribute("label", `@${domain}`);
          setXulIcon(dmMenu, ICONS.domain);
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
          (addyMenu as any)._addyCleanup?.();
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
          activeExistingMenuRenderers.forEach((render) => render());
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
              lifecycle.releaseEventListener();
            };
          },
        }).api(),
      },
    };
  }
};
