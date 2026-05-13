<template>
  <section class="profile-view">
    <header class="dialog-header">
      <h2>我的资料</h2>
    </header>

    <p v-if="loading">加载中...</p>
    <p v-else-if="errorMessage" class="error-text">{{ errorMessage }}</p>

    <template v-else>
      <el-form label-width="80px" class="profile-form">
        <el-form-item label="用户名">
          <el-input :model-value="profile.username" disabled />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="form.full_name" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="form.phone" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
        </el-form-item>
      </el-form>
    </template>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { updateProfile } from '../api/auth'
import { useAuth } from '../composables/useAuth'

const { currentUser } = useAuth()
const profile = ref({ username: '', full_name: '', phone: '' })
const form = ref({ full_name: '', phone: '' })
const loading = ref(true)
const saving = ref(false)
const errorMessage = ref('')

onMounted(async () => {
  try {
    if (currentUser.value) {
      profile.value = { ...currentUser.value }
      form.value = { full_name: currentUser.value.full_name || '', phone: currentUser.value.phone || '' }
    }
  } catch (error) {
    errorMessage.value = error?.message || '加载失败'
  } finally {
    loading.value = false
  }
})

const handleSave = async () => {
  saving.value = true
  try {
    const result = await updateProfile(form.value)
    profile.value = result
    if (currentUser.value) {
      currentUser.value.full_name = result.full_name
      currentUser.value.phone = result.phone
    }
    ElMessage.success('保存成功')
  } catch (error) {
    errorMessage.value = error?.message || '保存失败，请稍后再试'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.dialog-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.profile-form {
  max-width: 400px;
}

.error-text {
  color: #f56c6c;
  font-size: 14px;
}
</style>
