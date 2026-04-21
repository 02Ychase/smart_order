import api from './index'

export const listAddresses = () => api.get('/addresses')
export const createAddress = (payload) => api.post('/addresses', payload)
export const updateAddress = (addressId, payload) => api.put(`/addresses/${addressId}`, payload)
export const setDefaultAddress = (addressId) => api.post(`/addresses/${addressId}/default`)
export const deleteAddress = (addressId) => api.delete(`/addresses/${addressId}`)
