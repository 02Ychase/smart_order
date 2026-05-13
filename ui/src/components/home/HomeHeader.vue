<template>
  <section class="home-header">
    <div>
      <p class="eyebrow">smart_order</p>
      <h1>smart_order 智能外卖平台</h1>
      <p class="description">多商家点餐与智能推荐，先选口味，再快速完成下单。</p>
    </div>
    <div class="actions">
      <span v-if="currentUser" class="current-user">当前用户：{{ currentUser.username }}</span>
      <el-button plain @click="$emit('open-login')">登录</el-button>
      <el-badge :value="cartItemCount" :hidden="!cartItemCount">
        <el-button plain @click="$emit('open-cart')">购物车</el-button>
      </el-badge>
      <el-button plain @click="$emit('open-address')">地址管理</el-button>
      <el-button plain @click="$emit('open-orders')">我的订单</el-button>
    </div>
  </section>
</template>

<script setup>
import { useCart } from '../../composables/useCart'

const { cartItemCount } = useCart()

defineProps({
  currentUser: {
    type: Object,
    default: null,
  },
})

defineEmits(['open-login', 'open-cart', 'open-address', 'open-orders'])
</script>

<style scoped>
.home-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 28px 32px;
  border-radius: 28px;
  background: linear-gradient(135deg, #f8fbff, #edf5ff);
  box-shadow: 0 18px 40px rgba(61, 115, 202, 0.08);
}

.eyebrow {
  margin: 0 0 10px;
  color: #6d86a8;
  font-size: 14px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

h1 {
  margin: 0;
  color: #1f2a44;
  font-size: 34px;
}

.description {
  margin: 12px 0 0;
  color: #61708d;
  font-size: 16px;
}

.actions {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.current-user {
  color: #35507a;
  font-size: 14px;
  font-weight: 600;
}
</style>
