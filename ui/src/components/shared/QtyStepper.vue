<template>
  <span class="qty-stepper">
    <button class="minus" :style="btnSize" type="button" @click="$emit('minus')">−</button>
    <span class="count" :style="{ fontSize: small ? '13px' : '14px' }">{{ qty }}</span>
    <button class="plus" :style="btnSize" type="button" @click="$emit('plus')">+</button>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  qty: { type: Number, required: true },
  small: { type: Boolean, default: false },
})

defineEmits(['minus', 'plus'])

const btnSize = computed(() => {
  const s = props.small ? 22 : 26
  return { width: s + 'px', height: s + 'px', fontSize: props.small ? '14px' : '16px' }
})
</script>

<style scoped>
.qty-stepper {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.count {
  min-width: 18px;
  font-weight: 600;
  color: var(--so-ink-1);
  text-align: center;
}

.minus,
.plus {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  cursor: pointer;
  font-family: var(--so-font-sans);
  line-height: 1;
  padding: 0;
  transition: transform var(--so-dur) var(--so-ease-spring), background var(--so-dur) var(--so-ease), border-color var(--so-dur) var(--so-ease);
}

.minus:active,
.plus:active {
  transform: scale(0.85);
}

.minus {
  border: 1px solid var(--so-border-2);
  background: #fff;
  color: var(--so-ink-2);
}

.minus:hover {
  border-color: var(--so-orange);
  color: var(--so-orange);
}

.plus {
  border: none;
  background: var(--so-orange);
  color: #fff;
}

.plus:hover {
  background: var(--so-gold);
}
</style>
