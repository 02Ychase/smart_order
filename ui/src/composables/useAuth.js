import { ref } from 'vue'
import { login, register } from '../api/auth'

const currentUser = ref(null)
const authLoading = ref(false)

export function useAuth() {
  const loginWithPassword = async (payload) => {
    authLoading.value = true
    try {
      const result = await login(payload)
      window.localStorage.setItem('smart_order_access_token', result.access_token)
      window.localStorage.setItem('smart_order_refresh_token', result.refresh_token)
      currentUser.value = { username: payload.username }
      return result
    } finally {
      authLoading.value = false
    }
  }

  const registerWithPassword = async (payload) => register(payload)

  const logout = () => {
    window.localStorage.removeItem('smart_order_access_token')
    window.localStorage.removeItem('smart_order_refresh_token')
    currentUser.value = null
  }

  return { currentUser, authLoading, loginWithPassword, registerWithPassword, logout }
}
