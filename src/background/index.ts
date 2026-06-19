import { addyApiRequest, RateLimitError } from "../api/index.js";
import type {
  DomainOptions,
  Alias,
  PaginatedAliases,
  CreateAliasBody,
  AliasFormat,
} from "../api/types.js";
import {
  mergeAliasesIntoCache,
  type AliasCache,
} from "../shared/aliasCache.js";
import { shouldSyncCacheToExperiment } from "./cacheSync.js";

async function fetchDomainOptions(): Promise<void> {
  const result = await addyApiRequest<DomainOptions>("GET", "domain-options");
  await messenger.storage.local.set({ domainOptions: result });
}

async function fetchAllAliases(): Promise<void> {
  const all: Alias[] = [];
  let page = 1;
  while (true) {
    let response: PaginatedAliases;
    try {
      response = await addyApiRequest<PaginatedAliases>("GET", "aliases", {
        page: String(page),
        "page[size]": "100",
      });
    } catch (e) {
      if (e instanceof RateLimitError) {
        await new Promise((resolve) =>
          setTimeout(resolve, e.retryAfterSeconds * 1000),
        );
        continue;
      }
      throw e;
    }
    all.push(...response.data);
    if (response.meta.current_page >= response.meta.last_page) break;
    page++;
  }
  await messenger.storage.local.set({
    aliasCache: { aliases: all, fetchedAt: Date.now() },
  });
}

async function syncCacheToExperiment(): Promise<void> {
  const storage = await messenger.storage.local.get({
    domainOptions: {
      data: [],
      defaultAliasDomain: "",
      defaultAliasFormat: "random_characters",
    },
    aliasCache: { aliases: [], fetchedAt: 0 },
  });
  messenger.AddressChipMenu.setCache({
    aliases: (storage.aliasCache as { aliases: Alias[] }).aliases,
    domainOptions: storage.domainOptions as DomainOptions,
  });
}

async function refreshCache(): Promise<void> {
  await Promise.all([fetchDomainOptions(), fetchAllAliases()]);
  // Push fresh data into the experiment so context menus stay current.
  try {
    await syncCacheToExperiment();
  } catch {
    // Non-fatal — context menus will use stale data until next refresh.
  }
}

async function refreshAliasesForDomain(domain: string): Promise<void> {
  const stored = await messenger.storage.local.get({
    aliasCache: { aliases: [] as Alias[], fetchedAt: 0 },
  });
  const response = await addyApiRequest<{ data: Alias[] }>("GET", "aliases", {
    "filter[search]": domain,
    "filter[active]": "true",
  });
  const merged = mergeAliasesIntoCache(
    stored.aliasCache as AliasCache,
    response.data,
  );
  await messenger.storage.local.set({ aliasCache: merged });
  await syncCacheToExperiment();
}

// ── Helpers ────────────────────────────────────────────────────────────────────

async function findComposeTabId(): Promise<number | null> {
  try {
    const win = await messenger.windows.getLastFocused();
    if (win.id === undefined) return null;
    const tabs = await messenger.tabs.query({ windowId: win.id });
    return tabs[0]?.id ?? null;
  } catch {
    return null;
  }
}

function buildForwardingAddress(
  recipientEmail: string,
  recipientName: string,
  aliasEmail: string,
): string {
  const rm = recipientEmail.match(/^(.+)@(.+)$/);
  const am = aliasEmail.match(/^(.+)@(.+)$/);
  if (!rm || !am) return recipientEmail;
  const forwarding = `${am[1]}+${rm[1]}=${rm[2]}@${am[2]}`;
  return recipientName ? `${recipientName} <${forwarding}>` : forwarding;
}

async function applyAliasToCompose(
  tabId: number,
  recipientEmail: string,
  recipientName: string,
  aliasEmail: string,
): Promise<void> {
  const details = await messenger.compose.getComposeDetails(tabId);
  const lower = recipientEmail.toLowerCase();

  function rewrite(list: string[]): string[] {
    return list.map((raw) => {
      if (!raw.toLowerCase().includes(lower)) return raw;
      // Extract display name from "Name <email>" or plain "email"
      const nameMatch = raw.match(/^(.*?)\s*<[^>]+>$/);
      const name = nameMatch ? nameMatch[1].trim() : recipientName;
      return buildForwardingAddress(recipientEmail, name, aliasEmail);
    });
  }

  await messenger.compose.setComposeDetails(tabId, {
    to: rewrite(details.to),
    cc: rewrite(details.cc),
    bcc: rewrite(details.bcc),
  });
}

async function openAliasWindow(tabId: number): Promise<void> {
  await messenger.windows.create({
    url: messenger.runtime.getURL("composePopup.html") + `?tabId=${tabId}`,
    type: "popup",
    width: 640,
    height: 600,
  });
}

// ── Lifecycle ──────────────────────────────────────────────────────────────────

// Push stored cache into the experiment on every service-worker activation.
// The MV3 service worker restarts frequently; experiment module-level state
// (_cacheData) resets each time, so we sync it immediately from storage.
void syncCacheToExperiment().catch(() => {});

messenger.runtime.onStartup.addListener(() => {
  void syncCacheToExperiment().catch(() => {});
});

messenger.alarms.create("cache-refresh", { periodInMinutes: 60 });

messenger.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === "cache-refresh") {
    try {
      await refreshCache();
    } catch (e) {
      console.error("AddyTB: cache refresh failed", e);
    }
  }
});

messenger.storage.onChanged.addListener(async (changes) => {
  if (changes.options) {
    try {
      await refreshCache();
    } catch (e) {
      console.error("AddyTB: cache refresh on settings change failed", e);
    }
    return;
  }

  if (shouldSyncCacheToExperiment(changes)) {
    try {
      await syncCacheToExperiment();
    } catch (e) {
      console.error("AddyTB: cache sync to experiment failed", e);
    }
  }
});

messenger.runtime.onInstalled.addListener(async ({ reason: _reason }) => {
  const { options } = await messenger.storage.local.get({ options: {} });
  const opts = options as { apiKey?: string };
  if (!opts.apiKey) messenger.runtime.openOptionsPage();
  try {
    await refreshCache();
  } catch (e) {
    console.error("AddyTB: initial cache refresh failed", e);
  }
});

// Create-alias popup window → create alias and apply it to the compose tab.
messenger.runtime.onMessage.addListener(async (rawMessage) => {
  const message = rawMessage as {
    action: string;
    tabId?: number;
    email?: string;
    name?: string;
    domain?: string;
    format?: string;
    customPrefix?: string;
  };
  if (message.action === "alias_cache_updated") {
    await syncCacheToExperiment();
    return { success: true };
  }
  if (message.action === "refresh_aliases_for_domain") {
    if (!message.domain) return { success: false, error: "Missing domain" };
    await refreshAliasesForDomain(message.domain);
    return { success: true };
  }
  if (message.action !== "create_alias_and_apply") return;
  if (
    message.tabId === undefined ||
    !message.email ||
    message.name === undefined ||
    !message.domain ||
    !message.format
  ) {
    return { success: false, error: "Missing create alias parameters" };
  }
  try {
    const body: CreateAliasBody = {
      domain: message.domain,
      description: `Created by AddyTB for sending to ${message.email}`,
      format: message.format as AliasFormat,
    };
    if (message.format === "custom" && message.customPrefix?.trim()) {
      body.local_part = message.customPrefix.trim();
    }
    const response = await addyApiRequest<{ data: Alias }>(
      "POST",
      "aliases",
      null,
      body,
    );
    const alias = response.data;
    await applyAliasToCompose(
      message.tabId,
      message.email,
      message.name,
      alias.email,
    );
    refreshCache().catch(() => {});
    return { success: true, aliasEmail: alias.email };
  } catch (e) {
    return {
      success: false,
      error: e instanceof Error ? e.message : String(e),
    };
  }
});

// Toolbar button click → open alias window for the current compose tab.
messenger.composeAction.onClicked.addListener(async (tab) => {
  try {
    await openAliasWindow(tab.id);
  } catch (e) {
    console.error("AddyTB: could not open alias window", e);
  }
});

// Right-click context menu actions on address chips.
messenger.AddressChipMenu.onChipMenuClicked.addListener(async (info) => {
  const action = info.action ?? "open_popup";

  if (action === "open_popup") {
    try {
      const win = await messenger.windows.getLastFocused();
      if (win.id !== undefined) {
        const tabs = await messenger.tabs.query({ windowId: win.id });
        const tab = tabs[0];
        if (tab?.id !== undefined) {
          await openAliasWindow(tab.id);
          return;
        }
      }
      console.error(
        "AddyTB: could not find compose tab for chip menu click",
      );
    } catch (e) {
      console.error(
        "AddyTB: could not open alias window from chip menu",
        e,
      );
    }
    return;
  }

  if (action === "refresh_aliases") {
    if (!info.domain) return;
    try {
      await refreshAliasesForDomain(info.domain);
    } catch (e) {
      console.error(
        "AddyTB: could not refresh aliases from context menu",
        e,
      );
    }
    return;
  }

  const tabId = await findComposeTabId();
  if (tabId === null) {
    console.error(
      "AddyTB: could not find compose tab for chip action",
      action,
    );
    return;
  }

  if (action === "select_alias") {
    if (!info.aliasEmail) return;
    try {
      await applyAliasToCompose(
        tabId,
        info.email,
        info.displayName,
        info.aliasEmail,
      );
    } catch (e) {
      console.error("AddyTB: could not apply alias from context menu", e);
    }
    return;
  }

  if (action === "create_alias") {
    if (!info.domain || !info.format) return;
    try {
      const body: CreateAliasBody = {
        domain: info.domain,
        description: `Created by AddyTB for sending to ${info.email}`,
        format: info.format as AliasFormat,
      };
      if (info.format === "custom" && info.customPrefix?.trim()) {
        body.local_part = info.customPrefix.trim();
      }
      const response = await addyApiRequest<{ data: Alias }>(
        "POST",
        "aliases",
        null,
        body,
      );
      const aliasEmail = response.data.email;
      await applyAliasToCompose(
        tabId,
        info.email,
        info.displayName,
        aliasEmail,
      );
      // Refresh cache in the background so the new alias shows up next time.
      refreshCache().catch(() => {});
    } catch (e) {
      console.error("AddyTB: could not create alias from context menu", e);
    }
  }
});
