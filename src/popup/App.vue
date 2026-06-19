<script setup lang="ts">
import { ref, computed, onBeforeUnmount, onMounted } from "vue";
import LoadingSpinner from "./components/LoadingSpinner.vue";
import NoRecipientsMessage from "./components/NoRecipientsMessage.vue";
import RecipientCard from "./components/RecipientCard.vue";
import FooterBar from "./components/FooterBar.vue";
import { addyApiRequest } from "../api/index.js";
import { useI18n } from "../composables/useI18n.js";
import {
  matchingAliases,
  parseForwardingAddress,
  buildForwardingAddress,
} from "./utils.js";
import { hasApplyableChanges } from "./applyState.js";
import {
  createPopupWindowTracker,
  shouldCloseForRemovedTab,
} from "./windowTracker.js";
import {
  mergeAliasesIntoCache,
  type AliasCache,
} from "../shared/aliasCache.js";
import type { Alias, DomainOptions } from "../api/types.js";

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
  /** Address currently in the compose field (may be a forwarding address if pre-aliased). */
  composeAddress: string;
  existingAliases: Alias[];
  selectedAlias: string | null;
}

type PopupState =
  | { kind: "loading" }
  | { kind: "no_settings" }
  | { kind: "no_recipients" }
  | { kind: "ready"; recipients: RecipientState[] };

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
const childWindows = createPopupWindowTracker((windowId) =>
  messenger.windows.remove(windowId),
);

const { t } = useI18n();

const hasSelections = computed(() => {
  if (popupState.value.kind !== "ready") return false;
  return hasApplyableChanges(popupState.value.recipients);
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

    if (addyDomainSet.has(parsed.domain)) {
      // Could be a forwarding address from a previous Apply — detect and recover.
      const fwd = parseForwardingAddress(parsed.address, addyDomainSet);
      if (fwd && !seen.has(fwd.originalEmail)) {
        seen.add(fwd.originalEmail);
        const om = fwd.originalEmail.match(/^(.+)@(.+)$/);
        if (om) {
          const origDomain = om[2].toLowerCase();
          const existing = matchingAliases(cachedAliases, origDomain);
          recipientStates.push({
            parsed: {
              original: raw,
              address: fwd.originalEmail,
              localPart: om[1],
              domain: origDomain,
              name: parsed.name,
            },
            composeAddress: parsed.address,
            existingAliases: existing,
            selectedAlias: fwd.aliasEmail,
          });
        }
      }
      continue;
    }

    if (seen.has(parsed.address)) continue;
    seen.add(parsed.address);

    const existing = matchingAliases(cachedAliases, parsed.domain);
    const autoSelect = existing.length === 1 ? existing[0].email : null;

    recipientStates.push({
      parsed,
      composeAddress: parsed.address,
      existingAliases: existing,
      selectedAlias: autoSelect,
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
      Object.assign(cache, mergeAliasesIntoCache(cache, response.data));
    }

    await messenger.storage.local.set({ aliasCache: cache });
    void messenger.runtime
      .sendMessage({ action: "alias_cache_updated" })
      .catch(() => undefined);
    allAliases.value = cache.aliases;

    // If domain options are empty (first install / background hasn't run yet),
    // fetch them now so the domain combobox in CreateAliasForm isn't blank.
    if (domainOptions.value.data.length === 0) {
      const fresh = await addyApiRequest<DomainOptions>(
        "GET",
        "domain-options",
      );
      domainOptions.value = fresh;
      await messenger.storage.local.set({ domainOptions: fresh });
      void messenger.runtime
        .sendMessage({ action: "alias_cache_updated" })
        .catch(() => undefined);
    }

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
  r.composeAddress = newAddress;
  r.existingAliases = matchingAliases(allAliases.value, r.parsed.domain);
}

async function openCreateWindow(
  recipientIdx: number,
  payload: { email: string; name: string },
): Promise<void> {
  if (popupState.value.kind !== "ready") return;
  const url =
    messenger.runtime.getURL("createAlias.html") +
    `?tabId=${tabId.value}&email=${encodeURIComponent(payload.email)}&name=${encodeURIComponent(payload.name)}`;
  const win = await messenger.windows.create({
    url,
    type: "popup",
    width: 520,
    height: 480,
  });
  childWindows.remember(win.id);
}

async function handleDisable(
  recipientIdx: number,
  aliasId: string,
): Promise<void> {
  if (popupState.value.kind !== "ready") return;
  const r = popupState.value.recipients[recipientIdx];
  try {
    await addyApiRequest("PATCH", `aliases/${aliasId}`, null, {
      active: false,
    });
    const a = r.existingAliases.find((x) => x.id === aliasId);
    if (a) {
      a.active = false;
      if (r.selectedAlias === a.email) r.selectedAlias = null;
    }
  } catch (e) {
    console.error("AnonAddyTB: alias disable failed", e);
  }
}

async function handleRestore(
  recipientIdx: number,
  aliasId: string,
): Promise<void> {
  if (popupState.value.kind !== "ready") return;
  const r = popupState.value.recipients[recipientIdx];
  try {
    await addyApiRequest("PATCH", `aliases/${aliasId}`, null, { active: true });
    const a = r.existingAliases.find((x) => x.id === aliasId);
    if (a) {
      a.active = true;
      r.selectedAlias = a.email;
    }
  } catch (e) {
    console.error("AnonAddyTB: alias restore failed", e);
  }
}

async function handleDelete(
  recipientIdx: number,
  aliasId: string,
): Promise<void> {
  if (popupState.value.kind !== "ready") return;
  const r = popupState.value.recipients[recipientIdx];
  try {
    await addyApiRequest("DELETE", `aliases/${aliasId}`);
    const idx = r.existingAliases.findIndex((x) => x.id === aliasId);
    if (idx >= 0) {
      if (r.selectedAlias === r.existingAliases[idx].email)
        r.selectedAlias = null;
      r.existingAliases.splice(idx, 1);
    }
  } catch (e) {
    console.error("AnonAddyTB: alias delete failed", e);
  }
}

async function applyAndClose(): Promise<void> {
  if (popupState.value.kind !== "ready") return;

  const details = await messenger.compose.getComposeDetails(tabId.value);

  // Map keyed by what is currently in the compose field (composeAddress).
  // Includes pre-aliased recipients even when aliasEmail is null (= revert).
  interface ApplyEntry {
    aliasEmail: string | null;
    originalEmail: string;
    originalName: string;
  }
  const applyMap = new Map<string, ApplyEntry>();
  for (const r of popupState.value.recipients) {
    // Resolve selected alias email; verify it's still active before applying.
    const selectedEmail = r.selectedAlias;
    const isActive = selectedEmail
      ? (r.existingAliases.find((a) => a.email === selectedEmail)?.active ??
        false)
      : false;
    const selected = isActive ? selectedEmail : null;
    const isPreAliased = r.composeAddress !== r.parsed.address;
    if (selected || isPreAliased) {
      applyMap.set(r.composeAddress, {
        aliasEmail: selected ?? null,
        originalEmail: r.parsed.address,
        originalName: r.parsed.name,
      });
    }
  }

  async function rewrite(recipients: string[]): Promise<string[]> {
    const result: string[] = [];
    for (const raw of recipients) {
      const parsed = await parseAddress(raw);
      if (!parsed) {
        result.push(raw);
        continue;
      }
      const entry = applyMap.get(parsed.address);
      if (!entry) {
        result.push(raw);
        continue;
      }

      const displayName = parsed.name || entry.originalName;
      if (!entry.aliasEmail) {
        // Revert pre-aliased address back to original recipient email.
        result.push(
          displayName
            ? `${displayName} <${entry.originalEmail}>`
            : entry.originalEmail,
        );
        continue;
      }
      const forwarding = buildForwardingAddress(
        entry.aliasEmail,
        entry.originalEmail,
      );
      if (!forwarding) {
        result.push(raw);
        continue;
      }
      result.push(displayName ? `${displayName} <${forwarding}>` : forwarding);
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
  messenger.tabs.onRemoved.addListener((removedTabId) => {
    if (shouldCloseForRemovedTab(removedTabId, tabId.value)) {
      window.close();
    }
  });
  window.addEventListener("beforeunload", closeChildWindows);
  await load();
});

onBeforeUnmount(() => {
  closeChildWindows();
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

function closeChildWindows() {
  void childWindows.closeAll();
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
        :all-aliases="allAliases"
        :selected-alias="r.selectedAlias"
        @update:selected-alias="(v) => (r.selectedAlias = v)"
        @update:address="(v) => handleAddressUpdate(idx, v)"
        @open-create-window="(p) => openCreateWindow(idx, p)"
        @disable="(id) => handleDisable(idx, id)"
        @restore="(id) => handleRestore(idx, id)"
        @delete="(id) => handleDelete(idx, id)"
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
  max-width: $window-min-width;
  width: 100%;
  box-sizing: border-box;
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
