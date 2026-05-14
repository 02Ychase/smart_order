<template>
  <div class="login-view">
    <div class="logo-mark">S</div>
    <h2>{{ isRegisterMode ? '创建你的账号' : '欢迎回来' }}</h2>
    <p class="subtitle">{{ isRegisterMode ? '注册即得 ¥15 新客红包' : '登录后同步购物车、地址与订单' }}</p>

    <div v-if="errorMessage" class="error-bar">{{ errorMessage }}</div>

    <div class="field">
      <label>用户名</label>
      <input v-model="form.username" data-test="username-input" placeholder="demo_user" @focus="onFocus" @blur="onBlur" />
    </div>
    <div class="field">
      <label>密码</label>
      <input v-model="form.password" type="password" data-test="password-input" placeholder="demo123456" @focus="onFocus" @blur="onBlur" />
    </div>
    <template v-if="isRegisterMode">
      <div class="field">
        <label>姓名</label>
        <input v-model="form.full_name" data-test="full-name-input" placeholder="王小明" @focus="onFocus" @blur="onBlur" />
      </div>
      <div class="field">
        <label>手机号</label>
        <input v-model="form.phone" data-test="phone-input" placeholder="138 0000 0000" @focus="onFocus" @blur="onBlur" />
      </div>
    </template>

    <button
      class="cta-btn"
      :disabled="authLoading"
      :data-test="isRegisterMode ? 'register-submit' : 'login-submit'"
      @click="isRegisterMode ? submitRegister() : submitLogin()"
    >
      <span v-if="authLoading" class="spinner" />
      {{ isRegisterMode ? '注册并登录' : '登 录' }}
    </button>

    <p class="toggle-line">
      {{ isRegisterMode ? '已有账号？' : '还没有账号？' }}
      <span class="toggle-link" data-test="switch-to-register" @click="toggleMode">{{ isRegisterMode ? '返回登录' : '立即注册 ›' }}</span>
    </p>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useAuth } from '../composables/useAuth'

const emit = defineEmits(['auth-success'])
const form = reactive({ username: '', password: '', full_name: '', phone: '' })
const isRegisterMode = ref(false)
const errorMessage = ref('')
const { authLoading, loginWithPassword, registerWithPassword } = useAuth()

const toggleMode = () => {
  isRegisterMode.value = !isRegisterMode.value
  errorMessage.value = ''
}

const onFocus = (e) => { e.target.style.borderColor = 'var(--so-yellow-deep)' }
const onBlur = (e) => { e.target.style.borderColor = 'var(--so-border-2)' }

const submitLogin = async () => {
  errorMessage.value = ''
  try {
    await loginWithPassword({ username: form.username, password: form.password })
    emit('auth-success')
  } catch (error) {
    errorMessage.value = error?.message || '登录失败，请稍后再试'
  }
}

const submitRegister = async () => {
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
.login-view {
  padding: 24px 28px 28px;
  color: var(--so-ink-1);
}

.logo-mark {
  width: 44px; height: 44px; border-radius: 10px;
  background: var(--so-yellow); color: var(--so-ink-1);
  display: flex; align-items: center; justify-content: center;
  font-size: 22px; font-weight: 800; margin-bottom: 16px;
}

h2 { margin: 0; font-size: 22px; font-weight: 800; }

.subtitle { margin: 6px 0 22px; color: var(--so-ink-4); font-size: 13px; }

.error-bar {
  padding: 8px 12px;
  background: #fef0f0;
  color: var(--so-red);
  border-radius: var(--so-r-sm);
  font-size: 13px;
  margin-bottom: 12px;
}

.field { margin-bottom: 12px; }

.field label {
  display: block;
  font-size: 13px;
  color: var(--so-ink-3);
  margin-bottom: 6px;
}

.field input {
  width: 100%; height: 40px; padding: 0 14px;
  border: 1px solid var(--so-border-2);
  border-radius: var(--so-r-sm);
  font-size: 14px;
  font-family: var(--so-font-sans);
  color: var(--so-ink-1);
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.15s;
}

.cta-btn {
  width: 100%; height: 44px; margin-top: 8px;
  background: var(--so-yellow); color: var(--so-ink-1);
  border: none; border-radius: var(--so-r-pill);
  font-size: 15px; font-weight: 800; cursor: pointer;
  display: flex; align-items: center; justify-content: center; gap: 8px;
  transition: opacity 0.15s;
}

.cta-btn:disabled { opacity: 0.6; cursor: not-allowed; }

.spinner {
  width: 16px; height: 16px;
  border: 2px solid var(--so-ink-1);
  border-top-color: transparent;
  border-radius: 50%;
  animation: mt-spin 0.8s linear infinite;
}

.toggle-line {
  margin: 16px 0 0;
  text-align: center;
  font-size: 13px;
  color: var(--so-ink-3);
}

.toggle-link {
  color: var(--so-orange);
  margin-left: 4px;
  cursor: pointer;
  font-weight: 600;
}
</style>
