<template>
  <el-card>
    <template #header>
      <div class="merchant-header">
        <span>商家详情</span>
        <el-button
          :type="favorited ? 'danger' : 'default'"
          text
          @click="handleToggleFavorite"
        >
          {{ favorited ? '已收藏' : '收藏' }}
        </el-button>
      </div>
    </template>
    <p v-if="loading">加载中...</p>
    <p v-else-if="errorMessage">{{ errorMessage }}</p>
    <div v-if="merchantInfo" class="merchant-info">
      <span>{{ merchantInfo.name }}</span>
      <el-tag :type="formatBusinessStatus(merchantInfo.business_hours, true) === '营业中' ? 'success' : 'danger'" size="small">
        {{ formatBusinessStatus(merchantInfo.business_hours, true) }}
      </el-tag>
      <span v-if="merchantInfo.business_hours" class="business-hours">{{ merchantInfo.business_hours }}</span>
    </div>
    <el-empty v-if="!loading && !dishes.length" description="暂无菜品" />
    <template v-else>
      <div v-for="dish in dishes" :key="dish.id" class="dish-card">
        <h4>{{ dish.name }}</h4>
        <p>{{ dish.description }}</p>
        <div class="dish-footer">
          <p>{{ formatCurrency(dish.price) }}</p>
          <el-button :data-test="`add-cart-${dish.id}`" type="primary" :loading="addingDishId === dish.id" @click="addDishToCart(dish.id)">
            加入购物车
          </el-button>
        </div>
      </div>
    </template>
  </el-card>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getMerchant, listMerchantDishes } from '../api/catalog'
import { checkFavorite, toggleFavorite } from '../api/favorites'
import { useAuth } from '../composables/useAuth'
import { useCart } from '../composables/useCart'
import { formatCurrency } from '../utils/currency'
import { formatBusinessStatus } from '../utils/businessHours'

const emit = defineEmits(['request-login'])
const props = defineProps({
  merchantId: { type: Number, default: null },
})

const { currentUser } = useAuth()
const { addCartItem } = useCart()
const dishes = ref([])
const loading = ref(false)
const errorMessage = ref('')
const addingDishId = ref(null)
const favorited = ref(false)
const merchantInfo = ref(null)

const loadFavoriteStatus = async (merchantId) => {
  if (!merchantId || !currentUser.value) return
  try {
    const result = await checkFavorite(merchantId)
    favorited.value = result.favorited
  } catch {
    favorited.value = false
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

const loadDishes = async (merchantId) => {
  if (!merchantId) {
    dishes.value = []
    loading.value = false
    return
  }

  loading.value = true
  errorMessage.value = ''

  try {
    merchantInfo.value = await getMerchant(merchantId)
    dishes.value = await listMerchantDishes(merchantId)
    await loadFavoriteStatus(merchantId)
  } catch (error) {
    errorMessage.value = error?.message || '加载失败，请稍后再试'
  } finally {
    loading.value = false
  }
}

watch(() => props.merchantId, loadDishes, { immediate: true })
</script>

<style scoped>
.merchant-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.merchant-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 14px;
  color: #333;
}

.business-hours {
  font-size: 13px;
  color: #999;
}
</style>
