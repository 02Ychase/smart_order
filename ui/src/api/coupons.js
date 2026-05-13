import api from './index'

export const listCoupons = () => api.get('/coupons')
export const claimCoupon = (code) => api.post('/coupons/claim', { code })
