import api from './index'

export const previewCheckout = (payload) => api.post('/orders/preview', payload)
export const submitOrder = (payload) => api.post('/orders', payload)
export const mockPay = (payload) => api.post('/orders/mock-pay', payload)
export const listOrders = () => api.get('/orders')
export const getOrderDetail = (checkoutOrderId) => api.get(`/orders/${checkoutOrderId}`)
export const advanceOrderStatus = (checkoutOrderId) => api.post(`/orders/${checkoutOrderId}/advance`)
export const cancelOrder = (checkoutOrderId) => api.post(`/orders/${checkoutOrderId}/cancel`)
export const submitReview = (checkoutOrderId, payload) => api.post(`/orders/${checkoutOrderId}/review`, payload)
export const getReview = (checkoutOrderId) => api.get(`/orders/${checkoutOrderId}/review`)
export const reorder = (checkoutOrderId) => api.post(`/orders/${checkoutOrderId}/reorder`)
