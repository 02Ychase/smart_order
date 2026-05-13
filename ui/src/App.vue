<template>
  <div class="homepage-shell">
    <div class="homepage-container">
      <HomeHeader
        :current-user="currentUser"
        @open-login="loginOpen = true"
        @open-cart="cartOpen = true"
        @open-address="addressOpen = true"
        @open-orders="ordersOpen = true"
        @open-profile="profileOpen = true"
        @open-favorites="favoritesOpen = true"
      />
      <SearchBar @search="handleSearch" />
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

    <FloatingAssistant />

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
      <ProfileView />
    </el-dialog>
    <el-dialog v-model="favoritesOpen" width="520px" destroy-on-close>
      <FavoriteView @select-merchant="openMerchantFromFavorites" />
    </el-dialog>
    <el-dialog v-model="searchOpen" width="600px" destroy-on-close>
      <SearchResultView :keyword="searchKeyword" @select-merchant="openMerchantFromSearch" />
    </el-dialog>
    <el-drawer v-model="merchantDrawerOpen" size="480px" destroy-on-close>
      <MerchantDetailView :merchant-id="selectedMerchantId" @request-login="loginOpen = true" />
    </el-drawer>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import CategoryFilterBar from './components/home/CategoryFilterBar.vue'
import FloatingAssistant from './components/home/FloatingAssistant.vue'
import HomeHeader from './components/home/HomeHeader.vue'
import SearchBar from './components/home/SearchBar.vue'
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
const { currentUser } = useAuth()
const { refreshCart } = useCart()

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

onMounted(loadMerchants)
</script>

<style scoped>
.homepage-shell {
  min-height: 100vh;
  padding: 28px 32px 120px;
  background: linear-gradient(180deg, #f8fbff 0%, #f5f8ff 100%);
}

.homepage-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
  max-width: 1440px;
}
</style>
