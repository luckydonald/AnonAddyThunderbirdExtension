<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "../../composables/useI18n.js";

const props = defineProps<{
  hostUrl: string;
  hasSelections: boolean;
}>();

defineEmits<{
  apply: [];
  close: [];
  openSettings: [];
}>();

const { t } = useI18n();

const hostname = computed(() => {
  try {
    return new URL(props.hostUrl).hostname;
  } catch {
    return props.hostUrl;
  }
});
</script>

<template>
  <div class="footer">
    <div class="footer__links">
      <button class="link-btn" @click="$emit('openSettings')">
        {{ t("settingsLink") }}
      </button>
      <a :href="hostUrl" target="_blank" class="footer__addy-link">
        {{ t("goTo", hostname) }}
      </a>
    </div>
    <div class="footer__actions">
      <button @click="$emit('close')">{{ t("cancel") }}</button>
      <button
        class="primary"
        :disabled="!hasSelections"
        @click="$emit('apply')"
      >
        {{ t("apply") }}
      </button>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use "../styles/variables" as *;

.footer {
  border-top: 1px solid $color-border;
  padding-top: $spacing-md;
  margin-top: $spacing-sm;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: $spacing-sm;

  &__links {
    display: flex;
    align-items: center;
    gap: $spacing-md;
  }

  &__addy-link {
    font-size: $font-size-sm;
    color: $color-muted;
    text-decoration: none;

    &:hover {
      text-decoration: underline;
    }
  }

  &__actions {
    display: flex;
    gap: $spacing-sm;
  }
}

.link-btn {
  background: none;
  border: none;
  padding: 0;
  font-size: $font-size-sm;
  color: $color-muted;
  cursor: pointer;

  &:hover {
    color: $color-text;
  }
}
</style>
