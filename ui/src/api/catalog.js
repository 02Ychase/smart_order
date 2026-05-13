import api from './index'

export const listMerchants = (district) => api.get('/catalog/merchants', { params: { district } })
export const getMerchant = (merchantId) => api.get(`/catalog/merchants/${merchantId}`)
export const listMerchantDishes = (merchantId) => api.get(`/catalog/merchants/${merchantId}/dishes`)
export const searchCatalog = (keyword) => api.get('/catalog/search', { params: { keyword } })
