<script setup lang="ts">
import { useI18n } from "../../composables/useI18n.js";
import type { SaveStatus } from "../App.vue";

defineProps<{ status: SaveStatus }>();

const { t } = useI18n();
</script>

<template>
  <div
    v-if="status.kind !== 'idle'"
    class="banner"
    :class="{
      'banner--success':
        status.kind === 'success' || status.kind === 'permission_granted',
      'banner--error': status.kind === 'error',
      'banner--warning': status.kind === 'permission_denied',
    }"
  >
    <template v-if="status.kind === 'success'">{{
      t("settingsSaved")
    }}</template>
    <template v-else-if="status.kind === 'error'">{{
      status.message
    }}</template>
    <template v-else-if="status.kind === 'permission_denied'">
      {{ t("permissionDeniedPrefix") }}
      <strong>{{ status.hostUrl }}</strong>
      {{ t("permissionDeniedSuffix") }}
    </template>
    <template v-else-if="status.kind === 'permission_granted'">
      {{ t("permissionGrantedPrefix") }}
      <strong>{{ status.hostUrl }}</strong>
      {{ t("permissionGrantedSuffix") }}
    </template>
  </div>
</template>

<style scoped lang="scss">
@use "../styles/variables" as *;

.banner {
  padding: $spacing-sm $spacing-lg;
  border-radius: 4px;
  margin-bottom: $spacing-lg;
  font-size: $font-size-base;
  border-left: 4px solid currentcolor;

  &--success {
    background: $color-success-bg;
    color: $color-success;
  }

  &--error {
    background: $color-error-bg;
    color: $color-error;
  }

  &--warning {
    background: $color-warning-bg;
    color: $color-warning;
  }
}
</style>
