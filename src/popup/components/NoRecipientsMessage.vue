<script setup lang="ts">
import { useI18n } from "../../composables/useI18n.js";

defineEmits<{ close: [] }>();

const { t } = useI18n();
</script>

<template>
  <div class="no-recipients">
    <p>{{ t("noRecipientsMessage") }}</p>
    <button @click="$emit('close')">{{ t("close") }}</button>
  </div>
</template>

<style scoped lang="scss">
@use "../styles/variables" as *;

.no-recipients {
  padding: $spacing-md 0;
  color: $color-muted;

  p {
    margin: 0 0 $spacing-md;
  }
}
</style>
