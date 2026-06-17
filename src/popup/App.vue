<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import LoadingSpinner from "./components/LoadingSpinner.vue";
import NoRecipientsMessage from "./components/NoRecipientsMessage.vue";
import RecipientCard from "./components/RecipientCard.vue";
import FooterBar from "./components/FooterBar.vue";
import { addyApiRequest } from "../api/index.js";
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
    (a) => a.email.toLowerCase().includes(lower) && a.active,
  );
  // Sort: aliases whose address contains the domain first
  matched.sort((a) =>
    a.email.toLowerCase().startsWith(lower.split(".")[0]) ? -1 : 1,
  );
  return matched.slice(0, 10);
}

// ─── Initialization ───────────────────────────────────────────────────────────

async function loadStoredOptions(): Promise<AliasCache> {
  const storage = await messenger.storage.local.get({
    options: {},
    domainOptions: {
      data: [],
      defaultAliasDomain: "",
      defaultAliasFormat: "random_characters",
    },
    aliasCache: { aliases: [], fetchedAt: 0 },
  });

  const opts = (storage.options ?? {}) as { hostUrl?: string | null };
  hostUrl.value = opts.hostUrl || "https://app.addy.io";

  domainOptions.value = storage.domainOptions as DomainOptions;

  const cache = (storage.aliasCache ?? { aliases: [] }) as AliasCache;
  return cache;
}

async function buildRecipients(cachedAliases: Alias[]): Promise<void> {
  const tab = await messenger.tabs.getCurrent();
  tabId.value = tab.id;

  const details = await messenger.compose.getComposeDetails(tab.id);
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
    // Trigger background to refresh; listen for storage update
    // Meanwhile fetch fresh aliases for current domains directly
    if (popupState.value.kind !== "ready") return;
    const domains = [
      ...new Set(popupState.value.recipients.map((r) => r.parsed.domain)),
    ];
    for (const domain of domains) {
      const response = await addyApiRequest<{ data: Alias[] }>(
        "GET",
        "aliases",
        { "filter[search]": domain, "filter[active]": "true" },
      );
      updateAliasesForDomain(domain, response.data);
    }
  } catch {
    // Non-fatal: we already have cached data
  }
}

function updateAliasesForDomain(domain: string, fresh: Alias[]): void {
  if (popupState.value.kind !== "ready") return;
  for (const r of popupState.value.recipients) {
    if (r.parsed.domain === domain) {
      r.existingAliases = matchingAliases(fresh, domain);
    }
  }
}

// ─── User Actions ─────────────────────────────────────────────────────────────

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

  try {
    const response = await addyApiRequest<{ data: Alias }>(
      "POST",
      "aliases",
      null,
      body,
    );
    const alias = response.data;
    r.createdAlias = { id: alias.id, email: alias.email, active: true };
    r.selectedAlias = alias.email;
  } catch (e) {
    console.error("AnonAddyTB: alias creation failed", e);
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

onMounted(async () => {
  // Popup resize workaround: nudge #spacer so Thunderbird recalculates size
  let count = 0;
  const nudge = () => {
    const spacer = document.getElementById("spacer");
    if (spacer && count < 10) {
      spacer.textContent = " ".repeat(count);
      count++;
      setTimeout(nudge, 100);
    }
  };
  setTimeout(nudge, 50);

  const cache = await loadStoredOptions();
  await buildRecipients(cache.aliases);

  // Refresh alias data from API in the background after initial render
  void refreshAliasesInBackground();
});

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
        @create="(p) => handleCreate(idx, p)"
        @disable="() => handleDisable(idx)"
        @restore="() => handleRestore(idx)"
        @delete="() => handleDelete(idx)"
      />

      <FooterBar
        :host-url="hostUrl"
        :has-selections="hasSelections"
        @apply="applyAndClose"
        @close="close"
        @open-settings="openSettings"
      />
    </template>
  </div>
</template>

<style scoped lang="scss">
@use "./styles/variables" as *;

.popup {
  width: $popup-width;
}
</style>
