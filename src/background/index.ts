import { addyApiRequest } from "../api/index.js";
import type { DomainOptions, Alias, PaginatedAliases } from "../api/types.js";

async function fetchDomainOptions(): Promise<void> {
  const result = await addyApiRequest<DomainOptions>("GET", "domain-options");
  await messenger.storage.local.set({ domainOptions: result });
}

async function fetchAllAliases(): Promise<void> {
  const all: Alias[] = [];
  let page = 1;
  while (true) {
    const response = await addyApiRequest<PaginatedAliases>("GET", "aliases", {
      page: String(page),
      "page[size]": "100",
    });
    all.push(...response.data);
    if (response.meta.current_page >= response.meta.last_page) break;
    page++;
  }
  await messenger.storage.local.set({
    aliasCache: { aliases: all, fetchedAt: Date.now() },
  });
}

async function refreshCache(): Promise<void> {
  await Promise.all([fetchDomainOptions(), fetchAllAliases()]);
}

// Wake the background (and thus activate the Experiment) on Thunderbird startup.
// Without this the background only runs when an alarm or other event fires.
messenger.runtime.onStartup.addListener(() => {});

async function openAliasWindow(tabId: number): Promise<void> {
  await messenger.windows.create({
    url: messenger.runtime.getURL("composePopup.html") + `?tabId=${tabId}`,
    type: "popup",
    width: 640,
    height: 600,
  });
}

messenger.alarms.create("cache-refresh", { periodInMinutes: 60 });

messenger.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === "cache-refresh") {
    try {
      await refreshCache();
    } catch (e) {
      console.error("AnonAddyTB: cache refresh failed", e);
    }
  }
});

messenger.storage.onChanged.addListener(async (changes) => {
  if (changes.options) {
    try {
      await refreshCache();
    } catch (e) {
      console.error("AnonAddyTB: cache refresh on settings change failed", e);
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
    console.error("AnonAddyTB: initial cache refresh failed", e);
  }
});

// Toolbar button click → open alias window for the current compose tab.
messenger.composeAction.onClicked.addListener(async (tab) => {
  try {
    await openAliasWindow(tab.id);
  } catch (e) {
    console.error("AnonAddyTB: could not open alias window", e);
  }
});

// Right-click context menu on address chip → open alias window.
// The compose window is still focused when this fires, so getLastFocused()
// reliably returns it.
messenger.AddressChipMenu.onChipMenuClicked.addListener(async (_info) => {
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
    console.error("AnonAddyTB: could not find compose tab for chip menu click");
  } catch (e) {
    console.error("AnonAddyTB: could not open alias window from chip menu", e);
  }
});
