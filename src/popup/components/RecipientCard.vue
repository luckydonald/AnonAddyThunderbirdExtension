<script setup lang="ts">
import { ref, watch, computed } from "vue";
import { useI18n } from "../../composables/useI18n.js";
import type { Alias } from "../../api/types.js";

const props = defineProps<{
  address: string;
  name: string;
  existingAliases: Alias[];
  allAliases: Alias[];
  selectedAlias: string | null;
}>();

const emit = defineEmits<{
  "update:selectedAlias": [value: string | null];
  "update:address": [value: string];
  "open-create-window": [payload: { email: string; name: string }];
  disable: [id: string];
  delete: [id: string];
  restore: [id: string];
}>();

const { t } = useI18n();

const editableAddress = ref(props.address);
const aliasSearch = ref("");

watch(
  () => props.address,
  (v) => {
    editableAddress.value = v;
  },
);

function onAddressChange() {
  const v = editableAddress.value.trim();
  if (v && v !== props.address) emit("update:address", v);
}

function selectAlias(email: string) {
  emit("update:selectedAlias", email === props.selectedAlias ? null : email);
}

// Typeahead: search across ALL aliases when the user types.
const searchResults = computed(() => {
  const q = aliasSearch.value.trim().toLowerCase();
  if (!q) return [] as Alias[];
  return props.allAliases
    .filter(
      (a) =>
        a.email.toLowerCase().includes(q) ||
        (a.description ?? "").toLowerCase().includes(q),
    )
    .slice(0, 15);
});

// Pin the currently selected alias when it's not in the search results.
const pinnedAlias = computed((): Alias | null => {
  if (!props.selectedAlias || !aliasSearch.value.trim()) return null;
  if (searchResults.value.some((a) => a.email === props.selectedAlias))
    return null;
  return props.allAliases.find((a) => a.email === props.selectedAlias) ?? null;
});

function selectFromSearch(email: string) {
  emit("update:selectedAlias", email === props.selectedAlias ? null : email);
  aliasSearch.value = "";
}

function forwardingFor(aliasEmail: string): string | null {
  const am = aliasEmail.match(/^(.+)@(.+)$/);
  const rm = props.address.match(/^(.+)@(.+)$/);
  if (!am || !rm) return null;
  return `${am[1]}+${rm[1]}=${rm[2]}@${am[2]}`;
}
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

    <input
      v-model="aliasSearch"
      type="text"
      class="alias-search"
      placeholder="Search all aliases…"
    />

    <!-- Typeahead search results -->
    <div
      v-if="searchResults.length > 0 || pinnedAlias"
      class="alias-list alias-list--search"
    >
      <!-- Pinned selected alias (when not already in search results) -->
      <div
        v-if="pinnedAlias"
        class="alias-option selected alias-option--pinned"
        @click="selectFromSearch(pinnedAlias.email)"
      >
        <input
          type="radio"
          :name="`alias-${address}`"
          :value="pinnedAlias.email"
          :checked="true"
          @change="selectFromSearch(pinnedAlias.email)"
        />
        <div class="alias-option__body">
          <div class="alias-option__row">
            <kbd class="alias-option__email">{{ pinnedAlias.email }}</kbd>
            <span class="tag tag--selected">selected</span>
          </div>
          <div
            v-if="forwardingFor(pinnedAlias.email)"
            class="alias-option__row alias-option__row--fwd"
          >
            <span class="alias-option__fwd-label">{{
              t("aliasPreviewLabel")
            }}</span>
            <code class="alias-option__fwd">{{
              forwardingFor(pinnedAlias.email)
            }}</code>
          </div>
        </div>
      </div>
      <div
        v-for="alias in searchResults"
        :key="alias.id"
        class="alias-option"
        :class="{ selected: selectedAlias === alias.email }"
        @click="selectFromSearch(alias.email)"
      >
        <input
          type="radio"
          :name="`alias-${address}`"
          :value="alias.email"
          :checked="selectedAlias === alias.email"
          @change="selectFromSearch(alias.email)"
        />
        <div class="alias-option__body">
          <div class="alias-option__row">
            <kbd class="alias-option__email">{{ alias.email }}</kbd>
            <span v-if="alias.description" class="alias-option__desc">
              {{ alias.description }}
            </span>
          </div>
          <div
            v-if="forwardingFor(alias.email)"
            class="alias-option__row alias-option__row--fwd"
          >
            <span class="alias-option__fwd-label">{{
              t("aliasPreviewLabel")
            }}</span>
            <code class="alias-option__fwd">{{
              forwardingFor(alias.email)
            }}</code>
          </div>
        </div>
      </div>
    </div>

    <div class="alias-list" v-else>
      <!-- Existing aliases -->
      <div
        v-for="alias in existingAliases"
        :key="alias.id"
        class="alias-option"
        :class="{ selected: selectedAlias === alias.email }"
        @click="alias.active && selectAlias(alias.email)"
      >
        <input
          type="radio"
          :name="`alias-${address}`"
          :value="alias.email"
          :checked="selectedAlias === alias.email"
          :disabled="!alias.active"
          @change="selectAlias(alias.email)"
        />
        <div class="alias-option__body">
          <div class="alias-option__row">
            <kbd
              class="alias-option__email"
              :class="{ 'alias-option__email--inactive': !alias.active }"
              >{{ alias.email }}</kbd
            >
            <span v-if="!alias.active" class="tag tag--inactive">{{
              t("inactive")
            }}</span>
            <span v-if="alias.description" class="alias-option__desc">
              {{ alias.description }}
            </span>
          </div>
          <div
            v-if="forwardingFor(alias.email)"
            class="alias-option__row alias-option__row--fwd"
          >
            <span class="alias-option__fwd-label">{{
              t("aliasPreviewLabel")
            }}</span>
            <code class="alias-option__fwd">{{
              forwardingFor(alias.email)
            }}</code>
          </div>
          <div class="alias-option__actions" @click.stop>
            <button
              v-if="alias.active"
              class="small danger"
              :title="t('disableHint')"
              @click="$emit('disable', alias.id)"
            >
              {{ t("disable") }}
            </button>
            <button
              v-else
              class="small"
              :title="t('disableHint')"
              @click="$emit('restore', alias.id)"
            >
              {{ t("reenable") }}
            </button>
            <button
              class="small danger"
              :title="t('deleteHint')"
              @click="$emit('delete', alias.id)"
            >
              {{ t("deleteAlias") }}
            </button>
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div v-if="existingAliases.length === 0" class="no-aliases">
        <em>{{ t("noExistingAliases") }}</em>
      </div>
    </div>

    <!-- Don't replace — visible when there are any aliases or a selection -->
    <label
      v-if="existingAliases.length > 0 || selectedAlias !== null"
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

    <!-- + New Alias — opens a dedicated TB popup window -->
    <div class="new-alias-trigger">
      <button
        class="new-alias-btn"
        @click="emit('open-create-window', { email: editableAddress, name })"
      >
        + {{ t("createAlias") }}
      </button>
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

.alias-search {
  width: 100%;
  box-sizing: border-box;
  font-size: $font-size-sm;
  padding: $spacing-xs $spacing-sm;
  border: 1px solid $color-border;
  border-radius: 3px;
  margin-bottom: $spacing-sm;
  background: transparent;
  color: inherit;

  &:focus {
    outline: none;
    border-color: $color-primary;
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

  &__row--fwd {
    margin-top: $spacing-xs;
    gap: $spacing-xs;
  }

  &__fwd-label {
    color: $color-muted;
    font-size: $font-size-sm;
    flex-shrink: 0;
  }

  &__fwd {
    font-family: monospace;
    font-size: $font-size-sm;
    color: $color-muted;
    word-break: break-all;
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

  &--selected {
    background: #dbeafe;
    color: $color-primary;
    font-weight: 600;
  }
}

button.small {
  font-size: $font-size-sm;
  padding: 1px $spacing-sm;
}

.new-alias-trigger {
  margin-top: $spacing-sm;
}

.new-alias-btn {
  font-size: $font-size-sm;
  padding: 3px $spacing-md;
  border: 1px dashed $color-border;
  border-radius: 3px;
  background: transparent;
  color: $color-primary;
  cursor: pointer;
  width: 100%;
  text-align: center;

  &:hover {
    border-color: $color-primary;
    background: #f0f5ff;
  }
}
</style>
