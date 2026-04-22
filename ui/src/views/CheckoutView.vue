<template>
  <section class="cart-dialog-view">
    <header class="dialog-header">
      <h2>购物车</h2>
      <p>按商家分组查看已选商品与总价。</p>
    </header>
    <p v-if="loading">加载中...</p>
    <p v-else-if="errorMessage">{{ errorMessage }}</p>
    <el-empty v-else-if="!merchantGroups.length" description="购物车为空" />
    <template v-else>
      <div v-for="group in merchantGroups" :key="group.merchant_id" class="cart-group">
        <h4>{{ group.merchant_name }}</h4>
        <div v-for="item in group.items" :key="item.dish_id" class="cart-item-row">
          <div>
            <p class="dish-name">{{ item.dish_name }}</p>
            <p class="dish-meta">{{ formatCurrency(item.unit_price) }} · × {{ item.quantity }}</p>
          </div>
          <el-button :data-test="`remove-cart-item-${item.dish_id}`" text :loading="removingDishId === item.dish_id" @click="deleteCartRow(item.dish_id)">
            删除
          </el-button>
        </div>
        <p>小计 {{ formatCurrency(group.subtotal) }}</p>
      </div>
    </template>
    <footer class="cart-footer">
      <strong>商品总价 {{ formatCurrency(goodsAmount) }}</strong>
      <el-button data-test="checkout-submit" type="primary" :disabled="!merchantGroups.length" @click="checkout">
        去结算
      </el-button>
    </footer>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useCart } from '../composables/useCart'
import { formatCurrency } from '../utils/currency'

const { cartMutating, goodsAmount, merchantGroups, refreshCart, removeCartItem } = useCart()
const loading = ref(true)
const errorMessage = ref('')
const removingDishId = ref(null)

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

const checkout = () => {
  if (!merchantGroups.value.length || cartMutating.value) {
    return
  }

  ElMessage.info('结算功能暂未开放')
}

onMounted(loadCart)
</script>
