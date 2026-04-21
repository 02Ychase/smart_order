<template>
  <section class="merchant-wall">
    <p v-if="loading">加载中...</p>
    <p v-else-if="errorMessage">{{ errorMessage }}</p>
    <el-empty v-else-if="!merchants.length" description="暂无商家" />
    <div v-else class="merchant-grid">
      <article
        v-for="merchant in merchants"
        :key="merchant.id"
        class="merchant-card"
        @click="$emit('select-merchant', merchant.id)"
      >
        <div class="merchant-cover" :style="merchantCover(merchant).imageSrc ? undefined : merchantCover(merchant).gradientStyle">
          <img
            v-if="merchantCover(merchant).imageSrc"
            :src="merchantCover(merchant).imageSrc"
            :alt="`${merchant.name} 封面图`"
            data-test="merchant-cover-image"
          />
          <span class="cover-badge">{{ merchant.homepage_category }}</span>
        </div>
        <div class="merchant-content">
          <div class="merchant-topline">
            <h3>{{ merchant.name }}</h3>
            <span>{{ merchant.rating.toFixed(1) }}</span>
          </div>
          <p class="category">{{ merchant.homepage_category }}</p>
          <p class="promo">{{ merchant.promo_text }}</p>
          <p class="meta">{{ merchant.district }} · 配送费 {{ formatCurrency(merchant.delivery_fee) }}</p>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup>
import { formatCurrency } from '../utils/currency'
import { getMerchantCover } from '../utils/homepage'

defineProps({
  merchants: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  errorMessage: { type: String, default: '' },
})

defineEmits(['select-merchant'])

const merchantCover = (merchant) => getMerchantCover(merchant.homepage_category)
</script>

<style scoped>
.merchant-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 20px;
}

.merchant-card {
  overflow: hidden;
  border-radius: 24px;
  background: #fff;
  box-shadow: 0 18px 36px rgba(44, 76, 128, 0.1);
  cursor: pointer;
}

.merchant-cover {
  position: relative;
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
  min-height: 132px;
  padding: 18px;
  color: #385071;
  font-weight: 600;
}

.merchant-cover img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-badge {
  position: relative;
  z-index: 1;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.88);
}

.merchant-content {
  padding: 18px;
}

.merchant-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.merchant-topline h3,
.category,
.promo,
.meta {
  margin: 0;
}

.category {
  margin-top: 10px;
  color: #6b7fa0;
}

.promo {
  margin-top: 8px;
  color: #2c456a;
  font-weight: 600;
}

.meta {
  margin-top: 12px;
  color: #7d8da8;
}
</style>
