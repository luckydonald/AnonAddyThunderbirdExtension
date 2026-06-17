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

messenger.alarms.create("cache-refresh", { periodInMinutes: 60 });

messenger.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === "cache-refresh") await refreshCache();
});

messenger.storage.onChanged.addListener(async (changes) => {
  if (changes.options) await refreshCache();
});

messenger.runtime.onInstalled.addListener(async ({ reason: _reason }) => {
  const { options } = await messenger.storage.local.get({ options: {} });
  const opts = options as { apiKey?: string };
  if (!opts.apiKey) messenger.runtime.openOptionsPage();
  await refreshCache();
});

// Open the compose popup when the user right-clicks an address chip and
// selects "Replace with Addy alias…". The compose popup handles alias
// selection and address rewriting for all recipients in that window.
messenger.AddressChipMenu.onChipMenuClicked.addListener(async (_info) => {
  try {
    await messenger.composeAction.openPopup();
  } catch (e) {
    console.error("AnonAddyTB: could not open popup from chip menu", e);
  }
});
