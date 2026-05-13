<template>
  <section class="order-list-view">
    <header class="dialog-header">
      <h2>我的订单</h2>
    </header>

    <p v-if="loading">加载中...</p>
    <p v-else-if="errorMessage" class="error-text">{{ errorMessage }}</p>
    <el-empty v-else-if="!orders.length" description="暂无订单" />

    <template v-else>
      <div
        v-for="order in orders"
        :key="order.checkout_order_id"
        class="order-card"
        @click="emit('view-order', order.checkout_order_id)"
      >
        <div class="order-card-header">
          <span class="order-id">订单 #{{ order.checkout_order_id }}</span>
          <el-tag :type="statusTagType(order.order_status)" size="small">
            {{ formatOrderStatus(order.order_status) }}
          </el-tag>
        </div>
        <div class="order-card-body">
          <p>{{ order.address_snapshot }}</p>
          <div class="order-merchants">
            <span v-for="mo in order.merchant_orders" :key="mo.merchant_order_id">
              {{ mo.merchant_name }}
            </span>
          </div>
        </div>
        <div class="order-card-footer">
          <span class="order-time">{{ formatTime(order.created_at) }}</span>
          <span class="order-amount">{{ formatCurrency(order.payable_amount) }}</span>
        </div>
      </div>
    </template>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { listOrders } from '../api/orders'
import { formatCurrency } from '../utils/currency'
import { formatOrderStatus } from '../utils/orderStatus'

const emit = defineEmits(['view-order'])

const orders = ref([])
const loading = ref(true)
const errorMessage = ref('')

const statusTagType = (status) => {
  const map = {
    pending_payment: 'warning',
    paid: 'success',
    preparing: 'primary',
    delivering: 'primary',
    completed: 'info',
    cancelled: 'danger',
  }
  return map[status] || 'info'
}

const formatTime = (isoString) => {
  if (!isoString) return ''
  const d = new Date(isoString)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

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

<style scoped>
.dialog-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.order-card {
  padding: 16px;
  border: 1px solid #eee;
  border-radius: 8px;
  margin-bottom: 12px;
  cursor: pointer;
  transition: box-shadow 0.2s;
}

.order-card:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.order-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.order-id {
  font-weight: 600;
  color: #1f2a44;
}

.order-card-body p {
  margin: 4px 0;
  color: #666;
  font-size: 14px;
}

.order-merchants {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 4px;
}

.order-merchants span {
  padding: 2px 8px;
  background: #f0f5ff;
  border-radius: 4px;
  font-size: 13px;
  color: #409eff;
}

.order-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #f0f0f0;
}

.order-time {
  font-size: 13px;
  color: #999;
}

.order-amount {
  font-weight: 600;
  color: #1f2a44;
}

.error-text {
  color: #f56c6c;
  font-size: 14px;
}
</style>
