<script setup lang="ts">
import { ref, watch } from "vue";
import CreateAliasForm from "./CreateAliasForm.vue";
import { useI18n } from "../../composables/useI18n.js";
import type { Alias, AliasFormat } from "../../api/types.js";

export interface CreatedAliasInfo {
  id: string;
  email: string;
  active: boolean;
}

const props = defineProps<{
  address: string;
  name: string;
  existingAliases: Alias[];
  selectedAlias: string | null;
  createdAlias: CreatedAliasInfo | null;
  availableDomains: string[];
  defaultDomain: string;
  defaultFormat: AliasFormat;
}>();

const emit = defineEmits<{
  "update:selectedAlias": [value: string | null];
  "update:address": [value: string];
  create: [
    payload: { domain: string; format: AliasFormat; customPrefix: string },
  ];
  disable: [];
  delete: [];
  restore: [];
}>();

const { t } = useI18n();

const creating = ref(false);
const editableAddress = ref(props.address);

watch(
  () => props.address,
  (v) => { editableAddress.value = v; },
);

function onAddressChange() {
  const v = editableAddress.value.trim();
  if (v && v !== props.address) emit("update:address", v);
}

function selectAlias(email: string) {
  emit("update:selectedAlias", email === props.selectedAlias ? null : email);
}

function handleCreate(payload: {
  domain: string;
  format: AliasFormat;
  customPrefix: string;
}) {
  creating.value = true;
  emit("create", payload);
}

defineExpose({ resetCreating: () => (creating.value = false) });
</script>

<template>
  <div class="card">
    <p class="card__header">
      {{ t("replaceWithPrefix") }}
      <span v-if="name" class="card__name">{{ name }}</span>
      <input
        v-model="editableAddress"
        type="text"
        class="card__address-input"
        @blur="onAddressChange"
        @keydown.enter.prevent="onAddressChange"
      />
      {{ t("replaceWithSuffix") }}
    </p>

    <!-- Created alias: show manage actions -->
    <div v-if="createdAlias" class="created-alias">
      <div class="created-alias__row">
        <kbd
          class="created-alias__email"
          :class="{ 'created-alias__email--inactive': !createdAlias.active }"
        >
          {{ createdAlias.email }}
        </kbd>
        <span v-if="!createdAlias.active" class="tag tag--inactive">{{
          t("inactive")
        }}</span>
      </div>
      <div class="created-alias__actions">
        <button
          v-if="createdAlias.active"
          class="danger"
          :title="t('disableHint')"
          @click="$emit('disable')"
        >
          {{ t("disable") }}
        </button>
        <button v-else :title="t('disableHint')" @click="$emit('restore')">{{ t("reenable") }}</button>
        <button class="danger" :title="t('deleteHint')" @click="$emit('delete')">
          {{ t("deleteAlias") }}
        </button>
      </div>
    </div>

    <!-- No created alias: show existing list + create form -->
    <div v-else>
      <!-- Existing aliases section -->
      <p class="section-heading">{{ t("existingAliasesSection") }}</p>

      <div v-if="existingAliases.length === 0" class="no-aliases">
        <em>{{ t("noExistingAliases") }}</em>
      </div>

      <div v-else class="alias-list">
        <label
          v-for="alias in existingAliases"
          :key="alias.id"
          class="alias-option"
          :class="{ selected: selectedAlias === alias.email }"
        >
          <input
            type="radio"
            :name="`alias-${address}`"
            :value="alias.email"
            :checked="selectedAlias === alias.email"
            @change="selectAlias(alias.email)"
          />
          <kbd class="alias-option__email">{{ alias.email }}</kbd>
          <span v-if="alias.description" class="alias-option__desc">
            {{ alias.description }}
          </span>
        </label>

        <label
          class="alias-option alias-option--none"
          :class="{ selected: selectedAlias === null }"
        >
          <input
            type="radio"
            :name="`alias-${address}`"
            :checked="selectedAlias === null"
            @change="$emit('update:selectedAlias', null)"
          />
          <span>{{ t("dontReplace") }}</span>
        </label>
      </div>

      <!-- Create new alias section (always visible) -->
      <CreateAliasForm
        :available-domains="availableDomains"
        :default-domain="defaultDomain"
        :default-format="defaultFormat"
        :loading="creating"
        :target-email="editableAddress"
        :target-name="name"
        @create="handleCreate"
      />
    </div>
  </div>
</template>

<style scoped lang="scss">
@use "../styles/variables" as *;

.card {
  border: 1px solid $color-border;
  border-radius: 4px;
  padding: $spacing-md;
  margin-bottom: $spacing-md;

  &__header {
    margin: 0 0 $spacing-md;
    font-size: $font-size-sm;
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: $spacing-xs;
  }

  &__name {
    font-weight: 600;
  }

  &__address-input {
    font-weight: 600;
    font-size: inherit;
    font-family: monospace;
    border: none;
    border-bottom: 1px dashed $color-border;
    background: transparent;
    padding: 0 2px;
    min-width: 120px;
    flex: 1;
    color: inherit;

    &:focus {
      outline: none;
      border-bottom-color: $color-primary;
    }
  }
}

.section-heading {
  margin: 0 0 $spacing-sm;
  font-size: $font-size-sm;
  font-weight: 600;
  color: $color-muted;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.alias-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-xs;
  margin-bottom: $spacing-sm;
}

.alias-option {
  display: flex;
  align-items: flex-start;
  gap: $spacing-sm;
  padding: $spacing-xs $spacing-sm;
  border-radius: 3px;
  cursor: pointer;

  &:hover,
  &.selected {
    background: #f0f5ff;
  }

  input[type="radio"] {
    margin-top: 2px;
    flex-shrink: 0;
  }

  &__email {
    font-family: monospace;
    font-size: $font-size-sm;
    background: #f5f5f5;
    border: 1px solid $color-border;
    border-radius: 3px;
    padding: 1px 5px;
    word-break: break-all;
  }

  &__desc {
    color: $color-muted;
    font-size: $font-size-sm;
    margin-left: $spacing-xs;
  }

  &--none {
    color: $color-muted;
    font-style: italic;
  }
}

.no-aliases {
  color: $color-muted;
  font-size: $font-size-sm;
  margin-bottom: $spacing-sm;
}

.created-alias {
  &__row {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    margin-bottom: $spacing-sm;
  }

  &__email {
    font-family: monospace;
    font-size: $font-size-sm;
    background: #f5f5f5;
    border: 1px solid $color-border;
    border-radius: 3px;
    padding: 2px 6px;
    word-break: break-all;

    &--inactive {
      color: $color-muted;
      text-decoration: line-through;
    }
  }

  &__actions {
    display: flex;
    gap: $spacing-sm;
  }
}

.tag {
  font-size: $font-size-sm;
  padding: 1px 6px;
  border-radius: 10px;

  &--inactive {
    background: #eee;
    color: $color-muted;
  }
}
</style>
