<template>
  <section class="order-detail-view">
    <div class="modal-header">
      <div>
        <h2>订单详情</h2>
        <p class="subtitle">订单号：#{{ order?.checkout_order_id || orderId }}</p>
      </div>
      <button class="close-x" @click="$emit('close')">×</button>
    </div>

    <div class="modal-body mt-scroll">
      <p v-if="loading" class="state-text">加载中...</p>
      <p v-else-if="errorMessage" class="state-text state-text--error">{{ errorMessage }}</p>
      <div v-else-if="!order" class="state-text">暂无订单详情</div>

      <template v-else>
        <!-- Big status block -->
        <div class="status-block" :style="statusBlockStyle">
          <div>
            <p class="status-label" :style="{ color: statusMeta.color }">状态：{{ statusMeta.label }}</p>
            <p class="status-desc">{{ statusDesc }}</p>
          </div>
          <span class="status-emoji">{{ statusEmoji }}</span>
        </div>

        <!-- Timeline -->
        <div v-if="showTimeline" class="timeline-bar">
          <template v-for="(step, i) in timelineSteps" :key="step.key">
            <div class="tl-step">
              <div class="tl-dot" :class="{ done: i <= timelineIdx }">{{ i <= timelineIdx ? '✓' : i + 1 }}</div>
              <span class="tl-label" :class="{ done: i <= timelineIdx }">{{ step.label }}</span>
            </div>
            <div v-if="i < timelineSteps.length - 1" class="tl-bar" :class="{ done: i < timelineIdx }" />
          </template>
        </div>

        <!-- Address -->
        <div class="section-block">
          <span class="section-icon">📍</span>
          <div class="section-content">
            <h4>配送地址</h4>
            <p>{{ order.address_snapshot }}</p>
          </div>
        </div>

        <!-- Merchant items -->
        <div v-for="mo in order.merchant_orders" :key="mo.merchant_order_id" class="merchant-card">
          <div class="merchant-card-header">
            <span class="merchant-name">{{ mo.merchant_name || `商家 ${mo.merchant_id}` }}</span>
            <span v-if="mo.delivery_quote" class="merchant-meta">
              · {{ (mo.delivery_quote.distance_meters / 1000).toFixed(1) }}km · 约 {{ mo.delivery_quote.estimated_minutes }} 分钟
            </span>
          </div>
          <p class="merchant-sub-status">子单状态：{{ merchantStatusLabel(mo.order_status) }}</p>
          <div v-for="item in mo.items" :key="item.dish_id" class="item-row">
            <div class="item-thumb" :style="{ background: dishBg(item) }">{{ dishGlyph(item) }}</div>
            <span class="item-name">{{ item.dish_name }}</span>
            <span class="item-qty"> × {{ item.quantity }}</span>
            <SoPrice v-if="item.unit_price != null" :value="item.unit_price * item.quantity" :size="14" />
          </div>
        </div>

        <!-- Summary -->
        <div class="summary-block">
          <div class="summary-row">
            <span>商品总额</span>
            <span>¥{{ Number(order.goods_amount).toFixed(2) }}</span>
          </div>
          <div class="summary-row">
            <span>配送费</span>
            <span>¥{{ Number(order.delivery_amount).toFixed(2) }}</span>
          </div>
          <div class="summary-total">
            <span>实付</span>
            <SoPrice :value="order.payable_amount" :size="22" />
          </div>
        </div>

        <p class="order-time">下单时间：{{ formatTime(order.created_at) }}</p>

        <!-- Review section -->
        <div v-if="order.order_status === 'completed'" class="review-section">
          <template v-if="review">
            <div class="section-block">
              <span class="section-icon">⭐</span>
              <div class="section-content">
                <h4>我的评价</h4>
                <div class="review-stars">
                  <SoStars :value="review.rating" :size="14" />
                </div>
                <p v-if="review.comment" class="review-comment">{{ review.comment }}</p>
                <span class="review-time">{{ formatTime(review.created_at) }}</span>
              </div>
            </div>
          </template>
          <template v-else-if="showReviewForm">
            <div class="section-block review-form-block">
              <span class="section-icon">✍️</span>
              <div class="section-content" style="flex: 1">
                <h4>写评价</h4>
                <el-rate v-model="reviewForm.rating" />
                <el-input
                  v-model="reviewForm.comment"
                  type="textarea"
                  :rows="3"
                  placeholder="写下你的评价（可选）"
                  style="margin-top: 8px"
                />
                <div class="review-form-actions">
                  <button class="btn-cta" :disabled="submittingReview" @click="handleSubmitReview">提交评价</button>
                  <button class="btn-ghost" @click="showReviewForm = false">取消</button>
                </div>
              </div>
            </div>
          </template>
          <template v-else>
            <button class="btn-ghost review-trigger" @click="showReviewForm = true">⭐ 去评价</button>
          </template>
        </div>
      </template>
    </div>

    <!-- Action bar -->
    <div v-if="order && !loading" class="action-bar">
      <el-popconfirm
        v-if="canCancel"
        title="确定要取消该订单吗？"
        confirm-button-text="取消订单"
        cancel-button-text="暂不"
        @confirm="cancelCurrentOrder"
      >
        <template #reference>
          <button class="btn-ghost" :disabled="cancelling">取消订单</button>
        </template>
      </el-popconfirm>
      <button v-if="canReorder" class="btn-ghost" :disabled="reordering" @click="handleReorder">再来一单</button>
      <button v-if="canAdvance" class="btn-cta" :disabled="advancing" @click="advanceStatus">{{ advanceButtonLabel }} ›</button>
    </div>
  </section>
</template>

<script setup>
import { computed, onUnmounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { advanceOrderStatus, cancelOrder, getOrderDetail, getReview, listOrders, reorder, submitReview } from '../api/orders'
import SoPrice from '../components/shared/SoPrice.vue'
import SoStars from '../components/shared/SoStars.vue'

const props = defineProps({
  orderId: { type: Number, default: null },
})

const emit = defineEmits(['reorder-done', 'close'])

let eventSource = null

const order = ref(null)
const loading = ref(true)
const errorMessage = ref('')
const advancing = ref(false)

const STATUS_META = {
  pending_payment: { label: '待支付', color: '#ff8f1f', bg: '#fff7e6' },
  paid:            { label: '已支付', color: '#52c41a', bg: '#f6ffed' },
  preparing:       { label: '制作中', color: '#fe5c34', bg: '#fff3eb' },
  delivering:      { label: '配送中', color: '#fe5c34', bg: '#fff3eb' },
  completed:       { label: '已完成', color: '#999',    bg: '#f2f2f2' },
  cancelled:       { label: '已取消', color: '#ff3b30', bg: '#fef0f0' },
}

const STATUS_EMOJI = {
  pending_payment: '💰',
  paid: '💰',
  preparing: '🍳',
  delivering: '🛵',
  completed: '🎉',
  cancelled: '❌',
}

const STATUS_DESC = {
  pending_payment: '请尽快完成支付',
  paid: '商家即将开始制作',
  preparing: '商家正在加紧制作',
  delivering: '骑手已取餐，正在送往你身边',
  completed: '订单已完成，感谢支持！',
  cancelled: '订单已取消',
}

const ADVANCE_LABELS = {
  paid: '开始制作',
  preparing: '配送中',
  delivering: '确认送达',
}

const DISH_PALETTE = [
  { glyph: '🍜', bg: 'linear-gradient(135deg,#fff3e0,#ffe0b2)' },
  { glyph: '🍛', bg: 'linear-gradient(135deg,#fff8e1,#ffecb3)' },
  { glyph: '🍲', bg: 'linear-gradient(135deg,#fce4ec,#f8bbd0)' },
  { glyph: '🍱', bg: 'linear-gradient(135deg,#e8f5e9,#c8e6c9)' },
  { glyph: '🥘', bg: 'linear-gradient(135deg,#fff3e0,#ffccbc)' },
]

const dishGlyph = (item) => DISH_PALETTE[(item.dish_id || 0) % DISH_PALETTE.length].glyph
const dishBg = (item) => DISH_PALETTE[(item.dish_id || 0) % DISH_PALETTE.length].bg

const statusMeta = computed(() => STATUS_META[order.value?.order_status] || {})
const merchantStatusLabel = (s) => STATUS_META[s]?.label || s
const statusEmoji = computed(() => STATUS_EMOJI[order.value?.order_status] || '')
const statusDesc = computed(() => STATUS_DESC[order.value?.order_status] || '')
const statusBlockStyle = computed(() => ({ background: statusMeta.value.bg }))

const timelineSteps = [
  { key: 'paid', label: '已支付' },
  { key: 'preparing', label: '制作中' },
  { key: 'delivering', label: '配送中' },
  { key: 'completed', label: '已完成' },
]
const timelineOrder = ['paid', 'preparing', 'delivering', 'completed']

const showTimeline = computed(() => {
  if (!order.value) return false
  return !['cancelled', 'pending_payment'].includes(order.value.order_status)
})

const timelineIdx = computed(() => timelineOrder.indexOf(order.value?.order_status))

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

const formatTime = (iso) => {
  if (!iso) return ''
  const d = new Date(iso)
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

const closeEventSource = () => {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
}

const loadOrder = async (orderId) => {
  closeEventSource()
  loading.value = true
  errorMessage.value = ''
  order.value = null

  try {
    let targetOrderId = orderId
    if (!targetOrderId) {
      const orders = await listOrders()
      targetOrderId = orders?.[0]?.checkout_order_id
      if (!targetOrderId) return
    }

    order.value = await getOrderDetail(targetOrderId)
    if (order.value && order.value.order_status === 'completed') {
      await loadReview(targetOrderId)
    }
    connectSSE(targetOrderId)
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
.order-detail-view {
  display: flex;
  flex-direction: column;
  max-height: 78vh;
  color: var(--so-ink-1);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
  border-bottom: 1px solid var(--so-border-1);
}

.modal-header h2 { margin: 0; font-size: 18px; font-weight: 700; }
.subtitle { margin: 4px 0 0; color: var(--so-ink-4); font-size: 13px; }

.close-x {
  width: 28px; height: 28px; border: none; background: transparent;
  cursor: pointer; color: var(--so-ink-4); font-size: 22px; line-height: 1; padding: 0;
}

.modal-body { flex: 1; overflow-y: auto; padding: 16px 24px 8px; }

/* Status block */
.status-block {
  padding: 18px 20px;
  border-radius: var(--so-r-md);
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.status-label { margin: 0; font-size: 20px; font-weight: 800; }
.status-desc { margin: 4px 0 0; font-size: 13px; color: var(--so-ink-3); }
.status-emoji { font-size: 36px; line-height: 1; }

/* Timeline */
.timeline-bar {
  display: flex;
  align-items: center;
  padding: 14px 8px;
  margin-bottom: 16px;
  background: var(--so-surface);
  border-radius: var(--so-r-md);
  box-shadow: var(--so-shadow-card);
}

.tl-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  gap: 6px;
}

.tl-dot {
  width: 24px; height: 24px; border-radius: 50%;
  background: var(--so-surface-line);
  color: var(--so-ink-4);
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700;
}

.tl-dot.done { background: var(--so-yellow); color: var(--so-ink-1); }

.tl-label { font-size: 12px; color: var(--so-ink-4); font-weight: 400; }
.tl-label.done { color: var(--so-ink-1); font-weight: 600; }

.tl-bar {
  flex: 1; height: 2px; margin-bottom: 18px;
  background: var(--so-surface-line);
}

.tl-bar.done { background: var(--so-yellow); }

/* Section block */
.section-block {
  padding: 14px 18px;
  background: var(--so-surface);
  border-radius: var(--so-r-md);
  box-shadow: var(--so-shadow-card);
  margin-bottom: 16px;
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.section-icon { font-size: 20px; line-height: 1.2; }

.section-content { flex: 1; }
.section-content h4 { margin: 0 0 4px; font-size: 12px; color: var(--so-ink-4); font-weight: 600; }
.section-content p { margin: 0; color: var(--so-ink-1); font-size: 14px; }

/* Merchant card */
.merchant-card {
  background: var(--so-surface);
  border-radius: var(--so-r-md);
  box-shadow: var(--so-shadow-card);
  overflow: hidden;
  margin-bottom: 16px;
}

.merchant-card-header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--so-border-1);
  display: flex;
  align-items: center;
  gap: 8px;
}

.merchant-name { font-size: 14px; font-weight: 700; color: var(--so-ink-1); }
.merchant-meta { font-size: 12px; color: var(--so-ink-4); }
.merchant-sub-status { margin: 0; padding: 4px 16px 0; font-size: 12px; color: var(--so-ink-3); }

.item-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
}

.item-thumb {
  width: 40px; height: 40px; border-radius: var(--so-r-sm);
  display: flex; align-items: center; justify-content: center;
  font-size: 22px; flex-shrink: 0;
}

.item-name { flex: 1; font-size: 14px; color: var(--so-ink-1); }
.item-qty { font-size: 12px; color: var(--so-ink-4); }

/* Summary */
.summary-block {
  padding: 16px;
  background: var(--so-yellow-faint);
  border-radius: var(--so-r-md);
  margin-bottom: 16px;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: var(--so-ink-3);
  padding: 2px 0;
}

.summary-total {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding-top: 8px;
  margin-top: 8px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

.summary-total span { font-size: 14px; color: var(--so-ink-2); font-weight: 600; }

.order-time { margin: 0 0 16px; font-size: 12px; color: var(--so-ink-4); }

/* Review */
.review-section { margin-bottom: 16px; }

.review-stars { margin: 4px 0; }
.review-comment { margin: 6px 0 4px; color: var(--so-ink-2); font-size: 14px; }
.review-time { font-size: 12px; color: var(--so-ink-4); }

.review-form-block { align-items: flex-start; }

.review-form-actions {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.review-trigger {
  width: 100%;
  text-align: center;
  padding: 10px;
  font-size: 14px;
}

/* Action bar */
.action-bar {
  display: flex;
  gap: 10px;
  padding: 14px 24px;
  border-top: 1px solid var(--so-border-1);
  background: var(--so-surface);
  justify-content: flex-end;
}

/* Buttons */
.btn-ghost {
  height: 36px; padding: 0 18px;
  background: var(--so-surface); color: var(--so-ink-2);
  border: 1px solid var(--so-border-2);
  border-radius: var(--so-r-pill);
  font-size: 13px; font-weight: 500; cursor: pointer;
  transition: all 0.15s;
}

.btn-ghost:hover { border-color: var(--so-ink-4); }
.btn-ghost:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-cta {
  height: 36px; padding: 0 22px;
  background: var(--so-orange); color: #fff;
  border: none;
  border-radius: var(--so-r-pill);
  font-size: 13px; font-weight: 600; cursor: pointer;
  transition: all 0.15s;
}

.btn-cta:hover { opacity: 0.9; }
.btn-cta:disabled { opacity: 0.5; cursor: not-allowed; }

.state-text { padding: 60px 0; text-align: center; color: var(--so-ink-4); font-size: 14px; }
.state-text--error { color: var(--so-red); }
</style>
