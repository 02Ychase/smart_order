<template>
  <section class="order-detail-view">
    <header class="dialog-header">
      <h2>订单详情</h2>
    </header>

    <p v-if="loading">加载中...</p>
    <p v-else-if="errorMessage" class="error-text">{{ errorMessage }}</p>
    <el-empty v-else-if="!order" description="订单不存在" />

    <template v-else>
      <div class="detail-status">
        <el-tag :type="statusTagType(order.order_status)" size="large">
          {{ formatOrderStatus(order.order_status) }}
        </el-tag>
        <span class="detail-order-id">订单号：#{{ order.checkout_order_id }}</span>
      </div>

      <div class="detail-section">
        <h4>配送地址</h4>
        <p>{{ order.address_snapshot }}</p>
      </div>

      <div v-for="mo in order.merchant_orders" :key="mo.merchant_order_id" class="detail-merchant">
        <h4>{{ mo.merchant_name }}</h4>
        <div v-for="item in mo.items" :key="item.dish_id" class="detail-item">
          <span class="item-name">{{ item.dish_name }}</span>
          <span class="item-qty">× {{ item.quantity }}</span>
          <span class="item-price">{{ formatCurrency(item.unit_price * item.quantity) }}</span>
        </div>
        <div class="detail-merchant-footer">
          <span>商品：{{ formatCurrency(mo.goods_amount) }}</span>
          <span>配送：{{ formatCurrency(mo.delivery_amount) }}</span>
          <span v-if="mo.delivery_quote">
            {{ (mo.delivery_quote.distance_meters / 1000).toFixed(1) }}km ·
            预计 {{ mo.delivery_quote.estimated_minutes }} 分钟
          </span>
        </div>
      </div>

      <div class="detail-total">
        <p>商品总额：{{ formatCurrency(order.goods_amount) }}</p>
        <p>配送费：{{ formatCurrency(order.delivery_amount) }}</p>
        <p class="total-highlight">实付金额：{{ formatCurrency(order.payable_amount) }}</p>
      </div>

      <div class="detail-time">
        <p>下单时间：{{ formatTime(order.created_at) }}</p>
      </div>
    </template>
  </section>
</template>

<script setup>
import { ref, watch } from 'vue'
import { getOrderDetail } from '../api/orders'
import { formatCurrency } from '../utils/currency'
import { formatOrderStatus } from '../utils/orderStatus'

const props = defineProps({
  orderId: { type: Number, default: null },
})

const order = ref(null)
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

const loadOrder = async (orderId) => {
  if (!orderId) {
    loading.value = false
    return
  }
  loading.value = true
  errorMessage.value = ''
  try {
    order.value = await getOrderDetail(orderId)
  } catch (error) {
    errorMessage.value = error?.message || '加载失败，请稍后再试'
  } finally {
    loading.value = false
  }
}

watch(() => props.orderId, loadOrder, { immediate: true })
</script>

<style scoped>
.dialog-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.detail-status {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.detail-order-id {
  color: #666;
  font-size: 14px;
}

.detail-section {
  padding: 12px 16px;
  background: #f8fbff;
  border-radius: 8px;
  margin-bottom: 16px;
}

.detail-section h4 {
  margin: 0 0 4px;
  font-size: 14px;
  color: #666;
}

.detail-section p {
  margin: 0;
  color: #1f2a44;
}

.detail-merchant {
  margin-bottom: 16px;
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
}

.detail-merchant h4 {
  margin: 0 0 8px;
  color: #1f2a44;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
}

.item-name {
  flex: 1;
}

.item-qty {
  margin: 0 12px;
  color: #999;
}

.item-price {
  font-weight: 500;
}

.detail-merchant-footer {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  margin-top: 8px;
  font-size: 13px;
  color: #666;
}

.detail-total {
  padding: 16px;
  background: #f8fbff;
  border-radius: 8px;
  margin-bottom: 16px;
}

.detail-total p {
  margin: 4px 0;
}

.total-highlight {
  font-size: 18px;
  font-weight: bold;
  color: #409eff;
}

.detail-time p {
  margin: 0;
  font-size: 13px;
  color: #999;
}

.error-text {
  color: #f56c6c;
  font-size: 14px;
}
</style>
