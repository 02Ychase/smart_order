<template>
  <span class="so-stars" :style="{ fontSize: size + 'px' }">
    <span class="filled">{{ filled }}</span><span class="empty">{{ empty }}</span>
    <strong v-if="showNum">{{ numText }}</strong>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  value: { type: Number, default: 0 },
  size: { type: Number, default: 12 },
  showNum: { type: Boolean, default: true },
})

const clamped = computed(() => Math.min(5, Math.max(0, Math.round(props.value))))
const filled = computed(() => '★★★★★'.slice(0, clamped.value))
const empty = computed(() => '★★★★★'.slice(clamped.value))
const numText = computed(() => props.value.toFixed(1))
</script>

<style scoped>
.so-stars {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  line-height: 1;
}

.filled {
  color: var(--so-gold);
  letter-spacing: -1px;
}

.empty {
  color: var(--so-border-2);
  letter-spacing: -1px;
}

strong {
  color: var(--so-gold);
  font-weight: 700;
}
</style>
