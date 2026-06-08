<template>
  <section class="merchant-wall">
    <div v-if="loading" class="merchant-panel" aria-busy="true" aria-label="商家加载中">
      <div v-for="n in 4" :key="`sk-${n}`" class="merchant-row merchant-row--skeleton" :class="{ 'merchant-row--first': n === 1 }">
        <div class="so-skeleton merchant-cover"></div>
        <div class="merchant-content skeleton-lines">
          <span class="so-skeleton line line--title"></span>
          <span class="so-skeleton line line--sm"></span>
          <span class="so-skeleton line line--md"></span>
          <span class="so-skeleton line line--lg"></span>
        </div>
      </div>
    </div>
    <div v-else-if="errorMessage" class="merchant-state merchant-state--error">{{ errorMessage }}</div>
    <el-empty v-else-if="!merchants.length" description="暂无商家" />
    <div v-else class="merchant-panel">
      <article
        v-for="(merchant, index) in merchants"
        :key="merchant.id"
        class="merchant-row"
        :class="{ 'merchant-row--first': index === 0 }"
        @click="$emit('select-merchant', merchant.id)"
      >
        <div class="merchant-cover" :style="merchantCover(merchant).imageSrc ? undefined : merchantCover(merchant).gradientStyle">
          <img
            v-if="merchantCover(merchant).imageSrc"
            :src="merchantCover(merchant).imageSrc"
            :alt="`${merchant.name} 封面图`"
            data-test="merchant-cover-image"
          />
          <span v-if="coverPromo(merchant)" class="cover-promo">{{ coverPromo(merchant) }}</span>
          <span class="cover-category">{{ merchant.homepage_category }}</span>
          <div class="cover-shade" aria-hidden="true"></div>
          <div v-if="isClosed(merchant)" class="closed-mask">休息中</div>
        </div>

        <div class="merchant-content">
          <div class="merchant-title-row">
            <h3>{{ merchant.name }}</h3>
            <span v-if="isFeatured(merchant)" class="brand-tag">品牌</span>
          </div>

          <div class="rating-row">
            <span class="stars" aria-hidden="true">
              {{ filledStars(merchant.rating) }}<span>{{ emptyStars(merchant.rating) }}</span>
            </span>
            <strong>{{ ratingText(merchant.rating) }}</strong>
            <span>月售 {{ salesText(merchant) }}</span>
          </div>

          <div class="promo-row">
            <span
              v-for="badge in promoBadges(merchant)"
              :key="`${merchant.id}-${badge.kind}-${badge.text}`"
              class="promo-badge"
              :class="`promo-badge--${badge.kind}`"
            >
              {{ badge.text }}
            </span>
          </div>

          <div class="meta-row">
            <span class="delivery-time">{{ deliveryMinutes(merchant) }}分钟</span>
            <span>·</span>
            <span>{{ distanceText(merchant) }}km</span>
            <span>·</span>
            <span>起送 {{ mtYuan(minOrder(merchant)) }}</span>
            <span>·</span>
            <span>配送费 {{ mtYuan(merchant.delivery_fee) }}</span>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup>
import { getMerchantCover } from '../utils/homepage'

defineProps({
  merchants: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  errorMessage: { type: String, default: '' },
})

defineEmits(['select-merchant'])

const merchantCover = (merchant) => getMerchantCover(merchant.homepage_category)

const clampStars = (value) => Math.min(5, Math.max(0, Math.round(Number(value || 0))))
const filledStars = (value) => '★★★★★'.slice(0, clampStars(value))
const emptyStars = (value) => '★★★★★'.slice(clampStars(value))
const ratingText = (value) => Number(value || 0).toFixed(1)

const mtYuan = (value) => {
  const numberValue = Number(value || 0)
  const digits = numberValue % 1 === 0 ? 0 : 1
  return `¥${numberValue.toFixed(digits)}`
}

const salesText = (merchant) => merchant.sales || merchant.monthly_sales || merchant.monthly_sales_text || '300+'
const deliveryMinutes = (merchant) => merchant.delivery_minutes || merchant.delivery_time_minutes || merchant.estimated_delivery_minutes || 28
const distanceText = (merchant) => Number(merchant.distance_km || merchant.distance || 1.2).toFixed(1)
const minOrder = (merchant) => merchant.min_order_amount || merchant.min_order || merchant.minimum_order_amount || 20
const isFeatured = (merchant) => Boolean(merchant.featured || merchant.is_featured)
const isClosed = (merchant) => merchant.open === false || merchant.status === 'closed'

const coverPromo = (merchant) => {
  const text = (merchant.promo_text || '').split(/[·，,\/]/)[0]?.trim()
  return text || '满50减8'
}

const promoKind = (text) => {
  if (text.includes('红包')) return 'hongbao'
  if (text.includes('折')) return 'discount'
  if (text.includes('新')) return 'newcomer'
  if (text.includes('免')) return 'free'
  return 'manjian'
}

const promoBadges = (merchant) => {
  const pieces = (merchant.promo_text || '')
    .split(/[·，,\/]/)
    .map((text) => text.trim())
    .filter(Boolean)
    .slice(0, 3)

  if (!pieces.length) {
    return [
      { kind: 'manjian', text: '满50减8' },
      { kind: 'newcomer', text: '新客券' },
    ]
  }

  const badges = pieces.map((text) => ({ kind: promoKind(text), text }))
  if (!badges.some((badge) => badge.kind === 'newcomer')) {
    badges.push({ kind: 'newcomer', text: '新客券' })
  }
  if (isFeatured(merchant)) {
    badges.push({ kind: 'discount', text: '折' })
  }
  return badges.slice(0, 3)
}
</script>

<style scoped>
.merchant-wall {
  width: 100%;
}

.merchant-panel,
.merchant-state {
  border-radius: var(--so-r-lg);
  background: var(--so-surface);
  box-shadow: var(--so-shadow-card);
}

.merchant-panel {
  padding: 0 20px 8px;
}

.merchant-state {
  padding: 40px 0;
  color: var(--so-ink-4);
  font-size: 14px;
  text-align: center;
}

.merchant-state--error {
  color: var(--so-red);
}

.merchant-row {
  display: flex;
  gap: 14px;
  padding: 14px;
  border-top: 1px solid var(--so-surface-line);
  border-radius: var(--so-r-md);
  background: var(--so-surface);
  cursor: pointer;
  transition: background var(--so-dur) var(--so-ease),
    box-shadow var(--so-dur) var(--so-ease),
    transform var(--so-dur) var(--so-ease);
}

.merchant-row--first {
  border-top: 0;
}

.merchant-row:not(.merchant-row--skeleton):hover {
  background: var(--so-yellow-faint);
  box-shadow: var(--so-shadow-card-hover);
  transform: translateY(-2px);
}

.merchant-row:not(.merchant-row--skeleton):active {
  transform: translateY(0) scale(0.995);
}

.merchant-row--skeleton {
  cursor: default;
}

.skeleton-lines {
  gap: 10px;
  padding-top: 4px;
}

.skeleton-lines .line {
  display: block;
  height: 12px;
  border-radius: var(--so-r-xs);
}

.line--title { width: 52%; height: 16px; }
.line--sm { width: 38%; }
.line--md { width: 70%; }
.line--lg { width: 84%; }

.merchant-cover {
  position: relative;
  width: 96px;
  height: 96px;
  flex-shrink: 0;
  overflow: hidden;
  border-radius: var(--so-r-sm);
  background: var(--so-surface-line);
}

.merchant-cover img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.4s var(--so-ease);
}

.merchant-row:hover .merchant-cover img {
  transform: scale(1.06);
}

.cover-shade {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(0, 0, 0, 0) 58%, rgba(0, 0, 0, 0.18) 100%);
}

.cover-promo {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 1;
  max-width: 78px;
  overflow: hidden;
  padding: 2px 7px;
  border-radius: 3px;
  background: var(--so-red);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cover-category {
  position: absolute;
  bottom: 7px;
  left: 8px;
  z-index: 1;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.25);
  writing-mode: vertical-rl;
}

.closed-mask {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.45);
  color: #fff;
  font-size: 14px;
  font-weight: 700;
}

.merchant-content {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 6px;
}

.merchant-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.merchant-title-row h3 {
  min-width: 0;
  flex: 1;
  margin: 0;
  overflow: hidden;
  color: var(--so-ink-1);
  font-size: 16px;
  font-weight: 800;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.brand-tag {
  flex-shrink: 0;
  padding: 2px 5px;
  border-radius: 3px;
  background: var(--so-ink-1);
  color: var(--so-yellow);
  font-size: 10px;
  font-weight: 800;
  line-height: 1.2;
}

.rating-row,
.promo-row,
.meta-row {
  display: flex;
  align-items: center;
}

.rating-row {
  gap: 8px;
  color: var(--so-ink-4);
  font-size: 12px;
}

.rating-row strong {
  color: var(--so-gold);
  font-size: 11px;
  line-height: 1;
}

.stars {
  color: var(--so-gold);
  font-size: 11px;
  letter-spacing: -1px;
  line-height: 1;
}

.stars span {
  color: var(--so-border-2);
}

.promo-row {
  gap: 6px;
  flex-wrap: wrap;
}

.promo-badge {
  display: inline-flex;
  align-items: center;
  height: 18px;
  padding: 0 5px;
  border-radius: 3px;
  font-size: 11px;
  font-weight: 700;
  line-height: 1;
  white-space: nowrap;
}

.promo-badge--manjian {
  border: 1px solid var(--so-red);
  background: #fff;
  color: var(--so-red);
}

.promo-badge--hongbao {
  background: var(--so-red);
  color: #fff;
}

.promo-badge--discount {
  background: var(--so-yellow);
  color: var(--so-ink-1);
}

.promo-badge--newcomer {
  background: var(--so-orange);
  color: #fff;
}

.promo-badge--free {
  border: 1px solid #b7eb8f;
  background: var(--so-success-soft);
  color: var(--so-success);
}

.meta-row {
  gap: 10px;
  margin-top: auto;
  color: var(--so-ink-3);
  font-size: 12px;
}

.delivery-time {
  color: var(--so-ink-1);
  font-weight: 800;
}
</style>
