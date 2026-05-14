import { onMounted, ref } from 'vue'
import { getCurrentUser, login, register } from '../api/auth'

const currentUser = ref(null)
const authLoading = ref(false)
const authInitialized = ref(false)

const applySession = (result) => {
  window.localStorage.setItem('smart_order_access_token', result.access_token)
  window.localStorage.setItem('smart_order_refresh_token', result.refresh_token)
  currentUser.value = result.user
  return result
}

const restoreSession = async () => {
  const token = window.localStorage.getItem('smart_order_access_token')
  if (!token) {
    authInitialized.value = true
    return
  }
  try {
    const user = await getCurrentUser()
    currentUser.value = user
  } catch {
    window.localStorage.removeItem('smart_order_access_token')
    window.localStorage.removeItem('smart_order_refresh_token')
    currentUser.value = null
  } finally {
    authInitialized.value = true
  }
}

export function useAuth() {
  onMounted(() => {
    if (!authInitialized.value) {
      restoreSession()
    }
  })

  const loginWithPassword = async (payload) => {
    authLoading.value = true
    try {
      const result = await login(payload)
      return applySession(result)
    } finally {
      authLoading.value = false
    }
  }

  const registerWithPassword = async (payload) => {
    authLoading.value = true
    try {
      const result = await register(payload)
      return applySession(result)
    } finally {
      authLoading.value = false
    }
  }

  const logout = () => {
    window.localStorage.removeItem('smart_order_access_token')
    window.localStorage.removeItem('smart_order_refresh_token')
    currentUser.value = null
  }

  return { currentUser, authLoading, authInitialized, loginWithPassword, registerWithPassword, logout }
}
