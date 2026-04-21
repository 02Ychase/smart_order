import axios from 'axios'

const formatErrorDetail = (detail) => {
  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === 'string' && item.trim()) {
          return item
        }

        if (!item || typeof item !== 'object') {
          return ''
        }

        const field = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : ''
        return field ? `${field}: ${item.msg}` : item.msg || ''
      })
      .filter(Boolean)

    if (messages.length) {
      return messages.join('；')
    }
  }

  if (detail && typeof detail === 'object' && typeof detail.msg === 'string' && detail.msg.trim()) {
    return detail.msg
  }

  return '请求失败，请稍后再试'
}

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  const accessToken = window.localStorage.getItem('smart_order_access_token')
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const requestError = new Error(formatErrorDetail(error.response?.data?.detail))
    requestError.status = error.response?.status
    requestError.data = error.response?.data
    requestError.payload = error.response?.data
    throw requestError
  },
)

export default api
