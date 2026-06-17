<script setup lang="ts">
import { ref, computed } from "vue";
import type { AliasFormat } from "../../api/types.js";

const props = defineProps<{
  availableDomains: string[];
  defaultDomain: string;
  defaultFormat: AliasFormat;
  loading: boolean;
}>();

const emit = defineEmits<{
  create: [
    payload: { domain: string; format: AliasFormat; customPrefix: string },
  ];
}>();

const domain = ref(props.defaultDomain);
const format = ref<AliasFormat>(props.defaultFormat);
const customPrefix = ref("");
const domainSearch = ref("");

const filteredDomains = computed(() => {
  const q = domainSearch.value.toLowerCase();
  return q
    ? props.availableDomains.filter((d) => d.toLowerCase().includes(q))
    : props.availableDomains;
});

const formats: { value: AliasFormat; label: string }[] = [
  { value: "random_characters", label: "Characters" },
  { value: "random_words", label: "Words" },
  { value: "random_male_name", label: "Male name" },
  { value: "random_female_name", label: "Female name" },
  { value: "random_noun", label: "Noun" },
  { value: "custom", label: "Custom…" },
];

function submit() {
  emit("create", {
    domain: domain.value,
    format: format.value,
    customPrefix: customPrefix.value,
  });
}
</script>

<template>
  <div class="create-form">
    <div class="field">
      <label>Domain</label>
      <div class="domain-picker">
        <input
          v-model="domainSearch"
          type="text"
          placeholder="Filter domains…"
          class="domain-search"
        />
        <select v-model="domain" size="3" class="domain-select">
          <option v-for="d in filteredDomains" :key="d" :value="d">
            {{ d }}
          </option>
        </select>
      </div>
    </div>

    <div class="field">
      <label>Format</label>
      <div class="format-pills">
        <label
          v-for="f in formats"
          :key="f.value"
          class="pill"
          :class="{ selected: format === f.value }"
        >
          <input
            v-model="format"
            type="radio"
            :value="f.value"
            class="sr-only"
          />
          {{ f.label }}
        </label>
      </div>
    </div>

    <div v-if="format === 'custom'" class="field">
      <label>Prefix</label>
      <div class="prefix-input">
        <input
          v-model="customPrefix"
          type="text"
          placeholder="custom"
          class="prefix-text"
        />
        <span class="prefix-suffix">@{{ domain }}</span>
      </div>
    </div>

    <button
      class="primary create-btn"
      :disabled="loading || (format === 'custom' && !customPrefix.trim())"
      @click="submit"
    >
      {{ loading ? "Creating…" : "Create alias" }}
    </button>
  </div>
</template>

<style scoped lang="scss">
@use "../styles/variables" as *;

.create-form {
  border-top: 1px solid $color-border;
  padding-top: $spacing-md;
  margin-top: $spacing-sm;
}

.field {
  display: flex;
  align-items: flex-start;
  gap: $spacing-md;
  margin-bottom: $spacing-md;

  > label {
    min-width: 56px;
    padding-top: 5px;
    font-size: $font-size-sm;
    color: $color-muted;
    text-align: right;
  }
}

.domain-picker {
  display: flex;
  flex-direction: column;
  gap: $spacing-xs;
  flex: 1;
}

.domain-search {
  width: 100%;
}

.domain-select {
  width: 100%;
  min-height: 60px;
}

.format-pills {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-xs;
  flex: 1;
}

.pill {
  display: inline-block;
  padding: 2px $spacing-md;
  border: 1px solid $color-border;
  border-radius: 12px;
  cursor: pointer;
  font-size: $font-size-sm;
  user-select: none;

  &.selected {
    background: $color-primary;
    border-color: $color-primary;
    color: #fff;
  }

  &:hover:not(.selected) {
    background: #eee;
  }
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
}

.prefix-input {
  display: flex;
  align-items: center;
  flex: 1;
  border: 1px solid $color-border;
  border-radius: 3px;
  overflow: hidden;

  .prefix-text {
    flex: 1;
    border: none;
    outline: none;
    padding: $spacing-sm $spacing-md;
    min-width: 0;
  }

  .prefix-suffix {
    padding: $spacing-sm $spacing-md;
    background: #f0f0f0;
    color: $color-muted;
    font-size: $font-size-sm;
    white-space: nowrap;
    border-left: 1px solid $color-border;
  }
}

.create-btn {
  width: 100%;
}
</style>
