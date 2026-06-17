<script setup lang="ts">
import { ref } from "vue";
import CreateAliasForm from "./CreateAliasForm.vue";
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
  create: [
    payload: { domain: string; format: AliasFormat; customPrefix: string },
  ];
  disable: [];
  delete: [];
  restore: [];
}>();

const showCreate = ref(props.existingAliases.length === 0);
const creating = ref(false);

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
      Replace
      <strong>{{ name ? `${name} <${address}>` : address }}</strong>
      with:
    </p>

    <div v-if="createdAlias" class="created-alias">
      <div class="created-alias__row">
        <span
          class="created-alias__email"
          :class="{ 'created-alias__email--inactive': !createdAlias.active }"
        >
          {{ createdAlias.email }}
        </span>
        <span v-if="!createdAlias.active" class="tag tag--inactive"
          >inactive</span
        >
      </div>
      <div class="created-alias__actions">
        <button
          v-if="createdAlias.active"
          class="danger"
          @click="$emit('disable')"
        >
          Disable
        </button>
        <button v-else @click="$emit('restore')">Re-enable</button>
        <button class="danger" @click="$emit('delete')">Delete</button>
      </div>
    </div>

    <div v-else>
      <div v-if="existingAliases.length === 0" class="no-aliases">
        <em>No existing aliases for this domain.</em>
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
          <span class="alias-option__email">{{ alias.email }}</span>
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
          <span>Don't replace</span>
        </label>
      </div>

      <button class="toggle-create" @click="showCreate = !showCreate">
        {{ showCreate ? "▲ Hide create form" : "▼ Create new alias" }}
      </button>

      <CreateAliasForm
        v-if="showCreate"
        :available-domains="availableDomains"
        :default-domain="defaultDomain"
        :default-format="defaultFormat"
        :loading="creating"
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
  }
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
    font-weight: 500;
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

.toggle-create {
  background: none;
  border: none;
  padding: 0;
  color: $color-primary;
  font-size: $font-size-sm;
  cursor: pointer;
  margin-bottom: $spacing-sm;

  &:hover {
    text-decoration: underline;
  }
}

.created-alias {
  &__row {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    margin-bottom: $spacing-sm;
  }

  &__email {
    font-weight: 500;
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
