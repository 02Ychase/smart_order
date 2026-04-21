<template>
  <el-card>
    <template #header>订单详情</template>
    <p v-if="loading">加载中...</p>
    <p v-else-if="errorMessage">{{ errorMessage }}</p>
    <el-empty v-else-if="!order" description="暂无订单详情" />
    <div v-else>
      <p>订单号：#{{ order.checkout_order_id }}</p>
      <p>状态：{{ formatOrderStatus(order.order_status) }}</p>
      <div v-for="merchantOrder in order.merchant_orders" :key="merchantOrder.merchant_order_id" class="merchant-order-card">
        <h4>商家 {{ merchantOrder.merchant_id }}</h4>
        <p>子单状态：{{ formatOrderStatus(merchantOrder.order_status) }}</p>
        <ul>
          <li v-for="item in merchantOrder.items" :key="`${merchantOrder.merchant_order_id}-${item.dish_id}`">
            {{ item.dish_name }} × {{ item.quantity }}
          </li>
        </ul>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { getOrderDetail, listOrders } from '../api/orders'
import { formatOrderStatus } from '../utils/orderStatus'

const order = ref(null)
const loading = ref(true)
const errorMessage = ref('')

onMounted(async () => {
  try {
    const orders = await listOrders()
    const firstOrder = orders[0]

    if (!firstOrder) {
      return
    }

    order.value = await getOrderDetail(firstOrder.checkout_order_id)
  } catch (error) {
    errorMessage.value = error?.message || '加载失败，请稍后再试'
  } finally {
    loading.value = false
  }
})
</script>
