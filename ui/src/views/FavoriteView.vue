<template>
  <section class="favorite-view">
    <header class="dialog-header">
      <h2>我的收藏</h2>
    </header>

    <p v-if="loading">加载中...</p>
    <p v-else-if="errorMessage" class="error-text">{{ errorMessage }}</p>
    <el-empty v-else-if="!favorites.length" description="暂无收藏" />

    <template v-else>
      <div
        v-for="fav in favorites"
        :key="fav.id"
        class="favorite-card"
        @click="emit('select-merchant', fav.merchant_id)"
      >
        <span class="favorite-name">{{ fav.merchant_name }}</span>
        <el-button
          size="small"
          type="danger"
          text
          @click.stop="removeFavorite(fav.merchant_id)"
        >
          取消收藏
        </el-button>
      </div>
    </template>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { listFavorites, toggleFavorite } from '../api/favorites'

const emit = defineEmits(['select-merchant'])

const favorites = ref([])
const loading = ref(true)
const errorMessage = ref('')

const loadFavorites = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    favorites.value = await listFavorites()
  } catch (error) {
    errorMessage.value = error?.message || '加载失败，请稍后再试'
  } finally {
    loading.value = false
  }
}

const removeFavorite = async (merchantId) => {
  try {
    await toggleFavorite(merchantId)
    await loadFavorites()
  } catch (error) {
    errorMessage.value = error?.message || '操作失败，请稍后再试'
  }
}

onMounted(loadFavorites)
</script>

<style scoped>
.dialog-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.favorite-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border: 1px solid #eee;
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: box-shadow 0.2s;
}

.favorite-card:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.favorite-name {
  font-weight: 600;
  color: #1f2a44;
}

.error-text {
  color: #f56c6c;
  font-size: 14px;
}
</style>
