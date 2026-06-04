import { ref } from 'vue'
import { streamChatWithAssistant } from '../api/assistant'

export function useAssistant() {
  const sessionId = ref(null)
  const draft = ref('')
  const loading = ref(false)
  const errorMessage = ref('')
  const messages = ref([
    { role: 'assistant', text: '你好，欢迎来到 smart_order。' },
    {
      role: 'assistant',
      text: '我可以根据你的口味、人数和预算，帮你推荐合适的商家和菜品，也可以协助你更快完成下单选择。',
    },
  ])
  const lastResponseType = ref(null)
  const extractedConstraints = ref([])
  const recommendations = ref([])
  const comparisons = ref([])
  const citations = ref([])
  const suggestedActions = ref([])
  const pendingAction = ref(null)
  const executedActions = ref([])

  const replaceMessageText = (index, text) => {
    messages.value[index] = { ...messages.value[index], text }
  }

  const applyAssistantResponse = (payload, assistantMessageIndex) => {
    sessionId.value = payload.session_id
    lastResponseType.value = payload.response_type
    replaceMessageText(assistantMessageIndex, payload.message)

    const constraints = payload.extracted_constraints
    if (constraints) {
      extractedConstraints.value = [
        ...(constraints.cuisine_types || []),
        ...(constraints.party_size ? [`${constraints.party_size}人`] : []),
        ...(constraints.budget_max ? [`${constraints.budget_max}元内`] : []),
        ...(constraints.exclude_allergens || []),
      ]
    }
    recommendations.value = payload.recommendations || []
    comparisons.value = payload.comparisons || []
    citations.value = payload.citations || []
    suggestedActions.value = payload.suggested_actions || []
    pendingAction.value = payload.pending_action || null
    executedActions.value = payload.executed_actions || []
  }

  const submit = async () => {
    const question = draft.value.trim()
    if (!question || loading.value) {
      return
    }

    messages.value.push({ role: 'user', text: question })
    draft.value = ''
    loading.value = true
    errorMessage.value = ''

    // Clear previous structured data before new request
    lastResponseType.value = null
    extractedConstraints.value = []
    recommendations.value = []
    comparisons.value = []
    citations.value = []
    suggestedActions.value = []
    pendingAction.value = null
    executedActions.value = []

    let assistantMessageIndex = -1

    try {
      const payload = {
        message: question,
        session_id: sessionId.value,
      }
      messages.value.push({ role: 'assistant', text: '' })
      assistantMessageIndex = messages.value.length - 1

      let responseApplied = false
      const response = await streamChatWithAssistant(payload, {
        onToken: (token) => {
          const currentText = messages.value[assistantMessageIndex]?.text || ''
          replaceMessageText(assistantMessageIndex, currentText + token)
        },
        onPayload: (payload) => {
          responseApplied = true
          applyAssistantResponse(payload, assistantMessageIndex)
        },
      })

      if (response && !responseApplied) {
        applyAssistantResponse(response, assistantMessageIndex)
      } else if (!response && !messages.value[assistantMessageIndex]?.text) {
        replaceMessageText(assistantMessageIndex, '智能助手暂时没有返回内容，请稍后再试')
      }
    } catch (error) {
      if (assistantMessageIndex >= 0 && !messages.value[assistantMessageIndex]?.text) {
        messages.value.splice(assistantMessageIndex, 1)
      }
      errorMessage.value = error?.message || '智能助手暂时不可用，请稍后再试'
    } finally {
      loading.value = false
    }
  }

  return {
    draft,
    loading,
    errorMessage,
    messages,
    lastResponseType,
    extractedConstraints,
    recommendations,
    comparisons,
    citations,
    suggestedActions,
    pendingAction,
    executedActions,
    submit,
  }
}
