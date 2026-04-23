import api from './index'

export const chatWithAssistant = (payload) => api.post('/assistant/chat', payload)
export const getAssistantHealth = () => api.get('/assistant/health')
