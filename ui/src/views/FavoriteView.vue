<template>
  <section class="favorite-view">
    <div class="modal-header">
      <div>
        <h2>我的收藏</h2>
        <p class="subtitle">{{ favorites.length }} 家商家</p>
      </div>
      <button class="close-x" @click="$emit('close')">×</button>
    </div>

    <div class="modal-body mt-scroll">
      <p v-if="loading" class="state-text">加载中...</p>
      <p v-else-if="errorMessage" class="state-text state-text--error">{{ errorMessage }}</p>
      <div v-else-if="!favorites.length" class="empty-state">
        <div class="empty-heart">♡</div>
        <p>还没有收藏的商家</p>
      </div>

      <div
        v-for="fav in favorites"
        v-else
        :key="fav.id"
        class="fav-row"
        @click="emit('select-merchant', fav.merchant_id)"
      >
        <div class="fav-cover">
          <span class="fav-cover-emoji">🏪</span>
        </div>
        <div class="fav-info">
          <p class="fav-name">{{ fav.merchant_name }}</p>
          <div v-if="fav.rating" class="fav-meta">
            <SoStars :value="fav.rating" :size="10" />
            <span v-if="fav.monthly_sales" class="fav-sales">月售 {{ fav.monthly_sales }}</span>
          </div>
          <p v-if="fav.district || fav.category" class="fav-loc">{{ fav.district }}{{ fav.category ? ' · ' + fav.category : '' }}</p>
        </div>
        <button class="heart-btn" @click.stop="removeFavorite(fav.merchant_id)">♥</button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { listFavorites, toggleFavorite } from '../api/favorites'
import SoStars from '../components/shared/SoStars.vue'

const emit = defineEmits(['select-merchant', 'close'])

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
.favorite-view {
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

/* Empty state */
.empty-state {
  padding: 60px 0;
  text-align: center;
  color: var(--so-ink-4);
}

.empty-heart { font-size: 60px; opacity: 0.3; }
.empty-state p { margin: 12px 0 0; font-size: 14px; }

/* Favorite row */
.fav-row {
  display: flex;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--so-surface-line);
  cursor: pointer;
  transition: background 0.15s;
}

.fav-row:hover { background: var(--so-yellow-faint); margin: 0 -12px; padding: 12px; border-radius: var(--so-r-sm); }

.fav-cover {
  width: 64px; height: 64px; border-radius: var(--so-r-sm);
  background: linear-gradient(135deg, #fff3e0, #ffe0b2);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}

.fav-cover-emoji { font-size: 28px; }

.fav-info { flex: 1; min-width: 0; }
.fav-name { margin: 0; font-size: 15px; font-weight: 700; color: var(--so-ink-1); }

.fav-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
  font-size: 12px;
}

.fav-sales { color: var(--so-ink-4); }
.fav-loc { margin: 4px 0 0; font-size: 12px; color: var(--so-ink-3); }

.heart-btn {
  align-self: flex-start;
  background: transparent; border: none; cursor: pointer;
  color: var(--so-red); font-size: 18px;
  padding: 4px;
  transition: transform 0.15s;
}

.heart-btn:hover { transform: scale(1.2); }

.state-text { padding: 60px 0; text-align: center; color: var(--so-ink-4); font-size: 14px; }
.state-text--error { color: var(--so-red); }
</style>
