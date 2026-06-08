<template>
  <header class="home-header">
    <el-button class="brand" text aria-label="smart_order 首页">
      <span class="brand-mark">S</span>
      <span class="brand-name">smart_order</span>
    </el-button>

    <span class="divider" aria-hidden="true"></span>

    <el-button class="location" text @click="$emit('open-address')">
      <svg class="location-icon" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 2.5c-3.3 0-6 2.6-6 5.9 0 4.4 6 12.9 6 12.9s6-8.5 6-12.9c0-3.3-2.7-5.9-6-5.9Zm0 8.1a2.2 2.2 0 1 1 0-4.4 2.2 2.2 0 0 1 0 4.4Z" />
      </svg>
      <template v-if="defaultAddress">
        <span class="city">{{ defaultAddress.city || '上海' }}</span>
        <span class="district">· {{ defaultAddress.district }}{{ defaultAddress.address }}</span>
      </template>
      <template v-else>
        <span class="city">选择地址</span>
      </template>
      <svg class="chevron" viewBox="0 0 24 24" aria-hidden="true">
        <path d="m7 9 5 5 5-5" />
      </svg>
    </el-button>

    <form class="search-form" @submit.prevent="doSearch">
      <div class="search-box">
        <svg class="search-icon" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="11" cy="11" r="7" />
          <path d="m16 16 5 5" />
        </svg>
        <input
          v-model="keyword"
          class="search-input"
          type="text"
          placeholder="搜索：黄焖鸡 / 奶茶 / 麻辣烫…"
          aria-label="搜索商家或菜品"
        />
        <button class="search-submit" type="submit">搜索</button>
      </div>
    </form>

    <nav class="header-nav" aria-label="顶部导航">
      <el-button text @click="$emit('open-orders')">我的订单</el-button>
      <el-button text @click="$emit('open-favorites')">收藏</el-button>
      <el-button class="cart-pill" @click="$emit('open-cart')">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M7 18c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2ZM1 2v2h2l3.6 7.59-1.35 2.45C5.09 14.32 5 14.65 5 15c0 1.1.9 2 2 2h12v-2H7.42c-.14 0-.25-.11-.25-.25l.03-.12.9-1.63h7.45c.75 0 1.41-.41 1.75-1.03l3.58-6.49c.08-.14.12-.31.12-.48 0-.55-.45-1-1-1H5.21l-.94-2H1Z" />
        </svg>
        <span>购物车{{ cartItemCount > 0 ? ` · ${cartItemCount}` : '' }}</span>
      </el-button>
      <el-button v-if="currentUser" class="avatar" @click="$emit('open-profile')">
        {{ userInitial }}
      </el-button>
      <el-button v-else class="login-pill" @click="$emit('open-login')">登录</el-button>
    </nav>
  </header>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useCart } from '../../composables/useCart'

const props = defineProps({
  currentUser: {
    type: Object,
    default: null,
  },
  defaultAddress: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['open-login', 'open-cart', 'open-address', 'open-orders', 'open-profile', 'open-favorites', 'search'])
const { cartItemCount } = useCart()
const keyword = ref('')

const userInitial = computed(() => props.currentUser?.username?.slice(0, 1).toUpperCase() || 'U')

const doSearch = () => {
  const trimmed = keyword.value.trim()
  if (trimmed) {
    emit('search', trimmed)
  }
}
</script>

<style scoped>
.home-header {
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  gap: 20px;
  width: 100%;
  min-height: 68px;
  padding: 14px 32px;
  background: var(--so-yellow);
  border-bottom: 1px solid var(--so-yellow-deep);
  box-shadow: var(--so-shadow-sticky);
}

.brand,
.location,
.header-nav :deep(.el-button) {
  border: 0;
  background: transparent;
  color: var(--so-ink-1);
}

.brand {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  gap: 10px;
  padding: 0;
}

.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--so-r-sm);
  background: var(--so-ink-1);
  color: var(--so-yellow);
  font-size: 18px;
  font-weight: 800;
  line-height: 1;
}

.brand-name {
  color: var(--so-ink-1);
  font-size: 18px;
  font-weight: 800;
  letter-spacing: -0.02em;
}

.divider {
  width: 1px;
  height: 18px;
  flex-shrink: 0;
  background: rgba(0, 0, 0, 0.12);
}

.location {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  max-width: 240px;
  min-width: 188px;
  padding: 0;
  color: var(--so-ink-1);
  font-size: 13px;
  white-space: nowrap;
}

.location-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  fill: var(--so-red);
}

.city {
  font-weight: 800;
}

.district {
  min-width: 0;
  overflow: hidden;
  color: var(--so-ink-3);
  text-overflow: ellipsis;
}

.chevron {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  fill: none;
  stroke: var(--so-ink-3);
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 2;
}

.search-form {
  flex: 1;
  min-width: 280px;
}

/* One seamless pill: icon + input + submit share a single rounded container,
   so there is no input-group divider line cutting through the submit label. */
.search-box {
  display: flex;
  align-items: center;
  gap: 10px;
  max-width: 460px;
  height: 40px;
  padding: 0 5px 0 16px;
  border-radius: var(--so-r-pill);
  background: var(--so-surface);
  box-shadow: 0 0 0 1px var(--so-border-1) inset;
  transition: box-shadow var(--so-dur) var(--so-ease);
}

.search-box:focus-within {
  box-shadow: 0 0 0 1px var(--so-orange) inset, 0 2px 12px rgba(254, 92, 52, 0.16);
}

.search-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  fill: none;
  stroke: var(--so-ink-4);
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 2.2;
}

.search-input {
  flex: 1;
  min-width: 0;
  height: 100%;
  border: 0;
  outline: none;
  background: transparent;
  color: var(--so-ink-1);
  font-size: 13px;
}

.search-input::placeholder {
  color: var(--so-ink-4);
}

.search-submit {
  flex-shrink: 0;
  height: 30px;
  padding: 0 18px;
  border: 0;
  border-radius: var(--so-r-pill);
  background: var(--so-ink-1);
  color: var(--so-yellow);
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  transition: background var(--so-dur) var(--so-ease), transform var(--so-dur) var(--so-ease);
}

.search-submit:hover {
  background: #000;
}

.search-submit:active {
  transform: scale(0.96);
}

.header-nav {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  gap: 14px;
  color: var(--so-ink-1);
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}

.header-nav :deep(.el-button) {
  height: auto;
  padding: 0;
  color: inherit;
  font-weight: inherit;
}

.header-nav :deep(.el-button + .el-button) {
  margin-left: 0;
}

.cart-pill,
.login-pill,
.avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--so-r-pill);
  transition: transform var(--so-dur) var(--so-ease), box-shadow var(--so-dur) var(--so-ease), filter var(--so-dur) var(--so-ease);
}

.cart-pill:hover,
.login-pill:hover,
.avatar:hover {
  transform: translateY(-1px);
  filter: brightness(1.05);
}

.cart-pill:active,
.login-pill:active,
.avatar:active {
  transform: translateY(0) scale(0.96);
}

.cart-pill:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.18);
}

.cart-pill {
  gap: 6px;
  padding: 6px 14px !important;
  background: var(--so-ink-1) !important;
  color: var(--so-yellow) !important;
}

.cart-pill svg {
  width: 14px;
  height: 14px;
  fill: currentColor;
}

.login-pill {
  padding: 6px 14px !important;
  background: rgba(0, 0, 0, 0.08) !important;
  color: var(--so-ink-1) !important;
}

.avatar {
  width: 32px;
  height: 32px;
  background: var(--so-ink-1) !important;
  color: var(--so-surface) !important;
  font-weight: 800 !important;
}

@media (max-width: 960px) {
  .home-header {
    flex-wrap: wrap;
    gap: 12px;
  }

  .search-form {
    order: 3;
    flex-basis: 100%;
  }

  .search-box {
    max-width: none;
  }
}
</style>
