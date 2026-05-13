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

      <div v-if="canAdvance || canCancel || canReorder" class="detail-actions">
        <el-button v-if="canAdvance" type="primary" :loading="advancing" @click="advanceStatus">
          {{ advanceButtonLabel }}
        </el-button>
        <el-popconfirm
          v-if="canCancel"
          title="确定要取消该订单吗？"
          confirm-button-text="取消订单"
          cancel-button-text="暂不"
          @confirm="cancelCurrentOrder"
        >
          <template #reference>
            <el-button :loading="cancelling">取消订单</el-button>
          </template>
        </el-popconfirm>
        <el-button v-if="canReorder" type="primary" :loading="reordering" @click="handleReorder">
          再来一单
        </el-button>
      </div>

      <div v-if="order.order_status === 'completed'" class="review-section">
        <h4>订单评价</h4>
        <template v-if="review">
          <div class="review-display">
            <el-rate :model-value="review.rating" disabled />
            <p v-if="review.comment">{{ review.comment }}</p>
            <span class="review-time">{{ formatTime(review.created_at) }}</span>
          </div>
        </template>
        <template v-else-if="showReviewForm">
          <div class="review-form">
            <el-rate v-model="reviewForm.rating" />
            <el-input
              v-model="reviewForm.comment"
              type="textarea"
              :rows="3"
              placeholder="写下你的评价（可选）"
            />
            <div class="review-form-actions">
              <el-button type="primary" :loading="submittingReview" @click="handleSubmitReview">提交评价</el-button>
              <el-button @click="showReviewForm = false">取消</el-button>
            </div>
          </div>
        </template>
        <template v-else>
          <el-button @click="showReviewForm = true">去评价</el-button>
        </template>
      </div>
    </template>
  </section>
</template>

<script setup>
import { computed, onUnmounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { advanceOrderStatus, cancelOrder, getOrderDetail, getReview, reorder, submitReview } from '../api/orders'
import { formatCurrency } from '../utils/currency'
import { formatOrderStatus } from '../utils/orderStatus'

const props = defineProps({
  orderId: { type: Number, default: null },
})

const emit = defineEmits(['reorder-done'])

let eventSource = null

const order = ref(null)
const loading = ref(true)
const errorMessage = ref('')
const advancing = ref(false)

const ADVANCE_LABELS = {
  paid: '开始制作',
  preparing: '配送中',
  delivering: '确认送达',
}

const canAdvance = computed(() => {
  if (!order.value) return false
  return ['paid', 'preparing', 'delivering'].includes(order.value.order_status)
})

const advanceButtonLabel = computed(() => {
  if (!order.value) return ''
  return ADVANCE_LABELS[order.value.order_status] || '推进状态'
})

const cancelling = ref(false)

const review = ref(null)
const showReviewForm = ref(false)
const submittingReview = ref(false)
const reviewForm = ref({ rating: 5, comment: '' })
const reordering = ref(false)

const canReorder = computed(() => {
  if (!order.value) return false
  return ['completed', 'cancelled'].includes(order.value.order_status)
})

const canCancel = computed(() => {
  if (!order.value) return false
  return ['pending_payment', 'paid'].includes(order.value.order_status)
})

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

const closeEventSource = () => {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
}

const loadOrder = async (orderId) => {
  closeEventSource()
  if (!orderId) {
    loading.value = false
    return
  }
  loading.value = true
  errorMessage.value = ''
  try {
    order.value = await getOrderDetail(orderId)
    if (order.value && order.value.order_status === 'completed') {
      await loadReview(orderId)
    }
    connectSSE(orderId)
  } catch (error) {
    errorMessage.value = error?.message || '加载失败，请稍后再试'
  } finally {
    loading.value = false
  }
}

const connectSSE = (orderId) => {
  const token = window.localStorage.getItem('smart_order_access_token')
  if (!token) return

  eventSource = new EventSource(`/api/orders/${orderId}/events?token=${encodeURIComponent(token)}`)
  eventSource.addEventListener('status_changed', (event) => {
    try {
      const data = JSON.parse(event.data)
      order.value = data
    } catch {
      // ignore parse errors
    }
  })
  eventSource.onerror = () => {
    closeEventSource()
  }
}

onUnmounted(closeEventSource)

const loadReview = async (orderId) => {
  try {
    review.value = await getReview(orderId)
  } catch {
    review.value = null
  }
}

const handleSubmitReview = async () => {
  if (!order.value || submittingReview.value) return
  submittingReview.value = true
  try {
    review.value = await submitReview(order.value.checkout_order_id, reviewForm.value)
    showReviewForm.value = false
  } catch (error) {
    errorMessage.value = error?.message || '评价失败，请稍后再试'
  } finally {
    submittingReview.value = false
  }
}

const handleReorder = async () => {
  if (!order.value || reordering.value) return
  reordering.value = true
  try {
    const result = await reorder(order.value.checkout_order_id)
    if (result.skipped_items && result.skipped_items.length) {
      ElMessage.warning(`${result.skipped_items.length} 个商品已下架，已跳过`)
    }
    ElMessage.success('已加入购物车')
    emit('reorder-done')
  } catch (error) {
    errorMessage.value = error?.message || '操作失败，请稍后再试'
  } finally {
    reordering.value = false
  }
}

const advanceStatus = async () => {
  if (!order.value || advancing.value) return
  advancing.value = true
  errorMessage.value = ''
  try {
    order.value = await advanceOrderStatus(order.value.checkout_order_id)
  } catch (error) {
    errorMessage.value = error?.message || '操作失败，请稍后再试'
  } finally {
    advancing.value = false
  }
}

const cancelCurrentOrder = async () => {
  if (!order.value || cancelling.value) return
  cancelling.value = true
  errorMessage.value = ''
  try {
    order.value = await cancelOrder(order.value.checkout_order_id)
  } catch (error) {
    errorMessage.value = error?.message || '取消失败，请稍后再试'
  } finally {
    cancelling.value = false
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

.detail-actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

.review-section {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

.review-section h4 {
  margin: 0 0 12px;
  color: #1f2a44;
}

.review-display p {
  margin: 8px 0 4px;
  color: #333;
}

.review-time {
  font-size: 13px;
  color: #999;
}

.review-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.review-form-actions {
  display: flex;
  gap: 8px;
}
</style>
