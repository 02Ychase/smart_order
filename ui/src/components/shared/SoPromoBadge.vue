<template>
  <span class="so-promo" :class="`so-promo--${kind}`"><slot /></span>
</template>

<script setup>
defineProps({
  kind: {
    type: String,
    default: 'manjian',
    validator: (v) => ['manjian', 'hongbao', 'discount', 'newcomer', 'free'].includes(v),
  },
})
</script>

<style scoped>
.so-promo {
  display: inline-flex;
  align-items: center;
  height: 18px;
  padding: 0 5px;
  border-radius: 3px;
  font-size: 11px;
  font-weight: 600;
  line-height: 1;
  white-space: nowrap;
}

.so-promo--manjian {
  border: 1px solid var(--so-red);
  background: #fff;
  color: var(--so-red);
}

.so-promo--hongbao {
  background: var(--so-red);
  color: #fff;
}

.so-promo--discount {
  background: var(--so-yellow);
  color: var(--so-ink-1);
}

.so-promo--newcomer {
  background: var(--so-orange);
  color: #fff;
}

.so-promo--free {
  border: 1px solid #b7eb8f;
  background: var(--so-success-soft);
  color: var(--so-success);
}
</style>
