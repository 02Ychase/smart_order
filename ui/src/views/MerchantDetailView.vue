<template>
  <section class="merchant-detail-page">
    <div class="detail-backbar">
      <el-button class="back-button" text @click="$emit('close')">‹ 返回首页</el-button>
      <span>· 当前位置：{{ merchantCategory }}</span>
    </div>

    <section class="merchant-masthead">
      <div class="masthead-inner">
        <div class="masthead-cover" :style="merchantCover.imageSrc ? undefined : merchantCover.gradientStyle">
          <img v-if="merchantCover.imageSrc" :src="merchantCover.imageSrc" :alt="`${merchantName} 封面图`" />
        </div>
        <div class="masthead-copy">
          <div class="title-row">
            <h1>{{ merchantName }}</h1>
            <span class="brand-tag">品牌</span>
            <el-tag :type="isOpen ? 'success' : 'danger'" size="small">{{ businessStatus }}</el-tag>
            <el-button class="favorite-button" text @click="handleToggleFavorite">
              {{ favorited ? '♥ 已收藏' : '♡ 收藏' }}
            </el-button>
          </div>
          <div class="merchant-meta">
            <span class="stars" aria-hidden="true">{{ filledStars(merchantRating) }}<span>{{ emptyStars(merchantRating) }}</span></span>
            <strong>{{ merchantRating.toFixed(1) }}</strong>
            <span>月售 {{ salesText }}</span>
            <span>·</span>
            <span><b>{{ deliveryMinutes }}分钟</b>送达</span>
            <span>·</span>
            <span>{{ distanceText }}km</span>
            <span>·</span>
            <span>起送 {{ mtYuan(minOrderAmount) }}</span>
            <span>·</span>
            <span>配送费 {{ mtYuan(deliveryFee) }}</span>
          </div>
          <div class="promo-row">
            <span class="promo-badge promo-badge--manjian">满50减8</span>
            <span class="promo-badge promo-badge--manjian">满100减20</span>
            <span class="promo-badge promo-badge--hongbao">¥5红包</span>
            <span class="promo-badge promo-badge--newcomer">新客立减¥5</span>
            <span class="promo-badge promo-badge--discount">折</span>
          </div>
          <div class="merchant-tabs">
            <span class="active">点餐</span>
            <span>评价 (1238)</span>
            <span>商家</span>
          </div>
        </div>
      </div>
    </section>

    <div v-if="loading" class="detail-skeleton" aria-busy="true" aria-label="菜品加载中">
      <div v-for="n in 5" :key="`dsk-${n}`" class="dish-row dish-row--skeleton">
        <div class="so-skeleton dish-thumb"></div>
        <div class="dish-content skeleton-lines">
          <span class="so-skeleton line line--title"></span>
          <span class="so-skeleton line line--md"></span>
          <span class="so-skeleton line line--sm"></span>
        </div>
      </div>
    </div>
    <div v-else-if="errorMessage" class="detail-state detail-state--error">{{ errorMessage }}</div>
    <div v-else class="detail-main">
      <aside class="category-sidebar mt-scroll">
        <button
          v-for="category in dishCategories"
          :key="category"
          :class="{ active: category === activeCategory }"
          type="button"
          @click="activeCategory = category"
        >
          {{ category }}
        </button>
      </aside>

      <main class="dish-list mt-scroll">
        <h3><span>🔥</span>{{ activeCategory }}</h3>
        <el-empty v-if="!visibleDishes.length" description="暂无菜品" />
        <article v-for="dish in visibleDishes" :key="dish.id" class="dish-row">
          <div class="dish-thumb" :style="{ background: dishBackground(dish) }">
            <span>{{ dishGlyph(dish) }}</span>
            <em v-if="isHotDish(dish)">HOT</em>
          </div>
          <div class="dish-content">
            <h4>{{ dish.name }}</h4>
            <p>{{ dish.description || dish.desc || '招牌现做，热乎送达。' }}</p>
            <div class="dish-stats">
              <span>月售 {{ dish.sales || 128 }}</span>
              <span>👍 {{ dish.positive_rate || 96 }}%</span>
            </div>
            <div class="dish-footer">
              <span class="so-price"><small>¥</small>{{ priceText(dish.price) }}</span>
              <el-button
                :data-test="`add-cart-${dish.id}`"
                class="add-button"
                type="primary"
                circle
                :loading="addingDishId === dish.id"
                @click="addDishToCart(dish.id)"
              >
                +
              </el-button>
            </div>
          </div>
        </article>
      </main>

      <aside class="cart-pane">
        <header>
          <h3>已选 ({{ merchantCartCount }})</h3>
          <el-button v-if="merchantCartItems.length" text @click="clearMerchantCart">清空</el-button>
        </header>
        <div class="cart-list mt-scroll">
          <div v-if="!merchantCartItems.length" class="cart-empty">
            <span>🛒</span>
            <p>购物车空空如也</p>
            <small>试试点击 + 加入菜品</small>
          </div>
          <div v-for="item in merchantCartItems" :key="item.dish_id" class="cart-row">
            <div class="cart-thumb" :style="{ background: cartItemBackground(item) }">{{ cartItemGlyph(item) }}</div>
            <div class="cart-info">
              <p>{{ item.dish_name }}</p>
              <span>{{ mtYuan(item.unit_price) }}</span>
            </div>
            <div class="cart-quantity">
              <el-button circle size="small" @click="removeCartItem(item.dish_id)">-</el-button>
              <b>{{ item.quantity }}</b>
              <el-button circle size="small" type="primary" @click="addDishToCart(item.dish_id)">+</el-button>
            </div>
          </div>
        </div>
        <footer>
          <p>商品 {{ mtYuan(merchantCartGoods) }} · 配送 {{ mtYuan(deliveryFee) }}</p>
          <div>
            <span>合计</span>
            <strong><small>¥</small>{{ totalPayable }}</strong>
          </div>
          <el-button class="checkout-button" type="primary" :disabled="checkoutDisabled" @click="goCheckout">
            {{ checkoutText }}
          </el-button>
        </footer>
      </aside>
    </div>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getMerchant, listMerchantDishes } from '../api/catalog'
import { checkFavorite, toggleFavorite } from '../api/favorites'
import { useAuth } from '../composables/useAuth'
import { useCart } from '../composables/useCart'
import { formatBusinessStatus } from '../utils/businessHours'
import { getMerchantCover } from '../utils/homepage'

const emit = defineEmits(['request-login', 'close', 'open-cart'])
const props = defineProps({
  merchantId: { type: Number, default: null },
})

const { currentUser } = useAuth()
const { merchantGroups, refreshCart, addCartItem, removeCartItem } = useCart()
const dishes = ref([])
const loading = ref(false)
const errorMessage = ref('')
const addingDishId = ref(null)
const favorited = ref(false)
const merchantInfo = ref(null)
const activeCategory = ref('热销榜')

const dishGlyphs = ['🐟', '🥩', '🌶️', '🍳', '🥔', '🍜', '🥗', '🍰']
const dishBackgrounds = [
  'linear-gradient(135deg, #ffe1d6, #ffb59c)',
  'linear-gradient(135deg, #ffd6c2, #ff9a7a)',
  'linear-gradient(135deg, #ffe0e0, #ff9999)',
  'linear-gradient(135deg, #fff4dc, #f3d8aa)',
  'linear-gradient(135deg, #fff0d8, #ffd18c)',
  'linear-gradient(135deg, #e8f5e9, #a5d6a7)',
]

const fallbackMerchant = computed(() => ({
  id: props.merchantId,
  name: '商家详情',
  homepage_category: '湘菜',
  rating: 4.7,
  delivery_fee: 0,
  min_order_amount: 20,
}))
const displayMerchant = computed(() => merchantInfo.value || fallbackMerchant.value)
const merchantName = computed(() => displayMerchant.value.name)
const merchantCategory = computed(() => displayMerchant.value.homepage_category || displayMerchant.value.category || '湘菜')
const merchantCover = computed(() => getMerchantCover(merchantCategory.value))
const merchantRating = computed(() => Number(displayMerchant.value?.rating || 4.7))
const businessStatus = computed(() => formatBusinessStatus(displayMerchant.value?.business_hours, true))
const isOpen = computed(() => businessStatus.value === '营业中')
const deliveryFee = computed(() => Number(displayMerchant.value?.delivery_fee || 0))
const minOrderAmount = computed(() => Number(displayMerchant.value?.min_order_amount || displayMerchant.value?.min_order || 20))
const salesText = computed(() => displayMerchant.value?.sales || displayMerchant.value?.monthly_sales || '300+')
const deliveryMinutes = computed(() => displayMerchant.value?.delivery_minutes || displayMerchant.value?.delivery_time_minutes || displayMerchant.value?.avg_delivery_minutes || 28)
const distanceText = computed(() => Number(displayMerchant.value?.distance_km || displayMerchant.value?.distance || 1.2).toFixed(1))

const dishCategories = computed(() => {
  const categories = dishes.value
    .map((dish) => dish.category || dish.category_name)
    .filter(Boolean)
  return ['热销榜', ...Array.from(new Set(categories))]
})

const visibleDishes = computed(() => {
  if (activeCategory.value === '热销榜') return dishes.value
  const filtered = dishes.value.filter((dish) => (dish.category || dish.category_name) === activeCategory.value)
  return filtered.length ? filtered : dishes.value
})

const currentMerchantGroup = computed(() => merchantGroups.value.find((group) => group.merchant_id === props.merchantId))
const merchantCartItems = computed(() => currentMerchantGroup.value?.items || [])
const merchantCartCount = computed(() => merchantCartItems.value.reduce((sum, item) => sum + item.quantity, 0))
const merchantCartGoods = computed(() => merchantCartItems.value.reduce(
  (sum, item) => sum + Number(item.unit_price || 0) * item.quantity,
  0,
))
const stillNeed = computed(() => Math.max(0, minOrderAmount.value - merchantCartGoods.value))
const checkoutDisabled = computed(() => !merchantCartItems.value.length || stillNeed.value > 0)
const checkoutText = computed(() => {
  if (!merchantCartItems.value.length) return '去结算'
  if (stillNeed.value > 0) return `还差 ${mtYuan(stillNeed.value)} 起送`
  return '去结算'
})
const totalPayable = computed(() => (merchantCartGoods.value + (merchantCartItems.value.length ? deliveryFee.value : 0)).toFixed(2))

const clampStars = (value) => Math.min(5, Math.max(0, Math.round(Number(value || 0))))
const filledStars = (value) => '★★★★★'.slice(0, clampStars(value))
const emptyStars = (value) => '★★★★★'.slice(clampStars(value))
const priceText = (value) => Number(value || 0).toFixed(2)
const mtYuan = (value) => `¥${Number(value || 0).toFixed(Number(value || 0) % 1 === 0 ? 0 : 2)}`
const isHotDish = (dish) => dish.hot || dish.is_hot || Number(dish.sales || 0) >= 300
const dishIndex = (dish) => Math.abs(Number(dish.id || 0))
const dishGlyph = (dish) => dish.glyph || dish.emoji || dishGlyphs[dishIndex(dish) % dishGlyphs.length]
const dishBackground = (dish) => dish.bg || dish.background || dishBackgrounds[dishIndex(dish) % dishBackgrounds.length]
const cartDish = (item) => dishes.value.find((dish) => dish.id === item.dish_id) || {}
const cartItemGlyph = (item) => dishGlyph(cartDish(item))
const cartItemBackground = (item) => dishBackground(cartDish(item))

const loadFavoriteStatus = async (merchantId) => {
  if (!merchantId || !currentUser.value) return
  try {
    const result = await checkFavorite(merchantId)
    favorited.value = result.favorited
  } catch {
    favorited.value = false
  }
}

const syncMerchantState = async (merchantId) => {
  await loadFavoriteStatus(merchantId)
  if (currentUser.value) {
    await refreshCart().catch(() => null)
  }
}

const handleToggleFavorite = async () => {
  if (!currentUser.value) {
    emit('request-login')
    return
  }
  if (!props.merchantId) return
  try {
    const result = await toggleFavorite(props.merchantId)
    favorited.value = result.favorited
    ElMessage.success(result.favorited ? '已收藏' : '已取消收藏')
  } catch (error) {
    ElMessage.error(error?.message || '操作失败')
  }
}

const addDishToCart = async (dishId) => {
  if (!currentUser.value) {
    emit('request-login')
    return
  }

  addingDishId.value = dishId
  try {
    await addCartItem(dishId)
    ElMessage.success('已加入购物车')
  } catch (error) {
    ElMessage.error(error?.message || '加入购物车失败，请稍后再试')
  } finally {
    addingDishId.value = null
  }
}

const clearMerchantCart = async () => {
  await Promise.all(merchantCartItems.value.map((item) => removeCartItem(item.dish_id)))
}

const goCheckout = () => {
  if (!currentUser.value) {
    emit('request-login')
    return
  }
  if (!checkoutDisabled.value) {
    emit('open-cart')
  }
}

const loadDishes = async (merchantId) => {
  if (!merchantId) {
    dishes.value = []
    loading.value = false
    return
  }

  loading.value = true
  errorMessage.value = ''
  activeCategory.value = '热销榜'
  merchantInfo.value = null

  // Fetch the merchant profile so the real name/rating/etc. show regardless of
  // how the user arrived (home list, search, or favorites). Runs in parallel
  // with the dish load; guarded so a missing endpoint never breaks the page.
  Promise.resolve(getMerchant?.(merchantId))
    .then((merchant) => {
      // Ignore a stale response if the user already switched merchants.
      if (merchant && String(merchant.id) === String(merchantId)) merchantInfo.value = merchant
    })
    .catch(() => {})

  try {
    const merchantDishes = await listMerchantDishes(merchantId)
    dishes.value = merchantDishes || []
    if (!merchantInfo.value) merchantInfo.value = merchantDishes?.[0]?.merchant || null
    syncMerchantState(merchantId)
  } catch (error) {
    errorMessage.value = error?.message || '加载失败，请稍后再试'
  } finally {
    loading.value = false
  }
}

watch(() => props.merchantId, loadDishes, { immediate: true })
</script>

<style scoped>
.merchant-detail-page {
  min-height: 100%;
  background: var(--so-page);
  color: var(--so-ink-1);
}

.detail-backbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 32px;
  border-bottom: 1px solid var(--so-border-1);
  background: var(--so-surface);
  color: var(--so-ink-5);
  font-size: 12px;
}

.back-button {
  padding: 6px 12px;
  color: var(--so-ink-2);
  font-size: 13px;
  font-weight: 700;
}

.merchant-masthead {
  padding: 24px 32px 16px;
  border-bottom: 1px solid var(--so-border-1);
  background: var(--so-surface);
}

.masthead-inner {
  display: flex;
  max-width: 1200px;
  margin: 0 auto;
  align-items: flex-start;
  gap: 18px;
}

.masthead-cover {
  width: 100px;
  height: 100px;
  flex-shrink: 0;
  overflow: hidden;
  border-radius: var(--so-r-md);
  background: var(--so-surface-line);
}

.masthead-cover {
  box-shadow: var(--so-shadow-card);
}

.masthead-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.5s var(--so-ease);
}

.masthead-cover:hover img {
  transform: scale(1.08);
}

.masthead-copy {
  min-width: 0;
  flex: 1;
}

.title-row,
.merchant-meta,
.promo-row,
.merchant-tabs,
.dish-stats,
.dish-footer {
  display: flex;
  align-items: center;
}

.title-row {
  gap: 10px;
}

.title-row h1 {
  min-width: 0;
  margin: 0;
  overflow: hidden;
  color: var(--so-ink-1);
  font-size: 24px;
  font-weight: 800;
  line-height: 1.2;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.brand-tag {
  padding: 2px 6px;
  border-radius: 3px;
  background: var(--so-ink-1);
  color: var(--so-yellow);
  font-size: 10px;
  font-weight: 800;
}

.favorite-button {
  margin-left: auto;
  color: var(--so-red);
  font-size: 13px;
  font-weight: 700;
}

.merchant-meta {
  gap: 12px;
  margin-top: 10px;
  color: var(--so-ink-3);
  font-size: 13px;
  flex-wrap: wrap;
}

.merchant-meta strong,
.stars {
  color: var(--so-gold);
}

.stars {
  font-size: 13px;
  letter-spacing: -1px;
  line-height: 1;
}

.stars span {
  color: var(--so-border-2);
}

.promo-row {
  gap: 8px;
  margin-top: 14px;
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

.merchant-tabs {
  gap: 22px;
  margin-top: 16px;
  color: var(--so-ink-3);
  font-size: 14px;
}

.merchant-tabs span {
  padding-bottom: 8px;
}

.merchant-tabs .active {
  border-bottom: 2px solid var(--so-yellow);
  color: var(--so-ink-1);
  font-weight: 800;
}

.detail-state {
  max-width: 1200px;
  margin: 20px auto;
  padding: 40px 0;
  border-radius: var(--so-r-lg);
  background: var(--so-surface);
  color: var(--so-ink-4);
  text-align: center;
}

.detail-state--error {
  color: var(--so-red);
}

.detail-main {
  display: flex;
  max-width: 1200px;
  height: calc(100vh - 236px);
  min-height: 560px;
  margin: 0 auto;
  overflow: hidden;
}

.category-sidebar {
  width: 120px;
  flex-shrink: 0;
  overflow-y: auto;
  background: var(--so-page);
}

.category-sidebar button {
  width: 100%;
  padding: 14px 12px;
  border: 0;
  border-left: 3px solid transparent;
  background: transparent;
  color: var(--so-ink-3);
  cursor: pointer;
  font-size: 13px;
  text-align: left;
}

.category-sidebar button.active {
  border-left-color: var(--so-yellow);
  background: var(--so-surface);
  color: var(--so-ink-1);
  font-weight: 800;
}

.dish-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 24px 24px;
  background: var(--so-surface);
}

.dish-list h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 16px 0 4px;
  color: var(--so-ink-3);
  font-size: 14px;
  font-weight: 800;
}

.dish-list h3 span {
  font-size: 18px;
}

.dish-row {
  display: flex;
  gap: 14px;
  padding: 16px;
  margin: 0 -16px;
  border-radius: var(--so-r-md);
  border-bottom: 1px solid var(--so-border-1);
  transition: background var(--so-dur) var(--so-ease);
}

.dish-row:not(.dish-row--skeleton):hover {
  background: var(--so-yellow-faint);
}

.detail-skeleton {
  flex: 1;
  padding: 8px 24px 24px;
  background: var(--so-surface);
}

.detail-skeleton .dish-row {
  margin: 0;
  padding: 16px 0;
}

.skeleton-lines {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-top: 6px;
}

.skeleton-lines .line {
  display: block;
  height: 13px;
  border-radius: var(--so-r-xs);
}

.line--title { width: 46%; height: 17px; }
.line--md { width: 78%; }
.line--sm { width: 34%; }

.dish-thumb {
  position: relative;
  display: flex;
  width: 88px;
  height: 88px;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border-radius: var(--so-r-md);
  font-size: 40px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.5), inset 0 -3px 8px rgba(40, 28, 8, 0.06);
  transition: transform var(--so-dur) var(--so-ease-spring);
}

.dish-row:not(.dish-row--skeleton):hover .dish-thumb {
  transform: scale(1.05);
}

.dish-thumb em {
  position: absolute;
  top: 4px;
  left: 4px;
  padding: 1px 4px;
  border-radius: 2px;
  background: var(--so-red);
  color: #fff;
  font-size: 9px;
  font-style: normal;
  font-weight: 800;
}

.dish-content {
  min-width: 0;
  flex: 1;
}

.dish-content h4,
.dish-content p {
  margin: 0;
}

.dish-content h4 {
  color: var(--so-ink-1);
  font-size: 15px;
  font-weight: 800;
}

.dish-content p {
  display: -webkit-box;
  overflow: hidden;
  margin-top: 4px;
  color: var(--so-ink-4);
  font-size: 12px;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.dish-stats {
  gap: 12px;
  margin-top: 8px;
  color: var(--so-ink-4);
  font-size: 12px;
}

.dish-stats span:last-child {
  color: var(--so-gold);
}

.dish-footer {
  justify-content: space-between;
  margin-top: 10px;
}

.so-price,
.cart-pane footer strong {
  color: var(--so-red);
  font-weight: 800;
  line-height: 1;
}

.so-price {
  font-size: 20px;
}

.so-price small,
.cart-pane footer strong small {
  font-size: 0.6em;
}

.add-button {
  width: 28px;
  height: 28px;
  font-size: 20px;
  font-weight: 800;
  transition: transform var(--so-dur) var(--so-ease-spring), box-shadow var(--so-dur) var(--so-ease);
}

.add-button:hover {
  transform: scale(1.12) rotate(90deg);
  box-shadow: var(--so-shadow-brand);
}

.add-button:active {
  transform: scale(0.92);
}

.cart-pane {
  display: flex;
  width: 300px;
  flex-shrink: 0;
  flex-direction: column;
  border-left: 1px solid var(--so-border-1);
  background: var(--so-surface);
}

.cart-pane header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 20px 12px;
  border-bottom: 1px solid var(--so-border-1);
}

.cart-pane header h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 800;
}

.cart-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 20px;
}

.cart-empty {
  padding: 50px 0;
  color: var(--so-ink-5);
  font-size: 13px;
  text-align: center;
}

.cart-empty span {
  font-size: 40px;
  opacity: 0.4;
}

.cart-empty p {
  margin: 8px 0 0;
}

.cart-empty small {
  display: block;
  margin-top: 4px;
  font-size: 11px;
}

.cart-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 0;
  border-bottom: 1px solid var(--so-surface-line);
}

.cart-thumb {
  display: flex;
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border-radius: var(--so-r-sm);
  font-size: 22px;
}

.cart-info {
  min-width: 0;
  flex: 1;
}

.cart-info p {
  overflow: hidden;
  margin: 0;
  color: var(--so-ink-1);
  font-size: 13px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cart-info span {
  color: var(--so-red);
  font-size: 13px;
  font-weight: 800;
}

.cart-quantity {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.cart-quantity b {
  min-width: 14px;
  font-size: 13px;
  text-align: center;
}

.cart-pane footer {
  padding: 14px 20px;
  border-top: 1px solid var(--so-border-1);
  background: var(--so-yellow-faint);
}

.cart-pane footer p {
  margin: 0 0 8px;
  color: var(--so-ink-3);
  font-size: 12px;
}

.cart-pane footer div {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 12px;
}

.cart-pane footer div span {
  color: var(--so-ink-2);
  font-size: 13px;
  font-weight: 700;
}

.cart-pane footer strong {
  font-size: 22px;
}

.checkout-button {
  width: 100%;
  border-radius: var(--so-r-pill);
  font-weight: 800;
  transition: transform var(--so-dur) var(--so-ease), box-shadow var(--so-dur) var(--so-ease);
}

.checkout-button:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: var(--so-shadow-brand);
}

.checkout-button:not(:disabled):active {
  transform: translateY(0) scale(0.99);
}

.category-sidebar button {
  transition: background var(--so-dur) var(--so-ease), color var(--so-dur) var(--so-ease);
}

.category-sidebar button:hover {
  background: var(--so-surface);
  color: var(--so-ink-1);
}
</style>
