<template>
  <span class="so-price" :style="{ color, fontSize: size + 'px' }">
    <span class="so-price-unit" :style="{ fontSize: Math.round(size * 0.6) + 'px' }">¥</span>
    <span>{{ display }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  value: { type: [Number, String], required: true },
  size: { type: Number, default: 18 },
  color: { type: String, default: 'var(--so-red)' },
})

const display = computed(() => {
  const n = Number(props.value)
  return Number.isFinite(n) ? n.toFixed(2) : props.value
})
</script>

<style scoped>
.so-price {
  font-weight: 700;
  line-height: 1;
  font-family: var(--so-font-sans);
  white-space: nowrap;
}
</style>
