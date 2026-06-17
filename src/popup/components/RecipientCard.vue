<script setup lang="ts">
import { ref, watch, computed } from "vue";
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

// Exclude the created alias from the regular list to avoid it appearing twice.
const displayAliases = computed(() => {
  if (!props.createdAlias) return props.existingAliases;
  return props.existingAliases.filter((a) => a.email !== props.createdAlias!.email);
});

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

    <!-- Existing aliases section (always visible) -->
    <p class="section-heading">{{ t("existingAliasesSection") }}</p>

    <div class="alias-list">
      <!-- Created alias pinned at top with inline manage controls -->
      <div
        v-if="createdAlias"
        class="alias-option alias-option--created"
        :class="{ selected: selectedAlias === createdAlias.email }"
        @click="!createdAlias.active || selectAlias(createdAlias.email)"
      >
        <input
          type="radio"
          :name="`alias-${address}`"
          :value="createdAlias.email"
          :checked="selectedAlias === createdAlias.email"
          :disabled="!createdAlias.active"
          @change="selectAlias(createdAlias.email)"
        />
        <div class="alias-option__body">
          <div class="alias-option__row">
            <kbd
              class="alias-option__email"
              :class="{ 'alias-option__email--inactive': !createdAlias.active }"
            >{{ createdAlias.email }}</kbd>
            <span class="tag tag--new">{{ t("newTag") }}</span>
            <span v-if="!createdAlias.active" class="tag tag--inactive">{{ t("inactive") }}</span>
          </div>
          <div class="alias-option__actions" @click.stop>
            <button
              v-if="createdAlias.active"
              class="small danger"
              :title="t('disableHint')"
              @click="$emit('disable')"
            >{{ t("disable") }}</button>
            <button
              v-else
              class="small"
              :title="t('disableHint')"
              @click="$emit('restore')"
            >{{ t("reenable") }}</button>
            <button
              class="small danger"
              :title="t('deleteHint')"
              @click="$emit('delete')"
            >{{ t("deleteAlias") }}</button>
          </div>
        </div>
      </div>

      <!-- Regular existing aliases -->
      <label
        v-for="alias in displayAliases"
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

      <!-- Empty state -->
      <div v-if="!createdAlias && displayAliases.length === 0" class="no-aliases">
        <em>{{ t("noExistingAliases") }}</em>
      </div>

      <!-- Don't replace option -->
      <label
        v-if="createdAlias || displayAliases.length > 0"
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
</template>

<style scoped lang="scss">
@use "../styles/variables" as *;

.card {
  border: 1px solid $color-border;
  border-radius: 4px;
  padding: $spacing-md;
  margin-bottom: $spacing-md;
  min-width: 0;

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

  &__body {
    display: flex;
    flex-direction: column;
    gap: $spacing-xs;
    min-width: 0;
    flex: 1;
  }

  &__row {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: $spacing-xs;
  }

  &__email {
    font-family: monospace;
    font-size: $font-size-sm;
    background: #f5f5f5;
    border: 1px solid $color-border;
    border-radius: 3px;
    padding: 1px 5px;
    word-break: break-all;

    &--inactive {
      color: $color-muted;
      text-decoration: line-through;
    }
  }

  &__desc {
    color: $color-muted;
    font-size: $font-size-sm;
  }

  &__actions {
    display: flex;
    flex-wrap: wrap;
    gap: $spacing-xs;
  }

  &--created {
    border: 1px solid $color-primary;
    background: #f0f5ff;

    &.selected {
      background: #dbeafe;
    }
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

.tag {
  font-size: $font-size-sm;
  padding: 1px 6px;
  border-radius: 10px;
  white-space: nowrap;

  &--inactive {
    background: #eee;
    color: $color-muted;
  }

  &--new {
    background: #dbeafe;
    color: $color-primary;
    font-weight: 600;
  }
}

button.small {
  font-size: $font-size-sm;
  padding: 1px $spacing-sm;
}
</style>
