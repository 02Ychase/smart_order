<template>
  <div class="category-row">
    <el-button
      v-for="category in categories"
      :key="category"
      :type="category === selectedCategory ? 'primary' : 'default'"
      round
      @click="$emit('select-category', category)"
    >
      {{ category }}
    </el-button>
  </div>
</template>

<script setup>
defineProps({
  categories: { type: Array, default: () => [] },
  selectedCategory: { type: String, default: '全部' },
})

defineEmits(['select-category'])
</script>

<style scoped>
.category-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  padding: 4px 0 8px;
}
</style>
