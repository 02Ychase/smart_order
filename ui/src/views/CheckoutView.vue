<template>
  <section class="cart-dialog-view">
    <!-- cart step -->
    <template v-if="step === 'cart'">
      <header class="dialog-header">
        <h2>购物车</h2>
        <p>按商家分组查看已选商品与总价。</p>
      </header>
      <p v-if="loading">加载中...</p>
      <p v-else-if="errorMessage" class="error-text">{{ errorMessage }}</p>
      <el-empty v-else-if="!merchantGroups.length" description="购物车为空" />
      <template v-else>
        <div v-for="group in merchantGroups" :key="group.merchant_id" class="cart-group">
          <h4>{{ group.merchant_name }}</h4>
          <div v-for="item in group.items" :key="item.dish_id" class="cart-item-row">
            <div>
              <p class="dish-name">{{ item.dish_name }}</p>
              <p class="dish-meta">{{ formatCurrency(item.unit_price) }}</p>
            </div>
            <div class="quantity-control">
              <el-button
                size="small"
                circle
                :disabled="mutatingDishId === item.dish_id"
                @click="changeQuantity(item.dish_id, item.quantity - 1)"
              >
                -
              </el-button>
              <span class="quantity-value">{{ item.quantity }}</span>
              <el-button
                size="small"
                circle
                :disabled="mutatingDishId === item.dish_id"
                @click="changeQuantity(item.dish_id, item.quantity + 1)"
              >
                +
              </el-button>
              <el-button :data-test="`remove-cart-item-${item.dish_id}`" text @click="deleteCartRow(item.dish_id)">
                删除
              </el-button>
            </div>
          </div>
          <p>小计 {{ formatCurrency(group.subtotal) }}</p>
        </div>
      </template>
      <footer class="cart-footer">
        <strong>商品总价 {{ formatCurrency(goodsAmount) }}</strong>
        <el-button data-test="checkout-submit" type="primary" :disabled="!merchantGroups.length || cartMutating" @click="checkout">
          去结算
        </el-button>
      </footer>
    </template>

    <!-- select_address step -->
    <section v-if="step === 'select_address'">
      <header class="dialog-header">
        <h2>选择配送地址</h2>
        <el-button text @click="step = 'cart'">返回购物车</el-button>
      </header>

      <p v-if="addressLoading">加载中...</p>
      <p v-else-if="errorMessage" class="error-text">{{ errorMessage }}</p>
      <el-empty v-else-if="!addresses.length" description="暂无地址，请先在地址管理中添加" />
      <template v-else>
        <el-radio-group v-model="selectedAddressId">
          <div v-for="addr in addresses" :key="addr.id" class="address-option">
            <el-radio :value="addr.id">
              <strong>{{ addr.label }}</strong>
              <span>{{ addr.contact_name }} {{ addr.contact_phone }}</span>
              <p>{{ addr.city }}{{ addr.district }} {{ addr.detail_address }}</p>
            </el-radio>
          </div>
        </el-radio-group>
      </template>

      <footer class="cart-footer">
        <el-button @click="step = 'cart'">返回</el-button>
        <el-button
          type="primary"
          :disabled="!selectedAddressId"
          :loading="previewLoading"
          @click="loadPreview"
        >
          下一步
        </el-button>
      </footer>
    </section>

    <!-- preview step -->
    <section v-if="step === 'preview'">
      <header class="dialog-header">
        <h2>确认订单</h2>
        <el-button text @click="step = 'select_address'">修改地址</el-button>
      </header>

      <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>

      <div class="preview-address">
        <p>{{ previewData.address_snapshot }}</p>
      </div>

      <div v-for="mo in previewData.merchant_orders" :key="mo.merchant_id" class="preview-merchant">
        <h4>{{ mo.merchant_name }}</h4>
        <div v-for="item in mo.items" :key="item.dish_id" class="preview-item">
          <span>{{ item.dish_name }}</span>
          <span>× {{ item.quantity }}</span>
          <span>{{ formatCurrency(item.unit_price * item.quantity) }}</span>
        </div>
        <div class="preview-subtotal">
          <span>商品小计：{{ formatCurrency(mo.goods_amount) }}</span>
          <span>配送费：{{ formatCurrency(mo.delivery_amount) }}</span>
          <span v-if="mo.delivery_quote">
            配送距离 {{ (mo.delivery_quote.distance_meters / 1000).toFixed(1) }}km ·
            预计 {{ mo.delivery_quote.estimated_minutes }} 分钟送达
          </span>
        </div>
      </div>

      <div class="preview-total">
        <p>商品总额：{{ formatCurrency(previewData.goods_amount) }}</p>
        <p>配送费：{{ formatCurrency(previewData.delivery_amount) }}</p>
        <p class="total-highlight">应付金额：{{ formatCurrency(previewData.payable_amount) }}</p>
      </div>

      <footer class="cart-footer">
        <el-button @click="step = 'select_address'">返回</el-button>
        <el-button type="primary" :loading="payLoading" @click="confirmAndPay">
          确认并支付 {{ formatCurrency(previewData.payable_amount) }}
        </el-button>
      </footer>
    </section>

    <!-- paying step -->
    <section v-if="step === 'paying'" class="paying-state">
      <el-icon class="is-loading" :size="48"><Loading /></el-icon>
      <p>正在处理订单...</p>
    </section>

    <!-- success step -->
    <section v-if="step === 'success'" class="success-state">
      <el-result icon="success" title="支付成功">
        <template #sub-title>
          <p>订单号：#{{ orderResult.checkout_order_id }}</p>
          <p>支付金额：{{ formatCurrency(orderResult.payable_amount) }}</p>
        </template>
        <template #extra>
          <el-button type="primary" @click="emit('order-created', orderResult.checkout_order_id)">
            查看订单
          </el-button>
          <el-button @click="backToCart">继续点餐</el-button>
        </template>
      </el-result>
    </section>
  </section>
</template>

<script setup>
import { Loading } from '@element-plus/icons-vue'
import { onMounted, ref } from 'vue'
import { listAddresses } from '../api/address'
import { updateCartItem } from '../api/cart'
import { mockPay, previewCheckout, submitOrder } from '../api/orders'
import { useCart } from '../composables/useCart'
import { formatCurrency } from '../utils/currency'

const emit = defineEmits(['order-created'])

const { cartMutating, goodsAmount, merchantGroups, refreshCart, removeCartItem } = useCart()
const loading = ref(true)
const errorMessage = ref('')
const removingDishId = ref(null)
const mutatingDishId = ref(null)

const step = ref('cart')

const addresses = ref([])
const selectedAddressId = ref(null)
const addressLoading = ref(false)

const previewData = ref(null)
const previewLoading = ref(false)

const orderResult = ref(null)
const payLoading = ref(false)

const loadCart = async () => {
  try {
    await refreshCart()
  } catch (error) {
    errorMessage.value = error?.message || '加载失败，请稍后再试'
  } finally {
    loading.value = false
  }
}

const deleteCartRow = async (dishId) => {
  removingDishId.value = dishId
  errorMessage.value = ''
  try {
    await removeCartItem(dishId)
  } catch (error) {
    errorMessage.value = error?.message || '删除失败，请稍后再试'
  } finally {
    removingDishId.value = null
  }
}

const changeQuantity = async (dishId, newQuantity) => {
  if (newQuantity <= 0) {
    await deleteCartRow(dishId)
    return
  }
  mutatingDishId.value = dishId
  errorMessage.value = ''
  try {
    await updateCartItem(dishId, { dish_id: dishId, quantity: newQuantity })
    await refreshCart()
  } catch (e) {
    errorMessage.value = e?.message || '更新失败'
  } finally {
    mutatingDishId.value = null
  }
}

const checkout = async () => {
  if (!merchantGroups.value.length || cartMutating.value) return

  step.value = 'select_address'
  addressLoading.value = true
  errorMessage.value = ''
  try {
    addresses.value = await listAddresses()
    const defaultAddr = addresses.value.find(a => a.is_default)
    if (defaultAddr) {
      selectedAddressId.value = defaultAddr.id
    }
  } catch (e) {
    errorMessage.value = e?.message || '获取地址失败'
    step.value = 'cart'
  } finally {
    addressLoading.value = false
  }
}

const loadPreview = async () => {
  previewLoading.value = true
  errorMessage.value = ''
  try {
    previewData.value = await previewCheckout({ address_id: selectedAddressId.value })
    step.value = 'preview'
  } catch (e) {
    errorMessage.value = e?.message || '获取结算预览失败'
  } finally {
    previewLoading.value = false
  }
}

const confirmAndPay = async () => {
  payLoading.value = true
  errorMessage.value = ''
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
  } finally {
    payLoading.value = false
  }
}

const backToCart = () => {
  step.value = 'cart'
  orderResult.value = null
  previewData.value = null
  selectedAddressId.value = null
}

onMounted(loadCart)
</script>

<style scoped>
.dialog-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.cart-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #eee;
}

.address-option {
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
}

.preview-address {
  padding: 12px 16px;
  background: #f8fbff;
  border-radius: 8px;
  margin-bottom: 16px;
}

.preview-merchant {
  margin-bottom: 16px;
}

.preview-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
}

.preview-subtotal {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  padding-top: 8px;
  border-top: 1px solid #f0f0f0;
  font-size: 13px;
  color: #666;
}

.preview-total {
  padding: 16px;
  background: #f8fbff;
  border-radius: 8px;
  margin-bottom: 16px;
}

.total-highlight {
  font-size: 18px;
  font-weight: bold;
  color: #409eff;
}

.paying-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
  gap: 16px;
}

.success-state {
  padding: 20px 0;
}

.error-text {
  color: #f56c6c;
  font-size: 14px;
  margin: 8px 0;
}

.quantity-control {
  display: flex;
  align-items: center;
  gap: 8px;
}

.quantity-value {
  min-width: 24px;
  text-align: center;
  font-weight: 500;
}
</style>
