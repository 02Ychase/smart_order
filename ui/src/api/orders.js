import api from './index'

export const previewCheckout = (payload) => api.post('/orders/preview', payload)
export const submitOrder = (payload) => api.post('/orders', payload)
export const mockPay = (payload) => api.post('/orders/mock-pay', payload)
export const listOrders = () => api.get('/orders')
export const getOrderDetail = (checkoutOrderId) => api.get(`/orders/${checkoutOrderId}`)
