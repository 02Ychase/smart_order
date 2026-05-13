import api from './index'

export const register = (payload) => api.post('/auth/register', payload)
export const login = (payload) => api.post('/auth/login', payload)
export const updateProfile = (payload) => api.put('/auth/me', payload)
