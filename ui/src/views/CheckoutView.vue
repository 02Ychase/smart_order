<template>
  <section class="checkout-view">
    <!-- cart step -->
    <template v-if="step === 'cart'">
      <div class="modal-header">
        <div>
          <h2>购物车</h2>
          <p class="subtitle">按商家分组</p>
        </div>
      </div>
      <div class="modal-body mt-scroll">
        <p v-if="loading" class="state-text">加载中...</p>
        <p v-else-if="errorMessage" class="state-text state-text--error">{{ errorMessage }}</p>
        <div v-else-if="!merchantGroups.length" class="empty-cart">
          <span class="empty-icon">🛒</span>
          <p class="empty-title">购物车为空</p>
          <p class="empty-hint">关闭对话框，挑几道菜吧</p>
        </div>
        <template v-else>
          <div v-for="group in merchantGroups" :key="group.merchant_id" class="cart-group">
            <div class="group-header">
              <span class="group-thumb">{{ groupGlyph(group) }}</span>
              <h3>{{ group.merchant_name }}</h3>
              <SoPromoBadge kind="manjian">满50减8</SoPromoBadge>
            </div>
            <div v-for="item in group.items" :key="item.dish_id" class="cart-item">
              <div class="item-thumb" :style="{ background: itemBg(item) }">{{ itemGlyph(item) }}</div>
              <div class="item-info">
                <p class="item-name">{{ item.dish_name }}</p>
                <SoPrice :value="item.unit_price" :size="14" />
              </div>
              <span class="item-qty-label">× {{ item.quantity }}</span>
              <QtyStepper
                :qty="item.quantity"
                small
                @minus="changeQuantity(item.dish_id, item.quantity - 1)"
                @plus="changeQuantity(item.dish_id, item.quantity + 1)"
              />
              <button class="remove-btn" :data-test="`remove-cart-item-${item.dish_id}`" @click="changeQuantity(item.dish_id, 0)">×</button>
            </div>
            <p class="group-subtotal">小计 <strong>{{ mtYuan(group.subtotal) }}</strong></p>
          </div>
        </template>
      </div>
      <div class="modal-footer">
        <div class="footer-left">
          <span class="footer-label">商品总价 </span>
          <SoPrice :value="goodsAmount" :size="24" />
        </div>
        <button
          class="cta-button"
          data-test="checkout-submit"
          :disabled="!merchantGroups.length || cartMutating"
          @click="checkout"
        >去结算 ›</button>
      </div>
    </template>

    <!-- select_address step -->
    <template v-if="step === 'select_address'">
      <div class="modal-header">
        <h2>选择配送地址</h2>
        <button class="text-link" @click="step = 'cart'">‹ 返回</button>
      </div>
      <div class="modal-body mt-scroll">
        <p v-if="addressLoading" class="state-text">加载中...</p>
        <p v-else-if="errorMessage" class="state-text state-text--error">{{ errorMessage }}</p>
        <div v-else-if="!addresses.length" class="state-text">暂无地址，请先添加</div>
        <label
          v-for="addr in addresses"
          v-else
          :key="addr.id"
          class="address-card"
          :class="{ selected: selectedAddressId === addr.id }"
          @click="selectedAddressId = addr.id"
        >
          <input type="radio" :checked="selectedAddressId === addr.id" />
          <div class="address-content">
            <div class="address-top">
              <strong>{{ addr.contact_name }}</strong>
              <span class="address-phone">{{ addr.contact_phone }}</span>
              <span class="chip chip--orange">{{ addr.label || '地址' }}</span>
              <span v-if="addr.is_default" class="chip">默认</span>
            </div>
            <p class="address-line">{{ addr.city }}{{ addr.district }} {{ addr.detail_address }}</p>
          </div>
        </label>
      </div>
      <div class="modal-footer">
        <div></div>
        <button class="cta-button" :disabled="!selectedAddressId" @click="loadPreview">下一步 ›</button>
      </div>
    </template>

    <!-- preview step -->
    <template v-if="step === 'preview'">
      <div class="modal-header">
        <h2>确认订单</h2>
        <button class="text-link" @click="step = 'select_address'">‹ 修改地址</button>
      </div>
      <div class="modal-body mt-scroll">
        <p v-if="errorMessage" class="state-text state-text--error">{{ errorMessage }}</p>
        <!-- Address -->
        <div v-if="previewAddress" class="preview-addr-card">
          <span class="addr-emoji">📍</span>
          <div>
            <p class="addr-name">{{ previewAddress.contact_name }} <span>{{ previewAddress.contact_phone }}</span></p>
            <p class="addr-detail">{{ previewAddress.city }}{{ previewAddress.district }} {{ previewAddress.detail_address }}</p>
          </div>
        </div>
        <!-- Items per merchant -->
        <div v-for="mo in (previewData?.merchant_orders || [])" :key="mo.merchant_id" class="preview-merchant">
          <div class="preview-merchant-header">
            <span class="merchant-label">{{ mo.merchant_name }}</span>
            <SoPromoBadge kind="manjian">满50减8</SoPromoBadge>
          </div>
          <div v-for="item in mo.items" :key="item.dish_id" class="preview-item">
            <div class="item-thumb item-thumb--sm" :style="{ background: itemBg(item) }">{{ itemGlyph(item) }}</div>
            <span class="item-flex-name">{{ item.dish_name }}</span>
            <span class="item-qty">× {{ item.quantity }}</span>
            <SoPrice :value="item.unit_price * item.quantity" :size="14" />
          </div>
        </div>
        <!-- Note -->
        <div class="note-row">
          <span class="note-label">备注</span>
          <input v-model="note" placeholder="如：不要香菜、少放辣..." class="note-input" />
        </div>
        <!-- Summary -->
        <div v-if="previewData" class="summary-block">
          <div class="summary-row"><span>商品小计</span><span>¥{{ previewData.goods_amount?.toFixed(2) }}</span></div>
          <div class="summary-row"><span>配送费</span><span>¥{{ previewData.delivery_amount?.toFixed(2) }}</span></div>
        </div>
      </div>
      <div class="modal-footer">
        <div class="footer-left">
          <span class="footer-label">实付</span>
          <SoPrice :value="previewData?.payable_amount || 0" :size="28" />
        </div>
        <button class="cta-button cta-button--gradient" :disabled="hasMinOrderViolation" @click="confirmAndPay">提交订单 ›</button>
      </div>
    </template>

    <!-- paying step -->
    <template v-if="step === 'paying'">
      <div class="center-state">
        <span class="mt-spinner pay-spinner"></span>
        <p class="center-title">正在处理订单…</p>
        <p class="center-hint">请稍候，正在为你下单并通知商家</p>
      </div>
    </template>

    <!-- success step -->
    <template v-if="step === 'success'">
      <div class="center-state">
        <div class="success-circle">✓</div>
        <h2 class="success-title">下单成功</h2>
        <p class="success-meta">订单号 #{{ orderResult?.checkout_order_id }} · 预计 28 分钟送达</p>
        <p class="success-amount">已支付 ¥{{ savedPayable.toFixed(2) }}</p>
        <div class="success-actions">
          <button class="cta-button" @click="emit('order-created', orderResult?.checkout_order_id)">查看订单</button>
          <button class="ghost-button" @click="backToCart">继续点餐</button>
        </div>
      </div>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { listAddresses } from '../api/address'
import { updateCartItem } from '../api/cart'
import { mockPay, previewCheckout, submitOrder } from '../api/orders'
import SoPrice from '../components/shared/SoPrice.vue'
import SoPromoBadge from '../components/shared/SoPromoBadge.vue'
import QtyStepper from '../components/shared/QtyStepper.vue'
import { useCart } from '../composables/useCart'

const emit = defineEmits(['order-created'])
const { cartMutating, goodsAmount, merchantGroups, refreshCart, removeCartItem } = useCart()

const loading = ref(true)
const errorMessage = ref('')
const mutatingDishId = ref(null)
const step = ref('cart')
const addresses = ref([])
const selectedAddressId = ref(null)
const addressLoading = ref(false)
const previewData = ref(null)
const orderResult = ref(null)
const savedPayable = ref(0)
const note = ref('')

const hasMinOrderViolation = computed(() =>
  previewData.value?.merchant_orders?.some((mo) => mo.goods_amount < mo.min_order_amount) || false,
)

const previewAddress = computed(() => addresses.value.find((a) => a.id === selectedAddressId.value))

const dishGlyphs = ['🐟', '🥩', '🌶️', '🍳', '🥔', '🍜', '🥗', '🍰']
const dishBgs = [
  'linear-gradient(135deg, #ffe1d6, #ffb59c)',
  'linear-gradient(135deg, #ffd6c2, #ff9a7a)',
  'linear-gradient(135deg, #ffe0e0, #ff9999)',
  'linear-gradient(135deg, #fff4dc, #f3d8aa)',
]
const itemGlyph = (item) => item.glyph || item.emoji || dishGlyphs[Math.abs(Number(item.dish_id || 0)) % dishGlyphs.length]
const itemBg = (item) => item.bg || item.background || dishBgs[Math.abs(Number(item.dish_id || 0)) % dishBgs.length]
const groupGlyph = (group) => dishGlyphs[Math.abs(Number(group.merchant_id || 0)) % dishGlyphs.length]
const mtYuan = (v) => `¥${Number(v || 0).toFixed(2)}`

const changeQuantity = async (dishId, newQty) => {
  if (newQty <= 0) {
    mutatingDishId.value = dishId
    try { await removeCartItem(dishId) } catch { /* ignore */ } finally { mutatingDishId.value = null }
    return
  }
  mutatingDishId.value = dishId
  try {
    await updateCartItem(dishId, { dish_id: dishId, quantity: newQty })
    await refreshCart()
  } catch { /* ignore */ } finally { mutatingDishId.value = null }
}

const checkout = async () => {
  if (!merchantGroups.value.length || cartMutating.value) return
  step.value = 'select_address'
  addressLoading.value = true
  errorMessage.value = ''
  try {
    addresses.value = await listAddresses()
    const def = addresses.value.find((a) => a.is_default)
    if (def) selectedAddressId.value = def.id
  } catch (e) {
    errorMessage.value = e?.message || '获取地址失败'
    step.value = 'cart'
  } finally { addressLoading.value = false }
}

const loadPreview = async () => {
  errorMessage.value = ''
  try {
    previewData.value = await previewCheckout({ address_id: selectedAddressId.value })
    step.value = 'preview'
  } catch (e) {
    errorMessage.value = e?.message || '获取结算预览失败'
  }
}

const confirmAndPay = async () => {
  errorMessage.value = ''
  savedPayable.value = previewData.value?.payable_amount || 0
  step.value = 'paying'
  try {
    const order = await submitOrder({ address_id: selectedAddressId.value })
    const payResult = await mockPay({ checkout_order_id: order.checkout_order_id })
    orderResult.value = {
      checkout_order_id: order.checkout_order_id,
      payable_amount: order.payable_amount,
      payment_status: payResult.payment_status,
      order_status: payResult.order_status,
    }
    await refreshCart()
    step.value = 'success'
  } catch (e) {
    errorMessage.value = e?.message || '下单失败，请稍后再试'
    step.value = 'preview'
  }
}

const backToCart = () => {
  step.value = 'cart'
  orderResult.value = null
  previewData.value = null
  selectedAddressId.value = null
  savedPayable.value = 0
}

onMounted(async () => {
  try { await refreshCart() } catch (e) { errorMessage.value = e?.message || '加载失败' } finally { loading.value = false }
})
</script>

<style scoped>
.checkout-view {
  display: flex;
  flex-direction: column;
  max-height: 78vh;
  color: var(--so-ink-1);
  font-family: var(--so-font-sans);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
  border-bottom: 1px solid var(--so-border-1);
}

.modal-header h2 { margin: 0; font-size: 18px; font-weight: 700; }
.modal-header .subtitle { margin: 4px 0 0; color: var(--so-ink-4); font-size: 13px; }

.text-link {
  background: transparent;
  border: none;
  color: var(--so-ink-3);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}

.modal-body { flex: 1; overflow-y: auto; padding: 20px 24px; }

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 24px;
  border-top: 1px solid var(--so-border-1);
  background: var(--so-surface);
}

.footer-left {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.footer-label { font-size: 13px; color: var(--so-ink-3); }

/* CTA */
.cta-button {
  height: 42px;
  padding: 0 28px;
  border: none;
  border-radius: var(--so-r-pill);
  background: var(--so-orange);
  color: #fff;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
}

.cta-button:disabled {
  background: var(--so-ink-5);
  cursor: not-allowed;
}

.cta-button--gradient {
  background: linear-gradient(90deg, #ff8f1f, #ff5b3c);
  box-shadow: 0 4px 12px rgba(255, 91, 60, 0.3);
}

.ghost-button {
  height: 42px;
  padding: 0 28px;
  border: 1px solid var(--so-border-2);
  border-radius: var(--so-r-pill);
  background: #fff;
  color: var(--so-ink-2);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

/* Empty */
.empty-cart { padding: 60px 20px; text-align: center; color: var(--so-ink-4); }
.empty-icon { display: block; font-size: 80px; opacity: 0.4; }
.empty-title { margin: 12px 0 4px; font-size: 15px; font-weight: 600; color: var(--so-ink-2); }
.empty-hint { margin: 0; font-size: 13px; }

/* Cart group */
.cart-group { margin-bottom: 20px; }
.group-header { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.group-thumb {
  width: 28px; height: 28px; border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  font-size: 16px; background: var(--so-surface-line);
}
.group-header h3 { margin: 0; font-size: 15px; font-weight: 700; }
.group-subtotal { padding: 8px 0 0; text-align: right; color: var(--so-ink-3); font-size: 13px; }

.cart-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--so-surface-line);
}

.item-thumb {
  width: 48px; height: 48px;
  border-radius: var(--so-r-sm);
  display: flex; align-items: center; justify-content: center;
  font-size: 24px; flex-shrink: 0;
}

.item-thumb--sm { width: 40px; height: 40px; font-size: 22px; }

.item-info { flex: 1; min-width: 0; }
.item-name { margin: 0 0 2px; font-size: 14px; font-weight: 600; color: var(--so-ink-1); }
.item-qty-label { font-size: 12px; color: var(--so-ink-4); margin-right: 4px; white-space: nowrap; }
.remove-btn {
  width: 20px; height: 20px; border: none; background: transparent;
  color: var(--so-ink-4); cursor: pointer; font-size: 14px; padding: 0;
  display: flex; align-items: center; justify-content: center;
}

/* Address cards */
.address-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  margin-bottom: 12px;
  border: 1.5px solid var(--so-border-1);
  border-radius: var(--so-r-md);
  background: var(--so-surface);
  cursor: pointer;
  transition: all 0.15s;
}

.address-card.selected {
  border-color: var(--so-yellow);
  background: var(--so-yellow-faint);
}

.address-card input[type="radio"] { margin-top: 4px; accent-color: var(--so-orange); }
.address-content { flex: 1; }
.address-top { display: flex; align-items: center; gap: 8px; }
.address-top strong { font-size: 15px; }
.address-phone { font-size: 13px; color: var(--so-ink-4); }
.address-line { margin: 6px 0 0; font-size: 13px; color: var(--so-ink-2); }

.chip {
  display: inline-flex;
  align-items: center;
  height: 18px;
  padding: 0 8px;
  border-radius: var(--so-r-pill);
  font-size: 10px;
  font-weight: 500;
  background: var(--so-surface-line);
  color: var(--so-ink-3);
}

.chip--orange {
  background: var(--so-orange-soft);
  color: var(--so-orange);
}

/* Preview */
.preview-addr-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  margin-bottom: 16px;
  border-left: 4px solid var(--so-yellow);
  border-radius: var(--so-r-md);
  background: var(--so-surface);
  box-shadow: var(--so-shadow-card);
}

.addr-emoji { font-size: 22px; }
.addr-name { margin: 0; font-size: 14px; font-weight: 600; }
.addr-name span { color: var(--so-ink-4); font-weight: 400; }
.addr-detail { margin: 4px 0 0; font-size: 13px; color: var(--so-ink-2); }

.preview-merchant {
  margin-bottom: 16px;
  border-radius: var(--so-r-md);
  background: var(--so-surface);
  box-shadow: var(--so-shadow-card);
  overflow: hidden;
}

.preview-merchant-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--so-border-1);
}

.merchant-label { font-size: 14px; font-weight: 700; }

.preview-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
}

.item-flex-name { flex: 1; font-size: 14px; }
.item-qty { font-size: 12px; color: var(--so-ink-4); }

.note-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  margin-bottom: 16px;
  border-radius: var(--so-r-md);
  background: var(--so-surface);
  box-shadow: var(--so-shadow-card);
}

.note-label { font-size: 14px; font-weight: 600; color: var(--so-ink-2); }
.note-input {
  flex: 1; height: 32px; border: none; outline: none;
  font-size: 14px; color: var(--so-ink-1); font-family: var(--so-font-sans);
}

.summary-block {
  padding: 16px;
  border-radius: var(--so-r-md);
  background: var(--so-yellow-faint);
}

.summary-row {
  display: flex;
  justify-content: space-between;
  padding: 5px 0;
  font-size: 13px;
}

.summary-row span:first-child { color: var(--so-ink-3); }

/* Center states */
.center-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 40px;
  gap: 12px;
}

.pay-spinner {
  width: 48px;
  height: 48px;
  border-width: 4px;
  color: var(--so-orange);
}

.center-title { margin: 0; font-size: 16px; font-weight: 600; }
.center-hint { margin: 0; font-size: 13px; color: var(--so-ink-4); }

.success-circle {
  width: 80px; height: 80px; border-radius: 50%;
  background: var(--so-success-soft); color: var(--so-success);
  display: flex; align-items: center; justify-content: center;
  font-size: 44px; margin-bottom: 12px;
}

.success-title { margin: 0; font-size: 24px; font-weight: 800; }
.success-meta { margin: 6px 0 0; color: var(--so-ink-3); font-size: 14px; }
.success-amount { margin: 4px 0 0; font-size: 16px; font-weight: 700; }
.success-actions { display: flex; gap: 12px; margin-top: 22px; }

.state-text { padding: 40px 0; text-align: center; color: var(--so-ink-4); font-size: 14px; }
.state-text--error { color: var(--so-red); }
</style>
