<template>
  <div class="homepage-shell">
    <div class="homepage-container">
      <HomeHeader
        :current-user="currentUser"
        @open-login="loginOpen = true"
        @open-cart="cartOpen = true"
        @open-address="addressOpen = true"
      />
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
      <CheckoutView />
    </el-dialog>
    <el-dialog v-model="addressOpen" width="560px" destroy-on-close>
      <AddressView />
    </el-dialog>
    <el-drawer v-model="merchantDrawerOpen" size="480px" destroy-on-close>
      <MerchantDetailView :merchant-id="selectedMerchantId" />
    </el-drawer>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import CategoryFilterBar from './components/home/CategoryFilterBar.vue'
import FloatingAssistant from './components/home/FloatingAssistant.vue'
import HomeHeader from './components/home/HomeHeader.vue'
import { useAuth } from './composables/useAuth'
import { useHomepage } from './composables/useHomepage'
import AddressView from './views/AddressView.vue'
import CheckoutView from './views/CheckoutView.vue'
import LoginView from './views/LoginView.vue'
import MerchantDetailView from './views/MerchantDetailView.vue'
import MerchantListView from './views/MerchantListView.vue'

const loginOpen = ref(false)
const cartOpen = ref(false)
const addressOpen = ref(false)
const merchantDrawerOpen = ref(false)
const { currentUser } = useAuth()

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
