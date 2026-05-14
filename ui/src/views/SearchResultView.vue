<template>
  <section class="search-result-view">
    <div class="modal-header">
      <div>
        <h2>搜索结果</h2>
        <p class="subtitle">关键词：{{ keyword }}</p>
      </div>
      <button class="close-x" @click="$emit('close')">×</button>
    </div>

    <div class="modal-body mt-scroll">
      <p v-if="loading" class="state-text">加载中...</p>
      <p v-else-if="errorMessage" class="state-text state-text--error">{{ errorMessage }}</p>
      <div v-else-if="!result.merchants.length && !result.dishes.length" class="state-text">
        未找到「{{ keyword }}」相关结果
      </div>

      <template v-else>
        <!-- Merchants -->
        <div v-if="result.merchants.length" class="result-section">
          <h4>商家 ({{ result.merchants.length }})</h4>
          <div
            v-for="merchant in result.merchants"
            :key="merchant.id"
            class="search-row"
            @click="emit('select-merchant', merchant.id)"
          >
            <div class="row-cover">
              <span class="cover-emoji">🏪</span>
            </div>
            <div class="row-info">
              <p class="row-name">{{ merchant.name }}</p>
              <p class="row-meta">{{ merchant.district }} · {{ merchant.homepage_category }}</p>
            </div>
            <SoStars :value="merchant.rating || 0" :size="11" />
          </div>
        </div>

        <!-- Dishes -->
        <div v-if="result.dishes.length" class="result-section">
          <h4>菜品 ({{ result.dishes.length }})</h4>
          <div
            v-for="dish in result.dishes"
            :key="dish.id"
            class="search-row"
            @click="emit('select-merchant', dish.merchant_id)"
          >
            <div class="dish-thumb" :style="{ background: dishBg(dish) }">{{ dishGlyph(dish) }}</div>
            <div class="row-info">
              <p class="row-name">{{ dish.name }}</p>
              <p class="row-meta-ellipsis">{{ dish.merchant_name }}{{ dish.description ? ' · ' + dish.description : '' }}</p>
            </div>
            <SoPrice :value="dish.price" :size="16" />
          </div>
        </div>
      </template>
    </div>
  </section>
</template>

<script setup>
import { ref, watch } from 'vue'
import { searchCatalog } from '../api/catalog'
import SoPrice from '../components/shared/SoPrice.vue'
import SoStars from '../components/shared/SoStars.vue'

const emit = defineEmits(['select-merchant', 'close'])
const props = defineProps({
  keyword: { type: String, default: '' },
})

const result = ref({ merchants: [], dishes: [] })
const loading = ref(false)
const errorMessage = ref('')

const DISH_PALETTE = [
  { glyph: '🍜', bg: 'linear-gradient(135deg,#fff3e0,#ffe0b2)' },
  { glyph: '🍛', bg: 'linear-gradient(135deg,#fff8e1,#ffecb3)' },
  { glyph: '🍲', bg: 'linear-gradient(135deg,#fce4ec,#f8bbd0)' },
  { glyph: '🍱', bg: 'linear-gradient(135deg,#e8f5e9,#c8e6c9)' },
  { glyph: '🥘', bg: 'linear-gradient(135deg,#fff3e0,#ffccbc)' },
]

const dishGlyph = (dish) => DISH_PALETTE[(dish.id || 0) % DISH_PALETTE.length].glyph
const dishBg = (dish) => DISH_PALETTE[(dish.id || 0) % DISH_PALETTE.length].bg

const loadResults = async (keyword) => {
  if (!keyword) return
  loading.value = true
  errorMessage.value = ''
  try {
    result.value = await searchCatalog(keyword)
  } catch (error) {
    errorMessage.value = error?.message || '搜索失败，请稍后再试'
  } finally {
    loading.value = false
  }
}

watch(() => props.keyword, loadResults, { immediate: true })
</script>

<style scoped>
.search-result-view {
  display: flex;
  flex-direction: column;
  max-height: 78vh;
  color: var(--so-ink-1);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
  border-bottom: 1px solid var(--so-border-1);
}

.modal-header h2 { margin: 0; font-size: 18px; font-weight: 700; }
.subtitle { margin: 4px 0 0; color: var(--so-ink-4); font-size: 13px; }

.close-x {
  width: 28px; height: 28px; border: none; background: transparent;
  cursor: pointer; color: var(--so-ink-4); font-size: 22px; line-height: 1; padding: 0;
}

.modal-body { flex: 1; overflow-y: auto; padding: 12px 24px 24px; }

/* Sections */
.result-section { margin-bottom: 16px; }

.result-section h4 {
  margin: 8px 0;
  font-size: 13px;
  color: var(--so-ink-4);
  font-weight: 600;
}

/* Search row */
.search-row {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid var(--so-surface-line);
  cursor: pointer;
  transition: background 0.15s;
}

.search-row:hover { background: var(--so-yellow-faint); margin: 0 -8px; padding: 10px 8px; border-radius: var(--so-r-sm); }

.row-cover {
  width: 48px; height: 48px; border-radius: var(--so-r-sm);
  background: linear-gradient(135deg, #fff3e0, #ffe0b2);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}

.cover-emoji { font-size: 22px; }

.dish-thumb {
  width: 48px; height: 48px; border-radius: var(--so-r-sm);
  display: flex; align-items: center; justify-content: center;
  font-size: 24px; flex-shrink: 0;
}

.row-info { flex: 1; min-width: 0; }
.row-name { margin: 0; font-size: 14px; font-weight: 700; color: var(--so-ink-1); }
.row-meta { margin: 4px 0 0; font-size: 12px; color: var(--so-ink-4); }

.row-meta-ellipsis {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--so-ink-4);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.state-text { padding: 60px 0; text-align: center; color: var(--so-ink-4); font-size: 14px; }
.state-text--error { color: var(--so-red); }
</style>
