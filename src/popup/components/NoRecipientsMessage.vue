<script setup lang="ts">
defineEmits<{ close: [] }>();
</script>

<template>
  <div class="no-recipients">
    <p>Add at least one address to the To/CC/BCC field first.</p>
    <button @click="$emit('close')">Close</button>
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
