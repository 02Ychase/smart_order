<template>
  <section class="profile-view">
    <div class="modal-header">
      <h2>我的</h2>
      <button class="close-x" @click="$emit('close')">×</button>
    </div>

    <div class="modal-body mt-scroll">
      <p v-if="loading" class="state-text">加载中...</p>
      <p v-else-if="errorMessage" class="state-text state-text--error">{{ errorMessage }}</p>

      <template v-else>
        <!-- User card -->
        <div class="user-card">
          <div class="user-avatar">{{ avatarLetter }}</div>
          <div>
            <h3>{{ profile.username }}</h3>
            <p class="user-sub">普通会员 · 已注册</p>
          </div>
        </div>

        <!-- Stats -->
        <div class="stat-grid">
          <div class="stat-box">
            <p class="stat-num">{{ orderCount }}</p>
            <p class="stat-label">订单</p>
          </div>
          <div class="stat-box">
            <p class="stat-num">{{ favCount }}</p>
            <p class="stat-label">收藏</p>
          </div>
          <div class="stat-box">
            <p class="stat-num">3</p>
            <p class="stat-label">红包</p>
          </div>
        </div>

        <!-- Edit form -->
        <div v-if="editMode" class="edit-section">
          <div class="field">
            <label>姓名</label>
            <input v-model="form.full_name" />
          </div>
          <div class="field">
            <label>手机号</label>
            <input v-model="form.phone" />
          </div>
          <div class="edit-actions">
            <button class="btn-cta" :disabled="saving" @click="handleSave">保存</button>
            <button class="btn-ghost" @click="editMode = false">取消</button>
          </div>
        </div>

        <!-- Menu rows -->
        <div class="menu-row" @click="editMode = true">
          <span class="menu-icon">✏️</span>
          <span class="menu-label">编辑资料</span>
          <span class="menu-chevron">›</span>
        </div>
        <div class="menu-row" @click="$emit('open-address')">
          <span class="menu-icon">📍</span>
          <span class="menu-label">地址管理</span>
          <span class="menu-chevron">›</span>
        </div>
        <div class="menu-row">
          <span class="menu-icon">🎁</span>
          <span class="menu-label">我的红包</span>
          <span class="menu-chevron">›</span>
        </div>
        <div class="menu-row">
          <span class="menu-icon">🎟️</span>
          <span class="menu-label">优惠券</span>
          <span class="menu-chip">3</span>
          <span class="menu-chevron">›</span>
        </div>
        <div class="menu-row">
          <span class="menu-icon">💬</span>
          <span class="menu-label">客服中心</span>
          <span class="menu-chevron">›</span>
        </div>
        <div class="menu-row">
          <span class="menu-icon">ℹ️</span>
          <span class="menu-label">关于 smart_order</span>
          <span class="menu-chevron">›</span>
        </div>

        <button class="logout-btn" @click="handleLogout">退出登录</button>
      </template>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { updateProfile } from '../api/auth'
import { useAuth } from '../composables/useAuth'

const emit = defineEmits(['close', 'open-address', 'logout'])

const { currentUser } = useAuth()
const profile = ref({ username: '', full_name: '', phone: '' })
const form = ref({ full_name: '', phone: '' })
const loading = ref(true)
const saving = ref(false)
const errorMessage = ref('')
const editMode = ref(false)
const orderCount = ref(0)
const favCount = ref(0)

const avatarLetter = computed(() => (profile.value.username || 'U').slice(0, 1).toUpperCase())

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
    editMode.value = false
    ElMessage.success('保存成功')
  } catch (error) {
    errorMessage.value = error?.message || '保存失败，请稍后再试'
  } finally {
    saving.value = false
  }
}

const handleLogout = () => {
  emit('logout')
}
</script>

<style scoped>
.profile-view {
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

.close-x {
  width: 28px; height: 28px; border: none; background: transparent;
  cursor: pointer; color: var(--so-ink-4); font-size: 22px; line-height: 1; padding: 0;
}

.modal-body { flex: 1; overflow-y: auto; padding: 16px 24px 24px; }

/* User card */
.user-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 18px;
  background: linear-gradient(135deg, var(--so-yellow), var(--so-gold));
  border-radius: var(--so-r-md);
  margin-bottom: 16px;
}

.user-avatar {
  width: 52px; height: 52px; border-radius: 50%;
  background: var(--so-ink-1); color: var(--so-yellow);
  display: inline-flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 22px; flex-shrink: 0;
}

.user-card h3 { margin: 0; font-size: 18px; font-weight: 800; color: var(--so-ink-1); }
.user-sub { margin: 4px 0 0; font-size: 12px; color: rgba(0, 0, 0, 0.55); }

/* Stats */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-bottom: 18px;
}

.stat-box {
  padding: 10px 8px;
  background: var(--so-surface);
  border: 1px solid var(--so-border-1);
  border-radius: var(--so-r-sm);
  text-align: center;
}

.stat-num { margin: 0; font-size: 22px; font-weight: 800; color: var(--so-ink-1); }
.stat-label { margin: 2px 0 0; font-size: 12px; color: var(--so-ink-4); }

/* Edit form */
.edit-section {
  padding: 16px;
  background: var(--so-yellow-faint);
  border-radius: var(--so-r-md);
  margin-bottom: 16px;
}

.field { margin-bottom: 12px; }
.field label { display: block; font-size: 13px; color: var(--so-ink-3); margin-bottom: 6px; }
.field input {
  width: 100%; height: 40px; padding: 0 14px;
  border: 1px solid var(--so-border-2); border-radius: var(--so-r-sm);
  font-size: 14px; color: var(--so-ink-1); outline: none; box-sizing: border-box;
}

.edit-actions { display: flex; gap: 10px; margin-top: 14px; }

/* Menu rows */
.menu-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 6px;
  border-bottom: 1px solid var(--so-surface-line);
  cursor: pointer;
}

.menu-icon { font-size: 20px; }
.menu-label { flex: 1; font-size: 14px; color: var(--so-ink-1); font-weight: 500; }
.menu-chevron { color: var(--so-ink-4); font-size: 14px; }

.menu-chip {
  display: inline-flex; align-items: center;
  height: 18px; padding: 0 8px;
  background: var(--so-orange-soft); color: var(--so-orange);
  border-radius: var(--so-r-pill);
  font-size: 11px; font-weight: 600;
}

/* Buttons */
.btn-cta {
  height: 36px; padding: 0 22px;
  background: var(--so-orange); color: #fff;
  border: none; border-radius: var(--so-r-pill);
  font-size: 13px; font-weight: 600; cursor: pointer;
}

.btn-cta:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-ghost {
  height: 36px; padding: 0 18px;
  background: var(--so-surface); color: var(--so-ink-2);
  border: 1px solid var(--so-border-2); border-radius: var(--so-r-pill);
  font-size: 13px; cursor: pointer;
}

.logout-btn {
  width: 100%; height: 42px; margin-top: 16px;
  background: var(--so-surface); color: var(--so-red);
  border: 1px solid var(--so-border-2); border-radius: var(--so-r-pill);
  font-size: 14px; font-weight: 600; cursor: pointer;
  transition: all 0.15s;
}

.logout-btn:hover { border-color: var(--so-red); }

.state-text { padding: 60px 0; text-align: center; color: var(--so-ink-4); font-size: 14px; }
.state-text--error { color: var(--so-red); }
</style>
