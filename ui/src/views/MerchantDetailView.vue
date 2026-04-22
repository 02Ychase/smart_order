<template>
  <el-card>
    <template #header>商家详情</template>
    <p v-if="loading">加载中...</p>
    <p v-else-if="errorMessage">{{ errorMessage }}</p>
    <el-empty v-else-if="!dishes.length" description="暂无菜品" />
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
import { listMerchantDishes } from '../api/catalog'
import { useAuth } from '../composables/useAuth'
import { useCart } from '../composables/useCart'
import { formatCurrency } from '../utils/currency'

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
    errorMessage.value = error?.message || '加入购物车失败，请稍后再试'
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
    dishes.value = await listMerchantDishes(merchantId)
  } catch (error) {
    errorMessage.value = error?.message || '加载失败，请稍后再试'
  } finally {
    loading.value = false
  }
}

watch(() => props.merchantId, loadDishes, { immediate: true })
</script>
