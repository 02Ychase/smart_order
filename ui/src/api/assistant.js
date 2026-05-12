import api from './index'

const formatStreamErrorDetail = (detail) => {
  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === 'string' && item.trim()) {
          return item
        }

        if (!item || typeof item !== 'object') {
          return ''
        }

        const field = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : ''
        return field ? `${field}: ${item.msg}` : item.msg || ''
      })
      .filter(Boolean)

    if (messages.length) {
      return messages.join('；')
    }
  }

  if (detail && typeof detail === 'object' && typeof detail.msg === 'string' && detail.msg.trim()) {
    return detail.msg
  }

  return '请求失败，请稍后再试'
}

const buildStreamHeaders = () => {
  const headers = {
    'Content-Type': 'application/json',
    Accept: 'text/event-stream',
  }
  const accessToken = window.localStorage.getItem('smart_order_access_token')
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`
  }
  return headers
}

const parseSseBlock = (block) => {
  const parsed = {
    event: 'message',
    data: '',
  }

  for (const line of block.split(/\r?\n/)) {
    if (line.startsWith('event:')) {
      parsed.event = line.slice(6).trim()
    } else if (line.startsWith('data:')) {
      parsed.data += `${parsed.data ? '\n' : ''}${line.slice(5).trimStart()}`
    }
  }

  return parsed
}

const getStreamErrorMessage = async (response) => {
  const body = await response.text()
  if (!body) {
    return '请求失败，请稍后再试'
  }

  try {
    const payload = JSON.parse(body)
    return formatStreamErrorDetail(payload.detail)
  } catch {
    return body
  }
}

export const chatWithAssistant = (payload) => api.post('/assistant/chat', payload)

export const streamChatWithAssistant = async (payload, handlers = {}) => {
  const response = await fetch('/api/assistant/chat/stream', {
    method: 'POST',
    headers: buildStreamHeaders(),
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const error = new Error(await getStreamErrorMessage(response))
    error.status = response.status
    throw error
  }

  if (!response.body) {
    throw new Error('当前浏览器不支持流式响应')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let finalPayload = null

  const dispatchEvent = (event) => {
    if (!event.data) {
      return
    }

    let chunk
    try {
      chunk = JSON.parse(event.data)
    } catch {
      return
    }

    const type = chunk.type || event.event
    if (type === 'token' && chunk.content) {
      handlers.onToken?.(chunk.content)
    } else if (type === 'payload' && chunk.data) {
      finalPayload = chunk.data
      handlers.onPayload?.(chunk.data)
    } else if (type === 'done') {
      handlers.onDone?.()
    }
  }

  while (true) {
    const { value, done } = await reader.read()
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done })
    const blocks = buffer.split(/\r?\n\r?\n/)
    buffer = blocks.pop() || ''

    for (const block of blocks) {
      if (block.trim()) {
        dispatchEvent(parseSseBlock(block))
      }
    }

    if (done) {
      break
    }
  }

  if (buffer.trim()) {
    dispatchEvent(parseSseBlock(buffer))
  }

  return finalPayload
}

export const getAssistantHealth = () => api.get('/assistant/health')
