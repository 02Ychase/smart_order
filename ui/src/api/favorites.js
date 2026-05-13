import api from './index'

export const listFavorites = () => api.get('/favorites')
export const toggleFavorite = (merchantId) => api.post(`/favorites/${merchantId}/toggle`)
export const checkFavorite = (merchantId) => api.get(`/favorites/${merchantId}/status`)
