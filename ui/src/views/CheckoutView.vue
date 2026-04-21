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
        <p>小计 {{ formatCurrency(group.subtotal) }}</p>
      </div>
      <footer class="cart-footer">
        <strong>商品总价 {{ formatCurrency(cart.goods_amount) }}</strong>
        <el-button type="primary">去结算</el-button>
      </footer>
    </template>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useCart } from '../composables/useCart'
import { formatCurrency } from '../utils/currency'

const { cart, merchantGroups, refreshCart } = useCart()
const loading = ref(true)
const errorMessage = ref('')

onMounted(async () => {
  try {
    await refreshCart()
  } catch (error) {
    errorMessage.value = error?.message || '加载失败，请稍后再试'
  } finally {
    loading.value = false
  }
})
</script>
