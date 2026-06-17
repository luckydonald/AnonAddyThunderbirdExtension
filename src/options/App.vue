<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import OptionsForm from "./components/OptionsForm.vue";
import StatusBanner from "./components/StatusBanner.vue";
import { useI18n } from "../composables/useI18n.js";

export type SaveStatus =
  | { kind: "idle" }
  | { kind: "success" }
  | { kind: "error"; message: string }
  | { kind: "permission_denied"; hostUrl: string }
  | { kind: "permission_granted"; hostUrl: string };

const hostUrl = ref("");
const apiKey = ref("");
const savedHostUrl = ref("");
const savedApiKey = ref("");
const saveStatus = ref<SaveStatus>({ kind: "idle" });
const { t } = useI18n();

const isDirty = computed(
  () =>
    hostUrl.value !== savedHostUrl.value || apiKey.value !== savedApiKey.value,
);

async function loadFromStorage() {
  const result = await messenger.storage.local.get({ options: {} });
  const opts = (result.options ?? {}) as {
    hostUrl?: string | null;
    apiKey?: string | null;
  };
  hostUrl.value = opts.hostUrl ?? "";
  apiKey.value = opts.apiKey ?? "";
  savedHostUrl.value = hostUrl.value;
  savedApiKey.value = apiKey.value;

  const all = await messenger.permissions.getAll();
  console.log("AnonAddyTB: permissions.getAll() on load:", JSON.stringify(all, null, 2));

  messenger.permissions.onAdded.addListener((added) => {
    console.log("AnonAddyTB: permissions.onAdded:", JSON.stringify(added));
  });
  messenger.permissions.onRemoved.addListener((removed) => {
    console.log("AnonAddyTB: permissions.onRemoved:", JSON.stringify(removed));
  });
}

async function save() {
  const url = hostUrl.value.replace(/\/+$/, "");
  if (url && !(url.startsWith("http://") || url.startsWith("https://"))) {
    saveStatus.value = { kind: "error", message: t("errorInvalidUrl") };
    return;
  }
  if (!apiKey.value.trim()) {
    saveStatus.value = { kind: "error", message: t("errorApiKeyRequired") };
    return;
  }
  hostUrl.value = url;

  let permissionJustGranted = false;
  if (url) {
    const origin = `${url}/`;
    console.log("AnonAddyTB: checking permission for origin:", origin);
    const alreadyGranted = await messenger.permissions.contains({
      origins: [origin],
    });
    console.log("AnonAddyTB: permissions.contains():", alreadyGranted);
    if (!alreadyGranted) {
      let granted: boolean;
      try {
        granted = await messenger.permissions.request({ origins: [origin] });
      } catch {
        granted = false;
      }
      console.log("AnonAddyTB: permissions.request() result:", granted);
      const allAfter = await messenger.permissions.getAll();
      console.log("AnonAddyTB: permissions.getAll() after request:", JSON.stringify(allAfter, null, 2));
      if (!granted) {
        saveStatus.value = { kind: "permission_denied", hostUrl: url };
        return;
      }
      permissionJustGranted = true;
    }
  }

  await messenger.storage.local.set({
    options: { hostUrl: url || null, apiKey: apiKey.value },
  });
  savedHostUrl.value = url;
  savedApiKey.value = apiKey.value;

  saveStatus.value = permissionJustGranted
    ? { kind: "permission_granted", hostUrl: url }
    : { kind: "success" };
}

function reset() {
  hostUrl.value = savedHostUrl.value;
  apiKey.value = savedApiKey.value;
  saveStatus.value = { kind: "idle" };
}

onMounted(loadFromStorage);
</script>

<template>
  <div class="options-page">
    <StatusBanner :status="saveStatus" />
    <OptionsForm
      v-model:host-url="hostUrl"
      v-model:api-key="apiKey"
      :is-dirty="isDirty"
      @save="save"
      @reset="reset"
    />
  </div>
</template>
