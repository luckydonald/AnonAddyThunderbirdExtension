<script setup lang="ts">
import { useI18n } from "../../composables/useI18n.js";

const props = defineProps<{
  hostUrl: string;
  apiKey: string;
  isDirty: boolean;
}>();

const emit = defineEmits<{
  "update:hostUrl": [value: string];
  "update:apiKey": [value: string];
  save: [];
  reset: [];
}>();

const { t } = useI18n();

function isValid() {
  if (
    props.hostUrl &&
    !(
      props.hostUrl.startsWith("http://") ||
      props.hostUrl.startsWith("https://")
    )
  )
    return false;
  if (!props.apiKey.trim()) return false;
  return true;
}
</script>

<template>
  <form @submit.prevent="emit('save')">
    <div class="field">
      <label for="hostUrl">{{ t("addyUrl") }}</label>
      <div class="field__input-wrap">
        <input
          id="hostUrl"
          type="text"
          :value="hostUrl"
          :placeholder="t('addyUrlPlaceholder')"
          @input="
            emit('update:hostUrl', ($event.target as HTMLInputElement).value)
          "
        />
        <span class="field__hint">{{ t("addyUrlHint") }}</span>
      </div>
    </div>
    <div class="field">
      <label for="apiKey">{{ t("apiKey") }}</label>
      <input
        id="apiKey"
        type="text"
        :value="apiKey"
        :placeholder="t('apiKeyPlaceholder')"
        @input="
          emit('update:apiKey', ($event.target as HTMLInputElement).value)
        "
      />
    </div>
    <div class="actions">
      <button type="submit" :disabled="!isDirty || !isValid()">
        {{ t("save") }}
      </button>
      <button type="button" :disabled="!isDirty" @click="emit('reset')">
        {{ t("reset") }}
      </button>
    </div>
  </form>
</template>

<style scoped lang="scss">
@use "../styles/variables" as *;

.field {
  display: flex;
  align-items: baseline;
  margin-bottom: $spacing-md;
  gap: $spacing-md;

  label {
    min-width: 70px;
    font-weight: 500;
  }

  &__input-wrap {
    display: flex;
    align-items: baseline;
    gap: $spacing-md;
    flex: 1;
  }

  &__hint {
    font-size: 0.85em;
    color: #666;
  }

  input {
    flex: 1;
    padding: $spacing-sm $spacing-md;
    font-size: $font-size-base;
    border: 1px solid #ccc;
    border-radius: 3px;
  }
}

.actions {
  margin-top: $spacing-lg;

  button {
    margin-right: $spacing-sm;
    padding: $spacing-sm $spacing-lg;
    cursor: pointer;

    &:disabled {
      opacity: 0.5;
      cursor: default;
    }
  }
}
</style>
