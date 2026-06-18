<script setup lang="ts">
import { ref, onMounted } from "vue";
import CreateAliasForm from "../popup/components/CreateAliasForm.vue";
import { useI18n } from "../composables/useI18n.js";
import type {
  Alias,
  AliasFormat,
  DomainOptions,
  CreateAliasBody,
} from "../api/types.js";

const params = new URLSearchParams(window.location.search);
const tabId = parseInt(params.get("tabId") ?? "0", 10);
const targetEmail = params.get("email") ?? "";
const targetName = params.get("name") ?? "";

const loading = ref(false);
const errorMsg = ref("");
const domainOptions = ref<DomainOptions>({
  data: [],
  defaultAliasDomain: "",
  defaultAliasFormat: "random_characters",
});

const { t } = useI18n();

onMounted(async () => {
  const storage = await messenger.storage.local.get({
    domainOptions: {
      data: [],
      defaultAliasDomain: "",
      defaultAliasFormat: "random_characters",
    },
  });
  domainOptions.value = storage.domainOptions as DomainOptions;
});

function cancel(): void {
  window.close();
}

async function handleCreate(payload: {
  domain: string;
  format: AliasFormat;
  customPrefix: string;
}): Promise<void> {
  loading.value = true;
  errorMsg.value = "";
  try {
    const raw = await messenger.runtime.sendMessage({
      action: "create_alias_and_apply",
      tabId,
      email: targetEmail,
      name: targetName,
      domain: payload.domain,
      format: payload.format,
      customPrefix: payload.customPrefix,
    });
    const response = raw as { success: boolean; error?: string } | null;
    if (response?.success) {
      window.close();
    } else {
      errorMsg.value = response?.error ?? "Alias creation failed.";
      loading.value = false;
    }
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : "Alias creation failed.";
    loading.value = false;
  }
}
</script>

<template>
  <div class="create-alias-page">
    <h2 class="page-title">
      {{ t("createAliasSection") }}
    </h2>
    <p class="page-recipient">
      {{ t("replaceWithPrefix") }}
      <strong>{{ targetName || targetEmail }}</strong>
      {{ t("replaceWithSuffix") }}
    </p>

    <p v-if="errorMsg" class="error-banner">{{ errorMsg }}</p>

    <CreateAliasForm
      :available-domains="domainOptions.data"
      :default-domain="domainOptions.defaultAliasDomain"
      :default-format="domainOptions.defaultAliasFormat"
      :loading="loading"
      :target-email="targetEmail"
      :target-name="targetName"
      @create="handleCreate"
    />

    <button class="cancel-btn" @click="cancel">
      {{ t("cancel") }}
    </button>
  </div>
</template>

<style scoped lang="scss">
@use "../popup/styles/variables" as *;

.create-alias-page {
  padding: $spacing-md;
  max-width: $window-min-width;
  width: 100%;
  box-sizing: border-box;
}

.page-title {
  margin: 0 0 $spacing-sm;
  font-size: $font-size-base;
  font-weight: 600;
}

.page-recipient {
  margin: 0 0 $spacing-md;
  font-size: $font-size-sm;
  color: $color-muted;
}

.error-banner {
  background: #fef2f2;
  border: 1px solid #fca5a5;
  border-radius: 4px;
  padding: $spacing-sm $spacing-md;
  color: $color-danger;
  font-size: $font-size-sm;
  margin-bottom: $spacing-md;
}

.cancel-btn {
  margin-top: $spacing-md;
  width: 100%;
}
</style>
