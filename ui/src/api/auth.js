import api from './index'

export const register = (payload) => api.post('/auth/register', payload)
export const login = (payload) => api.post('/auth/login', payload)
export const getCurrentUser = () => api.get('/auth/me')
export const updateProfile = (payload) => api.put('/auth/me', payload)
