import api from './index'

export const listMerchants = (district) => api.get('/catalog/merchants', { params: { district } })
export const listMerchantDishes = (merchantId) => api.get(`/catalog/merchants/${merchantId}/dishes`)
