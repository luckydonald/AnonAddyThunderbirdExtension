<script setup lang="ts">
import { ref, computed, watch, nextTick } from "vue";
import { useI18n } from "../../composables/useI18n.js";
import type { AliasFormat } from "../../api/types.js";

const FORMAT_PLACEHOLDERS: Record<AliasFormat, string> = {
  random_characters: "[chars]",
  random_words: "[words]",
  random_male_name: "[name]",
  random_female_name: "[name]",
  random_noun: "[noun]",
  custom: "",
};

const props = defineProps<{
  availableDomains: string[];
  defaultDomain: string;
  defaultFormat: AliasFormat;
  loading: boolean;
  targetEmail: string;
  targetName: string;
}>();

const emit = defineEmits<{
  create: [
    payload: { domain: string; format: AliasFormat; customPrefix: string },
  ];
}>();

const { t } = useI18n();

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

const formats = computed((): { value: AliasFormat; label: string }[] => [
  { value: "random_characters", label: t("formatCharacters") },
  { value: "random_words", label: t("formatWords") },
  { value: "random_male_name", label: t("formatMaleName") },
  { value: "random_female_name", label: t("formatFemaleName") },
  { value: "random_noun", label: t("formatNoun") },
  { value: "custom", label: t("formatCustom") },
]);

const aliasLocalPreview = computed(() => {
  if (format.value === "custom") {
    return customPrefix.value.trim() || "[custom]";
  }
  return FORMAT_PLACEHOLDERS[format.value] || "[alias]";
});

const forwardingPreview = computed(() => {
  const m = props.targetEmail.match(/^(.+)@(.+)$/);
  if (!m) return null;
  const [, targetLocal, targetDomain] = m;
  return `${aliasLocalPreview.value}+${targetLocal}=${targetDomain}@${domain.value}`;
});

const sendsAsPreview = computed(() => {
  if (!forwardingPreview.value) return null;
  return props.targetName
    ? `${props.targetName} <${forwardingPreview.value}>`
    : forwardingPreview.value;
});

// ── Domain combobox ───────────────────────────────────────────────────────────
const comboboxOpen = ref(false);
const comboboxActiveIdx = ref(0);
const searchInput = ref<HTMLInputElement | null>(null);

function openCombobox() {
  domainSearch.value = "";
  comboboxActiveIdx.value = 0;
  comboboxOpen.value = true;
  nextTick(() => searchInput.value?.focus());
}

function selectDomain(d: string) {
  domain.value = d;
  comboboxOpen.value = false;
  domainSearch.value = "";
}

function onComboboxKey(e: KeyboardEvent) {
  const len = filteredDomains.value.length;
  if (e.key === "ArrowDown") {
    comboboxActiveIdx.value = Math.min(comboboxActiveIdx.value + 1, len - 1);
    e.preventDefault();
  } else if (e.key === "ArrowUp") {
    comboboxActiveIdx.value = Math.max(comboboxActiveIdx.value - 1, 0);
    e.preventDefault();
  } else if (e.key === "Enter") {
    const d = filteredDomains.value[comboboxActiveIdx.value];
    if (d) selectDomain(d);
    e.preventDefault();
  } else if (e.key === "Escape") {
    comboboxOpen.value = false;
  }
}

watch(domainSearch, () => { comboboxActiveIdx.value = 0; });

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
    <p class="section-heading">{{ t("createAliasSection") }}</p>

    <div class="field">
      <label>{{ t("domain") }}</label>
      <div class="combobox" @keydown="onComboboxKey">
        <button
          type="button"
          class="combobox__trigger"
          @click="openCombobox"
        >
          <span>{{ domain }}</span>
          <span class="combobox__arrow">▾</span>
        </button>
        <div v-if="comboboxOpen" class="combobox__dropdown">
          <input
            ref="searchInput"
            v-model="domainSearch"
            type="text"
            :placeholder="t('filterDomains')"
            class="combobox__search"
            @blur.self="comboboxOpen = false"
          />
          <ul class="combobox__list">
            <li
              v-for="(d, i) in filteredDomains"
              :key="d"
              class="combobox__option"
              :class="{ selected: domain === d, active: i === comboboxActiveIdx }"
              @mousedown.prevent="selectDomain(d)"
            >
              {{ d }}
            </li>
          </ul>
        </div>
      </div>
    </div>

    <div class="field">
      <label>{{ t("format") }}</label>
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
      <label>{{ t("prefixLabel") }}</label>
      <div class="prefix-input">
        <input
          v-model="customPrefix"
          type="text"
          :placeholder="t('customPrefixPlaceholder')"
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
      {{ loading ? t("creating") : t("createAlias") }}
    </button>

    <!-- "Sends via:" only when name is present (forwarding addr buried in Sends as:) -->
    <p v-if="forwardingPreview && targetName" class="preview">
      <span class="preview-label">{{ t("aliasPreviewLabel") }}</span>
      <code class="preview-address">{{ forwardingPreview }}</code>
    </p>
    <!-- "Sends as:" always when preview available -->
    <p v-if="sendsAsPreview" class="preview">
      <span class="preview-label">{{ t("aliasDisplayLabel") }}</span>
      <code class="preview-address">{{ sendsAsPreview }}</code>
    </p>
  </div>
</template>

<style scoped lang="scss">
@use "../styles/variables" as *;

.create-form {
  border-top: 1px solid $color-border;
  padding-top: $spacing-md;
  margin-top: $spacing-md;
}

.section-heading {
  margin: 0 0 $spacing-sm;
  font-size: $font-size-sm;
  font-weight: 600;
  color: $color-muted;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.field {
  display: flex;
  align-items: flex-start;
  gap: $spacing-md;
  margin-bottom: $spacing-md;
  min-width: 0;

  > label {
    min-width: 56px;
    flex-shrink: 0;
    padding-top: 5px;
    font-size: $font-size-sm;
    color: $color-muted;
    text-align: right;
  }
}

.combobox {
  flex: 1;
  min-width: 0;
  position: relative;

  &__trigger {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: $spacing-sm $spacing-md;
    border: 1px solid $color-border;
    border-radius: 3px;
    background: #fff;
    cursor: pointer;
    font-size: $font-size-sm;
    text-align: left;

    &:hover {
      border-color: $color-primary;
    }
  }

  &__arrow {
    color: $color-muted;
    margin-left: $spacing-sm;
  }

  &__dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    z-index: 100;
    border: 1px solid $color-border;
    border-radius: 3px;
    background: #fff;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
    margin-top: 2px;
  }

  &__search {
    width: 100%;
    border: none;
    border-bottom: 1px solid $color-border;
    padding: $spacing-sm $spacing-md;
    font-size: $font-size-sm;
    box-sizing: border-box;

    &:focus {
      outline: none;
    }
  }

  &__list {
    list-style: none;
    margin: 0;
    padding: $spacing-xs 0;
    max-height: 120px;
    overflow-y: auto;
  }

  &__option {
    padding: $spacing-sm $spacing-md;
    font-size: $font-size-sm;
    cursor: pointer;

    &:hover,
    &.active {
      background: #f0f5ff;
    }

    &.selected {
      font-weight: 600;
      color: $color-primary;
    }
  }
}

.format-pills {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-xs;
  flex: 1;
  min-width: 0;
}

.pill {
  display: inline-block;
  padding: 2px $spacing-md;
  border: 1px solid $color-border;
  border-radius: 12px;
  cursor: pointer;
  font-size: $font-size-sm;
  user-select: none;
  white-space: nowrap;

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
  min-width: 0;
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

.preview {
  margin: $spacing-sm 0 0;
  font-size: $font-size-sm;
  color: $color-muted;
  display: flex;
  align-items: baseline;
  gap: $spacing-sm;
  flex-wrap: wrap;
}

.preview-label {
  flex-shrink: 0;
}

.preview-address {
  font-family: monospace;
  word-break: break-all;
  background: #f5f5f5;
  border: 1px solid $color-border;
  border-radius: 3px;
  padding: 1px 5px;
}
</style>
