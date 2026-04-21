<template>
  <div class="login-dialog-view">
    <p class="eyebrow">欢迎登录 smart_order</p>
    <h2>{{ isRegisterMode ? '创建你的 smart_order 账号' : '智能点餐，从这里开始' }}</h2>
    <p class="description">{{ isRegisterMode ? '注册后即可使用本地账号保存地址、订单与购物车。' : '登录后即可同步购物车、地址与订单状态。' }}</p>
    <p v-if="errorMessage" class="feedback error">{{ errorMessage }}</p>
    <p v-else-if="successMessage" class="feedback success">{{ successMessage }}</p>
    <el-form @submit.prevent>
      <el-form-item label="用户名"><el-input v-model="form.username" data-test="username-input" /></el-form-item>
      <el-form-item label="密码"><el-input v-model="form.password" type="password" show-password data-test="password-input" /></el-form-item>
      <template v-if="isRegisterMode">
        <el-form-item label="姓名"><el-input v-model="form.full_name" data-test="full-name-input" /></el-form-item>
        <el-form-item label="手机号"><el-input v-model="form.phone" data-test="phone-input" /></el-form-item>
      </template>
      <div class="actions">
        <el-button v-if="isRegisterMode" :loading="authLoading" data-test="register-submit" type="primary" @click="submitRegister">注册</el-button>
        <el-button v-else type="primary" :loading="authLoading" data-test="login-submit" @click="submitLogin">登录</el-button>
        <el-button text data-test="switch-to-register" @click="toggleMode">{{ isRegisterMode ? '返回登录' : '去注册' }}</el-button>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useAuth } from '../composables/useAuth'

const emit = defineEmits(['auth-success'])
const form = reactive({ username: '', password: '', full_name: '', phone: '' })
const isRegisterMode = ref(false)
const successMessage = ref('')
const errorMessage = ref('')
const { authLoading, loginWithPassword, registerWithPassword } = useAuth()

const toggleMode = () => {
  isRegisterMode.value = !isRegisterMode.value
  successMessage.value = ''
  errorMessage.value = ''
}

const submitLogin = async () => {
  successMessage.value = ''
  errorMessage.value = ''
  try {
    await loginWithPassword({ username: form.username, password: form.password })
    emit('auth-success')
  } catch (error) {
    errorMessage.value = error?.message || '登录失败，请稍后再试'
  }
}

const submitRegister = async () => {
  successMessage.value = ''
  errorMessage.value = ''
  try {
    await registerWithPassword({
      username: form.username,
      password: form.password,
      full_name: form.full_name,
      phone: form.phone,
    })
    emit('auth-success')
  } catch (error) {
    errorMessage.value = error?.message || '注册失败，请稍后再试'
  }
}
</script>

<style scoped>
.actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.feedback {
  margin: 0 0 12px;
}

.success {
  color: #1f8f55;
}

.error {
  color: #c24141;
}
</style>
