<template>
  <div class="homepage-shell">
    <HomeHeader
      :current-user="currentUser"
      :default-address="defaultAddress"
      @open-login="loginOpen = true"
      @open-cart="requireLogin(() => cartOpen = true)"
      @open-address="requireLogin(() => addressOpen = true)"
      @open-orders="requireLogin(() => ordersOpen = true)"
      @open-profile="profileOpen = true"
      @open-favorites="requireLogin(() => favoritesOpen = true)"
      @search="handleSearch"
    />
    <div class="homepage-container mt-scroll">
      <section class="promo-banner" :class="activeBanner.className">
        <div class="banner-copy">
          <span class="banner-tag">{{ activeBanner.tag }}</span>
          <h1>{{ activeBanner.big }}</h1>
          <p>{{ activeBanner.small }}</p>
          <el-button class="banner-cta" @click="handleBannerAction(activeBanner)">
            {{ activeBanner.cta }} ›
          </el-button>
        </div>
        <div class="banner-emoji" aria-hidden="true">{{ activeBanner.emoji }}</div>
        <div class="banner-dots" aria-label="切换活动">
          <button
            v-for="(_, index) in promoBanners"
            :key="index"
            :class="{ active: index === activeBannerIndex }"
            type="button"
            @click.stop="activeBannerIndex = index"
          ></button>
        </div>
      </section>

      <section class="home-category-grid" aria-label="快捷分类">
        <button
          v-for="item in homeCategoryIcons"
          :key="item.key"
          class="home-category-cell"
          type="button"
          @click="selectCategory(item.category)"
        >
          <span class="category-bubble" :style="{ background: item.bg, color: item.fg }">{{ item.glyph }}</span>
          <span>{{ item.key }}</span>
        </button>
      </section>

      <section class="flash-strip">
        <span class="flash-label">⚡ 限时秒杀</span>
        <span class="flash-countdown">距结束 <strong>02 : 14 : 36</strong></span>
        <div class="flash-spacer"></div>
        <button v-for="dish in flashDishes" :key="dish.id" class="flash-dish" type="button" @click="requireLogin(() => cartOpen = true)">
          <span class="flash-thumb" :style="{ background: dish.bg }">{{ dish.glyph }}</span>
          <span class="flash-info">
            <span class="flash-name">{{ dish.name }}</span>
            <span class="flash-price">¥{{ (dish.price * 0.5).toFixed(1) }}</span>
          </span>
        </button>
      </section>

      <CategoryFilterBar
        :categories="categories"
        :selected-category="selectedCategory"
        @select-category="selectCategory"
      />
      <MerchantListView
        :merchants="filteredMerchants"
        :loading="loading"
        :error-message="errorMessage"
        @select-merchant="openMerchantDrawer"
      />
    </div>

    <FloatingAssistant :initial-open="true" @request-login="loginOpen = true" />

    <el-dialog v-model="loginOpen" width="420px" destroy-on-close>
      <LoginView @auth-success="loginOpen = false" />
    </el-dialog>
    <el-dialog v-model="cartOpen" width="520px" destroy-on-close>
      <CheckoutView @order-created="onOrderCreated" />
    </el-dialog>
    <el-dialog v-model="addressOpen" width="560px" destroy-on-close>
      <AddressView />
    </el-dialog>
    <el-dialog v-model="ordersOpen" width="600px" destroy-on-close>
      <OrderListView @view-order="openOrderDetail" />
    </el-dialog>
    <el-dialog v-model="orderDetailOpen" width="600px" destroy-on-close>
      <OrderDetailView :order-id="selectedOrderId" @reorder-done="onReorderDone" />
    </el-dialog>
    <el-dialog v-model="profileOpen" width="480px" destroy-on-close>
      <ProfileView @logout="handleLogout" />
    </el-dialog>
    <el-dialog v-model="favoritesOpen" width="520px" destroy-on-close>
      <FavoriteView @select-merchant="openMerchantFromFavorites" />
    </el-dialog>
    <el-dialog v-model="searchOpen" width="600px" destroy-on-close>
      <SearchResultView :keyword="searchKeyword" @select-merchant="openMerchantFromSearch" />
    </el-dialog>
    <el-drawer v-model="merchantDrawerOpen" size="100%" destroy-on-close :with-header="false">
      <MerchantDetailView
        :merchant-id="selectedMerchantId"
        @request-login="loginOpen = true"
        @close="merchantDrawerOpen = false"
        @open-cart="cartOpen = true"
      />
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { listAddresses } from './api/address'
import CategoryFilterBar from './components/home/CategoryFilterBar.vue'
import FloatingAssistant from './components/home/FloatingAssistant.vue'
import HomeHeader from './components/home/HomeHeader.vue'
import { useAuth } from './composables/useAuth'
import { useCart } from './composables/useCart'
import { useHomepage } from './composables/useHomepage'
import AddressView from './views/AddressView.vue'
import CheckoutView from './views/CheckoutView.vue'
import FavoriteView from './views/FavoriteView.vue'
import LoginView from './views/LoginView.vue'
import MerchantDetailView from './views/MerchantDetailView.vue'
import MerchantListView from './views/MerchantListView.vue'
import OrderDetailView from './views/OrderDetailView.vue'
import OrderListView from './views/OrderListView.vue'
import ProfileView from './views/ProfileView.vue'
import SearchResultView from './views/SearchResultView.vue'

const loginOpen = ref(false)
const cartOpen = ref(false)
const addressOpen = ref(false)
const merchantDrawerOpen = ref(false)
const ordersOpen = ref(false)
const orderDetailOpen = ref(false)
const selectedOrderId = ref(null)
const searchOpen = ref(false)
const searchKeyword = ref('')
const profileOpen = ref(false)
const favoritesOpen = ref(false)
const { currentUser, logout } = useAuth()
const { refreshCart } = useCart()
const activeBannerIndex = ref(0)
const defaultAddress = ref(null)
let bannerTimer

const loadDefaultAddress = async () => {
  if (!currentUser.value) {
    defaultAddress.value = null
    return
  }
  try {
    const addresses = await listAddresses()
    defaultAddress.value = addresses.find((a) => a.is_default) || addresses[0] || null
  } catch {
    defaultAddress.value = null
  }
}

watch(currentUser, loadDefaultAddress, { immediate: true })

const promoBanners = [
  {
    tag: '限时',
    big: '新客立减',
    small: '首单立减 ¥15',
    cta: '立即领取',
    emoji: '🎁',
    className: 'promo-banner--yellow',
    action: 'login',
  },
  {
    tag: '满减',
    big: '今日满减狂欢',
    small: '满 50 减 8 / 满 100 减 20',
    cta: '查看',
    emoji: '🍱',
    className: 'promo-banner--warm',
    action: 'orders',
  },
  {
    tag: '红包',
    big: '¥30 新人红包',
    small: '已为你预留，登录即得',
    cta: '去登录',
    emoji: '🧧',
    className: 'promo-banner--red',
    action: 'login',
  },
]

const homeCategoryIcons = [
  { key: '美食', glyph: '🍱', bg: '#fff0eb', fg: '#ff5722', category: '湘菜' },
  { key: '甜品', glyph: '🍰', bg: '#fff5e8', fg: '#ff8f1f', category: '咖啡甜品' },
  { key: '汉堡', glyph: '🍔', bg: '#fff8d6', fg: '#d09800', category: '炸鸡汉堡' },
  { key: '日韩', glyph: '🍣', bg: '#ffeaf2', fg: '#e91e63', category: '日韩料理' },
  { key: '湘川', glyph: '🌶️', bg: '#ffe3df', fg: '#d32f2f', category: '湘菜' },
  { key: '面食', glyph: '🍜', bg: '#fff3e0', fg: '#e65100', category: '粥面' },
  { key: '轻食', glyph: '🥗', bg: '#e8f5e9', fg: '#43a047', category: '轻食' },
  { key: '夜宵', glyph: '🌙', bg: '#ede7f6', fg: '#673ab7', category: '麻辣烫' },
]

const flashDishes = [
  { id: 101, name: '剁椒鱼头', price: 58, glyph: '🐟', bg: 'linear-gradient(135deg, #ffe1d6, #ffb59c)' },
  { id: 102, name: '小炒黄牛肉', price: 38, glyph: '🥩', bg: 'linear-gradient(135deg, #ffd6c2, #ff9a7a)' },
  { id: 103, name: '辣椒炒肉', price: 28, glyph: '🌶️', bg: 'linear-gradient(135deg, #ffe0e0, #ff9999)' },
  { id: 104, name: '剁椒蒸蛋', price: 18, glyph: '🍳', bg: 'linear-gradient(135deg, #fff4dc, #f3d8aa)' },
]

const activeBanner = computed(() => promoBanners[activeBannerIndex.value])

const {
  loading,
  errorMessage,
  categories,
  selectedCategory,
  filteredMerchants,
  selectedMerchantId,
  loadMerchants,
  selectCategory,
  selectMerchant,
} = useHomepage()

const openMerchantDrawer = (merchantId) => {
  selectMerchant(merchantId)
  merchantDrawerOpen.value = true
}

const openOrderDetail = (orderId) => {
  selectedOrderId.value = orderId
  orderDetailOpen.value = true
}

const onOrderCreated = (orderId) => {
  cartOpen.value = false
  openOrderDetail(orderId)
}

const handleSearch = (keyword) => {
  searchKeyword.value = keyword
  searchOpen.value = true
}

const handleBannerAction = (banner) => {
  if (banner.action === 'login') {
    loginOpen.value = true
  } else {
    ordersOpen.value = true
  }
}

const openMerchantFromSearch = (merchantId) => {
  searchOpen.value = false
  openMerchantDrawer(merchantId)
}

const onReorderDone = () => {
  orderDetailOpen.value = false
  cartOpen.value = true
  refreshCart()
}

const openMerchantFromFavorites = (merchantId) => {
  favoritesOpen.value = false
  openMerchantDrawer(merchantId)
}

const handleLogout = () => {
  logout()
  profileOpen.value = false
}

const requireLogin = (action) => {
  if (!currentUser.value) {
    loginOpen.value = true
    return
  }
  action()
}

onMounted(() => {
  loadMerchants()
  bannerTimer = window.setInterval(() => {
    activeBannerIndex.value = (activeBannerIndex.value + 1) % promoBanners.length
  }, 5000)
})

onUnmounted(() => {
  window.clearInterval(bannerTimer)
})
</script>

<style scoped>
.homepage-shell {
  min-height: 100vh;
  background: var(--so-page);
}

.homepage-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px 0 80px;
}

.promo-banner {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  height: 168px;
  overflow: hidden;
  padding: 28px 32px;
  border-radius: var(--so-r-lg);
  color: #fff;
  box-shadow: var(--so-shadow-card);
  transition: background 0.3s ease;
}

.promo-banner--yellow {
  background: linear-gradient(135deg, #ffd100 0%, #ffb700 100%);
}

.promo-banner--warm {
  background: linear-gradient(135deg, #fff6c2 0%, #ffd100 100%);
  color: var(--so-ink-1);
}

.promo-banner--red {
  background: linear-gradient(135deg, #ff5b3c 0%, #ff8f1f 100%);
}

.banner-copy {
  position: relative;
  z-index: 1;
  min-width: 0;
  flex: 1;
}

.banner-tag {
  display: inline-block;
  padding: 3px 8px;
  border-radius: var(--so-r-xs);
  background: rgba(0, 0, 0, 0.85);
  color: var(--so-yellow);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 1px;
  line-height: 1.3;
}

.banner-copy h1 {
  margin: 14px 0 6px;
  color: inherit;
  font-size: 34px;
  font-weight: 800;
  line-height: 1.1;
}

.banner-copy p {
  margin: 0;
  color: inherit;
  font-size: 15px;
  opacity: 0.85;
}

.banner-cta {
  height: 32px;
  margin-top: 14px;
  padding: 0 18px;
  border: 0;
  border-radius: var(--so-r-pill);
  background: #fff;
  color: var(--so-ink-1);
  font-size: 13px;
  font-weight: 800;
}

.promo-banner--warm .banner-cta {
  background: var(--so-ink-1);
  color: var(--so-yellow);
}

.banner-emoji {
  position: relative;
  z-index: 1;
  font-size: 96px;
  line-height: 1;
  filter: drop-shadow(0 6px 16px rgba(0, 0, 0, 0.15));
}

.banner-dots {
  position: absolute;
  right: 32px;
  bottom: 14px;
  z-index: 1;
  display: flex;
  gap: 6px;
}

.banner-dots button {
  width: 6px;
  height: 6px;
  padding: 0;
  border: 0;
  border-radius: 3px;
  background: rgba(0, 0, 0, 0.25);
  cursor: pointer;
  transition: width 0.2s ease;
}

.banner-dots button.active {
  width: 18px;
  background: currentColor;
}

.home-category-grid {
  display: grid;
  grid-template-columns: repeat(8, minmax(0, 1fr));
  gap: 8px;
  padding: 20px 24px;
  border-radius: var(--so-r-lg);
  background: var(--so-surface);
  box-shadow: var(--so-shadow-card);
}

.home-category-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--so-ink-2);
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
}

.category-bubble {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  font-size: 28px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.flash-strip {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 14px 18px;
  border-radius: var(--so-r-lg);
  background: var(--so-surface);
  box-shadow: var(--so-shadow-card);
}

.flash-label {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: var(--so-r-xs);
  background: linear-gradient(90deg, var(--so-red), var(--so-orange));
  color: #fff;
  font-size: 11px;
  font-weight: 800;
  line-height: 1.3;
  white-space: nowrap;
}

.flash-countdown {
  flex-shrink: 0;
  color: var(--so-ink-2);
  font-size: 13px;
}

.flash-countdown strong {
  color: var(--so-red);
  font-variant-numeric: tabular-nums;
}

.flash-spacer {
  flex: 1;
}

.flash-dish {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  max-width: 128px;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: pointer;
}

.flash-thumb {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: var(--so-r-sm);
  font-size: 22px;
}

.flash-info {
  display: flex;
  min-width: 0;
  flex-direction: column;
  align-items: flex-start;
}

.flash-name {
  max-width: 80px;
  overflow: hidden;
  color: var(--so-ink-3);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.flash-price {
  color: var(--so-red);
  font-size: 14px;
  font-weight: 800;
  line-height: 1;
}

@media (max-width: 960px) {
  .homepage-container {
    padding-right: 16px;
    padding-left: 16px;
  }

  .home-category-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .flash-strip {
    flex-wrap: wrap;
  }
}
</style>
