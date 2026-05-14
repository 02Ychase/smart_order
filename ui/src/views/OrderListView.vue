<template>
  <section class="order-list-view">
    <div class="modal-header">
      <div>
        <h2>我的订单</h2>
        <p class="subtitle">共 {{ orders.length }} 单</p>
      </div>
      <button class="close-x" @click="$emit('close')">×</button>
    </div>

    <div class="modal-body mt-scroll">
      <p v-if="loading" class="state-text">加载中...</p>
      <p v-else-if="errorMessage" class="state-text state-text--error">{{ errorMessage }}</p>
      <div v-else-if="!orders.length" class="state-text">暂无订单</div>

      <article
        v-for="order in orders"
        v-else
        :key="order.checkout_order_id"
        class="order-card"
        @click="emit('view-order', order.checkout_order_id)"
      >
        <div class="order-top">
          <span class="order-id">订单 #{{ order.checkout_order_id }}</span>
          <span class="status-pill" :style="statusStyle(order.order_status)">{{ statusLabel(order.order_status) }}</span>
        </div>
        <p class="order-address">{{ order.address_snapshot }}</p>
        <div class="merchant-chips">
          <span v-for="mo in order.merchant_orders" :key="mo.merchant_order_id" class="merchant-chip">{{ mo.merchant_name }}</span>
        </div>
        <div class="order-bottom">
          <span class="order-time">{{ formatTime(order.created_at) }}</span>
          <div class="bottom-right">
            <SoPrice :value="order.payable_amount" :size="16" />
            <el-popconfirm
              v-if="['pending_payment', 'paid'].includes(order.order_status)"
              title="确定要取消该订单吗？"
              confirm-button-text="取消订单"
              cancel-button-text="暂不"
              @confirm.stop="cancelOrderFromList(order.checkout_order_id)"
            >
              <template #reference>
                <button class="cancel-mini" :disabled="cancellingId === order.checkout_order_id" @click.stop>取消</button>
              </template>
            </el-popconfirm>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { cancelOrder, listOrders } from '../api/orders'
import SoPrice from '../components/shared/SoPrice.vue'

const emit = defineEmits(['view-order', 'close'])

const orders = ref([])
const loading = ref(true)
const errorMessage = ref('')
const cancellingId = ref(null)

const STATUS_META = {
  pending_payment: { label: '待支付', color: '#ff8f1f', bg: '#fff7e6' },
  paid:            { label: '已支付', color: '#52c41a', bg: '#f6ffed' },
  preparing:       { label: '制作中', color: '#fe5c34', bg: '#fff3eb' },
  delivering:      { label: '配送中', color: '#fe5c34', bg: '#fff3eb' },
  completed:       { label: '已完成', color: '#999',    bg: '#f2f2f2' },
  cancelled:       { label: '已取消', color: '#ff3b30', bg: '#fef0f0' },
}

const statusLabel = (s) => STATUS_META[s]?.label || s
const statusStyle = (s) => {
  const m = STATUS_META[s] || {}
  return { color: m.color, background: m.bg }
}

const formatTime = (iso) => {
  if (!iso) return ''
  const d = new Date(iso)
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

const cancelOrderFromList = async (orderId) => {
  cancellingId.value = orderId
  try {
    await cancelOrder(orderId)
    orders.value = await listOrders()
  } catch (e) {
    errorMessage.value = e?.message || '取消失败'
  } finally { cancellingId.value = null }
}

onMounted(async () => {
  try { orders.value = await listOrders() } catch (e) { errorMessage.value = e?.message || '加载失败' } finally { loading.value = false }
})
</script>

<style scoped>
.order-list-view {
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

.modal-body { flex: 1; overflow-y: auto; padding: 12px 24px 24px; }

.order-card {
  padding: 16px;
  border: 1px solid var(--so-border-1);
  border-radius: var(--so-r-md);
  margin-bottom: 12px;
  cursor: pointer;
  transition: all 0.15s;
  background: var(--so-surface);
}

.order-card:hover { box-shadow: var(--so-shadow-card); }

.order-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.order-id { font-weight: 600; font-size: 14px; }

.status-pill {
  font-size: 12px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: var(--so-r-pill);
}

.order-address {
  margin: 8px 0 0;
  color: var(--so-ink-3);
  font-size: 13px;
  line-height: 1.5;
}

.merchant-chips {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin: 8px 0;
}

.merchant-chip {
  padding: 2px 8px;
  background: var(--so-yellow-soft);
  color: #866a00;
  border-radius: 3px;
  font-size: 12px;
  font-weight: 500;
}

.order-bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--so-surface-line);
}

.order-time { font-size: 12px; color: var(--so-ink-4); }
.bottom-right { display: flex; align-items: center; gap: 10px; }

.cancel-mini {
  height: 26px; padding: 0 12px;
  background: #fff; color: var(--so-ink-3);
  border: 1px solid var(--so-border-2);
  border-radius: var(--so-r-pill);
  font-size: 12px; cursor: pointer;
}

.state-text { padding: 60px 0; text-align: center; color: var(--so-ink-4); font-size: 14px; }
.state-text--error { color: var(--so-red); }
</style>
