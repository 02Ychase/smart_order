<template>
  <div class="search-bar">
    <el-input
      v-model="keyword"
      placeholder="搜索商家或菜品"
      clearable
      @keyup.enter="doSearch"
    >
      <template #append>
        <el-button @click="doSearch">搜索</el-button>
      </template>
    </el-input>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['search'])
const keyword = ref('')

const doSearch = () => {
  const trimmed = keyword.value.trim()
  if (trimmed) {
    emit('search', trimmed)
  }
}
</script>

<style scoped>
.search-bar {
  max-width: 480px;
}
</style>
