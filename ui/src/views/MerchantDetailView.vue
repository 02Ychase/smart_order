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
        <p>{{ formatCurrency(dish.price) }}</p>
      </div>
    </template>
  </el-card>
</template>

<script setup>
import { ref, watch } from 'vue'
import { listMerchantDishes } from '../api/catalog'
import { formatCurrency } from '../utils/currency'

const props = defineProps({
  merchantId: { type: Number, default: null },
})

const dishes = ref([])
const loading = ref(false)
const errorMessage = ref('')

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
