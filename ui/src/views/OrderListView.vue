<template>
  <el-card>
    <template #header>订单列表</template>
    <p v-if="loading">加载中...</p>
    <p v-else-if="errorMessage">{{ errorMessage }}</p>
    <el-empty v-else-if="!orders.length" description="暂无订单" />
    <template v-else>
      <div v-for="order in orders" :key="order.checkout_order_id" class="order-card">
        <h4>订单 #{{ order.checkout_order_id }}</h4>
        <p>状态：{{ formatOrderStatus(order.order_status) }}</p>
        <p>支付：{{ formatOrderStatus(order.payment_status) }}</p>
        <p>实付：{{ formatCurrency(order.payable_amount) }}</p>
      </div>
    </template>
  </el-card>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { listOrders } from '../api/orders'
import { formatCurrency } from '../utils/currency'
import { formatOrderStatus } from '../utils/orderStatus'

const orders = ref([])
const loading = ref(true)
const errorMessage = ref('')

onMounted(async () => {
  try {
    orders.value = await listOrders()
  } catch (error) {
    errorMessage.value = error?.message || '加载失败，请稍后再试'
  } finally {
    loading.value = false
  }
})
</script>
