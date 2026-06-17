<template>
  <div class="spinner-wrap">
    <img src="/icon.svg" class="spinner" alt="" aria-hidden="true" />
    <p class="spinner-label">Loading…</p>
  </div>
</template>

<style scoped lang="scss">
@keyframes addy-swirl {
  0% {
    transform: scale(0.4) rotate(0deg);
    opacity: 0.6;
  }
  25% {
    transform: scale(1.3) rotate(90deg);
    opacity: 1;
  }
  50% {
    transform: scale(0.6) rotate(200deg);
    opacity: 0.7;
  }
  75% {
    transform: scale(1.5) rotate(300deg);
    opacity: 1;
  }
  100% {
    transform: scale(0.4) rotate(360deg);
    opacity: 0.6;
  }
}

.spinner-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px 0 16px;
}

.spinner {
  width: 56px;
  height: 56px;
  animation: addy-swirl 1.6s ease-in-out infinite;
}

.spinner-label {
  margin: 12px 0 0;
  color: #888;
  font-size: 12px;
}
</style>
