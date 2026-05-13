<template>
  <section class="search-result-view">
    <header class="dialog-header">
      <h2>搜索结果</h2>
      <span class="search-keyword">关键词：{{ keyword }}</span>
    </header>

    <p v-if="loading">加载中...</p>
    <p v-else-if="errorMessage" class="error-text">{{ errorMessage }}</p>
    <el-empty v-else-if="!result.merchants.length && !result.dishes.length" description="未找到相关结果" />

    <template v-else>
      <div v-if="result.merchants.length" class="result-section">
        <h4>商家</h4>
        <div
          v-for="merchant in result.merchants"
          :key="merchant.id"
          class="merchant-card"
          @click="emit('select-merchant', merchant.id)"
        >
          <div class="merchant-info">
            <strong>{{ merchant.name }}</strong>
            <span class="merchant-meta">{{ merchant.district }} · {{ merchant.homepage_category }}</span>
          </div>
          <span class="merchant-rating">{{ merchant.rating }}</span>
        </div>
      </div>

      <div v-if="result.dishes.length" class="result-section">
        <h4>菜品</h4>
        <div
          v-for="dish in result.dishes"
          :key="dish.id"
          class="dish-card"
          @click="emit('select-merchant', dish.merchant_id)"
        >
          <div class="dish-info">
            <strong>{{ dish.name }}</strong>
            <span class="dish-meta">{{ dish.description }}</span>
          </div>
          <span class="dish-price">{{ formatCurrency(dish.price) }}</span>
        </div>
      </div>
    </template>
  </section>
</template>

<script setup>
import { ref, watch } from 'vue'
import { searchCatalog } from '../api/catalog'
import { formatCurrency } from '../utils/currency'

const emit = defineEmits(['select-merchant'])
const props = defineProps({
  keyword: { type: String, default: '' },
})

const result = ref({ merchants: [], dishes: [] })
const loading = ref(false)
const errorMessage = ref('')

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
.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.search-keyword {
  color: #666;
  font-size: 14px;
}

.result-section {
  margin-bottom: 20px;
}

.result-section h4 {
  margin: 0 0 8px;
  font-size: 15px;
  color: #1f2a44;
}

.merchant-card,
.dish-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border: 1px solid #eee;
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: box-shadow 0.2s;
}

.merchant-card:hover,
.dish-card:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.merchant-info,
.dish-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.merchant-meta,
.dish-meta {
  font-size: 13px;
  color: #999;
}

.merchant-rating {
  font-weight: 600;
  color: #ff9900;
}

.dish-price {
  font-weight: 600;
  color: #1f2a44;
}

.error-text {
  color: #f56c6c;
  font-size: 14px;
}
</style>
