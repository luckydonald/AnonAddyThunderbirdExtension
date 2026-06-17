<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import LoadingSpinner from "./components/LoadingSpinner.vue";
import NoRecipientsMessage from "./components/NoRecipientsMessage.vue";
import RecipientCard from "./components/RecipientCard.vue";
import FooterBar from "./components/FooterBar.vue";
import { addyApiRequest } from "../api/index.js";
import { useI18n } from "../composables/useI18n.js";
import type {
  Alias,
  AliasFormat,
  DomainOptions,
  CreateAliasBody,
} from "../api/types.js";

// ─── Types ────────────────────────────────────────────────────────────────────

interface ParsedAddress {
  original: string;
  address: string;
  localPart: string;
  domain: string;
  name: string;
}

interface RecipientState {
  parsed: ParsedAddress;
  existingAliases: Alias[];
  selectedAlias: string | null;
  createdAlias: { id: string; email: string; active: boolean } | null;
}

type PopupState =
  | { kind: "loading" }
  | { kind: "no_settings" }
  | { kind: "no_recipients" }
  | { kind: "ready"; recipients: RecipientState[] };

interface AliasCache {
  aliases: Alias[];
  fetchedAt: number;
}

// ─── State ────────────────────────────────────────────────────────────────────

const popupState = ref<PopupState>({ kind: "loading" });
const domainOptions = ref<DomainOptions>({
  data: [],
  defaultAliasDomain: "",
  defaultAliasFormat: "random_characters",
});
const hostUrl = ref("https://app.addy.io");
const tabId = ref(0);
const allAliases = ref<Alias[]>([]);

const { t } = useI18n();

const hasSelections = computed(() => {
  if (popupState.value.kind !== "ready") return false;
  return popupState.value.recipients.some(
    (r) => r.selectedAlias !== null || r.createdAlias !== null,
  );
});

// ─── Helpers ──────────────────────────────────────────────────────────────────

async function parseAddress(raw: string): Promise<ParsedAddress | null> {
  const parsed = (
    await messenger.messengerUtilities.parseMailboxString(raw)
  )[0];
  if (!parsed) return null;
  const match = parsed.email.match(/^(.+)@(.+)$/);
  if (!match) return null;
  const localPart = match[1];
  const domain = match[2].toLowerCase();
  const address = `${localPart}@${domain}`;
  if (address.includes('"')) return null;
  return { original: raw, address, localPart, domain, name: parsed.name ?? "" };
}

function matchingAliases(aliases: Alias[], domain: string): Alias[] {
  const lower = domain.toLowerCase();
  const matched = aliases.filter(
    (a) =>
      a.active &&
      (a.email.toLowerCase().includes(lower) ||
        (a.description ?? "").toLowerCase().includes(lower)),
  );
  // Sort: aliases whose address contains the domain first
  matched.sort((a) =>
    a.email.toLowerCase().startsWith(lower.split(".")[0]) ? -1 : 1,
  );
  return matched.slice(0, 10);
}

// ─── Initialization ───────────────────────────────────────────────────────────

async function initTabId(): Promise<void> {
  const params = new URLSearchParams(window.location.search);
  const param = params.get("tabId");
  if (param) {
    tabId.value = parseInt(param, 10);
  } else {
    // Fallback: window opened without URL param (shouldn't happen in normal flow)
    const tab = await messenger.tabs.getCurrent();
    tabId.value = tab.id;
  }
}

interface LoadResult {
  cache: AliasCache;
  hasApiKey: boolean;
}

async function loadStoredOptions(): Promise<LoadResult> {
  const storage = await messenger.storage.local.get({
    options: {},
    domainOptions: {
      data: [],
      defaultAliasDomain: "",
      defaultAliasFormat: "random_characters",
    },
    aliasCache: { aliases: [], fetchedAt: 0 },
  });

  const opts = (storage.options ?? {}) as {
    hostUrl?: string | null;
    apiKey?: string;
  };
  hostUrl.value = opts.hostUrl || "https://app.addy.io";

  domainOptions.value = storage.domainOptions as DomainOptions;

  const cache = (storage.aliasCache ?? { aliases: [] }) as AliasCache;
  allAliases.value = cache.aliases;
  return { cache, hasApiKey: !!opts.apiKey };
}

async function buildRecipients(cachedAliases: Alias[]): Promise<void> {
  const details = await messenger.compose.getComposeDetails(tabId.value);
  const allRecipients = [...details.to, ...details.cc, ...details.bcc];

  if (allRecipients.length === 0) {
    popupState.value = { kind: "no_recipients" };
    return;
  }

  const addyDomainSet = new Set(
    domainOptions.value.data.map((d) => d.toLowerCase()),
  );
  const seen = new Set<string>();
  const recipientStates: RecipientState[] = [];

  for (const raw of allRecipients) {
    const parsed = await parseAddress(raw);
    if (!parsed) continue;
    if (seen.has(parsed.address)) continue;
    if (addyDomainSet.has(parsed.domain)) continue;
    seen.add(parsed.address);

    const existing = matchingAliases(cachedAliases, parsed.domain);
    const autoSelect = existing.length === 1 ? existing[0].email : null;

    recipientStates.push({
      parsed,
      existingAliases: existing,
      selectedAlias: autoSelect,
      createdAlias: null,
    });
  }

  if (recipientStates.length === 0) {
    popupState.value = { kind: "no_recipients" };
    return;
  }

  popupState.value = { kind: "ready", recipients: recipientStates };
}

async function refreshAliasesInBackground(): Promise<void> {
  try {
    if (popupState.value.kind !== "ready") return;
    const domains = [
      ...new Set(popupState.value.recipients.map((r) => r.parsed.domain)),
    ];

    // Read full cache once; merge fresh API results in by ID so
    // description-matched aliases (e.g. created by this extension) survive.
    const stored = await messenger.storage.local.get({
      aliasCache: { aliases: [] as Alias[], fetchedAt: 0 },
    });
    const cache = stored.aliasCache as AliasCache;

    for (const domain of domains) {
      const response = await addyApiRequest<{ data: Alias[] }>(
        "GET",
        "aliases",
        { "filter[search]": domain, "filter[active]": "true" },
      );
      for (const fresh of response.data) {
        const idx = cache.aliases.findIndex((a) => a.id === fresh.id);
        if (idx >= 0) cache.aliases[idx] = fresh;
        else cache.aliases.push(fresh);
      }
    }

    await messenger.storage.local.set({ aliasCache: cache });
    allAliases.value = cache.aliases;

    if (popupState.value.kind !== "ready") return;
    for (const r of popupState.value.recipients) {
      r.existingAliases = matchingAliases(cache.aliases, r.parsed.domain);
    }
  } catch {
    // Non-fatal: we already have cached data
  }
}

// ─── User Actions ─────────────────────────────────────────────────────────────

async function handleAddressUpdate(
  recipientIdx: number,
  newAddress: string,
): Promise<void> {
  if (popupState.value.kind !== "ready") return;
  const m = newAddress.match(/^(.+)@(.+)$/);
  if (!m) return;
  const r = popupState.value.recipients[recipientIdx];
  r.parsed.address = newAddress;
  r.parsed.localPart = m[1];
  r.parsed.domain = m[2].toLowerCase();
  r.parsed.original = newAddress;
  r.existingAliases = matchingAliases(allAliases.value, r.parsed.domain);
}

async function handleCreate(
  recipientIdx: number,
  payload: { domain: string; format: AliasFormat; customPrefix: string },
): Promise<void> {
  if (popupState.value.kind !== "ready") return;
  const r = popupState.value.recipients[recipientIdx];

  const body: CreateAliasBody = {
    domain: payload.domain,
    description: `Created by AnonAddyTB for sending to ${r.parsed.address}`,
    format: payload.format,
  };
  if (payload.format === "custom" && payload.customPrefix.trim()) {
    body.local_part = payload.customPrefix.trim();
  }

  let alias: Alias | null = null;
  try {
    const response = await addyApiRequest<{ data: Alias }>(
      "POST",
      "aliases",
      null,
      body,
    );
    alias = response.data;
  } catch (e) {
    // 422 means the alias already exists — recover it for custom format
    const msg = e instanceof Error ? e.message : "";
    if (msg.includes("422") && msg.includes("already exists") && body.local_part) {
      try {
        const searchEmail = `${body.local_part}@${payload.domain}`;
        const res = await addyApiRequest<{ data: Alias[] }>("GET", "aliases", {
          "filter[search]": searchEmail,
        });
        alias = res.data.find((a) => a.email === searchEmail) ?? null;
      } catch {
        // fall through
      }
    }
    if (!alias) {
      console.error("AnonAddyTB: alias creation failed", e);
      return;
    }
  }

  r.createdAlias = { id: alias.id, email: alias.email, active: alias.active };
  r.selectedAlias = alias.active ? alias.email : null;

  // Eagerly add to the local cache so the alias appears on the next popup open.
  try {
    const stored = await messenger.storage.local.get({
      aliasCache: { aliases: [] as Alias[], fetchedAt: 0 },
    });
    const cache = stored.aliasCache as AliasCache;
    if (!cache.aliases.some((a) => a.id === alias!.id)) {
      cache.aliases.push(alias!);
      await messenger.storage.local.set({ aliasCache: cache });
    }
  } catch {
    // Non-fatal — background refresh will pick it up eventually.
  }
}

async function handleDisable(recipientIdx: number): Promise<void> {
  if (popupState.value.kind !== "ready") return;
  const r = popupState.value.recipients[recipientIdx];
  if (!r.createdAlias) return;
  try {
    await addyApiRequest("PATCH", `aliases/${r.createdAlias.id}`, null, {
      active: false,
    });
    r.createdAlias.active = false;
    r.selectedAlias = null;
  } catch (e) {
    console.error("AnonAddyTB: alias disable failed", e);
  }
}

async function handleRestore(recipientIdx: number): Promise<void> {
  if (popupState.value.kind !== "ready") return;
  const r = popupState.value.recipients[recipientIdx];
  if (!r.createdAlias) return;
  try {
    await addyApiRequest("PATCH", `aliases/${r.createdAlias.id}`, null, {
      active: true,
    });
    r.createdAlias.active = true;
    r.selectedAlias = r.createdAlias.email;
  } catch (e) {
    console.error("AnonAddyTB: alias restore failed", e);
  }
}

async function handleDelete(recipientIdx: number): Promise<void> {
  if (popupState.value.kind !== "ready") return;
  const r = popupState.value.recipients[recipientIdx];
  if (!r.createdAlias) return;
  try {
    await addyApiRequest("DELETE", `aliases/${r.createdAlias.id}`);
    r.createdAlias = null;
    r.selectedAlias = null;
  } catch (e) {
    console.error("AnonAddyTB: alias delete failed", e);
  }
}

async function applyAndClose(): Promise<void> {
  if (popupState.value.kind !== "ready") return;

  const details = await messenger.compose.getComposeDetails(tabId.value);

  const aliasMap = new Map<string, string>();
  for (const r of popupState.value.recipients) {
    const selected = r.createdAlias?.active
      ? r.createdAlias.email
      : (r.selectedAlias ?? null);
    if (selected) aliasMap.set(r.parsed.address, selected);
  }

  async function rewrite(recipients: string[]): Promise<string[]> {
    const result: string[] = [];
    for (const raw of recipients) {
      const parsed = await parseAddress(raw);
      if (!parsed || !aliasMap.has(parsed.address)) {
        result.push(raw);
        continue;
      }
      const addy = aliasMap.get(parsed.address)!;
      const m = addy.match(/^(.+)@(.+)$/);
      if (!m) {
        result.push(raw);
        continue;
      }
      const forwarding = `${m[1]}+${parsed.localPart}=${parsed.domain}@${m[2]}`;
      result.push(parsed.name ? `${parsed.name} <${forwarding}>` : forwarding);
    }
    return result;
  }

  const newDetails = {
    to: await rewrite(details.to),
    cc: await rewrite(details.cc),
    bcc: await rewrite(details.bcc),
  };

  await messenger.compose.setComposeDetails(tabId.value, newDetails);
  window.close();
}

// ─── Lifecycle ────────────────────────────────────────────────────────────────

async function load(): Promise<void> {
  popupState.value = { kind: "loading" };
  const { cache, hasApiKey } = await loadStoredOptions();
  if (!hasApiKey) {
    popupState.value = { kind: "no_settings" };
    void messenger.runtime.openOptionsPage();
    return;
  }
  try {
    await buildRecipients(cache.aliases);
  } catch (e) {
    console.error("AnonAddyTB: failed to read compose details", e);
    popupState.value = { kind: "no_recipients" };
    return;
  }
  void refreshAliasesInBackground();
}

onMounted(async () => {
  await initTabId();
  await load();
});

async function refresh(): Promise<void> {
  await load();
}

function close() {
  window.close();
}

function openSettings() {
  void messenger.runtime.openOptionsPage();
}
</script>

<template>
  <div class="popup">
    <LoadingSpinner v-if="popupState.kind === 'loading'" />

    <div v-else-if="popupState.kind === 'no_settings'" class="no-settings">
      <p>{{ t("noApiKeyMessage") }}</p>
      <button @click="openSettings">{{ t("settingsLink") }}</button>
    </div>

    <NoRecipientsMessage
      v-else-if="popupState.kind === 'no_recipients'"
      @close="close"
    />

    <template v-else-if="popupState.kind === 'ready'">
      <RecipientCard
        v-for="(r, idx) in popupState.recipients"
        :key="r.parsed.address"
        :address="r.parsed.address"
        :name="r.parsed.name"
        :existing-aliases="r.existingAliases"
        :selected-alias="r.selectedAlias"
        :created-alias="r.createdAlias"
        :available-domains="domainOptions.data"
        :default-domain="domainOptions.defaultAliasDomain"
        :default-format="domainOptions.defaultAliasFormat"
        @update:selected-alias="(v) => (r.selectedAlias = v)"
        @update:address="(v) => handleAddressUpdate(idx, v)"
        @create="(p) => handleCreate(idx, p)"
        @disable="() => handleDisable(idx)"
        @restore="() => handleRestore(idx)"
        @delete="() => handleDelete(idx)"
      />

      <div class="flex-spacer" />

      <FooterBar
        :host-url="hostUrl"
        :has-selections="hasSelections"
        @apply="applyAndClose"
        @refresh="refresh"
        @close="close"
        @open-settings="openSettings"
      />
    </template>
  </div>
</template>

<style scoped lang="scss">
@use "./styles/variables" as *;

.popup {
  min-width: $window-min-width;
  min-height: 100%;
  display: flex;
  flex-direction: column;
}

.flex-spacer {
  flex: 1;
}

.no-settings {
  padding: $spacing-lg;
  color: $color-muted;

  p {
    margin: 0 0 $spacing-md;
  }
}
</style>
