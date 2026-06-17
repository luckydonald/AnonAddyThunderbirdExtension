<script setup lang="ts">
import type { SaveStatus } from "../App.vue";

defineProps<{ status: SaveStatus }>();
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
    <template v-if="status.kind === 'success'">Settings saved.</template>
    <template v-else-if="status.kind === 'error'">{{
      status.message
    }}</template>
    <template v-else-if="status.kind === 'permission_denied'">
      Permission to access <strong>{{ status.hostUrl }}</strong> was denied.
      Settings were not saved. Grant the host permission to use a custom server
      URL.
    </template>
    <template v-else-if="status.kind === 'permission_granted'">
      Host permission for <strong>{{ status.hostUrl }}</strong> granted.
      Settings saved.
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
