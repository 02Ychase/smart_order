import axios from 'axios'

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
    const requestError = new Error(error.response?.data?.detail || '请求失败，请稍后再试')
    requestError.status = error.response?.status
    requestError.data = error.response?.data
    requestError.payload = error.response?.data
    throw requestError
  },
)

export default api
