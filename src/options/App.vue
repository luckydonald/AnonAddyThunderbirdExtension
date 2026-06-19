<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import OptionsForm from "./components/OptionsForm.vue";
import StatusBanner from "./components/StatusBanner.vue";
import { useI18n } from "../composables/useI18n.js";
import { addyApiRequest } from "../api/index.js";

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
  console.log(
    "AddyTB: permissions.getAll() on load:",
    JSON.stringify(all, null, 2),
  );

  messenger.permissions.onAdded.addListener((added) => {
    console.log("AddyTB: permissions.onAdded:", JSON.stringify(added));
  });
  messenger.permissions.onRemoved.addListener((removed) => {
    console.log("AddyTB: permissions.onRemoved:", JSON.stringify(removed));
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

  // Save first so addyApiRequest() below picks up the new credentials.
  await messenger.storage.local.set({
    options: { hostUrl: url || null, apiKey: apiKey.value },
  });
  savedHostUrl.value = url;
  savedApiKey.value = apiKey.value;

  // Try the permissions API.
  let permissionJustGranted = false;
  if (url) {
    const origin = `${url}/`;
    console.log("AddyTB: checking permission for origin:", origin);
    const alreadyGranted = await messenger.permissions.contains({
      origins: [origin],
    });
    console.log("AddyTB: permissions.contains():", alreadyGranted);
    if (!alreadyGranted) {
      let granted = false;
      try {
        console.log("AddyTB: messenger.permissions.request()", {
          origins: [origin],
        });
        granted = await messenger.permissions.request({ origins: [origin] });
        console.log("AddyTB: no error in messenger.permissions.request.", {
          origins: [origin],
          granted,
        });
      } catch (e) {
        console.warn("AddyTB: error in messenger.permissions.request:", e, {
          origins: [origin],
        });
      }
      console.log("AddyTB: permissions.request() result:", granted);
      const allAfter = await messenger.permissions.getAll();
      console.log(
        "AddyTB: permissions.getAll() after request:",
        JSON.stringify(allAfter, null, 2),
      );
      if (granted) {
        permissionJustGranted = true;
      } else {
        saveStatus.value = { kind: "permission_denied", hostUrl: url };
        // Fall through: still try a real request — it may itself trigger the prompt.
      }
    }
  }

  // Also fire an actual API request; this may trigger Thunderbird's native
  // host-permission prompt even when permissions.request() silently fails.
  console.log("AddyTB: testing API request (GET domain-options)...");
  try {
    const result = await addyApiRequest("GET", "domain-options");
    console.log("AddyTB: API test succeeded:", JSON.stringify(result));
    saveStatus.value = permissionJustGranted
      ? { kind: "permission_granted", hostUrl: url }
      : { kind: "success" };
  } catch (e) {
    console.warn("AddyTB: API test failed:", e);
    // Keep permission_denied if already set; otherwise surface the API error.
    if (saveStatus.value.kind !== "permission_denied") {
      saveStatus.value = { kind: "error", message: String(e) };
    }
  }
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
