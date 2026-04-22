import api from './index'

export const getCart = () => api.get('/cart')
export const addCartItem = (payload) => api.post('/cart/items', payload)
export const removeCartItem = (dishId) => api.delete(`/cart/items/${dishId}`)
